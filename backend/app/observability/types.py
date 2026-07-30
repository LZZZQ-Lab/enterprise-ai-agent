from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from uuid import uuid4


class TraceEventType(str, Enum):
    PROMPT = "prompt"
    LLM = "llm"
    TOOL = "tool"
    OBSERVATION = "observation"
    MEMORY = "memory"
    RETRIEVAL = "retrieval"
    PLANNER = "planner"
    WORKFLOW = "workflow"
    MULTI_AGENT = "multi_agent"
    AGENT = "agent"
    GPU = "gpu"


def _new_event_id() -> str:
    return uuid4().hex


@dataclass
class TraceEvent:
    """
    Trace 事件基类。
    """

    event_type: TraceEventType

    timestamp: float

    event_id: str = field(
        default_factory=_new_event_id
    )


@dataclass
class PromptEvent(TraceEvent):
    """
    Prompt 构建事件。
    """

    messages: list[dict[str, Any]] = field(
        default_factory=list
    )

    message_count: int = 0

    prompt_length: int = 0

    token_count: int | None = None


@dataclass
class LLMEvent(TraceEvent):
    """
    LLM 调用事件。
    """

    model: str = ""

    input_message_count: int = 0

    content_preview: str = ""

    has_tool_calls: bool = False

    tool_call_count: int = 0

    duration_ms: float = 0.0

    ttft_ms: float | None = None

    tokens_per_second: float | None = None

    prompt_tokens: int = 0

    completion_tokens: int = 0

    error: str | None = None


@dataclass
class ToolEvent(TraceEvent):
    """
    Tool 执行事件。
    """

    tool_name: str = ""

    arguments: dict[str, Any] = field(
        default_factory=dict
    )

    output: str = ""

    success: bool = True

    duration_ms: float = 0.0

    error: str | None = None


@dataclass
class ObservationEvent(TraceEvent):
    """
    Tool 观察结果事件。
    """

    tool_call_id: str = ""

    tool_name: str = ""

    content: str = ""


@dataclass
class MemoryEvent(TraceEvent):
    """
    Memory 加载事件。
    """

    session_id: str = ""

    record_count: int = 0

    memory_record_count: int = 0


@dataclass
class RetrievalDocument:
    """
    RAG 检索文档快照。
    """

    document_id: str

    score: float

    content_preview: str

    source: str = ""


@dataclass
class RetrievalEvent(TraceEvent):
    """
    RAG 检索事件。
    """

    query: str = ""

    embedding_provider: str = ""

    top_k: int = 0

    hit_count: int = 0

    documents: list[RetrievalDocument] = field(
        default_factory=list
    )

    injected_content: str = ""


@dataclass
class PlannerStepSnapshot:
    """
    Plan Step 快照，便于序列化与回放。
    """

    step_id: str

    description: str

    tool: str | None = None

    status: str = "pending"

    result: str = ""


@dataclass
class PlannerEvent(TraceEvent):
    """
    Planner / Plan 事件。
    """

    action: str = ""

    goal: str = ""

    plan_status: str = ""

    step_count: int = 0

    steps: list[PlannerStepSnapshot] = field(
        default_factory=list
    )

    step_id: str = ""

    step_result: str = ""


@dataclass
class WorkflowEvent(TraceEvent):
    """
    Workflow 执行状态事件。
    """

    action: str = ""

    workflow_mode: str = ""

    plan_status: str = ""

    current_step_id: str = ""

    success: bool = True

    content_preview: str = ""


@dataclass
class MultiAgentEvent(TraceEvent):
    """
    Multi-Agent 协作事件。
    """

    action: str = ""

    agent_name: str = ""

    task_id: str = ""

    task_input: str = ""

    selected_agent: str = ""

    message_type: str = ""

    success: bool = True

    content_preview: str = ""


@dataclass
class AgentSpanEvent(TraceEvent):
    """
    Agent 执行跨度（Runtime 自动记录）。
    """

    agent_name: str = ""

    phase: str = ""

    prompt: str = ""

    response: str = ""

    prompt_tokens: int = 0

    completion_tokens: int = 0

    total_tokens: int = 0

    duration_ms: float = 0.0

    success: bool = True

    tool_call_count: int = 0


@dataclass
class GPUMetricsEvent(TraceEvent):
    """
    GPU 显存与利用率快照。
    """

    memory_used_mib: float | None = None

    memory_total_mib: float | None = None

    utilization_percent: float | None = None

    gpu_index: int = 0

    phase: str = ""


@dataclass
class Trace:
    """
    一次 Agent 执行的完整 Trace。
    """

    trace_id: str

    session_id: str

    start_time: float

    end_time: float | None = None

    duration: float | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    events: list[TraceEvent] = field(
        default_factory=list
    )
