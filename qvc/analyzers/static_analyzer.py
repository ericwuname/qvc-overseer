"""Static analyzer V8 — with Python AST semantic context"""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from qvc.models.bug import Bug
from qvc.rules.registry import RuleRegistry
from qvc.rules.base import BaseRule


class StaticAnalyzer:
    def __init__(self, registry: RuleRegistry, max_workers: int = 4, use_ast: bool = True):
        self.registry = registry
        self.max_workers = max_workers
        self.use_ast = use_ast
        self._ast_analyzer = None  # Lazy init

    def _get_ast_analyzer(self):
        if self._ast_analyzer is None and self.use_ast:
            try:
                from qvc.analyzers.ast_analyzer import ASTAnalyzer
                self._ast_analyzer = ASTAnalyzer()
            except ImportError:
                self._ast_analyzer = None
        return self._ast_analyzer

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
            rules = [r for r in rules if r.supports_language(language)]

        if not rules:
            return []

        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            return []

        ast_tree = None
        ast_context = None
        if language == "python":
            try:
                import ast
                ast_tree = ast.parse(source)
                # V8: Build AST semantic context for better rule accuracy
                analyzer = self._get_ast_analyzer()
                if analyzer:
                    ast_context = analyzer.analyze(file_path, source)
            except SyntaxError:
                pass

        bugs = []
        for rule in rules:
            try:
                # V8: Pass ast_context to rules that accept it
                try:
                    rule_bugs = rule.analyze(file_path, source, ast_tree, ast_context=ast_context)
                except TypeError:
                    # Fallback for rules that don't accept ast_context
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