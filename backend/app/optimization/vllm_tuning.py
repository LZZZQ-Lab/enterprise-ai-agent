"""
Task 4.4：vLLM 服务调优配置（batch / max tokens / GPU 利用率 / KV Cache）。

与 ``backend/benchmark/vllm_concurrency_benchmark.py`` 配合做优化前后对比。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILES_PATH = BACKEND_ROOT / "data" / "vllm_profiles.json"


@dataclass(frozen=True)
class VllmServeProfile:
    """vLLM ``serve`` 启动参数集合。"""

    label: str
    description: str
    max_model_len: int
    gpu_memory_utilization: float
    max_num_seqs: int
    max_num_batched_tokens: int
    swap_space_gb: int
    enable_prefix_caching: bool
    enforce_eager: bool
    client_max_tokens: int

    def to_dict(self) -> dict[str, Any]:

        return {
            "label": self.label,
            "description": self.description,
            "max_model_len": self.max_model_len,
            "gpu_memory_utilization": self.gpu_memory_utilization,
            "max_num_seqs": self.max_num_seqs,
            "max_num_batched_tokens": self.max_num_batched_tokens,
            "swap_space_gb": self.swap_space_gb,
            "enable_prefix_caching": self.enable_prefix_caching,
            "enforce_eager": self.enforce_eager,
            "client_max_tokens": self.client_max_tokens,
        }

    def serve_argv(self) -> list[str]:
        """追加到 ``vllm serve MODEL`` 后的 CLI 参数。"""

        argv = [
            "--max-model-len",
            str(self.max_model_len),
            "--gpu-memory-utilization",
            str(self.gpu_memory_utilization),
            "--max-num-seqs",
            str(self.max_num_seqs),
            "--max-num-batched-tokens",
            str(self.max_num_batched_tokens),
            "--swap-space",
            str(self.swap_space_gb),
        ]

        if self.enable_prefix_caching:

            argv.append("--enable-prefix-caching")

        if self.enforce_eager:

            argv.append("--enforce-eager")

        return argv

    def shell_env(self) -> dict[str, str]:
        """供 ``start_vllm_server.sh`` 使用的环境变量。"""

        return {
            "VLLM_PROFILE": self.label,
            "VLLM_MAX_LEN": str(self.max_model_len),
            "VLLM_GPU_UTIL": str(self.gpu_memory_utilization),
            "VLLM_MAX_NUM_SEQS": str(self.max_num_seqs),
            "VLLM_MAX_BATCHED_TOKENS": str(
                self.max_num_batched_tokens
            ),
            "VLLM_SWAP_SPACE": str(self.swap_space_gb),
            "VLLM_PREFIX_CACHING": (
                "1" if self.enable_prefix_caching else "0"
            ),
            "VLLM_ENFORCE_EAGER": (
                "1" if self.enforce_eager else "0"
            ),
        }


def load_profiles(
    path: Path | None = None,
) -> dict[str, VllmServeProfile]:

    config_path = path or DEFAULT_PROFILES_PATH

    raw = json.loads(
        config_path.read_text(encoding="utf-8"),
    )

    profiles: dict[str, VllmServeProfile] = {}

    for key, item in raw.items():

        profiles[key] = VllmServeProfile(
            label=item.get("label", key),
            description=item.get("description", ""),
            max_model_len=int(item["max_model_len"]),
            gpu_memory_utilization=float(
                item["gpu_memory_utilization"]
            ),
            max_num_seqs=int(item["max_num_seqs"]),
            max_num_batched_tokens=int(
                item["max_num_batched_tokens"]
            ),
            swap_space_gb=int(item["swap_space_gb"]),
            enable_prefix_caching=bool(
                item.get("enable_prefix_caching", False)
            ),
            enforce_eager=bool(item.get("enforce_eager", True)),
            client_max_tokens=int(
                item.get("client_max_tokens", 128)
            ),
        )

    return profiles


def get_profile(
    name: str,
    *,
    path: Path | None = None,
) -> VllmServeProfile:

    profiles = load_profiles(path)

    if name not in profiles:

        known = ", ".join(sorted(profiles))
        raise KeyError(
            f"Unknown vLLM profile {name!r}; known: {known}"
        )

    return profiles[name]
