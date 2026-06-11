# -*- coding: utf-8 -*-
"""V2 回归测试套件 — V3.0 Phase 0 第一优先级

所有测试必须先 RED（确认 bug 存在），修复后全部 GREEN。
V2 原有测试不退化。
"""

import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════════════════════════════
# B1: 裸 except 不误报 except Exception:
# ═══════════════════════════════════════════════════════════

def test_bare_except_not_trigger_on_exception():
    """B1: except Exception: 不应被报为裸 except"""
    from qvc.rules.python.exception_handling import PythonExceptionHandlingRule
    import ast

    code = """
try:
    risky_call()
except Exception:
    logger.error("failed")
"""
    rule = PythonExceptionHandlingRule()
    bugs = rule.analyze(Path("test.py"), code, ast.parse(code))
    bare_except_bugs = [b for b in bugs if "bare_except" in (b.id or "")]
    assert len(bare_except_bugs) == 0, (
        f"except Exception: 不应被报为裸 except，实际检出 {len(bare_except_bugs)} 条"
    )


def test_bare_except_still_detects_real_bare():
    """B1 复核: 真正的裸 except: 仍然应被检出"""
    from qvc.rules.python.exception_handling import PythonExceptionHandlingRule
    import ast

    code = """
try:
    risky_call()
except:
    pass
"""
    rule = PythonExceptionHandlingRule()
    bugs = rule.analyze(Path("test.py"), code, ast.parse(code))
    bare_except_bugs = [b for b in bugs if "bare_except" in (b.id or "")]
    assert len(bare_except_bugs) >= 1, (
        f"真正的裸 except: 应被检出，实际检出 {len(bare_except_bugs)} 条"
    )


# ═══════════════════════════════════════════════════════════
# B2: 关键字参数不计入必需参数
# ═══════════════════════════════════════════════════════════

def test_keyword_args_not_confused_with_required():
    """B2: func(a, b, c=1) 不因 c=1 误报参数过多"""
    from qvc.rules.python.api_signature import PythonAPISignatureRule
    import ast

    code = """
def func(x, y):
    pass

def caller():
    func(a, b, c=1)
"""
    rule = PythonAPISignatureRule()
    bugs = rule.analyze(Path("test.py"), code, ast.parse(code))
    param_bugs = [b for b in bugs if "args" in (b.id or "").lower() or ("参数" in (b.title or "") and "func" in (b.title or ""))]
    assert len(param_bugs) == 0, (
        f"func(a,b,c=1) 不应因关键字参数误报，实际检出 {len(param_bugs)} 条: "
        + ", ".join(b.title for b in param_bugs)
    )


def test_keyword_args_still_detects_real_mismatch():
    """B2 复核: 真正的参数不足仍被检出"""
    from qvc.rules.python.api_signature import PythonAPISignatureRule
    import ast

    code = """
def func(x, y, z):
    pass

def caller():
    func(1)
"""
    rule = PythonAPISignatureRule()
    bugs = rule.analyze(Path("test.py"), code, ast.parse(code))
    assert len(bugs) >= 1, f"func(1) 参数不足应被检出，实际检出 {len(bugs)} 条"


# ═══════════════════════════════════════════════════════════
# B3: and 短路不求值 → 不报空值安全
# ═══════════════════════════════════════════════════════════

def test_and_short_circuit_not_null_safety():
    """B3: if x and x.method() 不应触发空值安全"""
    from qvc.rules.python.null_safety import PythonNullSafetyRule
    import ast

    code = """
def handler(auth):
    if auth and auth.startswith("Bearer"):
        return auth[7:]
    return None
"""
    rule = PythonNullSafetyRule()
    bugs = rule.analyze(Path("test.py"), code, ast.parse(code))
    null_bugs = [b for b in bugs if "空值" in (b.title or "")]
    assert len(null_bugs) == 0, (
        f"if auth and auth.startswith() 不应报空值安全（短路保护），实际检出 {len(null_bugs)} 条"
    )


def test_and_short_circuit_still_detects_without_guard():
    """B3 复核: 无 and 保护时仍应检出空值安全问题"""
    from qvc.rules.python.null_safety import PythonNullSafetyRule
    import ast

    code = """
def handler(auth):
    token = auth.startswith("Bearer")
    return token
"""
    rule = PythonNullSafetyRule()
    bugs = rule.analyze(Path("test.py"), code, ast.parse(code))
    assert len(bugs) >= 1, f"无 and 保护时应检出空值安全，实际检出 {len(bugs)} 条"


# ═══════════════════════════════════════════════════════════
# B4: _removed/ 目录应被排除
# ═══════════════════════════════════════════════════════════

def test_removed_dir_excluded_by_default():
    """B4: _removed/ 目录应在默认排除列表中"""
    from qvc.scanner.file_scanner import FileScanner

    scanner = FileScanner()
    assert "_removed" in scanner.exclude_dirs, (
        f"_removed 应在默认排除目录中，当前: {scanner.exclude_dirs}"
    )


def test_removed_dir_not_scanned():
    """B4 复核: _removed/ 下的文件不被扫描"""
    from qvc.scanner.file_scanner import FileScanner

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        removed_dir = root / "_removed"
        removed_dir.mkdir()
        (removed_dir / "old_code.py").write_text("x = 1", encoding="utf-8")
        (root / "main.py").write_text("print(1)", encoding="utf-8")

        scanner = FileScanner()
        files = scanner.scan(str(root))
        file_paths = [str(f) for f in files]

        assert any("main.py" in p for p in file_paths), "main.py 应被扫描"
        assert not any("_removed" in p for p in file_paths), (
            f"_removed/ 目录不应被扫描，实际扫描到: {file_paths}"
        )


# ═══════════════════════════════════════════════════════════
# B5: __init__.py 嵌套再导出
# ═══════════════════════════════════════════════════════════

def test_init_py_reexport_deep_nesting():
    """B5: from a.b.c import x 应在 __init__.py 再导出链中识别"""
    from qvc.rules.python.import_check import PythonImportCheckRule
    import ast

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # 创建嵌套包结构: a/b/c/__init__.py 再导出 d.py 中的 x
        pkg = root / "a" / "b" / "c"
        pkg.mkdir(parents=True)
        (root / "a" / "__init__.py").write_text("", encoding="utf-8")
        (root / "a" / "b" / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "__init__.py").write_text("from .d import x\n", encoding="utf-8")
        (pkg / "d.py").write_text("x = 42\n", encoding="utf-8")

        # 编写测试文件导入
        test_file = root / "main.py"
        code = "from a.b.c import x\nprint(x)\n"
        test_file.write_text(code, encoding="utf-8")

        rule = PythonImportCheckRule()
        bugs = rule.analyze(test_file, code, ast.parse(code))
        import_bugs = [b for b in bugs if "导入" in (b.title or "")]
        assert len(import_bugs) == 0, (
            f"有效的包内导入不应被报错，实际检出 {len(import_bugs)} 条: "
            + ", ".join(b.title for b in import_bugs)
        )


# ═══════════════════════════════════════════════════════════
# B6: except SyntaxError: pass 豁免
# ═══════════════════════════════════════════════════════════

def test_except_syntax_error_pass_exempted():
    """B6: except SyntaxError: pass 应豁免（合法静默模式）"""
    from qvc.rules.python.exception_handling import PythonExceptionHandlingRule
    import ast

    code = """
try:
    eval(user_input)
except SyntaxError:
    pass
"""
    rule = PythonExceptionHandlingRule()
    bugs = rule.analyze(Path("test.py"), code, ast.parse(code))
    silent_bugs = [b for b in bugs if "silent" in (b.id or "") or "静默" in (b.title or "")]
    assert len(silent_bugs) == 0, (
        f"except SyntaxError: pass 应豁免，实际检出 {len(silent_bugs)} 条"
    )


def test_except_syntax_error_pass_still_detects_other_silent():
    """B6 复核: 非 SyntaxError 的静默 pass 仍应检出"""
    from qvc.rules.python.exception_handling import PythonExceptionHandlingRule
    import ast

    code = """
try:
    do_stuff()
except ValueError:
    pass
"""
    rule = PythonExceptionHandlingRule()
    bugs = rule.analyze(Path("test.py"), code, ast.parse(code))
    assert len(bugs) >= 1, f"except ValueError: pass 应被检出（非豁免异常），实际检出 {len(bugs)} 条"


# ═══════════════════════════════════════════════════════════
# 运行入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("QVC V2 Regression Test Suite (Phase 0)")
    print("=" * 60)

    tests = [
        ("B1a-bare_except_not_on_Exception", test_bare_except_not_trigger_on_exception),
        ("B1b-real_bare_still_detected", test_bare_except_still_detects_real_bare),
        ("B2a-keyword_args_not_confused", test_keyword_args_not_confused_with_required),
        ("B2b-real_mismatch_still_detected", test_keyword_args_still_detects_real_mismatch),
        ("B3a-and_short_circuit_no_null", test_and_short_circuit_not_null_safety),
        ("B3b-no_guard_still_detected", test_and_short_circuit_still_detects_without_guard),
        ("B4a-_removed_in_excludes", test_removed_dir_excluded_by_default),
        ("B4b-_removed_not_scanned", test_removed_dir_not_scanned),
        ("B5-init_py_reexport", test_init_py_reexport_deep_nesting),
        ("B6a-SyntaxError_pass_exempt", test_except_syntax_error_pass_exempted),
        ("B6b-other_silent_still_detected", test_except_syntax_error_pass_still_detects_other_silent),
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
    if failed == 0:
        print(f"\n11/11 GREEN → Phase 0 通过!")
    else:
        print(f"\n还剩 {failed} 条 RED → 需要修复")



# ============================================================
# V4 new regression tests (12-25)
# ============================================================

def test_bom_detection_works():
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="wb") as f:
        f.write(b"\xef\xbb\xbfprint(42)\n")
        tmp = f.name
    try:
        from qvc.rules.universal.encoding import EncodingCheckRule
        from pathlib import Path
        rule = EncodingCheckRule()
        bugs = rule.analyze(Path(tmp), open(tmp, encoding="utf-8-sig").read())
        assert len(bugs) >= 1
    finally:
        os.unlink(tmp)


def test_bom_no_false_positive():
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
        f.write("print(42)\n")
        tmp = f.name
    try:
        from qvc.rules.universal.encoding import EncodingCheckRule
        from pathlib import Path
        rule = EncodingCheckRule()
        source = open(tmp, encoding="utf-8").read()
        bugs = rule.analyze(Path(tmp), source)
        bom_bugs = [b for b in bugs if "BOM" in (b.title or "")]
        assert len(bom_bugs) == 0
    finally:
        os.unlink(tmp)


def test_go_rule_detects_nil():
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".go", delete=False, mode="w", encoding="utf-8") as f:
        f.write("package main\ntype Data struct {}\nfunc (d *Data) Process() {}\nfunc run(d *Data) {\n  d.Process()\n}\n")
        tmp = f.name
    try:
        from qvc.rules.go.nil_safety import GoNilSafetyRule
        from pathlib import Path
        rule = GoNilSafetyRule()
        bugs = rule.analyze(Path(tmp), open(tmp, encoding="utf-8").read())
        assert len(bugs) >= 1, f"Expected nil detection, got {len(bugs)}"
    finally:
        os.unlink(tmp)


def test_go_rule_no_fp():
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".go", delete=False, mode="w", encoding="utf-8") as f:
        f.write("package main\nimport \"fmt\"\nfunc main() { fmt.Println(42) }\n")
        tmp = f.name
    try:
        from qvc.rules.go.nil_safety import GoNilSafetyRule
        from pathlib import Path
        rule = GoNilSafetyRule()
        bugs = rule.analyze(Path(tmp), open(tmp, encoding="utf-8").read())
        assert len(bugs) == 0
    finally:
        os.unlink(tmp)


def test_go_language_detection():
    from qvc.scanner.file_scanner import FileScanner
    from pathlib import Path
    scanner = FileScanner()
    lang = scanner.get_language(Path("test.go"))
    assert lang == "go"


def test_diff_flag_registered():
    from click.testing import CliRunner
    from qvc.cli import main
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert "--diff" in result.output


def test_sarif_valid_json():
    import json, tempfile, os
    from datetime import datetime
    from qvc.reporters.sarif_reporter import SARIFReporter
    from qvc.models.report import Report, ScanSummary
    from qvc.models.bug import Bug, Severity, BugCategory
    from pathlib import Path
    bug = Bug(id="T1", severity=Severity.MODERATE, category=BugCategory.STYLE,
              title="T", description="D", file_path="f.py",
              line_start=1, line_end=1, confidence=0.80, rule_id="R1",
              code_snippet="test")
    summary = ScanSummary(total_files=1, total_lines=10, languages=["python"])
    report = Report(project_name="test", scan_summary=summary, bugs=[bug])
    report.generated_at = datetime.now()
    reporter = SARIFReporter()
    out = reporter.generate(report, Path(tempfile.gettempdir() + "/test_sarif"))
    with open(out, encoding="utf-8") as f:
        data = json.load(f)
    assert data["version"] == "2.1.0"
    assert len(data["runs"]) >= 1
    os.unlink(out)


def test_gene_pool_preserves_state():
    from qvc.evolution import GenePool
    gp1 = GenePool()
    c1 = gp1.get_total_count()
    gp2 = GenePool()
    c2 = gp2.get_total_count()
    assert c1 == c2
    assert c1 >= 50


def test_friendly_error_wrapper_exists():
    from qvc.cli import _friendly_error_wrapper
    assert callable(_friendly_error_wrapper)


def test_full_scan_flag():
    from click.testing import CliRunner
    from qvc.cli import main
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert "--full" in result.output


def test_progress_callback_integration():
    from qvc.analyzers.static_analyzer import StaticAnalyzer
    import inspect
    sig = inspect.signature(StaticAnalyzer.analyze_files)
    assert "progress_callback" in sig.parameters


def test_core_rules_still_loaded():
    from qvc.cli import _register_builtin_rules
    from qvc.rules.registry import registry as reg
    _register_builtin_rules()
    rule_ids = {r.rule_id for r in reg.get_all_rules()}
    required = {"PY_VAR_SCOPE_001", "JS_VAR_SCOPE_001", "UNI_ENCODING_001", "REACT_USE_EFFECT_DEPS_001"}
    missing = required - rule_ids
    assert not missing


def test_go_rule_registered():
    from qvc.cli import _register_builtin_rules
    from qvc.rules.registry import registry as reg
    _register_builtin_rules()
    rule_ids = {r.rule_id for r in reg.get_all_rules()}
    assert "GO_NIL_SAFETY_001" in rule_ids
