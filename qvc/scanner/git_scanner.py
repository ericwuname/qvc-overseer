"""Git 仓库扫描器"""

import tempfile
import shutil
from pathlib import Path
from .base import BaseScanner
from .file_scanner import FileScanner


class GitScanner(BaseScanner):
    """Git 仓库扫描器 —— clone 仓库后扫描"""

    def __init__(
        self,
        branch: str | None = None,
        depth: int = 50,
        file_scanner: FileScanner | None = None,
    ):
        self.branch = branch
        self.depth = depth
        self.file_scanner = file_scanner or FileScanner()
        self._temp_dir: str | None = None

    def scan(self, target: str) -> list[Path]:
        try:
            from git import Repo
        except ImportError:
            raise ImportError(
                "需要 GitPython 库。请安装: pip install gitpython"
            )

        self._temp_dir = tempfile.mkdtemp(prefix="qvc_git_")

        clone_kwargs = {"depth": self.depth}
        if self.branch:
            clone_kwargs["branch"] = self.branch

        Repo.clone_from(target, self._temp_dir, **clone_kwargs)

        return self.file_scanner.scan(self._temp_dir)

    def cleanup(self):
        """清理临时目录"""
        if self._temp_dir and Path(self._temp_dir).exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None

    def __del__(self):
        self.cleanup()
