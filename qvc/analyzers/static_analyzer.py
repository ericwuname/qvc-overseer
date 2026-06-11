"""静态分析器 V2 —— 修复语言过滤"""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from qvc.models.bug import Bug
from qvc.rules.registry import RuleRegistry
from qvc.rules.base import BaseRule


class StaticAnalyzer:
    def __init__(self, registry: RuleRegistry, max_workers: int = 4):
        self.registry = registry
        self.max_workers = max_workers

    def analyze_file(
        self,
        file_path: Path,
        language: str,
        rules: list[BaseRule] | None = None,
    ) -> list[Bug]:
        if rules is None:
            rules = self.registry.get_rules_for_language(language)
            rules += [
                r for r in self.registry.get_all_rules()
                if "*" in r.languages and r not in rules
            ]
        else:
            # 即使外部传入了 rules，也按语言过滤
            rules = [r for r in rules if r.supports_language(language)]

        if not rules:
            return []

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            return []

        ast_tree = None
        if language == "python":
            try:
                import ast
                ast_tree = ast.parse(source)
            except SyntaxError:
                pass

        bugs = []
        for rule in rules:
            try:
                rule_bugs = rule.analyze(file_path, source, ast_tree)
                bugs.extend(rule_bugs)
            except Exception:  # intentional: one bad rule must not crash the scan
                pass

        return bugs

    def analyze_files(
        self,
        file_paths: list[Path],
        language_map: dict[Path, str] | None = None,
        rules: list[BaseRule] | None = None,
        progress_callback=None,
    ) -> list[Bug]:
        all_bugs = []
        total = len(file_paths)
        done = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for fp in file_paths:
                lang = language_map.get(fp, "unknown") if language_map else self._detect_language(fp)
                futures[executor.submit(self.analyze_file, fp, lang, rules)] = fp
            for future in as_completed(futures):
                try:
                    bugs = future.result()
                    all_bugs.extend(bugs)
                except Exception:
                    pass
                done += 1
                if progress_callback:
                    progress_callback(done, total, len(all_bugs))
        return self._deduplicate(all_bugs)

    def _detect_language(self, file_path: Path) -> str:
        ext_map = {
            ".py": "python", ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript",
        }
        return ext_map.get(file_path.suffix.lower(), "unknown")

    def _deduplicate(self, bugs: list[Bug]) -> list[Bug]:
        seen = set()
        unique = []
        for bug in bugs:
            key = (bug.file_path, bug.line_start, bug.rule_id, bug.title)
            if key not in seen:
                seen.add(key)
                unique.append(bug)
        return unique
