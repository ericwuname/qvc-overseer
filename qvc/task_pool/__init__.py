"""Task Pool — QVC discovers bugs, writes tasks for AI Agent to consume."""

from .writer import TaskPoolWriter
from .protocol import ProtocolGenerator

__all__ = ["TaskPoolWriter", "ProtocolGenerator"]
