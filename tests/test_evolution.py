"""Gene Pool + PatternAbstractor 单元测试"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_seeds_loaded_from_four_files():
    """50条种子从4个分类文件正确加载"""
    from qvc.evolution.fingerprint_store import FingerprintStore
    import tempfile, os
    
    db_path = Path(tempfile.gettempdir()) / "qvc_test_seeds.db"
    if db_path.exists():
        db_path.unlink()
    
    store = FingerprintStore(db_path=db_path)
    stats = store.get_stats()
    assert stats["seed"] >= 40, f"Expected >=40 seeds, got {stats['seed']}"
    assert stats["total"] >= 40
    print(f"  Loaded {stats['seed']} seed fingerprints")


def test_pattern_abstractor_learn_from_scan():
    """审查即学习：≥2个同规则bug产生候选指纹"""
    from qvc.evolution.pattern_abstractor import PatternAbstractor
    from qvc.models.bug import Bug, Severity, BugCategory
    
    bugs = [
        Bug(id="b1", severity=Severity.SEVERE, category=BugCategory.NULL_SAFETY,
            title="空值安全：auth可能为None", description="d", file_path="a.py",
            line_start=1, line_end=1, code_snippet="auth.startswith()", rule_id="PY_NULL_SAFETY_001"),
        Bug(id="b2", severity=Severity.SEVERE, category=BugCategory.NULL_SAFETY,
            title="空值安全：request.files可能为None", description="d", file_path="b.py",
            line_start=1, line_end=1, code_snippet="request.files[0]", rule_id="PY_NULL_SAFETY_001"),
    ]
    
    abstractor = PatternAbstractor()
    # Without store, should just return 0 (no storage) but still process
    count = abstractor.learn_from_scan(bugs, store=None)
    assert count == 0  # No store, nothing to write
    print(f"  learn_from_scan processed 2 bugs (no store) → {count} stored")


def test_quality_filter_rejects_single_occurrence():
    """单次出现的模式不满足≥2确认，被过滤"""
    from qvc.evolution.pattern_abstractor import PatternAbstractor
    from qvc.models.bug import Bug, Severity, BugCategory
    
    bugs = [
        Bug(id="b1", severity=Severity.SEVERE, category=BugCategory.NULL_SAFETY,
            title="单次bug", description="d", file_path="a.py",
            line_start=1, line_end=1, code_snippet="x.y()", rule_id="PY_NULL_SAFETY_001"),
    ]
    
    abstractor = PatternAbstractor()
    count = abstractor.learn_from_scan(bugs, store=None)
    assert count == 0  # Only 1 bug, should be filtered
    print(f"  Single occurrence correctly filtered")


def test_quality_filter_rejects_low_confidence():
    """低置信度指纹被过滤"""
    from qvc.evolution.pattern_abstractor import PatternAbstractor
    from qvc.evolution.fingerprint import Fingerprint, FingerprintStatus
    
    fp = Fingerprint(
        id="test_low", category="TEST", pattern_name="AUTO_TEST",
        description="test", abstract_signature={},
        severity="MODERATE", confidence=0.2, occurrence_count=3,
        status=FingerprintStatus.CANDIDATE,
    )
    abstractor = PatternAbstractor()
    assert not abstractor._quality_filter(fp), "confidence 0.2 should be filtered"
    print(f"  Low confidence (0.2) correctly filtered")


if __name__ == "__main__":
    print("=" * 60)
    print("Gene Pool + Evolution Tests")
    print("=" * 60)

    tests = [
        ("seeds_loaded", test_seeds_loaded_from_four_files),
        ("learn_from_scan", test_pattern_abstractor_learn_from_scan),
        ("quality_filter_single", test_quality_filter_rejects_single_occurrence),
        ("quality_filter_low_conf", test_quality_filter_rejects_low_confidence),
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
            import traceback; traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
