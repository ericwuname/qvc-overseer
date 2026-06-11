"""UNI_HYGIENE_001 — 项目卫生规范检查"""

import os
from pathlib import Path

from qvc.rules.base import BaseRule
from qvc.models.bug import Bug, Severity, BugCategory, RootCause


class HygieneRule(BaseRule):
    """检测不应提交到版本控制的文件和目录"""

    rule_id = "UNI_HYGIENE_001"
    name = "项目卫生检查"
    description = "检测 __pycache__/.pytest_cache/*.pyc/node_modules 等不应提交的文件"
    languages = ["universal", "python", "javascript", "typescript"]

    SHOULD_NOT_COMMIT = [
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        ".mypy_cache",
        ".ruff_cache",
        "*.pyc",
        "*.pyo",
        "*.egg-info",
        ".DS_Store",
        "Thumbs.db",
    ]

    def analyze(self, file_path: Path, source: str) -> list[Bug]:
        bugs = []
        path_str = str(file_path)
        parts = Path(path_str).parts

        for pattern in self.SHOULD_NOT_COMMIT:
            if pattern.startswith("*"):
                # Extension pattern like *.pyc
                ext = pattern[1:]
                if path_str.endswith(ext):
                    bugs.append(self._make_bug(file_path, pattern))
                    break
            elif pattern in parts:
                bugs.append(self._make_bug(file_path, pattern))
                break

        return bugs

    def _make_bug(self, file_path: Path, pattern: str) -> Bug:
        return Bug(
            id=f"HYGIENE-{hash(str(file_path)) & 0xFFFF:04x}",
            severity=Severity.MINOR,
            category=BugCategory.MISC,
            title=f"不应提交的文件: {file_path.name}",
            description=f"该文件匹配不应提交的模式 '{pattern}'，应在 .gitignore 中排除",
            file_path=str(file_path),
            line_start=1,
            line_end=1,
            code_snippet="",
            fix_suggestion=f"将 '{pattern}' 添加到 .gitignore 并删除已提交的缓存文件",
            confidence=0.98,
            rule_id=self.rule_id,
            root_cause=RootCause.TRIVIAL_MISTAKE,
            blindspot_type="self_harvest",
            detectable_by_self_review=False,
        )
