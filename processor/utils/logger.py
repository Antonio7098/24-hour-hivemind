"""
Structured logging setup for the Checklist Processor.

Provides clean, user-friendly logging with comprehensive status display.
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
        "blue": "\033[34m",
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

    # Phase order for display
    PHASE_ORDER = ["init", "research", "tests", "execution", "report"]

    def __init__(self, use_colors: bool = True, verbose: bool = False):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
        self.verbose = verbose
        # Track state across log messages
        self._state = {
            "iteration": 0,
            "max_iterations": 0,
            "batch_size": 1,
            "completed_count": 0,
            "total_count": 0,
            "failed_count": 0,
            "session_start": None,
            "current_item": None,
            "current_item_start": None,
        }

    def _color(self, name: str) -> str:
        return self.COLORS.get(name, "") if self.use_colors else ""

    def _reset(self) -> str:
        return self.COLORS["reset"] if self.use_colors else ""

    def _fmt_time(self, seconds: int) -> str:
        """Format seconds as M:SS or H:MM:SS."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            m, s = divmod(seconds, 60)
            return f"{m}:{s:02d}"
        else:
            h, m = divmod(seconds // 60, 60)
            s = seconds % 60
            return f"{h}:{m:02d}:{s:02d}"

    def _update_state(self, extra: dict) -> None:
        """Update tracked state from extra data."""
        if extra.get("iteration"):
            self._state["iteration"] = extra["iteration"]
        if extra.get("max_iterations"):
            self._state["max_iterations"] = extra["max_iterations"]
        if extra.get("batch_size"):
            self._state["batch_size"] = extra["batch_size"]
        if extra.get("completed_count") is not None:
            self._state["completed_count"] = extra["completed_count"]
        if extra.get("total_count"):
            self._state["total_count"] = extra["total_count"]
        if extra.get("failed_count") is not None:
            self._state["failed_count"] = extra["failed_count"]
        if extra.get("session_start"):
            self._state["session_start"] = extra["session_start"]

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
        """Format processor logs."""
        self._update_state(extra)

        if "Starting iteration" in message:
            parts = message.split("iteration")[1].strip().split("/")
            iteration = parts[0].strip()
            max_iter = parts[1].strip() if len(parts) > 1 else "?"
            self._state["iteration"] = int(iteration)
            self._state["max_iterations"] = int(max_iter) if max_iter.isdigit() else 0
            return ""

        if "Processing batch" in message:
            return ""

        if "Starting" in message and extra.get("tier"):
            item_id = message.split("Starting")[1].strip()
            self._state["current_item"] = item_id
            self._state["current_item_start"] = datetime.now()
            return ""

        if "Completed" in message:
            self._state["completed_count"] += 1
            return ""

        if "Failed" in message and extra.get("error_type"):
            self._state["failed_count"] += 1
            error_msg = (
                message.split(":", 1)[1].strip() if ":" in message else "Unknown"
            )
            return f"\n{self._color('red')}✗ {error_msg}{self._reset()}"

        if "Batch" in message and "complete" in message:
            return ""

        if "Processing complete" in message:
            processed = extra.get("processed", 0)
            completed = extra.get("completed", 0)
            failed = extra.get("failed", 0)
            lines = [f"\n{self._color('bold')}━━━ Final Summary ━━━{self._reset()}"]
            lines.append(
                f"  {self._color('green')}✓ Completed: {completed}{self._reset()}"
            )
            if failed > 0:
                lines.append(f"  {self._color('red')}✗ Failed: {failed}{self._reset()}")
            lines.append(
                f"  {self._color('dim')}Total processed: {processed}{self._reset()}"
            )
            return "\n".join(lines)

        if "All checklist items are complete" in message:
            return f"\n{self._color('green')}✓ All items complete!{self._reset()}"

        if "Reached max iterations" in message:
            return f"\n{self._color('yellow')}⚠ Reached max iterations{self._reset()}"

        if "Prioritizing" in message and "checkpoints" in message:
            count = message.split()[1]
            return f"{self._color('yellow')}↻ Resuming {count} incomplete items{self._reset()}"

        if "Re-queued" in message:
            return ""

        if "DRY RUN" in message:
            return f"{self._color('cyan')}○ {message}{self._reset()}"

        if self.verbose:
            return f"{self._color('dim')}[{record.name}] {message}{self._reset()}"

        return ""

    def _format_run_agent(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format run_agent logs with comprehensive status panel."""

        if "Progress:" in message:
            return self._format_status_panel(extra)

        if "Agent started" in message:
            return ""

        if "Resuming" in message and "checkpoint" in message:
            return ""

        if "Saved checkpoint" in message:
            return ""

        if "timed out" in message.lower():
            return f"\n{self._color('yellow')}⏱ Timeout, retrying...{self._reset()}"

        if self.verbose:
            return f"{self._color('dim')}[run_agent] {message}{self._reset()}"

        return ""

    def _format_status_panel(self, extra: dict) -> str:
        """Format a comprehensive status panel."""
        item_id = extra.get("item_id", "?")
        elapsed = extra.get("elapsed", 0)
        phase = extra.get("phase", "working")
        phase_sec = extra.get("phase_sec", 0)
        completed_phases = extra.get("completed_phases", [])

        # Status line: iteration, completed, time
        iter_num = self._state["iteration"]
        max_iter = self._state["max_iterations"]
        completed = self._state["completed_count"]
        failed = self._state["failed_count"]

        # Stages line - compact format
        stage_parts = []
        for p in self.PHASE_ORDER:
            if p in completed_phases:
                stage_parts.append(f"{self._color('green')}{p}✓{self._reset()}")
            elif p == phase:
                stage_parts.append(
                    f"{self._color('yellow')}{p}:{self._fmt_time(phase_sec)}{self._reset()}"
                )
            else:
                stage_parts.append(f"{self._color('dim')}{p}{self._reset()}")

        # If current phase not in PHASE_ORDER, add it at the end
        if phase not in self.PHASE_ORDER:
            stage_parts.append(
                f"{self._color('yellow')}{phase}:{self._fmt_time(phase_sec)}{self._reset()}"
            )

        stages_line = " → ".join(stage_parts)

        # Single compact line
        status = f"{self._color('bold')}▶ {item_id}{self._reset()} "
        status += f"{self._color('dim')}iter {iter_num}/{max_iter} │ {completed} done"
        if failed > 0:
            status += (
                f" {self._color('red')}{failed} fail{self._reset()}{self._color('dim')}"
            )
        status += f" │ {self._fmt_time(elapsed)}{self._reset()}\n  {stages_line}"

        return status

    def _format_observability(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format observability/stage logs."""
        return ""  # Suppress these for cleaner output

    def _format_checkpoint(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format checkpoint logs."""
        if self.verbose:
            return f"{self._color('dim')}[checkpoint] {message}{self._reset()}"
        return ""

    def _format_error(
        self, record: logging.LogRecord, message: str, extra: dict
    ) -> str:
        """Format error messages with clear visibility."""
        lines = []
        lines.append(f"\n{self._color('red')}{'─' * 60}{self._reset()}")
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

        lines.append(f"{self._color('red')}{'─' * 60}{self._reset()}")

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
