from app.modules.assistant.schemas import AssistantModelOption, AssistantOptionsResponse, AssistantReasoningModeOption

ASSISTANT_MODEL_OPTIONS = [
    AssistantModelOption(id="deepseek-v4-pro", label="DeepSeek V4 Pro", description="更强的复杂创作和推理能力，适合正式生成文案和分镜。"),
    AssistantModelOption(id="deepseek-v4-flash", label="DeepSeek V4 Flash", description="更快、更轻，适合快速改写、头脑风暴和短任务。"),
]

ASSISTANT_REASONING_MODE_OPTIONS = [
    AssistantReasoningModeOption(id="disabled", label="非思考", description="关闭思考模式，响应更快，适合简单改写。"),
    AssistantReasoningModeOption(id="high", label="High", description="标准思考强度，适合大多数策划和分镜任务。"),
    AssistantReasoningModeOption(id="max", label="Max", description="最高思考强度，适合复杂项目拆解和高要求推理。"),
]


def get_assistant_options() -> AssistantOptionsResponse:
    return AssistantOptionsResponse(models=ASSISTANT_MODEL_OPTIONS, reasoning_modes=ASSISTANT_REASONING_MODE_OPTIONS)
