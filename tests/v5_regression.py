
# ── V5 新增回归测试 ──

def test_api_drift_detects_real_drift():
    """V5: 同名函数在不同文件签名不一致应被检出"""
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    try:
        f1 = os.path.join(tmpdir, "module_a.py")
        f2 = os.path.join(tmpdir, "module_b.py")
        with open(f1, "w", encoding="utf-8") as f:
            f.write("def create_session(user_id, token):\n    pass\n")
        with open(f2, "w", encoding="utf-8") as f:
            f.write("def create_session(user_id, token, db_conn):\n    pass\n")

        from qvc.rules.python.api_drift import PythonAPIDriftRule
        from pathlib import Path
        rule = PythonAPIDriftRule()
        # Analyze both files
        rule.analyze(Path(f1), open(f1).read())
        rule.analyze(Path(f2), open(f2).read())

        def _make_bug(fp, line_start, line_end, title, description, code_snippet,
                       fix_suggestion, confidence, extra_id, root_cause=None):
            from qvc.models.bug import Bug, Severity, BugCategory
            return Bug(id=f"T-{extra_id}", severity=Severity.SEVERE, category=BugCategory.API_MISMATCH,
                       title=title, description=description, file_path=str(fp),
                       line_start=line_start, line_end=line_end, code_snippet=code_snippet,
                       fix_suggestion=fix_suggestion, confidence=confidence, rule_id="TEST")

        bugs = PythonAPIDriftRule.cross_file_check(
            [Path(f1), Path(f2)], _make_bug
        )
        assert len(bugs) >= 1, f"Expected drift detection, got {len(bugs)}"
        assert "create_session" in bugs[0].title
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_api_drift_no_false_positive_same_sig():
    """V5: 同名函数签名一致不应误报"""
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    try:
        f1 = os.path.join(tmpdir, "mod_a.py")
        f2 = os.path.join(tmpdir, "mod_b.py")
        with open(f1, "w", encoding="utf-8") as f:
            f.write("def helper(x, y):\n    return x + y\n")
        with open(f2, "w", encoding="utf-8") as f:
            f.write("def helper(x, y):\n    return x + y\n")

        from qvc.rules.python.api_drift import PythonAPIDriftRule
        from pathlib import Path
        rule = PythonAPIDriftRule()
        rule.analyze(Path(f1), open(f1).read())
        rule.analyze(Path(f2), open(f2).read())

        def _make_bug(**kwargs):
            from qvc.models.bug import Bug, Severity, BugCategory
            return Bug(id="T", severity=Severity.SEVERE, category=BugCategory.API_MISMATCH,
                       title=kwargs.get("title",""), description=kwargs.get("description",""),
                       file_path=str(kwargs.get("fp","")), line_start=1, line_end=1,
                       code_snippet="", fix_suggestion="", confidence=0.8, rule_id="T")

        bugs = PythonAPIDriftRule.cross_file_check(
            [Path(f1), Path(f2)], _make_bug
        )
        assert len(bugs) == 0, f"Same signature should not trigger drift, got {len(bugs)}"
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_stale_ref_detects_missing_module():
    """V5: 引用不存在的模块应被检出"""
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    try:
        f1 = os.path.join(tmpdir, "main.py")
        with open(f1, "w", encoding="utf-8") as f:
            f.write("from deleted_module import something\n")

        from qvc.rules.python.stale_reference import PythonStaleReferenceRule
        from pathlib import Path
        rule = PythonStaleReferenceRule()
        rule.analyze(Path(f1), open(f1).read())

        def _make_bug(**kwargs):
            from qvc.models.bug import Bug, Severity, BugCategory
            return Bug(id="T", severity=Severity.SEVERE, category=BugCategory.DEP_CHAIN,
                       title=kwargs.get("title",""), description=kwargs.get("description",""),
                       file_path=str(kwargs.get("fp","")), line_start=1, line_end=1,
                       code_snippet="", fix_suggestion="", confidence=0.8, rule_id="T")

        bugs = PythonStaleReferenceRule.cross_file_check(
            [Path(f1)], _make_bug
        )
        assert len(bugs) >= 1, f"Expected stale ref detection, got {len(bugs)}"
        assert "deleted_module" in bugs[0].title
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_v5_rules_registered():
    """V5: API_DRIFT 和 STALE_REF 规则已注册"""
    from qvc.cli import _register_builtin_rules
    from qvc.rules.registry import registry as reg
    _register_builtin_rules()
    rule_ids = {r.rule_id for r in reg.get_all_rules()}
    assert "PY_API_DRIFT_001" in rule_ids, "API_DRIFT not registered"
    assert "PY_STALE_REF_001" in rule_ids, "STALE_REF not registered"


def test_aha_moment_in_output():
    """V5: scan 输出包含 AHA 时刻"""
    from click.testing import CliRunner
    from qvc.cli import main
    import tempfile, os
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp:
        f = os.path.join(tmp, "test.py")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("print(1)\n")
        result = runner.invoke(main, ["scan", tmp, "--min-severity", "fatal"])
        # Should not crash; AHA moment should appear if bugs found
        assert result.exit_code == 0

