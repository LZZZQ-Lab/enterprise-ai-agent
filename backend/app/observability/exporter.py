from abc import ABC
from abc import abstractmethod
import json
from pathlib import Path

from app.core.logger import logger
from app.observability.serialization import trace_to_dict
from app.observability.types import Trace


class TraceExporter(ABC):
    """
    Trace 导出器抽象。

    预留 Langfuse / OpenTelemetry / Phoenix / W&B 等集成。
    """

    @abstractmethod
    def export(self, trace: Trace) -> None:
        pass


class ConsoleTraceExporter(TraceExporter):
    """
    默认导出器：输出到控制台日志。
    """

    def export(self, trace: Trace) -> None:

        logger.info(
            "Trace exported trace_id=%s session_id=%s "
            "duration=%.3fs events=%d",
            trace.trace_id,
            trace.session_id,
            trace.duration or 0.0,
            len(trace.events),
        )

        for index, event in enumerate(trace.events):

            logger.info(
                "  [%d] type=%s event_id=%s",
                index,
                event.event_type.value,
                event.event_id,
            )


class JSONTraceExporter(TraceExporter):
    """
    JSON 导出器（预留）。
    """

    def __init__(
        self,
        output_dir: str | Path = "traces",
    ):

        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def export(self, trace: Trace) -> None:

        path = (
            self._output_dir
            / f"{trace.trace_id}.json"
        )

        path.write_text(
            json.dumps(
                trace_to_dict(trace),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        logger.info(
            "Trace exported to JSON: %s",
            path,
        )


class FileTraceExporter(TraceExporter):
    """
    文件导出器（预留，与 JSON 类似可扩展格式）。
    """

    def __init__(
        self,
        output_dir: str | Path = "traces",
    ):

        self._json_exporter = JSONTraceExporter(
            output_dir=output_dir,
        )

    def export(self, trace: Trace) -> None:

        self._json_exporter.export(trace)


class OpenTelemetryTraceExporter(TraceExporter):
    """
    OpenTelemetry 导出器（预留）。
    """

    def export(self, trace: Trace) -> None:

        logger.info(
            "OpenTelemetryTraceExporter (stub): "
            "trace_id=%s events=%d",
            trace.trace_id,
            len(trace.events),
        )


def create_trace_exporter(
    exporter_type: str,
) -> TraceExporter:

    from app.config.settings import get_settings

    settings = get_settings()

    if exporter_type == "structured":

        from app.logging.trace_exporter import StructuredTraceExporter

        return StructuredTraceExporter(
            output_dir=settings.TRACE_EXPORT_DIR,
        )

    exporters = {
        "console": ConsoleTraceExporter,
        "json": JSONTraceExporter,
        "file": FileTraceExporter,
        "opentelemetry": OpenTelemetryTraceExporter,
    }

    exporter_cls = exporters.get(
        exporter_type,
        ConsoleTraceExporter,
    )

    if exporter_type == "json" or exporter_type == "file":

        return exporter_cls(output_dir=settings.TRACE_EXPORT_DIR)

    return exporter_cls()
