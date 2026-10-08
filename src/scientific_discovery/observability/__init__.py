"""Observable, append-only execution tracing for benchmark runs."""

from .trace import EVENT_TYPES, TraceProvider, TraceRecorder, read_trace

__all__ = ["EVENT_TYPES", "TraceProvider", "TraceRecorder", "read_trace"]
