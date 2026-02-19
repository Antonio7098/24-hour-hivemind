"""
Structured logging setup for the Checklist Processor.

Provides clean, user-friendly logging with tier/item/stage visibility.
"""

import logging
import sys
from datetime import datetime
from typing import Any


class CleanFormatter(logging.Formatter):
    """Clean, user-friendly formatter for processor output."""

    COLORS = {
        "dim": "\033[90m",
        "cyan": "\033[36m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "red": "\033[31m",
        "magenta": "\033[35m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }

    LEVEL_COLORS = {
        logging.DEBUG: "dim",
        logging.INFO: "cyan",
        logging.WARNING: "yellow",
        logging.ERROR: "red",
        logging.CRITICAL: "magenta",
    }

    NOISY_LOGGERS = {
        "stageflow",
        "asyncio",
        "httpx",
        "httpcore",
        "urllib3",
    }

    def __init__(self, use_colors: bool = True, verbose: bool = False):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
        self.verbose = verbose
        self._last_tier = None
        self._last_item = None

    def _color(self, name: str) -> str:
        return self.COLORS.get(name, "") if self.use_colors else ""

    def _reset(self) -> str:
        return self.COLORS["reset"] if self.use_colors else ""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        extra = getattr(record, "extra_data", {}) or {}
        logger_name = record.name

        if record.levelno >= logging.ERROR:
            return self._format_error(record, message, extra)

        if logger_name == "processor":
            return self._format_processor(record, message, extra)

        if logger_name == "run_agent":
            return self._format_run_agent(record, message, extra)

        if logger_name == "observability":
            return self._format_observability(record, message, extra)

        if logger_name == "checkpoint":
            if record.levelno == logging.DEBUG and not self.verbose:
                return ""
            return self._format_checkpoint(record, message, extra)

        if logger_name in self.NOISY_LOGGERS and not self.verbose:
            return ""

        if record.levelno == logging.DEBUG and not self.verbose:
            return ""

        if record.levelno == logging.INFO and logger_name not in (
            "processor",
            "run_agent",
            "cli",
        ):
            if not self.verbose:
                return ""

        return self._format_default(record, message, extra)

    def _format_processor(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format processor logs with tier/item context."""
        lines = []

        tier = extra.get("tier")
        target = extra.get("target")
        items = extra.get("items", [])
        error_type = extra.get("error_type")

        if "Starting iteration" in message:
            iteration = message.split("iteration")[1].split("/")[0].strip()
            lines.append(
                f"\n{self._color('bold')}━━━ Iteration {iteration} ━━━{self._reset()}"
            )
            return "\n".join(lines)

        if "Starting" in message and tier:
            item_id = message.split("Starting")[1].strip()
            tier_short = (
                tier.replace("Tier ", "T").split(":")[0] if ":" in tier else tier
            )
            lines.append(
                f"\n{self._color('cyan')}▶ {item_id}{self._reset()} {self._color('dim')}[{tier_short}]{self._reset()}"
            )
            if target:
                lines.append(f"  {self._color('dim')}Target: {target}{self._reset()}")
            return "\n".join(lines)

        if "Completed" in message:
            item_id = message.split("Completed")[1].strip()
            duration = extra.get("duration_ms", 0)
            duration_sec = duration / 1000
            lines.append(
                f"  {self._color('green')}✓ Completed{self._reset()} {self._color('dim')}({duration_sec:.1f}s){self._reset()}"
            )
            return "\n".join(lines)

        if "Failed" in message and error_type:
            item_id = message.split("Failed")[1].split(":")[0].strip()
            error_msg = (
                message.split(":", 1)[1].strip() if ":" in message else "Unknown error"
            )
            lines.append(f"  {self._color('red')}✗ Failed{self._reset()}")
            lines.append(f"    {self._color('red')}Error: {error_msg}{self._reset()}")
            return "\n".join(lines)

        if "Processing batch" in message and items:
            lines.append(
                f"{self._color('dim')}Processing: {', '.join(items[:5])}{' ...' if len(items) > 5 else ''}{self._reset()}"
            )
            return "\n".join(lines)

        if "Batch" in message and "complete" in message:
            completed = (
                message.split("completed")[0].split(",")[-1].strip().split()[0]
                if "completed" in message
                else "0"
            )
            failed = (
                message.split("failed")[0].split(",")[-1].strip().split()[0]
                if "failed" in message
                else "0"
            )
            retry = (
                "to retry" in message
                and message.split("to retry")[0].split(",")[-1].strip().split()[0]
                or "0"
            )

            status = f"{self._color('green')}✓ {completed} done{self._reset()}"
            if int(failed) > 0:
                status += f" {self._color('red')}✗ {failed} failed{self._reset()}"
            if int(retry) > 0:
                status += f" {self._color('yellow')}↻ {retry} retry{self._reset()}"
            lines.append(status)
            return "\n".join(lines)

        if "Processing complete" in message:
            processed = extra.get("processed", 0)
            completed = extra.get("completed", 0)
            failed = extra.get("failed", 0)
            lines.append(f"\n{self._color('bold')}━━━ Summary ━━━{self._reset()}")
            lines.append(
                f"  {self._color('green')}✓ Completed: {completed}{self._reset()}"
            )
            if failed > 0:
                lines.append(f"  {self._color('red')}✗ Failed: {failed}{self._reset()}")
            lines.append(f"  {self._color('dim')}Total: {processed}{self._reset()}")
            return "\n".join(lines)

        if "All checklist items are complete" in message:
            return f"\n{self._color('green')}✓ All items complete!{self._reset()}"

        if "Reached max iterations" in message:
            return f"{self._color('yellow')}⚠ Reached max iterations{self._reset()}"

        if "Prioritizing" in message and "checkpoints" in message:
            count = message.split()[1]
            return f"{self._color('yellow')}↻ Resuming {count} incomplete items{self._reset()}"

        if "Re-queued" in message:
            count = message.split()[1]
            return f"  {self._color('yellow')}↻ {count} items queued for retry{self._reset()}"

        if "DRY RUN" in message:
            return f"{self._color('cyan')}○ {message}{self._reset()}"

        if self.verbose:
            return f"{self._color('dim')}[{record.name}] {message}{self._reset()}"

        return ""

    def _format_run_agent(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format run_agent logs."""
        if "Progress:" in message:
            elapsed = extra.get("elapsed", 0)
            phase = extra.get("phase", "working")
            phase_sec = extra.get("phase_sec", 0)
            completed = extra.get("completed_phases", [])

            def fmt_time(s):
                if s < 60:
                    return f"{s}s"
                m, s = s // 60, s % 60
                return f"{m}:{s:02d}"

            # Build progress line: completed phases with ✓, current phase with time
            parts = []
            for p in completed:
                parts.append(f"{p} ✓")
            parts.append(f"{phase} {fmt_time(phase_sec)}")

            progress_line = " → ".join(parts)
            total_str = fmt_time(elapsed)

            return f"  {self._color('dim')}⏳ {progress_line} (total {total_str}){self._reset()}"

        if "Agent started" in message:
            timeout = extra.get("timeout_sec", 0)
            mins = timeout // 60
            return f"  {self._color('dim')}⚙ Agent running (timeout: {mins}m){self._reset()}"

        if "Resuming" in message and "checkpoint" in message:
            phase = message.split("phase=")[1] if "phase=" in message else "unknown"
            return f"  {self._color('yellow')}↻ Resuming from {phase}{self._reset()}"

        if "Saved checkpoint" in message:
            phase = message.split("phase=")[1] if "phase=" in message else ""
            return f"  {self._color('dim')}Checkpoint saved: {phase}{self._reset()}"

        if "timed out" in message.lower():
            attempt = ""
            if "attempt" in message:
                attempt = message.split("attempt")[1].split(")")[0].strip()
                attempt = f" (attempt {attempt})"
            return f"  {self._color('yellow')}⏱ Timeout{attempt}{self._reset()}"

        if self.verbose:
            return f"{self._color('dim')}[run_agent] {message}{self._reset()}"

        return ""

    def _format_observability(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format observability/stage logs."""
        stage_name = extra.get("stage", "")
        duration = extra.get("duration_ms", 0)

        if "▶" in message:
            return f"  {self._color('dim')}→ {stage_name}{self._reset()}"

        if "✓" in message:
            return f"  {self._color('green')}  ✓ {stage_name}{self._reset()} {self._color('dim')}({duration}ms){self._reset()}"

        if "✗" in message:
            error = extra.get("error", "")
            return f"  {self._color('red')}  ✗ {stage_name}{self._reset()}\n    {self._color('red')}{error}{self._reset()}"

        if "⊘" in message:
            reason = extra.get("reason", "skipped")
            return f"  {self._color('dim')}⊘ {stage_name}: {reason}{self._reset()}"

        return ""

    def _format_checkpoint(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format checkpoint logs."""
        if "Detected existing progress" in message:
            phase = message.split("phase=")[1] if "phase=" in message else ""
            item = (
                message.split("for")[1].split(":")[0].strip()
                if "for" in message
                else ""
            )
            return f"  {self._color('yellow')}↻ Found checkpoint for {item}: {phase}{self._reset()}"

        if self.verbose:
            return f"{self._color('dim')}[checkpoint] {message}{self._reset()}"

        return ""

    def _format_error(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format error messages with clear visibility."""
        lines = []
        lines.append(f"\n{self._color('red')}{'─' * 50}{self._reset()}")
        lines.append(f"{self._color('red')}✗ ERROR{self._reset()}")

        if extra.get("item_id"):
            lines.append(f"  Item: {extra['item_id']}")
        if extra.get("tier"):
            lines.append(f"  Tier: {extra['tier']}")
        if extra.get("stage"):
            lines.append(f"  Stage: {extra['stage']}")

        error_type = extra.get("error_type", type(record).__name__)
        lines.append(f"  {self._color('red')}{error_type}: {message}{self._reset()}")

        if extra.get("exit_code"):
            lines.append(f"  Exit code: {extra['exit_code']}")
        if extra.get("log_path"):
            lines.append(f"  Log: {extra['log_path']}")

        lines.append(f"{self._color('red')}{'─' * 50}{self._reset()}")

        return "\n".join(lines)

    def _format_default(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format other logs with minimal noise."""
        level_name = record.levelname
        color = self._color(self.LEVEL_COLORS.get(record.levelno, ""))

        timestamp = datetime.now().strftime("%H:%M:%S")

        if record.levelno >= logging.WARNING:
            return f"{color}[{timestamp}] {level_name}: {message}{self._reset()}"

        if self.verbose:
            return f"{self._color('dim')}[{timestamp}] [{record.name}] {message}{self._reset()}"

        return ""


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that adds context to all log messages."""

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = kwargs.get("extra", {})
        if self.extra:
            extra.update(self.extra)
        kwargs["extra"] = extra

        if extra:
            kwargs.setdefault("extra", {})["extra_data"] = extra

        return msg, kwargs


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    if quiet:
        level = logging.WARNING

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CleanFormatter(use_colors=True, verbose=verbose))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str, **context) -> ContextLogger:
    """Get a context-aware logger."""
    logger = logging.getLogger(name)
    return ContextLogger(logger, context)
