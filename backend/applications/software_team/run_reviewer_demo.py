#!/usr/bin/env python3
"""
Task 5.5 Demo：Reviewer Agent 审查 Git Diff。

用法：
    cd backend
    python -m applications.software_team.run_reviewer_demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


SAMPLE_DIFF = """diff --git a/src/app.py b/src/app.py
index 111..222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,5 +1,8 @@
+password = "admin123"
+
 def health():
-    return {"status": "ok"}
+    eval(user_input)
+    print("debug")
+    return {"status": "ok", "data": db.execute("SELECT * FROM users")}
"""


class ReviewerDemoMockLLM:
    model = "demo-mock-reviewer"

    def bind_tool_manager(self, tool_manager) -> None:

        return None

    def chat(self, messages, use_tools=True):
        from app.llm.types import ChatResult

        body = """# Code Review Report

## 摘要
需修改：发现硬编码密码与 eval 使用。

## 代码规范
- **[info]** `src/app.py`：使用 print 调试，建议改为 logger。

## 安全问题
- **[critical]** 硬编码 password，必须移除。
- **[critical]** eval(user_input) 代码注入风险。

## 性能问题
- **[minor]** SELECT * 可能过度拉取列。

## 架构问题
- 未发现明显问题。

## 修改建议汇总
1. 删除明文 password，改用环境变量。
2. 移除 eval，使用安全解析。
3. 将 print 替换为结构化日志。
4. 查询指定列并加索引。
"""

        return ChatResult(model=self.model, content=body)


class MockStandardsRetriever:
    def retrieve(self, query, top_k=3, score_threshold=0.0):
        from app.rag.types import Document
        from app.rag.types import ScoredDocument

        return [
            ScoredDocument(
                document=Document(
                    id="sec-1",
                    content="禁止提交明文密钥；禁止 eval/exec。",
                    metadata={"source": "security-standards.md"},
                ),
                score=0.9,
            )
        ]


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Reviewer Agent Demo (Task 5.5)",
    )

    parser.add_argument(
        "--write",
        default="",
        help="写入 docs/REVIEW_REPORT.md 的目录",
    )

    args = parser.parse_args()

    from app.agents.software_team.reviewer_agent import ReviewerAgent
    from app.agents.types import AgentContext
    from app.config import AgentConfig

    metadata = {"git_diff": SAMPLE_DIFF}

    if args.write:

        metadata["artifact_dir"] = args.write

    agent = ReviewerAgent(
        config=AgentConfig(
            enable_rag=True,
            enable_trace=False,
            enable_mcp=False,
        ),
        client=ReviewerDemoMockLLM(),
        retriever=MockStandardsRetriever(),
    )

    result = agent.run(
        AgentContext(
            session_id="demo-reviewer",
            user_message=SAMPLE_DIFF,
            agent_name="reviewer",
            metadata=metadata,
        )
    )

    print(result.content)


if __name__ == "__main__":

    main()
