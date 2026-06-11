"""扫描器基类"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseScanner(ABC):
    """代码扫描器基类"""

    @abstractmethod
    def scan(self, target: str) -> list[Path]:
        """扫描目标，返回文件路径列表"""
        ...

    def get_language(self, file_path: Path) -> str:
        """根据文件扩展名识别语言"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".sql": "sql",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".vue": "vue",
            ".svelte": "svelte",
        }
        ext = file_path.suffix.lower()
        return ext_map.get(ext, "unknown")
