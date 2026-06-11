"""BlindspotAnalyzer 单元测试"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_classify_blindspots_on_bugs():
    """盲区分类：每个 bug 打上正确的 blindspot_type"""
    from qvc.analyzers.blindspot_analyzer import BlindspotAnalyzer
    from qvc.models.bug import Bug, Severity, BugCategory

    bugs = [
        Bug(id="T1", severity=Severity.SEVERE, category=BugCategory.VAR_SCOPE,
            title="变量作用域", description="d", file_path="f.py",
            line_start=1, line_end=1, code_snippet="x", fix_suggestion="",
            rule_id="PY_VAR_SCOPE_001"),
        Bug(id="T2", severity=Severity.SEVERE, category=BugCategory.NULL_SAFETY,
            title="空值安全", description="d", file_path="f.py",
            line_start=2, line_end=2, code_snippet="x", fix_suggestion="",
            rule_id="PY_NULL_SAFETY_001"),
        Bug(id="T3", severity=Severity.SEVERE, category=BugCategory.API_MISMATCH,
            title="API签名", description="d", file_path="f.py",
            line_start=3, line_end=3, code_snippet="x", fix_suggestion="",
            rule_id="PY_API_SIGNATURE_001"),
    ]

    analyzer = BlindspotAnalyzer()
    analyzer._classify_blindspots(bugs)

    assert bugs[0].blindspot_type == "memory_trap", f"PY_VAR_SCOPE → memory_trap, got {bugs[0].blindspot_type}"
    assert bugs[1].blindspot_type == "boundary", f"PY_NULL_SAFETY → boundary, got {bugs[1].blindspot_type}"
    assert bugs[2].blindspot_type == "context_lost", f"PY_API_SIGNATURE → context_lost, got {bugs[2].blindspot_type}"

    # All should be non-self-reviewable (structural blind spots)
    assert bugs[0].detectable_by_self_review == False
    assert bugs[1].detectable_by_self_review == False
    assert bugs[2].detectable_by_self_review == False


def test_mode_b_without_self_review():
    """模式 B：无自审报告 → 行业基准模式"""
    from qvc.analyzers.blindspot_analyzer import BlindspotAnalyzer
    from qvc.models.bug import Bug, Severity, BugCategory

    bugs = [
        Bug(id="T1", severity=Severity.SEVERE, category=BugCategory.VAR_SCOPE,
            title="test", description="d", file_path="f.py",
            line_start=1, line_end=1, code_snippet="x", fix_suggestion="",
            rule_id="PY_VAR_SCOPE_001"),
    ]

    report = BlindspotAnalyzer().analyze(bugs, self_review_path=None)
    assert report.mode == "B", f"Expected mode B, got {report.mode}"
    assert report.leak_rate > 0, f"Expected leak rate > 0, got {report.leak_rate}"
    assert report.total_qvc_bugs == 1
    assert "memory_trap" in report.blindspot_distribution


def test_mode_a_with_self_review():
    """模式 A：有自审报告 → 精确对比模式"""
    from qvc.analyzers.blindspot_analyzer import BlindspotAnalyzer
    from qvc.models.bug import Bug, Severity, BugCategory

    bugs = [
        Bug(id="T1", severity=Severity.SEVERE, category=BugCategory.VAR_SCOPE,
            title="变量未定义 sub_tasks", description="d", file_path="f.py",
            line_start=1, line_end=1, code_snippet="x", fix_suggestion="",
            rule_id="PY_VAR_SCOPE_001"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# AI Agent Self-Review\n\nCode quality: passed. No issues found.\n")
        report_path = f.name

    try:
        report = BlindspotAnalyzer().analyze(bugs, self_review_path=report_path)
        assert report.mode == "A", f"Expected mode A, got {report.mode}"
        assert report.self_review_available == True
        assert report.total_qvc_bugs == 1
        assert report.leak_rate == 1.0, f"Expected 100% leak rate, got {report.leak_rate:.0%}"
    finally:
        Path(report_path).unlink(missing_ok=True)


def test_mode_a_partial_match():
    """模式 A：自审报告发现了部分问题 → 漏报率 < 100%"""
    from qvc.analyzers.blindspot_analyzer import BlindspotAnalyzer
    from qvc.models.bug import Bug, Severity, BugCategory

    bugs = [
        Bug(id="T1", severity=Severity.SEVERE, category=BugCategory.VAR_SCOPE,
            title="变量未定义", description="d", file_path="a.py",
            line_start=1, line_end=1, code_snippet="x", fix_suggestion="",
            rule_id="PY_VAR_SCOPE_001"),
        Bug(id="T2", severity=Severity.SEVERE, category=BugCategory.NULL_SAFETY,
            title="空值安全", description="d", file_path="b.py",
            line_start=2, line_end=2, code_snippet="x", fix_suggestion="",
            rule_id="PY_NULL_SAFETY_001"),
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Review\nBug #1: 变量未定义\nFiles: a.py\n")
        report_path = f.name

    try:
        report = BlindspotAnalyzer().analyze(bugs, self_review_path=report_path)
        assert report.mode == "A"
        assert report.total_qvc_bugs == 2
        assert report.bugs_not_in_self_review == 1  # Only null_safety not found
        assert 0.4 < report.leak_rate < 0.6, f"Expected ~50%, got {report.leak_rate:.0%}"
    finally:
        Path(report_path).unlink(missing_ok=True)


def test_mode_c_no_bugs():
    """模式 C：0 缺陷 → 待激活模式"""
    from qvc.analyzers.blindspot_analyzer import BlindspotAnalyzer

    report = BlindspotAnalyzer().analyze([], self_review_path=None)
    assert report.mode == "C", f"Expected mode C, got {report.mode}"
    assert report.total_qvc_bugs == 0
    assert report.leak_rate == 0.0


if __name__ == "__main__":
    print("=" * 60)
    print("BlindspotAnalyzer Unit Tests")
    print("=" * 60)

    tests = [
        ("classify_blindspots", test_classify_blindspots_on_bugs),
        ("mode_b_no_self_review", test_mode_b_without_self_review),
        ("mode_a_with_self_review", test_mode_a_with_self_review),
        ("mode_a_partial_match", test_mode_a_partial_match),
        ("mode_c_no_bugs", test_mode_c_no_bugs),
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
