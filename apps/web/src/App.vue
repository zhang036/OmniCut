<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'

type AssistantOption = {
  id: string
  label: string
  description: string
}

type AssistantMessage = {
  role: 'user' | 'assistant'
  content: string
  reasoning?: string
  reasoningOpen?: boolean
  phase?: 'thinking' | 'answering' | 'done'
}

type ResizeTarget = 'project' | 'assistant'

type ShotDraft = {
  id: string
  title: string
  visualDescription: string
  voiceover: string
  onScreenText: string
  durationSeconds?: number
  sortOrder: number
}

type ChapterDraft = {
  id: string
  title: string
  sortOrder: number
  shots: ShotDraft[]
}

type CreateChapterOperation = {
  id: string
  type: 'create_chapter'
  tempId: string
  title: string
  sortOrder: number
}

type CreateShotOperation = {
  id: string
  type: 'create_shot'
  chapterTempId: string
  title: string
  visualDescription: string
  voiceover: string
  onScreenText: string
  durationSeconds: number
  sortOrder: number
}

type DraftOperation = CreateChapterOperation | CreateShotOperation

type ConversationHistoryItem = {
  id: number
  title: string
  model: string
  reasoning_mode: string
  last_message_preview: string | null
  message_count: number
  is_pinned: number
  updated_at: string
}

type AssistantHistoryMessage = {
  role: 'user' | 'assistant'
  content: string
  reasoning_content: string | null
  sequence: number
}

type ProjectHistoryItem = {
  id: number
  title: string
  description: string | null
  status: string
  chapter_count: number
  shot_count: number
  is_pinned: number
  last_opened_at: string | null
  updated_at: string
}

type ProjectDetailShot = {
  id: number
  title: string
  visual_description: string | null
  voiceover: string | null
  on_screen_text: string | null
  duration_seconds: number | null
  sort_order: number
}

type ProjectDetailChapter = {
  id: number
  title: string
  summary: string | null
  sort_order: number
  shots: ProjectDetailShot[]
}

type ProjectDetail = {
  id: number
  title: string
  description: string | null
  status: string
  chapter_count: number
  shot_count: number
  chapters: ProjectDetailChapter[]
}

const models = ref<AssistantOption[]>([
  { id: 'deepseek-v4-pro', label: 'DeepSeek V4 Pro', description: '更强的复杂创作和推理能力。' },
  { id: 'deepseek-v4-flash', label: 'DeepSeek V4 Flash', description: '更快的轻量任务模型。' },
])
const reasoningModes = ref<AssistantOption[]>([
  { id: 'disabled', label: '非思考', description: '关闭思考模式。' },
  { id: 'high', label: 'High', description: '标准思考强度。' },
  { id: 'max', label: 'Max', description: '最高思考强度。' },
])
const selectedModel = ref('deepseek-v4-flash')
const selectedReasoningMode = ref('high')
const sessionId = ref<number | null>(null)
const activeProjectId = ref<number | null>(null)
const input = ref('')
const isStreaming = ref(false)
const isSavingDraft = ref(false)
const cacheUsage = ref({ hit: 0, miss: 0 })
const chatThread = ref<HTMLElement | null>(null)
const streamDelayMs = 12
const streamQueues = new WeakMap<AssistantMessage, Promise<void>>()
const projectPanelWidth = ref(280)
const assistantPanelWidth = ref(420)
const activeResizeTarget = ref<ResizeTarget | null>(null)
const minProjectPanelWidth = 190
const minAssistantPanelWidth = 320
const minEditorPanelWidth = 420
const activityRailWidth = 64
const resizeHandleWidth = 8
let resizeStartX = 0
let resizeStartProjectWidth = 0
let resizeStartAssistantWidth = 0
let projectSearchTimer: number | undefined
let conversationSearchTimer: number | undefined
const projectSearch = ref('')
const conversationSearch = ref('')
const projectHistory = ref<ProjectHistoryItem[]>([])
const conversationHistory = ref<ConversationHistoryItem[]>([])
const messages = ref<AssistantMessage[]>([
  {
    role: 'assistant',
    content: '描述你的产品、受众和视频目标，我会帮你生成可编辑的分镜草稿。',
    reasoningOpen: false,
  },
])
const projectDraft = reactive<{
  title: string
  description: string
  chapters: ChapterDraft[]
}>({
  title: '未命名项目',
  description: '',
  chapters: [],
})
const selectedShotId = ref('')
const pendingDraftOperations = ref<DraftOperation[]>([])

const selectedModelLabel = computed(() => models.value.find((model) => model.id === selectedModel.value)?.label ?? selectedModel.value)
const selectedReasoningLabel = computed(() => reasoningModes.value.find((mode) => mode.id === selectedReasoningMode.value)?.label ?? selectedReasoningMode.value)
const workspaceGridStyle = computed(() => ({
  gridTemplateColumns: `${activityRailWidth}px ${projectPanelWidth.value}px ${resizeHandleWidth}px minmax(${minEditorPanelWidth}px, 1fr) ${resizeHandleWidth}px ${assistantPanelWidth.value}px`,
}))
const pendingChapterOperations = computed(() => pendingDraftOperations.value.filter((operation): operation is CreateChapterOperation => operation.type === 'create_chapter'))
const pendingShotOperations = computed(() => pendingDraftOperations.value.filter((operation): operation is CreateShotOperation => operation.type === 'create_shot'))
const totalShotCount = computed(() => projectDraft.chapters.reduce((total, chapter) => total + chapter.shots.length, 0))
const activeProject = computed(() => projectHistory.value.find((project) => project.id === activeProjectId.value))
const activeConversation = computed(() => conversationHistory.value.find((conversation) => conversation.id === sessionId.value))

onMounted(async () => {
  await Promise.all([loadAssistantOptions(), loadProjectHistory(), loadConversationHistory()])
  if (projectHistory.value[0]) {
    await loadProject(projectHistory.value[0].id)
  }
  if (conversationHistory.value[0]) {
    await loadConversation(conversationHistory.value[0].id)
  }
})

onUnmounted(() => {
  stopPanelResize()
  window.clearTimeout(projectSearchTimer)
  window.clearTimeout(conversationSearchTimer)
})

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), Math.max(min, max))
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json() as Promise<T>
}

function defaultAssistantMessages(): AssistantMessage[] {
  return [
    {
      role: 'assistant',
      content: '描述你的产品、受众和视频目标，我会帮你生成可编辑的分镜草稿。',
      reasoningOpen: false,
    },
  ]
}

function formatHistoryTime(value: string | null) {
  if (!value) {
    return '未打开'
  }
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadAssistantOptions() {
  const data = await fetchJson<{ models: AssistantOption[]; reasoning_modes: AssistantOption[] }>('/api/assistant/options')
  models.value = data.models
  reasoningModes.value = data.reasoning_modes
}

async function loadProjectHistory() {
  const search = projectSearch.value.trim()
  const query = search ? `?q=${encodeURIComponent(search)}` : ''
  const data = await fetchJson<{ items: ProjectHistoryItem[] }>(`/api/projects${query}`)
  projectHistory.value = data.items
}

function scheduleProjectSearch() {
  window.clearTimeout(projectSearchTimer)
  projectSearchTimer = window.setTimeout(() => {
    void loadProjectHistory()
  }, 220)
}

function updateProjectDraft(detail: ProjectDetail) {
  projectDraft.title = detail.title
  projectDraft.description = detail.description ?? ''
  projectDraft.chapters.splice(
    0,
    projectDraft.chapters.length,
    ...detail.chapters.map((chapter) => ({
      id: String(chapter.id),
      title: chapter.title,
      sortOrder: chapter.sort_order,
      shots: chapter.shots.map((shot) => ({
        id: String(shot.id),
        title: shot.title,
        visualDescription: shot.visual_description ?? '',
        voiceover: shot.voiceover ?? '',
        onScreenText: shot.on_screen_text ?? '',
        durationSeconds: shot.duration_seconds ?? 0,
        sortOrder: shot.sort_order,
      })),
    })),
  )
  selectedShotId.value = projectDraft.chapters[0]?.shots[0]?.id ?? ''
}

function clearProjectDraft() {
  activeProjectId.value = null
  projectDraft.title = '未命名项目'
  projectDraft.description = ''
  projectDraft.chapters.splice(0, projectDraft.chapters.length)
  selectedShotId.value = ''
}

async function loadProject(projectId: number) {
  const detail = await fetchJson<ProjectDetail>(`/api/projects/${projectId}`)
  activeProjectId.value = projectId
  updateProjectDraft(detail)
  await fetch(`/api/projects/${projectId}/open`, { method: 'POST' })
}

async function createProject() {
  const project = await fetchJson<ProjectHistoryItem>('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: '未命名项目', description: '' }),
  })
  await loadProjectHistory()
  await loadProject(project.id)
}

async function renameActiveProject() {
  if (!activeProjectId.value) {
    return
  }
  const title = window.prompt('项目名称', projectDraft.title)?.trim()
  if (!title) {
    return
  }
  await fetchJson<ProjectHistoryItem>(`/api/projects/${activeProjectId.value}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  projectDraft.title = title
  await loadProjectHistory()
}

async function deleteActiveProject() {
  if (!activeProjectId.value || !window.confirm('确认删除当前项目历史？')) {
    return
  }
  await fetchJson<{ ok: boolean }>(`/api/projects/${activeProjectId.value}`, { method: 'DELETE' })
  await loadProjectHistory()
  const nextProject = projectHistory.value[0]
  if (nextProject) {
    await loadProject(nextProject.id)
  } else {
    clearProjectDraft()
  }
}

async function saveProjectDraft() {
  isSavingDraft.value = true
  try {
    let projectId = activeProjectId.value
    if (!projectId) {
      const project = await fetchJson<ProjectHistoryItem>('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: projectDraft.title.trim() || '未命名项目', description: projectDraft.description }),
      })
      projectId = project.id
      activeProjectId.value = project.id
    }
    await fetchJson<ProjectHistoryItem>(`/api/projects/${projectId}/draft`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: projectDraft.title.trim() || '未命名项目',
        description: projectDraft.description,
        chapters: projectDraft.chapters.map((chapter, chapterIndex) => ({
          title: chapter.title.trim() || `章节 ${chapterIndex + 1}`,
          sort_order: chapter.sortOrder || chapterIndex + 1,
          shots: chapter.shots.map((shot, shotIndex) => ({
            title: shot.title.trim() || `镜头 ${shotIndex + 1}`,
            visual_description: shot.visualDescription,
            voiceover: shot.voiceover,
            on_screen_text: shot.onScreenText,
            duration_seconds: shot.durationSeconds ?? 0,
            sort_order: shot.sortOrder || shotIndex + 1,
          })),
        })),
      }),
    })
    await loadProjectHistory()
  } finally {
    isSavingDraft.value = false
  }
}

async function createProjectSnapshot() {
  await saveProjectDraft()
  if (!activeProjectId.value) {
    return
  }
  const title = window.prompt('快照名称', `${projectDraft.title} 快照`)?.trim()
  if (!title) {
    return
  }
  await fetchJson(`/api/projects/${activeProjectId.value}/snapshots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, summary: '手动保存的项目版本', snapshot_type: 'manual' }),
  })
}

async function loadConversationHistory() {
  const search = conversationSearch.value.trim()
  const query = search ? `?q=${encodeURIComponent(search)}` : ''
  const data = await fetchJson<{ items: ConversationHistoryItem[] }>(`/api/assistant/sessions${query}`)
  conversationHistory.value = data.items
}

function scheduleConversationSearch() {
  window.clearTimeout(conversationSearchTimer)
  conversationSearchTimer = window.setTimeout(() => {
    void loadConversationHistory()
  }, 220)
}

async function createConversation() {
  const conversation = await fetchJson<ConversationHistoryItem>('/api/assistant/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: '新对话', model: selectedModel.value, reasoning_mode: selectedReasoningMode.value }),
  })
  sessionId.value = conversation.id
  messages.value = defaultAssistantMessages()
  await loadConversationHistory()
}

async function loadConversation(conversationId: number) {
  const conversation = conversationHistory.value.find((item) => item.id === conversationId)
  if (conversation) {
    selectedModel.value = conversation.model
    selectedReasoningMode.value = conversation.reasoning_mode
  }
  sessionId.value = conversationId
  const data = await fetchJson<{ items: AssistantHistoryMessage[] }>(`/api/assistant/sessions/${conversationId}/messages`)
  messages.value = data.items.length
    ? data.items
        .sort((left, right) => left.sequence - right.sequence)
        .map((message) => ({
          role: message.role,
          content: message.content,
          reasoning: message.reasoning_content ?? '',
          reasoningOpen: false,
          phase: 'done',
        }))
    : defaultAssistantMessages()
  await scrollChatToBottom()
}

async function renameActiveConversation() {
  if (!sessionId.value) {
    return
  }
  const title = window.prompt('对话名称', activeConversation.value?.title ?? '新对话')?.trim()
  if (!title) {
    return
  }
  await fetchJson<ConversationHistoryItem>(`/api/assistant/sessions/${sessionId.value}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  await loadConversationHistory()
}

async function deleteActiveConversation() {
  if (!sessionId.value || !window.confirm('确认删除当前对话历史？')) {
    return
  }
  await fetchJson<{ ok: boolean }>(`/api/assistant/sessions/${sessionId.value}`, { method: 'DELETE' })
  sessionId.value = null
  messages.value = defaultAssistantMessages()
  await loadConversationHistory()
  if (conversationHistory.value[0]) {
    await loadConversation(conversationHistory.value[0].id)
  }
}

function maxProjectPanelWidth() {
  return window.innerWidth - activityRailWidth - resizeHandleWidth * 2 - assistantPanelWidth.value - minEditorPanelWidth
}

function maxAssistantPanelWidth() {
  return window.innerWidth - activityRailWidth - resizeHandleWidth * 2 - projectPanelWidth.value - minEditorPanelWidth
}

function startPanelResize(target: ResizeTarget, event: PointerEvent) {
  activeResizeTarget.value = target
  resizeStartX = event.clientX
  resizeStartProjectWidth = projectPanelWidth.value
  resizeStartAssistantWidth = assistantPanelWidth.value
  window.addEventListener('pointermove', resizePanel)
  window.addEventListener('pointerup', stopPanelResize)
  event.preventDefault()
}

function resizePanel(event: PointerEvent) {
  const deltaX = event.clientX - resizeStartX
  if (activeResizeTarget.value === 'project') {
    projectPanelWidth.value = clamp(resizeStartProjectWidth + deltaX, minProjectPanelWidth, maxProjectPanelWidth())
  }
  if (activeResizeTarget.value === 'assistant') {
    assistantPanelWidth.value = clamp(resizeStartAssistantWidth - deltaX, minAssistantPanelWidth, maxAssistantPanelWidth())
  }
}

function stopPanelResize() {
  activeResizeTarget.value = null
  window.removeEventListener('pointermove', resizePanel)
  window.removeEventListener('pointerup', stopPanelResize)
}

function handleResizeKeydown(target: ResizeTarget, event: KeyboardEvent) {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') {
    return
  }
  const step = event.shiftKey ? 40 : 16
  const direction = event.key === 'ArrowRight' ? 1 : -1
  if (target === 'project') {
    projectPanelWidth.value = clamp(projectPanelWidth.value + direction * step, minProjectPanelWidth, maxProjectPanelWidth())
  }
  if (target === 'assistant') {
    assistantPanelWidth.value = clamp(assistantPanelWidth.value - direction * step, minAssistantPanelWidth, maxAssistantPanelWidth())
  }
  event.preventDefault()
}

async function selectShot(shotId: string) {
  selectedShotId.value = shotId
  await nextTick()
  document.getElementById(`shot-card-${shotId}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function applyPendingDraftOperations() {
  const chapterIdMap = new Map<string, string>()
  for (const operation of pendingChapterOperations.value) {
    const chapterId = `chapter-ai-${Date.now()}-${operation.sortOrder}`
    chapterIdMap.set(operation.tempId, chapterId)
    projectDraft.chapters.push({
      id: chapterId,
      title: operation.title,
      sortOrder: projectDraft.chapters.length + operation.sortOrder,
      shots: [],
    })
  }
  for (const operation of pendingShotOperations.value) {
    const chapterId = chapterIdMap.get(operation.chapterTempId)
    const chapter = projectDraft.chapters.find((item) => item.id === chapterId)
    if (!chapter) {
      continue
    }
    chapter.shots.push({
      id: `shot-ai-${Date.now()}-${operation.sortOrder}`,
      title: operation.title,
      visualDescription: operation.visualDescription,
      voiceover: operation.voiceover,
      onScreenText: operation.onScreenText,
      durationSeconds: operation.durationSeconds,
      sortOrder: operation.sortOrder,
    })
  }
  const firstCreatedChapter = projectDraft.chapters[projectDraft.chapters.length - pendingChapterOperations.value.length]
  const firstCreatedShot = firstCreatedChapter?.shots[0]
  pendingDraftOperations.value = []
  if (firstCreatedShot) {
    void selectShot(firstCreatedShot.id)
  }
}

function discardPendingDraftOperations() {
  pendingDraftOperations.value = []
}

async function sendMessage() {
  const message = input.value.trim()
  if (!message || isStreaming.value) {
    return
  }
  messages.value.push({ role: 'user', content: message })
  const assistantMessage = reactive<AssistantMessage>({ role: 'assistant', content: '', reasoning: '', reasoningOpen: true, phase: 'thinking' })
  messages.value.push(assistantMessage)
  input.value = ''
  isStreaming.value = true
  await scrollChatToBottom()

  try {
    const response = await fetch('/api/assistant/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: sessionId.value,
        model: selectedModel.value,
        reasoning_mode: selectedReasoningMode.value,
      }),
    })
    if (!response.ok || !response.body) {
      assistantMessage.content = '请求失败，请确认后端服务已经启动。'
      return
    }
    await readSseStream(response.body, assistantMessage)
  } finally {
    await streamQueues.get(assistantMessage)
    isStreaming.value = false
    await loadConversationHistory()
  }
}

function handleComposerKeydown(event: KeyboardEvent) {
  if (event.isComposing || event.shiftKey || event.key !== 'Enter') {
    return
  }
  event.preventDefault()
  void sendMessage()
}

async function readSseStream(body: ReadableStream<Uint8Array>, assistantMessage: AssistantMessage) {
  const reader = body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      buffer += decoder.decode()
      if (buffer.trim()) {
        await handleSseEvent(buffer, assistantMessage)
      }
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split(/\r?\n\r?\n/)
    buffer = events.pop() ?? ''
    for (const rawEvent of events) {
      await handleSseEvent(rawEvent, assistantMessage)
    }
  }
}

async function scrollChatToBottom() {
  await nextTick()
  if (chatThread.value) {
    chatThread.value.scrollTop = chatThread.value.scrollHeight
  }
}

async function appendStreamingText(applyChunk: (chunk: string) => void, text: string) {
  for (const char of text) {
    applyChunk(char)
    await scrollChatToBottom()
    await new Promise<void>((resolve) => window.setTimeout(resolve, streamDelayMs))
  }
}

function enqueueStreamingText(assistantMessage: AssistantMessage, applyChunk: (chunk: string) => void, text: string) {
  const previous = streamQueues.get(assistantMessage) ?? Promise.resolve()
  const next = previous.then(() => appendStreamingText(applyChunk, text))
  streamQueues.set(assistantMessage, next)
}

async function handleSseEvent(rawEvent: string, assistantMessage: AssistantMessage) {
  const lines = rawEvent.split(/\r?\n/)
  const event = lines.find((line) => line.startsWith('event:'))?.replace(/^event:\s*/, '').trim()
  const dataText = lines
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.replace(/^data:\s*/, ''))
    .join('\n')
  if (!event || !dataText) {
    return
  }
  const data = JSON.parse(dataText)
  if (event === 'session') {
    sessionId.value = data.session_id
  }
  if (event === 'reasoning') {
    enqueueStreamingText(assistantMessage, (chunk) => {
      assistantMessage.reasoning = `${assistantMessage.reasoning ?? ''}${chunk}`
    }, data.delta)
  }
  if (event === 'content') {
    assistantMessage.phase = 'answering'
    enqueueStreamingText(assistantMessage, (chunk) => {
      assistantMessage.content = `${assistantMessage.content}${chunk}`
    }, data.delta)
  }
  if (event === 'usage') {
    cacheUsage.value = {
      hit: data.prompt_cache_hit_tokens ?? 0,
      miss: data.prompt_cache_miss_tokens ?? 0,
    }
  }
  if (event === 'error') {
    assistantMessage.phase = 'done'
    assistantMessage.content = `调用模型失败：${data.message}`
    await scrollChatToBottom()
  }
  if (event === 'done') {
    assistantMessage.phase = 'done'
  }
}

function routeAssistantWheel(event: WheelEvent) {
  const target = event.target as HTMLElement | null
  if (target?.closest('textarea, select, .reasoning-box')) {
    return
  }
  if (chatThread.value) {
    chatThread.value.scrollTop += event.deltaY
    event.preventDefault()
  }
}
</script>

<template>
  <main class="workspace-shell" :class="{ resizing: activeResizeTarget }" :style="workspaceGridStyle">
    <section class="activity-rail">
      <div class="brand-mark">OC</div>
      <div class="rail-dot active"></div>
      <div class="rail-dot"></div>
      <div class="rail-dot"></div>
    </section>

    <aside class="project-tree">
      <div class="panel-block">
        <div class="history-header">
          <div>
            <div class="panel-kicker">Project History</div>
            <h1>项目历史</h1>
          </div>
          <button type="button" class="mini-action" @click="createProject">新建</button>
        </div>
        <input v-model="projectSearch" class="history-search" placeholder="搜索项目" @input="scheduleProjectSearch" />
        <div class="history-list">
          <button
            v-for="project in projectHistory"
            :key="project.id"
            type="button"
            :class="['history-row', { active: activeProjectId === project.id }]"
            @click="loadProject(project.id)"
          >
            <span>{{ project.title }}</span>
            <small>{{ project.chapter_count }} 章 / {{ project.shot_count }} 镜头</small>
            <em>{{ formatHistoryTime(project.last_opened_at || project.updated_at) }}</em>
          </button>
          <div v-if="!projectHistory.length" class="empty-state">还没有项目历史</div>
        </div>
        <div class="history-actions" v-if="activeProjectId">
          <button type="button" @click="renameActiveProject">重命名</button>
          <button type="button" @click="deleteActiveProject">删除</button>
        </div>
      </div>

      <div class="panel-block outline-block">
        <div class="panel-kicker">Project Draft</div>
        <h1>{{ projectDraft.title }}</h1>
        <div v-for="chapter in projectDraft.chapters" :key="chapter.id" class="tree-group">
          <div class="tree-title">第{{ chapter.sortOrder }}章：{{ chapter.title }}</div>
          <button
            v-for="shot in chapter.shots"
            :key="shot.id"
            :class="['tree-shot', { active: selectedShotId === shot.id }]"
            @click="selectShot(shot.id)"
          >
            镜头 {{ String(shot.sortOrder).padStart(2, '0') }} · {{ shot.title }}
          </button>
        </div>
        <div v-if="!projectDraft.chapters.length" class="empty-state">选择或新建项目后开始编辑分镜</div>
        <div v-if="pendingDraftOperations.length" class="tree-group pending-tree-group">
          <div class="tree-title">AI 待应用</div>
          <div v-for="operation in pendingShotOperations" :key="operation.id" class="tree-shot pending">
            + {{ operation.title }}
          </div>
        </div>
      </div>
    </aside>

    <div
      :class="['panel-resizer', { active: activeResizeTarget === 'project' }]"
      role="separator"
      aria-label="调整项目栏宽度"
      aria-orientation="vertical"
      tabindex="0"
      @pointerdown="startPanelResize('project', $event)"
      @keydown="handleResizeKeydown('project', $event)"
    ></div>

    <section class="draft-editor">
      <div class="editor-header">
        <div>
          <div class="panel-kicker">Storyboard Document</div>
          <h2>{{ projectDraft.title }}</h2>
          <p v-if="activeProject" class="editor-subtitle">上次更新：{{ formatHistoryTime(activeProject.updated_at) }}</p>
        </div>
        <div class="editor-actions">
          <span class="status-pill">{{ projectDraft.chapters.length }} 章 / {{ totalShotCount }} 镜头</span>
          <button type="button" class="ghost-button" :disabled="isSavingDraft" @click="createProjectSnapshot">保存快照</button>
          <button type="button" class="apply-button" :disabled="isSavingDraft" @click="saveProjectDraft">{{ isSavingDraft ? '保存中' : '保存草稿' }}</button>
        </div>
      </div>

      <div v-if="pendingDraftOperations.length" class="pending-draft-panel">
        <div class="pending-draft-header">
          <div>
            <div class="panel-kicker">AI Preview</div>
            <h3>生成了 {{ pendingChapterOperations.length }} 个章节 / {{ pendingShotOperations.length }} 个镜头</h3>
          </div>
          <div class="pending-actions">
            <button type="button" class="ghost-button" @click="discardPendingDraftOperations">放弃</button>
            <button type="button" class="apply-button" @click="applyPendingDraftOperations">应用到草稿</button>
          </div>
        </div>
        <div class="pending-shot-grid">
          <article v-for="operation in pendingShotOperations" :key="operation.id" class="pending-shot-card">
            <strong>{{ operation.title }}</strong>
            <span>{{ operation.durationSeconds }}s</span>
            <p>{{ operation.visualDescription }}</p>
          </article>
        </div>
      </div>

      <div v-if="!projectDraft.chapters.length" class="empty-document">
        <div class="panel-kicker">Empty Draft</div>
        <h3>当前项目还没有章节和镜头</h3>
        <p>你可以在右侧和 AI 对话生成草稿，或直接保存一个空项目历史。</p>
      </div>

      <div v-else class="storyboard-document">
        <section v-for="chapter in projectDraft.chapters" :key="chapter.id" class="chapter-section">
          <div class="chapter-heading">
            <span>第{{ chapter.sortOrder }}章</span>
            <h3>{{ chapter.title }}</h3>
          </div>
          <article
            v-for="shot in chapter.shots"
            :id="`shot-card-${shot.id}`"
            :key="shot.id"
            :class="['shot-card', 'storyboard-shot', { active: selectedShotId === shot.id }]"
          >
            <div class="shot-card-header">
              <div>
                <span class="shot-index">镜头 {{ String(shot.sortOrder).padStart(2, '0') }}</span>
                <h4>{{ shot.title }}</h4>
              </div>
              <span class="shot-duration">{{ shot.durationSeconds ?? 0 }}s</span>
            </div>
            <label>画面描述</label>
            <textarea v-model="shot.visualDescription" placeholder="填写或让 AI 生成这个镜头的画面描述" />
            <div class="two-column">
              <div>
                <label>旁白</label>
                <textarea v-model="shot.voiceover" placeholder="填写旁白" />
              </div>
              <div>
                <label>屏幕文字</label>
                <textarea v-model="shot.onScreenText" placeholder="填写屏幕文字" />
              </div>
            </div>
          </article>
        </section>
      </div>
    </section>

    <div
      :class="['panel-resizer', { active: activeResizeTarget === 'assistant' }]"
      role="separator"
      aria-label="调整助手栏宽度"
      aria-orientation="vertical"
      tabindex="0"
      @pointerdown="startPanelResize('assistant', $event)"
      @keydown="handleResizeKeydown('assistant', $event)"
    ></div>

    <aside class="assistant-panel" @wheel="routeAssistantWheel">
      <div class="assistant-topbar">
        <div>
          <div class="panel-kicker">Omni Assistant</div>
          <h2>流式创作助手</h2>
        </div>
        <button type="button" class="mini-action" @click="createConversation">新对话</button>
      </div>

      <div class="conversation-history-panel">
        <div class="history-header compact">
          <div>
            <div class="panel-kicker">Conversation History</div>
            <strong>{{ activeConversation?.title ?? '未选择对话' }}</strong>
          </div>
          <div class="history-actions inline" v-if="sessionId">
            <button type="button" @click="renameActiveConversation">改名</button>
            <button type="button" @click="deleteActiveConversation">删除</button>
          </div>
        </div>
        <input v-model="conversationSearch" class="history-search" placeholder="搜索对话" @input="scheduleConversationSearch" />
        <div class="conversation-list">
          <button
            v-for="conversation in conversationHistory"
            :key="conversation.id"
            type="button"
            :class="['history-row', { active: sessionId === conversation.id }]"
            @click="loadConversation(conversation.id)"
          >
            <span>{{ conversation.title }}</span>
            <small>{{ conversation.last_message_preview || '暂无消息' }}</small>
            <em>{{ conversation.message_count }} 条 · {{ formatHistoryTime(conversation.updated_at) }}</em>
          </button>
          <div v-if="!conversationHistory.length" class="empty-state">还没有对话历史</div>
        </div>
      </div>

      <div class="assistant-meta">
        <span>{{ selectedModelLabel }} · {{ selectedReasoningLabel }}</span>
        <span>Cache hit {{ cacheUsage.hit }} / miss {{ cacheUsage.miss }}</span>
      </div>

      <div ref="chatThread" class="chat-thread">
        <article v-for="(message, index) in messages" :key="index" :class="['chat-bubble', message.role]">
          <div class="bubble-header">
            <span>{{ message.role === 'assistant' ? 'OmniCut' : 'You' }}</span>
          </div>
          <div v-if="message.role === 'assistant' && (message.reasoning || message.phase === 'thinking')" class="reasoning-card">
            <button class="reasoning-toggle" @click="message.reasoningOpen = !message.reasoningOpen">
              <span>{{ message.reasoningOpen ? '收起思考链' : '展开思考链' }}</span>
              <small>{{ message.reasoning?.length ?? 0 }} chars</small>
            </button>
            <pre v-if="message.reasoningOpen" class="reasoning-box">{{ message.reasoning || '等待 DeepSeek 返回 reasoning_content…' }}</pre>
          </div>
          <p v-if="message.content" class="answer-text">{{ message.content }}</p>
          <div v-else-if="message.role === 'assistant' && message.phase === 'thinking'" class="stream-state">
            正文等待中
          </div>
        </article>
      </div>

      <form class="composer" @submit.prevent="sendMessage">
        <textarea v-model="input" placeholder="输入你的创作需求，例如：把这个产品功能拆成 5 个镜头" @keydown="handleComposerKeydown" />
        <div class="composer-toolbar">
          <div class="compact-selects">
            <select v-model="selectedModel" aria-label="选择模型">
              <option v-for="model in models" :key="model.id" :value="model.id">{{ model.label }}</option>
            </select>
            <select v-model="selectedReasoningMode" aria-label="选择思考程度">
              <option v-for="mode in reasoningModes" :key="mode.id" :value="mode.id">{{ mode.label }}</option>
            </select>
          </div>
          <button :disabled="isStreaming">{{ isStreaming ? '生成中' : '发送' }}</button>
        </div>
      </form>
    </aside>
  </main>
</template>
