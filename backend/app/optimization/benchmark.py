from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from app.optimization.quantization import QuantizationMode
from app.optimization.quantization import QuantizationProfile
from app.optimization.quantization import profile_mode


@dataclass
class QuantizationBenchmarkReport:
    """
    原模型 vs 量化模型对比报告。
    """

    model_path: str

    prompt: str

    max_new_tokens: int

    profiles: list[QuantizationProfile]

    created_at: str

    comparison: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:

        return {
            "model_path": self.model_path,
            "prompt": self.prompt,
            "max_new_tokens": self.max_new_tokens,
            "created_at": self.created_at,
            "profiles": [
                {
                    **asdict(profile),
                    "mode": profile.mode.value,
                }
                for profile in self.profiles
            ],
            "comparison": self.comparison,
        }

    def save(
        self,
        output_dir: Path,
    ) -> tuple[Path, Path]:

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        json_path = output_dir / "quantization_report.json"

        json_path.write_text(
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        md_path = output_dir / "quantization_report.md"

        md_path.write_text(
            self.to_markdown(),
            encoding="utf-8",
        )

        return json_path, md_path

    def to_markdown(self) -> str:

        lines = [
            "# 模型量化性能报告（Task 4.3）",
            "",
            f"- **模型**: `{self.model_path}`",
            f"- **时间**: {self.created_at}",
            f"- **生成长度**: {self.max_new_tokens} tokens",
            "",
            "## 对比摘要",
            "",
            "| 模式 | 模型大小(MiB) | 峰值显存(MiB) | 推理(ms) | tok/s | 加载(s) |",
            "|------|---------------|---------------|----------|-------|---------|",
        ]

        baseline_size = None
        baseline_infer = None

        for profile in self.profiles:

            if profile.mode == QuantizationMode.FP32:

                baseline_size = profile.model_size_mib
                baseline_infer = profile.inference_ms_avg

        for profile in self.profiles:

            peak = profile.gpu_memory_mib.get(
                "peak_allocated_mib"
            )

            if peak is None:

                peak = profile.gpu_memory_mib.get(
                    "used_mib"
                )

            peak_display = (
                f"{peak:.1f}"
                if peak is not None
                else "N/A"
            )

            lines.append(
                f"| {profile.mode.value} "
                f"| {profile.model_size_mib:.1f} "
                f"| {peak_display} "
                f"| {profile.inference_ms_avg:.1f} "
                f"| {profile.tokens_per_sec:.1f} "
                f"| {profile.load_time_seconds:.2f} |"
            )

        lines.extend(
            [
                "",
                "## 相对 FP32 基线",
                "",
            ]
        )

        for key, value in self.comparison.items():

            lines.append(f"- **{key}**: {value}")

        lines.append("")

        lines.append("## 说明")

        lines.append("")

        lines.append(
            "- **FP16**：半精度权重，通常降低显存并提升吞吐。"
        )

        lines.append(
            "- **INT8/INT4**：bitsandbytes 量化，需 NVIDIA GPU。"
        )

        lines.append(
            "- 模型大小为加载后参数 tensor 估算；"
            "峰值显存含 KV 与临时缓冲。"
        )

        for profile in self.profiles:

            if profile.notes:

                lines.append(
                    f"- {profile.mode.value}: {profile.notes}"
                )

        if (
            baseline_size
            and baseline_infer
        ):

            lines.extend(
                [
                    "",
                    "### 效果变化（相对原模型）",
                    "",
                ]
            )

            for profile in self.profiles:

                if profile.mode == QuantizationMode.FP32:

                    continue

                size_ratio = (
                    profile.model_size_mib / baseline_size
                    if baseline_size
                    else 0
                )

                speed_ratio = (
                    baseline_infer / profile.inference_ms_avg
                    if profile.inference_ms_avg
                    else 0
                )

                lines.append(
                    f"- **{profile.mode.value}**: "
                    f"权重大小约为 FP32 的 {size_ratio:.0%}；"
                    f"推理耗时倍率约 {speed_ratio:.2f}x"
                )

        return "\n".join(lines)


class QuantizationBenchmark:
    """
    原模型 vs FP16/INT8/INT4 对比 benchmark。
    """

    def __init__(
        self,
        model_path: str,
        prompt: str,
        *,
        max_new_tokens: int = 32,
        modes: list[QuantizationMode] | None = None,
    ) -> None:

        self.model_path = model_path
        self.prompt = prompt
        self.max_new_tokens = max_new_tokens

        self.modes = modes or [
            QuantizationMode.FP32,
            QuantizationMode.FP16,
            QuantizationMode.INT8,
            QuantizationMode.INT4,
        ]

    def run(self) -> QuantizationBenchmarkReport:

        profiles: list[QuantizationProfile] = []

        for mode in self.modes:

            profiles.append(
                profile_mode(
                    self.model_path,
                    mode,
                    self.prompt,
                    max_new_tokens=self.max_new_tokens,
                )
            )

        comparison = self._build_comparison(profiles)

        return QuantizationBenchmarkReport(
            model_path=self.model_path,
            prompt=self.prompt,
            max_new_tokens=self.max_new_tokens,
            profiles=profiles,
            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
            comparison=comparison,
        )

    @staticmethod
    def _build_comparison(
        profiles: list[QuantizationProfile],
    ) -> dict[str, Any]:

        baseline = next(
            (
                profile
                for profile in profiles
                if profile.mode == QuantizationMode.FP32
            ),
            None,
        )

        result: dict[str, Any] = {}

        if baseline is None:

            return result

        for profile in profiles:

            if profile.mode == QuantizationMode.FP32:

                continue

            if profile.inference_ms_avg <= 0:

                result[profile.mode.value] = (
                    f"skipped: {profile.notes or 'no inference'}"
                )

                continue

            size_saved = (
                1
                - profile.model_size_mib
                / baseline.model_size_mib
            ) if baseline.model_size_mib else 0

            speedup = (
                baseline.inference_ms_avg
                / profile.inference_ms_avg
            ) if profile.inference_ms_avg else 0

            result[profile.mode.value] = {
                "model_size_reduction": round(
                    size_saved,
                    4,
                ),
                "inference_speedup": round(
                    speedup,
                    4,
                ),
                "tokens_per_sec": profile.tokens_per_sec,
            }

        return result


def run_quantization_benchmark(
    model_path: str,
    prompt: str,
    *,
    output_dir: str | Path = "artifacts/optimization/quantization",
    max_new_tokens: int = 32,
    modes: list[QuantizationMode] | None = None,
) -> QuantizationBenchmarkReport:

    benchmark = QuantizationBenchmark(
        model_path=model_path,
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        modes=modes,
    )

    report = benchmark.run()

    report.save(Path(output_dir))

    return report
