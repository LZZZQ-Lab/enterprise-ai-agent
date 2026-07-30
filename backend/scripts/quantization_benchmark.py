#!/usr/bin/env python3
"""
模型量化对比 Benchmark（Task 4.3）。

用法：
    cd backend
    python -m scripts.quantization_benchmark
    python -m scripts.quantization_benchmark --model Qwen/Qwen2.5-0.5B-Instruct
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:

    sys.path.insert(0, str(BACKEND_ROOT))


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Quantization benchmark FP32/FP16/INT8/INT4",
    )

    parser.add_argument(
        "--model",
        default="sshleifer/tiny-gpt2",
        help="HuggingFace model id or local path",
    )

    parser.add_argument(
        "--prompt",
        default="请用一句话说明企业知识库的作用。",
    )

    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=32,
    )

    parser.add_argument(
        "--output-dir",
        default="artifacts/optimization/quantization",
    )

    parser.add_argument(
        "--modes",
        default="fp32,fp16,int8,int4",
        help="Comma-separated modes",
    )

    parser.add_argument(
        "--copy-docs",
        action="store_true",
        help="Also write docs/quantization_report.md",
    )

    args = parser.parse_args()

    from app.optimization.benchmark import run_quantization_benchmark
    from app.optimization.quantization import QuantizationMode

    modes = []

    for token in args.modes.split(","):

        token = token.strip().lower()

        if token:

            modes.append(QuantizationMode(token))

    report = run_quantization_benchmark(
        model_path=args.model,
        prompt=args.prompt,
        output_dir=args.output_dir,
        max_new_tokens=args.max_new_tokens,
        modes=modes,
    )

    print("Quantization benchmark done.")

    for profile in report.profiles:

        print(
            f"  {profile.mode.value}: "
            f"size={profile.model_size_mib}MiB "
            f"infer={profile.inference_ms_avg}ms "
            f"tok/s={profile.tokens_per_sec} "
            f"notes={profile.notes or '-'}"
        )

    out = Path(args.output_dir)

    print(f"  report: {out / 'quantization_report.md'}")

    if args.copy_docs:

        docs_path = (
            BACKEND_ROOT.parent
            / "docs"
            / "quantization_report.md"
        )

        docs_path.write_text(
            report.to_markdown(),
            encoding="utf-8",
        )

        print(f"  copied: {docs_path}")


if __name__ == "__main__":

    main()
