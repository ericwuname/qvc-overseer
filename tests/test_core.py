"""测试套件入口"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import():
    from qvc import __version__
    assert __version__ == "0.6.1"


def test_models():
    from qvc.models import Severity, BugCategory, RootCause, Bug
    assert Severity.FATAL.level == 1
    assert Severity.MINOR.level == 4
    # Label updated in V5
    assert "变量作用域" in BugCategory.VAR_SCOPE.label
    assert len(list(BugCategory)) >= 10


def test_severity_from_string():
    """Test severity enum values"""
    from qvc.models.severity import Severity
    assert Severity.FATAL.level == 1
    assert Severity.FATAL.label == "致命"
    assert Severity.MINOR.level == 4


def test_scanner():
    from qvc.scanner import FileScanner
    scanner = FileScanner()
    fixtures_path = Path(__file__).parent / "fixtures" / "sample_bugs_py"
    files = scanner.scan(str(fixtures_path))
    assert len(files) >= 5


def test_rule_registry():
    from qvc.rules.registry import RuleRegistry
    from qvc.rules.python.variable_scope import PythonVariableScopeRule
    reg = RuleRegistry()
    rule = PythonVariableScopeRule()
    reg.register(rule)
    assert reg.rule_count == 1
    assert reg.get_rule("PY_VAR_SCOPE_001") is not None


def test_report():
    from qvc.models import Report, ScanSummary, Bug, Severity, BugCategory
    bugs = [Bug(id="T1", severity=Severity.FATAL, category=BugCategory.VAR_SCOPE,
                title="test", description="d", file_path="f.py",
                line_start=1, line_end=1, code_snippet="x", fix_suggestion="fix", rule_id="R1")]
    summary = ScanSummary(total_files=1, total_lines=10, languages=["python"])
    report = Report(project_name="test", scan_summary=summary, bugs=bugs)
    assert report.total_bugs == 1


def test_static_analyzer():
    from qvc.scanner import FileScanner
    from qvc.analyzers import StaticAnalyzer
    from qvc.rules.registry import registry as rule_registry
    from qvc.rules.python.variable_scope import PythonVariableScopeRule
    from qvc.rules.python.null_safety import PythonNullSafetyRule
    from qvc.rules.python.import_check import PythonImportCheckRule
    from qvc.rules.universal.encoding import EncodingCheckRule
    from qvc.rules.universal.dead_code import DeadCodeRule
    from qvc.rules.universal.regex_fragility import RegexFragilityRule

    if not rule_registry.get_all_rules():
        rule_registry.register_many([
            PythonVariableScopeRule(), PythonNullSafetyRule(),
            PythonImportCheckRule(), EncodingCheckRule(),
            DeadCodeRule(), RegexFragilityRule(),
        ])

    fixtures_path = Path(__file__).parent / "fixtures" / "sample_bugs_py"
    scanner = FileScanner()
    files = scanner.scan(str(fixtures_path))
    language_map = {fp: scanner.get_language(fp) for fp in files}

    analyzer = StaticAnalyzer(rule_registry)
    bugs = analyzer.analyze_files(files, language_map)

    bug1_found = any("sub_tasks" in b.title for b in bugs)
    assert bug1_found, "Should detect sub_tasks undefined variable"

    print(f"\nStatic analysis found {len(bugs)} bugs:")
    for b in bugs:
        print(f"  [{b.severity.name:8s}] {Path(b.file_path).name}:{b.line_start} - {b.title}")


if __name__ == "__main__":
    print("=" * 60)
    print("QVC - QA of Vebe Coding - Test Suite")
    print("=" * 60)

    tests = [
        ("import", test_import),
        ("models", test_models),
        ("severity", test_severity_from_string),
        ("scanner", test_scanner),
        ("rule_registry", test_rule_registry),
        ("report", test_report),
        ("static_analyzer", test_static_analyzer),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
