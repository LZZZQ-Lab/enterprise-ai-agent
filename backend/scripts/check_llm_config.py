"""检查 LLM 配置（不打印完整 API Key）。"""

from __future__ import annotations

from pathlib import Path

from app.config import settings


def main() -> None:

    key = settings.API_KEY or ""

    print("APP_NAME:", settings.APP_NAME)
    print("MODEL_PROVIDER:", settings.MODEL_PROVIDER)
    print("MODEL_NAME:", settings.MODEL_NAME)
    print("MAX_AGENT_LOOP:", settings.MAX_AGENT_LOOP)
    print("OPENAI_BASE_URL:", settings.OPENAI_BASE_URL)
    print("KEY length:", len(key))
    print("KEY starts with sk-:", key.startswith("sk-"))
    print("KEY has leading/trailing space:", key != key.strip())
    print("KEY is placeholder:", key in {"", "your-api-key-here"})

    env_path = Path(".env")

    if env_path.is_file():

        for line in env_path.read_text(encoding="utf-8-sig").splitlines():

            if line.startswith("API_KEY=") or line.startswith(
                "OPENAI_API_KEY=",
            ):

                raw = line.split("=", 1)[1]
                print("RAW .env value length:", len(raw))
                print("RAW .env has quotes:", raw.strip()[:1] in "\"'")


if __name__ == "__main__":

    main()
