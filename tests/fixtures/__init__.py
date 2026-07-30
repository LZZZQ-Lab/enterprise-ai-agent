"""Shared pytest fixtures and test doubles (Task 8.1)."""

from tests.fixtures.mock_llm import MockLLM
from tests.fixtures.mock_llm import MockLLMWithToolCall

__all__ = ["MockLLM", "MockLLMWithToolCall"]
