"""
Task 12 示例：Multi-Agent 东京旅行规划。

流程：
  User → Coordinator → Router → TravelAgent / WeatherAgent / HotelAgent
       → SummaryAgent → 最终答案

默认使用 TemplateAgent（无需 LLM）。
加 --llm 参数可切换为真实 ChatAgent 调用。

用法：
  cd backend
  python -m examples.travel_multi_agent
  python -m examples.travel_multi_agent --llm
"""

import argparse

from app.multi_agent.factory import create_travel_coordinator
from app.config import AgentConfig
from app.agents.executor.tracer import AgentTracer


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Multi-Agent Tokyo travel planning demo",
    )

    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use real LLM via ChatAgent instead of templates",
    )

    args = parser.parse_args()

    config = AgentConfig(
        enable_multi_agent=True,
        router_type="rule",
        max_agents=10,
        communication_mode="bus",
        enable_trace=True,
    )

    tracer = AgentTracer()

    coordinator = create_travel_coordinator(
        config=config,
        use_llm=args.llm,
        tracer=tracer,
    )

    user_input = "帮我规划一次东京旅行"

    print("=" * 60)
    print(f"User: {user_input}")
    print("=" * 60)

    result = coordinator.run(
        session_id="travel-demo",
        user_input=user_input,
    )

    print("\n--- MessageBus History ---")

    for message in coordinator.message_bus.history:

        print(
            f"  [{message.message_type.value}] "
            f"{message.sender} -> {message.receiver}: "
            f"{list(message.payload.keys())}"
        )

    print("\n--- Shared Memory ---")

    for key, value in coordinator.shared_memory.get_context_snapshot().items():

        preview = str(value)[:80]

        print(f"  {key}: {preview}...")

    print("\n--- Final Answer ---")
    print(result.content)
    print("\n--- Success:", result.success, "---")


if __name__ == "__main__":

    main()
