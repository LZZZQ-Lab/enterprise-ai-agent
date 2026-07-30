"""模型量化 optimization 模块测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.optimization.benchmark import QuantizationBenchmark
from app.optimization.benchmark import QuantizationBenchmarkReport
from app.optimization.quantization import QuantizationMode
from app.optimization.quantization import measure_model_memory_mib


def test_quantization_modes() -> None:

    assert QuantizationMode.FP16.value == "fp16"
    assert QuantizationMode.INT4.value == "int4"


def test_measure_model_memory_mib() -> None:

    pytest.importorskip("torch")
    pytest.importorskip("transformers")

    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(
        "sshleifer/tiny-gpt2"
    )

    size = measure_model_memory_mib(model)

    assert size > 0


@pytest.mark.integration
def test_benchmark_fp32_fp16_smoke(
    tmp_path: Path,
) -> None:

    pytest.importorskip("torch")
    pytest.importorskip("transformers")

    benchmark = QuantizationBenchmark(
        model_path="sshleifer/tiny-gpt2",
        prompt="hello",
        max_new_tokens=8,
        modes=[
            QuantizationMode.FP32,
            QuantizationMode.FP16,
        ],
    )

    report = benchmark.run()

    assert len(report.profiles) == 2

    assert isinstance(
        report,
        QuantizationBenchmarkReport,
    )

    json_path, md_path = report.save(tmp_path)

    assert json_path.is_file()
    text = md_path.read_text(encoding="utf-8")
    assert "fp32" in text.lower() or "FP32" in text
