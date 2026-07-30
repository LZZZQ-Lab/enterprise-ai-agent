"""
本地 LLM 运行环境 GPU / CUDA 检查脚本。

Task 2.1：输出 CUDA 是否可用、GPU 名称、GPU 显存。

运行:
    cd backend
    python scripts/check_gpu.py
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version


@dataclass
class GPUInfo:
    index: int
    name: str
    total_memory_mb: float | None = None
    used_memory_mb: float | None = None
    free_memory_mb: float | None = None


def _format_mb(value: float | None) -> str:

    if value is None:

        return "N/A"

    if value >= 1024:

        return f"{value / 1024:.2f} GB ({value:.0f} MB)"

    return f"{value:.0f} MB"


def _check_python() -> None:

    print("=== Python ===")
    print(f"Version     : {platform.python_version()}")
    print(f"Executable  : {sys.executable}")
    print(f"Platform    : {platform.platform()}")
    print()


def _check_pytorch() -> tuple[bool, object | None]:

    print("=== PyTorch ===")

    try:

        import torch

    except ImportError:

        print("Status      : NOT INSTALLED")
        print("Hint        : pip install torch --index-url https://download.pytorch.org/whl/cu124")
        print()
        return False, None

    print(f"Version     : {torch.__version__}")
    print(f"CUDA built  : {torch.version.cuda or 'None (CPU build)'}")
    print()
    return True, torch


def _collect_gpus_via_torch(torch) -> list[GPUInfo]:

    gpus: list[GPUInfo] = []

    if not torch.cuda.is_available():

        return gpus

    for index in range(torch.cuda.device_count()):

        props = torch.cuda.get_device_properties(index)
        total_mb = props.total_memory / (1024 ** 2)

        free_bytes, total_bytes = torch.cuda.mem_get_info(index)
        free_mb = free_bytes / (1024 ** 2)
        used_mb = (total_bytes - free_bytes) / (1024 ** 2)

        gpus.append(
            GPUInfo(
                index=index,
                name=props.name,
                total_memory_mb=total_mb,
                used_memory_mb=used_mb,
                free_memory_mb=free_mb,
            )
        )

    return gpus


def _collect_gpus_via_nvidia_smi() -> list[GPUInfo]:

    if shutil.which("nvidia-smi") is None:

        return []

    try:

        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):

        return []

    gpus: list[GPUInfo] = []

    for line in result.stdout.strip().splitlines():

        parts = [part.strip() for part in line.split(",")]

        if len(parts) < 5:

            continue

        index_str, name, total, used, free = parts[:5]

        gpus.append(
            GPUInfo(
                index=int(index_str),
                name=name,
                total_memory_mb=float(total),
                used_memory_mb=float(used),
                free_memory_mb=float(free),
            )
        )

    return gpus


def _check_cuda_toolkit() -> None:

    print("=== CUDA Toolkit (nvcc) ===")

    nvcc = shutil.which("nvcc")

    if nvcc is None:

        print("Status      : NOT FOUND in PATH")
        print("Note        : Driver CUDA != Toolkit; PyTorch wheels bundle runtime CUDA.")
        print()
        return

    try:

        result = subprocess.run(
            [nvcc, "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

        version_line = next(
            (
                line.strip()
                for line in result.stdout.splitlines()
                if "release" in line.lower()
            ),
            result.stdout.strip(),
        )

        print(f"Status      : FOUND ({nvcc})")
        print(f"Version     : {version_line}")

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:

        print(f"Status      : ERROR ({error})")

    print()


def _print_gpu_report(
    *,
    cuda_available: bool,
    gpus: list[GPUInfo],
    source: str,
) -> None:

    print("=== GPU ===")
    print(f"CUDA usable : {'YES' if cuda_available else 'NO'}")
    print(f"GPU source  : {source}")

    if not gpus:

        print("GPU count   : 0")
        print()
        return

    print(f"GPU count   : {len(gpus)}")
    print()

    for gpu in gpus:

        print(f"[GPU {gpu.index}] {gpu.name}")
        print(f"  Total VRAM : {_format_mb(gpu.total_memory_mb)}")
        print(f"  Used VRAM  : {_format_mb(gpu.used_memory_mb)}")
        print(f"  Free VRAM  : {_format_mb(gpu.free_memory_mb)}")
        print()


def _package_version(name: str) -> str:

    try:

        return version(name)

    except PackageNotFoundError:

        return "NOT INSTALLED"


def _print_transformers_stack() -> None:

    print("=== LLM Stack (optional) ===")

    for package in (
        "torch",
        "transformers",
        "accelerate",
        "sentencepiece",
    ):

        print(f"{package:<14}: {_package_version(package)}")

    print()


def main() -> None:

    print()
    print("Enterprise LLM Application Platform - GPU Environment Check")
    print("=" * 60)
    print()

    _check_python()

    torch_installed, torch = _check_pytorch()
    _check_cuda_toolkit()

    gpus: list[GPUInfo] = []
    cuda_available = False
    source = "none"

    if torch_installed and torch is not None:

        cuda_available = bool(torch.cuda.is_available())
        gpus = _collect_gpus_via_torch(torch)
        source = "torch.cuda"

    if not gpus:

        gpus = _collect_gpus_via_nvidia_smi()
        source = "nvidia-smi" if gpus else source

        if gpus and not cuda_available:

            cuda_available = True

    _print_gpu_report(
        cuda_available=cuda_available,
        gpus=gpus,
        source=source,
    )

    _print_transformers_stack()

    print("=" * 60)
    print("Check complete.")
    print()


if __name__ == "__main__":

    main()
