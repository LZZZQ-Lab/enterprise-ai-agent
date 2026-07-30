"""Task 9.1：验证 canonical 模块 facade 与 legacy 路径等价。"""

from __future__ import annotations

import importlib


def test_canonical_agent_exports_match_legacy() -> None:
    legacy = importlib.import_module("app.agents")
    canonical = importlib.import_module("core.agent")
    assert set(canonical.__all__) == set(legacy.__all__)


def test_canonical_llm_provider_exports() -> None:
    from llm.providers import BaseLLM, get_llm_client
    from app.llm import BaseLLM as LegacyBaseLLM

    assert BaseLLM is LegacyBaseLLM
    assert callable(get_llm_client)


def test_canonical_rag_pipeline() -> None:
    from knowledge.rag import RAGPipeline, create_rag_pipeline
    from app.rag import RAGPipeline as LegacyPipeline

    assert RAGPipeline is LegacyPipeline
    assert callable(create_rag_pipeline)


def test_canonical_api_app() -> None:
    from apps.api import app
    from app.main import app as legacy_app

    assert app is legacy_app


def test_canonical_tools_factory() -> None:
    from core.tools import ToolFactory
    from app.tools.factory import ToolFactory as LegacyFactory

    assert ToolFactory is LegacyFactory
