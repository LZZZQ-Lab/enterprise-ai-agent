"""
Task 5.4：代码变更历史（仅记录经 Tool 的修改）。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from uuid import uuid4


@dataclass
class CodeChangeRecord:
    id: str
    timestamp: str
    path: str
    operation: str
    tool: str
    agent: str = "developer"
    bytes_written: int = 0
    summary: str = ""

    def to_dict(self) -> dict:

        return asdict(self)


@dataclass
class CodeChangeHistory:
    session_id: str = ""
    records: list[CodeChangeRecord] = field(default_factory=list)

    def record(
        self,
        *,
        path: str,
        operation: str,
        tool: str,
        bytes_written: int = 0,
        summary: str = "",
        agent: str = "developer",
    ) -> CodeChangeRecord:

        entry = CodeChangeRecord(
            id=uuid4().hex[:12],
            timestamp=datetime.now(timezone.utc).isoformat(),
            path=path.replace("\\", "/"),
            operation=operation,
            tool=tool,
            agent=agent,
            bytes_written=bytes_written,
            summary=summary,
        )

        self.records.append(entry)

        return entry

    def to_dict(self) -> dict:

        return {
            "session_id": self.session_id,
            "records": [record.to_dict() for record in self.records],
        }

    def to_jsonl(self) -> str:

        lines = [
            json.dumps(record.to_dict(), ensure_ascii=False)
            for record in self.records
        ]

        return "\n".join(lines) + ("\n" if lines else "")

    def to_markdown(self) -> str:

        if not self.records:

            return "## Code Change History\n\n（无变更）\n"

        rows = [
            "| 时间 | 路径 | 操作 | 工具 | 说明 |",
            "|------|------|------|------|------|",
        ]

        for record in self.records:

            rows.append(
                f"| {record.timestamp[:19]} | `{record.path}` | "
                f"{record.operation} | {record.tool} | "
                f"{record.summary or record.bytes_written} |"
            )

        return "## Code Change History\n\n" + "\n".join(rows) + "\n"
