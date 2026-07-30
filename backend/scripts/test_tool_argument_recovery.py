from app.llm.openai_provider import OpenAIProvider


def main() -> None:
    broken = '{"path": "docs/PRD.md", "content": "# PRD\\n\\nHello **world**'
    args = OpenAIProvider._parse_arguments("write_file", broken)

    assert args.get("path") == "docs/PRD.md"
    assert "PRD" in args.get("content", "")

    print("tool argument recovery: PASS")


if __name__ == "__main__":
    main()
