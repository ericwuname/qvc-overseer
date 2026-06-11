"""文件系统扫描器"""

import os
from pathlib import Path
from .base import BaseScanner


class FileScanner(BaseScanner):
    """本地文件系统扫描器"""

    DEFAULT_EXCLUDE_DIRS = {
        "__pycache__", ".git", ".svn", ".hg",
        "node_modules", "venv", ".venv", "env", "fixtures",
        ".idea", ".vscode", "dist", "build",
        ".next", ".nuxt", "vendor", "target",
        "__MACOSX", ".DS_Store", "_removed",
    }

    DEFAULT_EXCLUDE_PATTERNS = [
        "*.pyc", "*.pyo", "*.so", "*.dll", "*.dylib",
        "*.min.js", "*.min.css", "*.bundle.js",
        "*.lock", "package-lock.json", "yarn.lock",
        "*.log", "*.bak", "*.swp",
    ]

    def __init__(
        self,
        exclude_dirs: set[str] | None = None,
        exclude_patterns: list[str] | None = None,
        include_extensions: list[str] | None = None,
    ):
        self.exclude_dirs = exclude_dirs or self.DEFAULT_EXCLUDE_DIRS
        self.exclude_patterns = exclude_patterns or self.DEFAULT_EXCLUDE_PATTERNS
        self.include_extensions = include_extensions

    def scan(self, target: str) -> list[Path]:
        target_path = Path(target).resolve()

        if target_path.is_file():
            if self._should_include(target_path):
                return [target_path]
            return []

        if not target_path.is_dir():
            raise FileNotFoundError(f"路径不存在: {target}")

        files = []
        for root, dirs, filenames in os.walk(str(target_path)):
            # 排除目录
            dirs[:] = [
                d for d in dirs
                if d not in self.exclude_dirs and not d.startswith(".")
            ]

            for filename in filenames:
                file_path = Path(root) / filename
                if self._should_include(file_path):
                    files.append(file_path)

        return sorted(files)

    def _should_include(self, file_path: Path) -> bool:
        """判断文件是否应被包含"""
        import fnmatch

        # 跳过二进制/非代码文件
        lang = self.get_language(file_path)
        if lang == "unknown":
            return False

        # 如果指定了扩展名白名单
        if self.include_extensions:
            if file_path.suffix.lower() not in self.include_extensions:
                return False

        # 检查排除模式
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path.name, pattern):
                return False

        # 跳过超大文件 (>5MB)
        try:
            if file_path.stat().st_size > 5 * 1024 * 1024:
                return False
        except OSError:
            return False

        return True
