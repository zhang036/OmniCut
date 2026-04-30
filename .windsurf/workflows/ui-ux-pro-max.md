---
description: Use UI UX Pro Max design intelligence for frontend redesign and UI review
---

# UI UX Pro Max Workflow

Use this workflow when the user asks to use UI UX Pro Max, redesign UI, improve frontend visuals, review UX, or create a design system for OmniCut.

## Trigger phrases

The user may invoke this workflow with natural language such as:

- "用 UI UX Pro Max 重新设计前端"
- "使用 ui-ux-pro-max 优化助手栏"
- "按 UI UX Pro Max 的建议改这个页面"
- "调用 UI UX Pro Max 生成设计系统"
- "/ui-ux-pro-max"

## Required behavior

1. Treat `.windsurf/skills/ui-ux-pro-max/SKILL.md` as the source of instructions.
2. Start with a design-system query before editing UI code.
3. Supplement with focused searches for style, UX, web accessibility, and Vue implementation.
4. Synthesize the results into a concise design direction.
5. Apply changes to the relevant frontend files.
6. Do not create extra documentation unless the user explicitly asks.
7. Do not run production builds after every small UI change. Prefer hot reload during iteration.

## Commands

Run these commands from the project root.

### Generate OmniCut design system

```powershell
python .windsurf\skills\ui-ux-pro-max\scripts\search.py "video editor AI assistant dark productivity workspace Vue" --design-system -p "OmniCut"
```

### Search AI assistant style guidance

```powershell
python .windsurf\skills\ui-ux-pro-max\scripts\search.py "AI native streaming text chat input context cards" --domain style -n 5
```

### Search UX guidance

```powershell
python .windsurf\skills\ui-ux-pro-max\scripts\search.py "dark chat assistant input streaming accessibility" --domain ux -n 5
```

### Search web accessibility guidance

```powershell
python .windsurf\skills\ui-ux-pro-max\scripts\search.py "keyboard focus scroll chat accessibility streaming" --domain web -n 5
```

### Search Vue-specific guidance

```powershell
python .windsurf\skills\ui-ux-pro-max\scripts\search.py "chat layout streaming input keyboard scroll" --stack vue -n 5
```

## OmniCut design baseline

For OmniCut, prefer:

- Dark video/productivity workspace.
- AI-native assistant panel.
- Streaming text as a first-class interaction.
- Reasoning chain above the final answer, collapsible but visible during active generation.
- Input composer always visible.
- Model and reasoning selectors near the input composer, not occupying the top of the assistant panel.
- User messages aligned right; assistant messages aligned left.
- Subtle micro-interactions only.
- Thin, low-contrast scrollbars that blend with the dark UI.
- Visible keyboard focus states for buttons, selects, and textareas.
- Respect `prefers-reduced-motion`.

Avoid:

- Generic AI-purple gradient UI.
- Large configuration blocks at the top of chat panels.
- Hidden or delayed assistant output behind spinners.
- Removing focus outlines without replacement.
- Scrollbars that visually dominate the chat area.

## Implementation targets

Most UI changes for the current OmniCut frontend are likely in:

- `apps/web/src/App.vue`
- `apps/web/src/styles.css`

Before making changes, inspect the current component and CSS. After changes, rely on Vite hot reload for visual iteration. Run `npm run build` only when final verification is needed or when TypeScript/CSS syntax risk is high.
