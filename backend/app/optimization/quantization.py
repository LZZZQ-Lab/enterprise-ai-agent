from __future__ import annotations

import gc
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.core.logger import logger


class QuantizationMode(str, Enum):
    """
    支持的量化/精度模式（Task 4.3）。

    - FP32：原精度基线
    - FP16：半精度（降低显存、加速推理）
    - INT8：bitsandbytes 8bit 权重量化
    - INT4：bitsandbytes 4bit NF4（QLoRA 同款加载方式）
    """

    FP32 = "fp32"

    FP16 = "fp16"

    INT8 = "int8"

    INT4 = "int4"


@dataclass
class QuantizationProfile:
    """
    单次加载 + 推理 profiling 结果。
    """

    mode: QuantizationMode

    model_path: str

    model_size_mib: float

    load_time_seconds: float

    gpu_memory_mib: dict[str, float | None]

    inference_ms_avg: float

    tokens_per_sec: float

    prompt_tokens: int

    generated_tokens: int

    notes: str = ""


def load_quantized_model(
    model_path: str,
    mode: QuantizationMode,
    *,
    trust_remote_code: bool = True,
) -> tuple[Any, Any]:
    """
    按模式加载 CausalLM 与 Tokenizer。

    Base Model → (FP16 / INT8 / INT4) 加载策略。
    """

    import torch
    from transformers import AutoModelForCausalLM
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=trust_remote_code,
    )

    if tokenizer.pad_token is None:

        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: dict[str, Any] = {
        "trust_remote_code": trust_remote_code,
    }

    if mode == QuantizationMode.FP32:

        model_kwargs["torch_dtype"] = torch.float32

        if torch.cuda.is_available():

            model_kwargs["device_map"] = "auto"

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            **model_kwargs,
        )

    elif mode == QuantizationMode.FP16:

        if torch.cuda.is_available():

            model_kwargs["torch_dtype"] = torch.float16
            model_kwargs["device_map"] = "auto"

        else:

            model_kwargs["torch_dtype"] = torch.float32

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            **model_kwargs,
        )

    elif mode in (
        QuantizationMode.INT8,
        QuantizationMode.INT4,
    ):

        if not torch.cuda.is_available():

            raise RuntimeError(
                f"{mode.value} quantization requires CUDA GPU."
            )

        try:

            from transformers import BitsAndBytesConfig

        except ImportError as error:

            raise RuntimeError(
                "INT8/INT4 requires transformers BitsAndBytesConfig"
            ) from error

        load_in_4bit = mode == QuantizationMode.INT4
        load_in_8bit = mode == QuantizationMode.INT8

        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=load_in_4bit,
            load_in_8bit=load_in_8bit,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

        model_kwargs["device_map"] = "auto"

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            **model_kwargs,
        )

    else:

        raise ValueError(f"Unknown mode: {mode}")

    return model, tokenizer


def measure_model_memory_mib(model: Any) -> float:
    """
    估算当前已加载权重占用（MiB，按 tensor 元素计）。
    """

    total_bytes = 0

    for parameter in model.parameters():

        total_bytes += (
            parameter.numel()
            * parameter.element_size()
        )

    return round(
        total_bytes / (1024 ** 2),
        2,
    )


def unload_model(model: Any) -> None:

    import torch

    del model

    gc.collect()

    if torch.cuda.is_available():

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()


def profile_mode(
    model_path: str,
    mode: QuantizationMode,
    prompt: str,
    *,
    max_new_tokens: int = 32,
) -> QuantizationProfile:
    """
    加载 → 测显存/大小 → 短生成测速 → 卸载。
    """

    import torch

    notes = ""

    if (
        mode == QuantizationMode.FP16
        and not torch.cuda.is_available()
    ):

        notes = "fp16_fallback_cpu_fp32"

    if torch.cuda.is_available():

        torch.cuda.reset_peak_memory_stats()

    start_load = time.perf_counter()

    try:

        model, tokenizer = load_quantized_model(
            model_path,
            mode,
        )

    except RuntimeError as error:

        return QuantizationProfile(
            mode=mode,
            model_path=model_path,
            model_size_mib=0.0,
            load_time_seconds=0.0,
            gpu_memory_mib=_gpu_snapshot(),
            inference_ms_avg=0.0,
            tokens_per_sec=0.0,
            prompt_tokens=0,
            generated_tokens=0,
            notes=str(error),
        )

    load_time = time.perf_counter() - start_load

    model_size = measure_model_memory_mib(model)

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    )

    device = _model_device(model)

    if device.type == "cuda":

        inputs = {
            key: value.to(device)
            for key, value in inputs.items()
        }

    prompt_tokens = int(inputs["input_ids"].shape[-1])

    model.eval()

    latencies: list[float] = []

    generated_tokens = 0

    with torch.no_grad():

        for _ in range(3):

            timer_start = time.perf_counter()

            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )

            latencies.append(
                (time.perf_counter() - timer_start) * 1000
            )

            generated_tokens = max(
                generated_tokens,
                int(outputs.shape[-1] - prompt_tokens),
            )

    inference_avg = sum(latencies) / len(latencies)

    tokens_per_sec = 0.0

    if inference_avg > 0 and generated_tokens > 0:

        tokens_per_sec = (
            generated_tokens / (inference_avg / 1000)
        )

    memory = _gpu_snapshot()

    if torch.cuda.is_available():

        memory["peak_allocated_mib"] = round(
            torch.cuda.max_memory_allocated()
            / (1024 ** 2),
            2,
        )

    unload_model(model)

    logger.info(
        "Quant profile %s size=%.2f MiB infer=%.1f ms",
        mode.value,
        model_size,
        inference_avg,
    )

    return QuantizationProfile(
        mode=mode,
        model_path=model_path,
        model_size_mib=model_size,
        load_time_seconds=round(load_time, 3),
        gpu_memory_mib=memory,
        inference_ms_avg=round(inference_avg, 2),
        tokens_per_sec=round(tokens_per_sec, 2),
        prompt_tokens=prompt_tokens,
        generated_tokens=generated_tokens,
        notes=notes,
    )


def _model_device(model: Any):

    import torch

    try:

        return next(model.parameters()).device

    except StopIteration:

        return torch.device("cpu")


def _gpu_snapshot() -> dict[str, float | None]:

    from benchmark.common import gpu_memory_snapshot
    from benchmark.common import torch_gpu_memory_snapshot

    snap = {}

    snap.update(gpu_memory_snapshot())

    snap.update(torch_gpu_memory_snapshot())

    return snap
