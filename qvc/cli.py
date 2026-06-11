"""CLI 入口 —— qvc 命令行工具 v4.0a1 外部监工·信任版"""

import sys
import time
from pathlib import Path

import click

from qvc import __version__
from qvc.config import ScanConfig
from qvc.scanner import FileScanner, GitScanner
from qvc.analyzers.static_analyzer import StaticAnalyzer
from qvc.analyzers.llm_reviewer import LLMReviewer
from qvc.reporters import MarkdownReporter, JSONReporter, SARIFReporter
from qvc.rules.registry import registry as rule_registry
from qvc.models.report import Report, ScanSummary
from qvc.models.bug import Severity
from qvc.evolution import (
    EvolutionCycle, FingerprintStore, GapDetector,
    Contributor, GenePoolSyncer, FingerprintStatus,
)
from qvc.task_pool import TaskPoolWriter, ProtocolGenerator
from qvc.analyzers.post_process import post_process
from datetime import datetime


def _show_aha_moments(bugs, blindspot_report):
    """V5 AHA时刻——高亮AI结构性盲区检测"""
    blindspot_bugs = [b for b in bugs if not b.detectable_by_self_review and b.confidence >= 0.80]
    if not blindspot_bugs:
        return
    click.echo()
    click.echo("-" * 58)
    click.echo("  [AHA] Your AI cannot see these")
    click.echo("-" * 58)
    for b in blindspot_bugs[:3]:
        label_map = {"memory_trap": "memory residue", "context_lost": "context lost",
                     "self_harvest": "self harvest", "cross_file": "cross file",
                     "boundary": "boundary condition"}
        bt_label = label_map.get(b.blindspot_type, b.blindspot_type or "unknown")
        click.echo(f"  [{b.confidence:.0%}] {b.title}")
        click.echo(f"       blindspot: {bt_label} | AI self-detectable: NO")
    click.echo(f"")
    click.echo(f"  Your AI Agent structurally cannot see these {len(blindspot_bugs)} issues.")
    click.echo(f"  This is why QVC exists as an external overseer.")
    if blindspot_report and blindspot_report.leak_rate > 0:
        click.echo(f"  AI missed rate (what your Agent did NOT find): {blindspot_report.leak_rate:.0%}")
    click.echo(f"")
    click.echo(f"  Full report: qvc-report.md")

    # V5: propagation hook
    fatal_count = len([b for b in bugs if b.confidence >= 0.90])
    if fatal_count > 0:
        click.echo()
        click.echo("-" * 58)
        click.echo("  If this helped, share with your team:")
        click.echo("-" * 58)
        click.echo(f"  \"QVC found {fatal_count} issues my AI reviewer and I both missed.\"")
        click.echo(f"  Try: pip install qvc-overseer && qvc scan .")
def _show_limitations(bugs, config):
    """V3.1 能力自白"""
    hints = []
    mid_conf = [b for b in bugs if 0.6 <= b.confidence < 0.9]
    if mid_conf and not config.llm.enabled:
        hints.append(dict(what='{} 条缺陷我只有 60-85% 的把握'.format(len(mid_conf)),
            how='qvc scan . --llm --llm-provider local',
            detail='我可以通过 Ollama（免费）逐条验证，通常能把其中大部分的置信度推到 90%+。',
            cost='免费（需 Ollama）或 ~.02/次（OpenAI API）'))
    if bugs and not getattr(config, "self_review_report", None):
        hints.append(dict(what='我不知道 AI 自审查到了什么',
            how='qvc scan . --self-review-report agent-review.md',
            detail='传入 AI 自审报告后，我能精确告诉你它漏掉了多少问题。',
            cost='免费，不需要 API'))
    if not hints:
        return
    click.echo()
    click.echo('\u2501' * 56)
    click.echo('  [*] 我的局限（{} 项）'.format(len(hints)))
    click.echo('\u2501' * 56)
    for h in hints:
        click.echo('  {}'.format(h['what']))
        click.echo('  -> {}  |  {}'.format(h['how'], h['cost']))
        click.echo('  -> {}'.format(h['detail']))
        click.echo()

def _register_builtin_rules():
    """注册内置规则"""
    from qvc.rules.python.variable_scope import PythonVariableScopeRule
    from qvc.rules.python.null_safety import PythonNullSafetyRule
    from qvc.rules.python.import_check import PythonImportCheckRule
    from qvc.rules.python.api_drift import PythonAPIDriftRule
    from qvc.rules.python.stale_reference import PythonStaleReferenceRule
    from qvc.rules.python.api_signature import PythonAPISignatureRule
    from qvc.rules.python.exception_handling import PythonExceptionHandlingRule
    from qvc.rules.javascript.variable_scope import JSVariableScopeRule
    from qvc.rules.universal.encoding import EncodingCheckRule
    from qvc.rules.universal.dead_code import DeadCodeRule
    from qvc.rules.universal.regex_fragility import RegexFragilityRule
    from qvc.rules.universal.hardcoded_secrets import HardcodedSecretsRule
    from qvc.rules.universal.hygiene import HygieneRule
    from qvc.rules.react.use_effect_deps import ReactUseEffectDepsRule
    from qvc.rules.javascript.null_safety import JSNullSafetyRule
    from qvc.rules.javascript.async_await import JSAsyncAwaitRule
    from qvc.rules.javascript.type_coercion import JSTypeCoercionRule
    from qvc.rules.javascript.memory_leak import JSMemoryLeakRule
    from qvc.rules.react.state_immutable import ReactStateImmutableRule
    from qvc.rules.typescript.type_safety import TSTypeSafetyRule
    from qvc.rules.go.nil_safety import GoNilSafetyRule
    from qvc.rules.python.sql_injection import SQLInjectionRule
    from qvc.rules.python.django_sql_injection import DjangoSQLInjectionRule
    from qvc.rules.python.mutable_defaults import MutableDefaultsRule
    from qvc.rules.python.resource_leak import ResourceLeakRule
    from qvc.rules.python.unsafe_pickle import UnsafePickleRule
    from qvc.rules.python.assert_in_prod import AssertForLogicRule
    from qvc.rules.python.http_no_timeout import HTTPNoTimeoutRule
    from qvc.rules.javascript.eval_usage import EvalUsageRule
    from qvc.rules.javascript.dom_xss import DOMXSSRule
    from qvc.rules.javascript.unhandled_promise import UnhandledPromiseRule
    from qvc.rules.javascript.unsafe_json_parse import UnsafeJSONParseRule
    from qvc.rules.react.missing_key import MissingKeyRule
    from qvc.rules.react.dangerous_html import DangerousHTMLRule
    from qvc.rules.universal.hardcoded_credentials import HardcodedCredentialsRule
    from qvc.rules.universal.insecure_random import InsecureRandomRule
    from qvc.rules.universal.todo_ticket import TODOTicketRule
    from qvc.rules.python.race_condition import RaceConditionRule
    from qvc.rules.python.path_traversal import PathTraversalRule
    from qvc.rules.python.subprocess_injection import SubprocessInjectionRule
    from qvc.rules.python.unsafe_yaml import UnsafeYAMLRule
    from qvc.rules.python.os_system import OSSystemRule
    from qvc.rules.python.socket_no_timeout import SocketNoTimeoutRule
    from qvc.rules.javascript.prototype_pollution import PrototypePollutionRule
    from qvc.rules.javascript.nosql_injection import NoSQLInjectionRule
    from qvc.rules.javascript.path_traversal_js import PathTraversalJSRule
    from qvc.rules.javascript.floating_promise import FloatingPromiseRule
    from qvc.rules.go.goroutine_leak import GoroutineLeakRule
    from qvc.rules.go.defer_error import DeferErrorRule
    from qvc.rules.react.unused_state import UnusedStateRule
    from qvc.rules.typescript.ts_any_type import TSAnyTypeRule

    if not rule_registry.get_all_rules():
        rule_registry.register_many([
            PythonVariableScopeRule(), PythonNullSafetyRule(),
            PythonImportCheckRule(), PythonAPISignatureRule(),
            PythonExceptionHandlingRule(), JSVariableScopeRule(),
            EncodingCheckRule(), DeadCodeRule(), RegexFragilityRule(),
            HardcodedSecretsRule(), ReactUseEffectDepsRule(),
            JSNullSafetyRule(), JSAsyncAwaitRule(), JSTypeCoercionRule(),
            JSMemoryLeakRule(), ReactStateImmutableRule(), TSTypeSafetyRule(),
            GoNilSafetyRule(),
            PythonAPIDriftRule(), PythonStaleReferenceRule(),
            SQLInjectionRule(), DjangoSQLInjectionRule(), MutableDefaultsRule(),
            ResourceLeakRule(), UnsafePickleRule(),
            AssertForLogicRule(), HTTPNoTimeoutRule(),
            EvalUsageRule(), DOMXSSRule(),
            UnhandledPromiseRule(), UnsafeJSONParseRule(),
            MissingKeyRule(), DangerousHTMLRule(),
            HardcodedCredentialsRule(), InsecureRandomRule(),
            TODOTicketRule(),
            RaceConditionRule(), PathTraversalRule(),
            SubprocessInjectionRule(), UnsafeYAMLRule(),
            OSSystemRule(), SocketNoTimeoutRule(),
            PrototypePollutionRule(), NoSQLInjectionRule(),
            PathTraversalJSRule(), FloatingPromiseRule(),
            GoroutineLeakRule(), DeferErrorRule(),
            UnusedStateRule(), TSAnyTypeRule(),
        ])


@click.group()
@click.version_option(version=__version__, prog_name="qvc")
def main():
    """QVC - QA of Vebe Coding —— AI Agent 代码生成质量审查工具"""
    pass

# V4: 友好报错包装器
def _friendly_error_wrapper():
    """包装 main() 以提供友好报错"""
    try:
        main()
    except ModuleNotFoundError as e:
        name = e.name or str(e)
        click.echo(f"\n  Missing dependency: {name}")
        click.echo(f"  Fix: pip install {name.split('.')[0] if name else 'qvc'}")
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"\n  Permission denied: {e.filename or 'unknown file'}")
        click.echo(f"  Fix: Check file permissions or run as administrator")
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(f"\n  File not found: {e.filename or 'unknown'}")
        click.echo(f"  Fix: Check the path exists and try again")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n  Scan cancelled by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n  Unexpected error: {type(e).__name__}: {e}")
        click.echo(f"  If this persists, please report at: https://github.com/ericwuname/qvc-overseer/issues")
        sys.exit(1)


@main.command()
@click.argument("target", default=".")
@click.option("--output", "-o", default="qvc-report", help="输出文件路径（不含扩展名）")
@click.option("--format", "-f", "formats", multiple=True, default=["markdown"],
              type=click.Choice(["markdown", "json", "sarif"]), help="输出格式")
@click.option("--lang", "-l", "languages", multiple=True, help="限定语言")
@click.option("--rules", "-r", multiple=True, help="仅运行指定规则（规则ID）")
@click.option("--exclude-rules", multiple=True, help="排除指定规则")
@click.option("--min-severity", default="minor",
              type=click.Choice(["fatal", "severe", "moderate", "minor"]),
              help="最低严重度阈值")
@click.option("--llm/--no-llm", default=False, help="启用 LLM 深度审查")
@click.option("--llm-model", default="gpt-5.2", help="LLM 模型")
@click.option("--llm-api-key", envvar="OPENAI_API_KEY", help="OpenAI API Key")
@click.option("--llm-base-url", envvar="OPENAI_BASE_URL", help="OpenAI API Base URL")
@click.option("--llm-provider", default="openai", type=click.Choice(["openai", "local", "custom"]), help="LLM backend: openai, local (Ollama), custom (DeepSeek/Qwen/etc)")
@click.option("--workers", "-w", default=4, type=int, help="并行工作线程数")
@click.option("--config", "-c", "config_file", default=None, help="Config file path")
@click.option("--evolve", is_flag=True, help="启用进化模式：自动发现知识缺口并生成候选指纹")
@click.option("--self-review-report", default=None, help="AI 自审报告路径（用于外部监工对比）")
@click.option("--self-review-agent", default=None, type=click.Choice(["codex", "cursor", "gpt", "generic"]), help="AI Agent 类型（codex/cursor/gpt/generic）")
@click.option("--diff/--no-diff", "diff", default=False, help="Incremental scan: only scan git-diff changed files")
@click.option("--full", "full_scan", is_flag=True, help="Force full project scan (skip smart detection)")
@click.option("--quiet", "-q", is_flag=True, help="静默模式")
@click.option("--fix-prompt", is_flag=True, help="Print AI-consumable fix instructions after scan")
@click.option("--no-pool", is_flag=True, help="Skip writing .qvc/tasks/pending.md")
def scan(
    target, output, formats, languages, rules, exclude_rules,
    min_severity, llm, llm_model, llm_api_key, llm_base_url, llm_provider,
    workers, config_file, evolve, quiet, full_scan,
    self_review_report, self_review_agent,
    diff,
    fix_prompt,
    no_pool,
):
    """扫描代码目录或 Git 仓库，产出审查报告"""

    _register_builtin_rules()

    config = ScanConfig.auto_load(
        target_path=Path(target) if target else None,
        config=config_file,
        target=target, output=output, formats=list(formats),
        languages=list(languages) if languages else None,
        rules=list(rules) if rules else None,
        exclude_rules=list(exclude_rules) if exclude_rules else None,
        min_severity=min_severity, llm_enabled=llm, llm_model=llm_model,
        llm_api_key=llm_api_key, llm_base_url=llm_base_url,
        max_workers=workers, quiet=quiet,
        evo_auto_evolve=evolve,
    )
    llm = config.llm.enabled
    evolve = config.evolution.auto_evolve

    start_time = time.time()

    # 1. 扫描文件
    if not quiet:
        click.echo(f"Scanning: {target}")

    if target.startswith(("http://", "https://", "git@")):
        git_scanner = GitScanner()
        try:
            file_paths = git_scanner.scan(target)
        finally:
            git_scanner.cleanup()
    else:
        scanner = FileScanner()
        file_paths = scanner.scan(target)

    # V4: 增量扫描 —— 只扫 git diff 变更文件
    if diff and file_paths:
        import subprocess
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=target if Path(target).is_dir() else Path(target).parent,
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                changed = set()
                for line in result.stdout.strip().split("\n"):
                    p = (Path(target) / line).resolve() if Path(target).is_dir() else Path(line).resolve()
                    if p.exists() and p.is_file():
                        changed.add(p)
                # Also include untracked files
                result2 = subprocess.run(
                    ["git", "ls-files", "--others", "--exclude-standard"],
                    cwd=target if Path(target).is_dir() else Path(target).parent,
                    capture_output=True, text=True, timeout=10,
                )
                if result2.returncode == 0 and result2.stdout.strip():
                    for line in result2.stdout.strip().split("\n"):
                        p = (Path(target) / line).resolve() if Path(target).is_dir() else Path(line).resolve()
                        if p.exists() and p.is_file():
                            changed.add(p)
                # Filter: only scan changed files that are in our file list
                changed_in_scope = [fp for fp in file_paths if fp.resolve() in changed]
                if changed_in_scope:
                    if not quiet:
                        click.echo(f"  Diff mode: {len(changed_in_scope)}/{len(file_paths)} files changed")
                    file_paths = changed_in_scope
        except Exception as e:
            if not quiet:
                click.echo(f"  Diff mode failed ({e}), falling back to full scan")

    if not file_paths:
        click.echo("No code files found")
        return

    language_map = {fp: scanner.get_language(fp) for fp in file_paths}
    detected_languages = list(set(language_map.values()) - {"unknown"})
    total_lines = 0
    for fp in file_paths:
        try:
            total_lines += len(fp.read_text(encoding="utf-8", errors="replace").split("\n"))
        except Exception:
            pass

    if not quiet:
        click.echo(f"Found {len(file_paths)} files, {total_lines:,} lines")
        click.echo(f"Languages: {', '.join(detected_languages) or 'none'}")

    # 2. 静态分析
    if not quiet:
        click.echo("Static analysis...")
        import sys as _sys

    selected_rules = rule_registry.filter_rules(
        languages=languages, rule_ids=rules, exclude_ids=exclude_rules,
    )
    analyzer = StaticAnalyzer(rule_registry, max_workers=workers)

    # V4: 进度条回调
    last_progress = [0]
    def _show_progress(done, total, bugs_found):
        if quiet:
            return
        pct = done * 100 // total
        # Only update every 5% to avoid flicker
        milestone = pct // 5 * 5
        if milestone > last_progress[0] or done == total:
            last_progress[0] = milestone
            bar_len = 20
            filled = pct * bar_len // 100
            bar = "[" + "=" * filled + ">" + " " * (bar_len - filled - 1) + "]"
            suffix = f" {done}/{total} files, {bugs_found} bugs found"
            # Use carriage return for in-place update
            click.echo(f"\r  {bar} {pct:3d}%{suffix}", nl=False)
        if done == total:
            click.echo("")  # newline at end

    bugs = analyzer.analyze_files(file_paths, language_map, selected_rules, progress_callback=_show_progress)

    if not quiet:
        click.echo(f"Candidates: {len(bugs)} -> filtering...")

    # 3. LLM 深度审查
    reviewer = None
    llm_bugs = None
    if llm:
        if not llm_api_key:
            click.echo("No API key, skipping LLM review")
        else:
            if not quiet:
                click.echo("LLM review...")
            try:
                reviewer = LLMReviewer(provider=llm_provider, model=llm_model, api_key=llm_api_key, api_base=llm_base_url)
                llm_file_count = min(len(file_paths), 20)
                contexts = []
                for fp in file_paths[:llm_file_count]:
                    try:
                        source = fp.read_text(encoding="utf-8", errors="replace")
                        if len(source) > 20000:
                            source = source[:20000]
                        contexts.append({
                            "path": fp, "source": source,
                            "language": language_map.get(fp, "unknown"),
                        })
                    except Exception:
                        pass
                llm_bugs = reviewer.review_files(contexts)
                bugs.extend(llm_bugs)
                if not quiet:
                    click.echo(f"LLM: {len(llm_bugs)} additional bugs")
            except Exception as e:
                click.echo(f"LLM error: {e}")

    # 4. 过滤严重度

    # ── V2 后处理：降噪 + 去重 + 严重度归一化 ──
    from qvc.analyzers.post_process import post_process
    from qvc.analyzers.blindspot_analyzer import BlindspotAnalyzer
    
    # V5: 跨文件规则检查（API 漂移 + 过期引用）
    try:
        from qvc.rules.python.api_drift import PythonAPIDriftRule
        from qvc.rules.python.stale_reference import PythonStaleReferenceRule
        def _make_cross_bug(fp, line_start, line_end, title, description, code_snippet, fix_suggestion, confidence, extra_id, root_cause=None):
            from qvc.models.bug import Bug, BugCategory
            return Bug(
                id=f"CROSS-{extra_id}", severity=Severity.SEVERE, category=BugCategory.API_MISMATCH,
                title=title, description=description,
                file_path=str(fp),
                line_start=line_start, line_end=line_end or line_start,
                code_snippet=code_snippet, fix_suggestion=fix_suggestion, confidence=confidence,
                rule_id="CROSS_FILE", root_cause=root_cause,
                blindspot_type="context_lost", detectable_by_self_review=False,
            )
        drift_bugs = PythonAPIDriftRule.cross_file_check(file_paths, _make_cross_bug)
        stale_bugs = PythonStaleReferenceRule.cross_file_check(file_paths, _make_cross_bug)
        cross_bugs = drift_bugs + stale_bugs
        if cross_bugs:
            bugs.extend(cross_bugs)
            if not quiet:
                click.echo(f"Cross-file: {len(drift_bugs)} drift + {len(stale_bugs)} stale")
    except Exception as e:
        if not quiet:
            click.echo(f"Cross-file check skipped: {e}")
    bugs = post_process(bugs)

    # ── V3.1 基因池自生长 + 置信度膨胀 ──
    try:
        from qvc.evolution import GenePool
        gp = GenePool()
        learned = gp.on_scan_complete(bugs)
        for b in bugs:
            boost = gp.get_confidence_boost(b)
            if boost > 0:
                b.confidence = min(0.99, b.confidence + boost)
    except Exception:
        pass


    # ── M5: LLM 候选验证（可选）──
    if llm and bugs:
        reviewer = LLMReviewer(provider=llm_provider, model=llm_model, api_key=llm_api_key, api_base=llm_base_url)
        try:
            bugs = reviewer.verify_bugs(bugs)
            if not quiet:
                click.echo(f"LLM verified: {len(bugs)} bugs (confidence adjusted)")
        except Exception as e:
            if not quiet:
                click.echo(f"LLM verify skipped: {e}")


    severity_order = {s.name.lower(): s for s in Severity}
    min_sev = severity_order.get(min_severity.lower(), Severity.MINOR)
    bugs = [b for b in bugs if b.severity.level <= min_sev.level]

    # 5. 进化模式

    # ── V3.0 外部监工分析 ──
    blindspot_report = BlindspotAnalyzer().analyze(bugs, self_review_report, self_review_agent)

    evo_report = None
    if evolve:
        if not quiet:
            click.echo("Evolution mode: analyzing knowledge gaps...")
        try:
            fp_store = FingerprintStore()
            evo_cycle = EvolutionCycle(
                static_analyzer=analyzer,
                fingerprint_store=fp_store,
                gap_detector=GapDetector(),
                llm_reviewer=reviewer if llm else None,
            )
            evo_report = evo_cycle.run(file_paths, bugs, llm_bugs)

            if not quiet:
                click.echo(f"  Gaps: {evo_report.new_gaps} | Candidates: {evo_report.new_candidates} | Pending: {evo_report.ready_for_review}")
                click.echo(f"  Fingerprint DB: {evo_report.total_fingerprints} total")
        except Exception as e:
            if not quiet:
                click.echo(f"  Evolution error: {e}")

    # 6. 生成报告
    duration_ms = int((time.time() - start_time) * 1000)
    summary = ScanSummary(
        total_files=len(file_paths), total_lines=total_lines,
        languages=detected_languages, duration_ms=duration_ms,
    )
    project_name = Path(target).name if not target.startswith(("http://", "https://")) else target.split("/")[-1].replace(".git", "")
    report = Report(project_name=project_name, scan_summary=summary, bugs=bugs)

    for fmt in formats:
        if fmt == "markdown":
            ext = ".md"
            reporter = MarkdownReporter()
            reporter.generate(report, Path(f"{output}{ext}"), blindspot_report=blindspot_report)
        elif fmt == "sarif":
            ext = ".sarif"
            reporter = SARIFReporter()
            reporter.generate(report, Path(f"{output}"))
        else:
            ext = ".json"
            reporter = JSONReporter()
            reporter.generate(report, Path(f"{output}{ext}"))
        if not quiet:
            click.echo(f"Report: {output}{ext}")

    if not quiet:
        click.echo(f"Done! {duration_ms/1000:.1f}s, {len(bugs)} bugs")

    # V6: Write task pool for AI Agent consumption
    if not no_pool:
        # V6.1: Always auto-close resolved bugs first
        try:
            pool = TaskPoolWriter(Path(target) if not target.startswith("http") else Path.cwd())
            pool.auto_close_resolved(bugs)
        except Exception:
            pass
        try:
            pool = TaskPoolWriter(Path(target) if not target.startswith("http") else Path.cwd())
            n = pool.write_pending(bugs, project_name)
            if n > 0 and not quiet:
                click.echo(f"  Tasks: {n} -> .qvc/tasks/pending.md (say 'fix qvc tasks' to your AI)")
        except Exception as e:
            if not quiet:
                click.echo(f"  Task pool skipped: {e}")

    # 7. 进化总结（在报告后输出）

    # ── V3.1 能力自白 ──
    # V5 AHA时刻
    if not quiet:
        _show_aha_moments(bugs, blindspot_report)
    if not quiet:
        _show_limitations(bugs, config)

    # V5: --fix-prompt: print AI-consumable fix instructions to stdout
    if fix_prompt:
        from qvc.reporters.markdown_reporter import AIFixPromptGenerator
        fix_lines = AIFixPromptGenerator.generate(bugs)
        if fix_lines:
            click.echo()
            click.echo("-" * 58)
            click.echo("  AI FIX INSTRUCTIONS (copy-paste to your AI):")
            click.echo("-" * 58)
            click.echo()
            for line in fix_lines:
                click.echo(line)
        else:
            click.echo()
            click.echo("No high-confidence bugs to fix (all < 70% confidence)")
    if evo_report:
        click.echo()
        click.echo("=" * 50)
        click.echo("Evolution Summary")
        click.echo("=" * 50)
        for detail in evo_report.details:
            click.echo(f"  {detail}")
        if evo_report.ready_for_review > 0:
            click.echo(f"\n  {evo_report.ready_for_review} fingerprints ready for review.")
            click.echo(f"  Run: qvc evolution status")


# ── 进化引擎命令组 ──

@main.group()
def evolution():
    """Evolution engine: status, review fingerprints"""
    pass


@evolution.command()
def status():
    """Show evolution engine status"""
    _register_builtin_rules()
    store = FingerprintStore()
    stats = store.get_stats()

    click.echo()
    click.echo("=" * 50)
    click.echo("  QVC Evolution Engine Status")
    click.echo("=" * 50)
    click.echo()
    click.echo(f"  Total fingerprints: {stats['total']}")
    click.echo(f"  Active:   {stats['active']}")
    click.echo(f"  Candidate: {stats['candidates']}")
    click.echo(f"  Verified:  {stats['verified']}")
    click.echo(f"  Rejected:  {stats['rejected']}")
    click.echo()
    click.echo(f"  Local: {stats['local']}")
    click.echo(f"  Pool:  {stats['pool']}")
    click.echo(f'  Seed:    {stats.get("seed", 0)}')
    click.echo()

    pending = store.get_pending_review()
    if pending:
        click.echo(f"Pending review ({len(pending)}):")
        for fp in pending[:10]:
            click.echo(f"  [{fp.id}] {fp.pattern_name} ({fp.occurrence_count}x, confidence {fp.confidence:.0%})")
    else:
        click.echo("No pending reviews")

    recent = store.get_recent_events(5)
    if recent:
        click.echo()
        click.echo("Recent events:")
        for evt in recent:
            click.echo(f"  {evt['timestamp'][:19]} | {evt['event']}")


@evolution.command()
@click.argument("fp_id")
def review(fp_id):
    """Review a candidate fingerprint"""
    store = FingerprintStore()
    fp = store.get_fingerprint(fp_id)
    if fp is None:
        click.echo(f"Fingerprint {fp_id} not found")
        return

    click.echo(f"\nReviewing: {fp.id}")
    click.echo(f"  Name: {fp.pattern_name}")
    click.echo(f"  Category: {fp.category}")
    click.echo(f"  Description: {fp.description}")
    click.echo(f"  Occurrences: {fp.occurrence_count}")
    click.echo(f"  Confidence: {fp.confidence:.0%}")
    click.echo(f"  Status: {fp.status.value}")
    click.echo()

    action = click.prompt(
        "Action [promote/reject/skip]",
        type=click.Choice(["promote", "reject", "skip"]),
        default="skip"
    )

    if action == "promote":
        store.promote(fp_id, "cli_user")
        click.echo(f"Promoted: {fp_id}")
    elif action == "reject":
        store.reject(fp_id, "cli_user")
        click.echo(f"Rejected: {fp_id}")
    else:
        click.echo("Skipped")

    store.log_event(f"review_{action}", f"Reviewed {fp_id}: {action}")


# ── 贡献命令组 ──

@main.group()
def contribute():
    """Contribute fingerprints to community gene pool"""
    pass


@contribute.command(name="preview")
def contribute_preview():
    """Preview contributable fingerprints"""
    store = FingerprintStore()
    contributor = Contributor(store)
    items = contributor.preview_contributable()

    if not items:
        click.echo("\nNo fingerprints to contribute. Run qvc scan --evolve first.")
        return

    click.echo(f"\nContributable fingerprints ({len(items)}):\n")
    for item in items:
        click.echo(f"  [{item['id']}] {item['name']}")
        click.echo(f"       category: {item['category']} | x{item['occurrences']} | confidence: {item['confidence']:.0%}")
        click.echo()
    click.echo("Run: qvc contribute submit --ids FP_001,FP_002")


@contribute.command(name="submit")
@click.option("--ids", "-i", "fp_ids", help="Fingerprint IDs to contribute (comma-separated)")
@click.option("--all", "-a", "submit_all", is_flag=True, help="Contribute all local fingerprints")
@click.option("--repo", "-r", default="https://github.com/ericwuname/qvc-overseer.git  # TODO: create separate fingerprints repo", help="Gene pool repo URL (or Gitee mirror)")
def contribute_submit(fp_ids, submit_all, repo):
    """Submit fingerprints to community gene pool"""
    store = FingerprintStore()
    contributor = Contributor(store)

    if submit_all:
        items = contributor.preview_contributable()
        ids = [item["id"] for item in items]
    elif fp_ids:
        ids = [i.strip() for i in fp_ids.split(",")]
    else:
        click.echo("Specify --ids or --all")
        return

    if not ids:
        click.echo("No fingerprints to contribute")
        return

    contributions = contributor.generate_contribution(ids)
    result = contributor.submit_via_pr(contributions, repo)

    if result["success"]:
        click.echo(f"\n{result['message']}")
        click.echo(f"  File: {result['contribution_file']}")
        click.echo(f"  Count: {result['fingerprint_count']}")
        click.echo(f"\nNext steps:")
        for step in result.get("instructions", []):
            click.echo(f"  {step}")
    else:
        click.echo(f"Failed: {result['message']}")


# ── 基因池同步 ──

@main.command()
@click.option("--repo", "-r", help="Gene pool repo URL")
@click.option("--dry-run", is_flag=True, help="Check for updates only")
def update(repo, dry_run):
    """Sync fingerprints from community gene pool"""
    store = FingerprintStore()
    syncer = GenePoolSyncer(store, pool_url=repo)

    if dry_run:
        result = syncer.check_updates()
        if result["has_updates"]:
            click.echo(f"Gene pool has {result.get('commits_behind', '?')} new commits")
        else:
            click.echo(f"{result['message']}")
        return

    click.echo("Syncing gene pool...")
    result = syncer.sync()

    if result["success"]:
        click.echo(f"{result['message']}")
        stats = store.get_stats()
        click.echo(f"  Local DB: {stats['total']} (local: {stats['local']} | pool: {stats['pool']})")
    else:
        click.echo(f"{result['message']}")


@main.command()
@click.option("--lang", "-l", "language", help="List rules for a language")
def list_rules(language):
    """List all available review rules"""
    _register_builtin_rules()
    if language:
        rules = rule_registry.get_rules_for_language(language)
        click.echo(f"\n{language} rules ({len(rules)}):\n")
    else:
        rules = rule_registry.get_all_rules()
        click.echo(f"\nAll rules ({len(rules)}):\n")
    for rule in sorted(rules, key=lambda r: r.rule_id):
        click.echo(f"  {rule.rule_id:25s} [{rule.severity.name:8s}] {rule.name}")



@main.command()
@click.option("--force", is_flag=True, help="Overwrite existing protocol")
def setup(force):
    """Initialize QVC protocol in current project (AGENTS.md + .qvc/)"""
    from pathlib import Path
    cwd = Path.cwd()
    
    gen = ProtocolGenerator()
    result = gen.setup(cwd, force=force)
    
    click.echo()
    click.echo("QVC Setup Complete")
    click.echo("=" * 40)
    if result["qvc_dir"]:
        click.echo("  + Created .qvc/ directory")
    if result["agents_md"]:
        click.echo("  + Added QVC protocol to AGENTS.md")
    else:
        click.echo("  - AGENTS.md already has QVC protocol (use --force to re-add)")
    if result["cursorrules"]:
        click.echo("  + Created .cursorrules for Cursor users")
    click.echo()
    click.echo("Your AI Agent now knows how to work with QVC.")
    click.echo("Try: say 'scan with qvc' to your AI Agent.")
    click.echo()


@main.command()
@click.option("--clean", is_flag=True, help="Remove completed tasks")
def tasks(clean):
    """View or manage .qvc/tasks/ task pool"""
    from pathlib import Path
    cwd = Path.cwd()
    pool = TaskPoolWriter(cwd)
    
    if clean:
        pool.clean_completed()
        click.echo("Completed tasks removed.")
        return
    
    pending = pool.get_pending_tasks()
    status = pool.load_status()
    
    click.echo()
    click.echo("QVC Task Pool")
    click.echo("=" * 40)
    click.echo(f"  Total tasks: {len(status)}")
    click.echo(f"  Pending:     {len(pending)}")
    click.echo(f"  Fixed:       {len(status) - len(pending)}")
    click.echo()
    
    if pending:
        click.echo("Pending tasks:")
        for t in pending:
            click.echo(f"  [{t['id']}] {t.get('title', '?')} ({t.get('confidence', 0):.0%})")
        click.echo()
        click.echo("  Say 'fix qvc tasks' to your AI Agent to resolve.")
    else:
        click.echo("  No pending tasks.")
    
    click.echo()


@main.command()
def guide():
    """Open the user guide"""
    import webbrowser
    from pathlib import Path

    # Try to open local guide first
    guide_path = Path(__file__).parent.parent / "docs" / "USER_GUIDE.md"
    if guide_path.exists():
        click.echo(f"Opening: {guide_path}")
        try:
            webbrowser.open(str(guide_path))
        except Exception:
            pass
        # Also print key sections
        click.echo()
        click.echo("=" * 60)
        click.echo("  QVC - Quick Start")
        click.echo("=" * 60)
        click.echo()
        click.echo("  Level 0: qvc scan .")
        click.echo("    -> Static review, no config needed")
        click.echo()
        click.echo("  Level 1: qvc scan . --llm --llm-provider local")
        click.echo("    -> AI review with Ollama (free, offline)")
        click.echo()
        click.echo("  Level 2: qvc scan . --llm --evolve")
        click.echo("    -> Auto-save new bug patterns")
        click.echo()
        click.echo("  Level 3: qvc update")
        click.echo("    -> Sync 1000+ community fingerprints")
        click.echo()
        click.echo("  Level 4: qvc contribute")
        click.echo("    -> Share your fingerprints with the world")
        click.echo()
        click.echo(f"  Full guide: {guide_path}")
    else:
        click.echo("User guide not found. See online docs.")

# ── Shortcut: qvc (no subcommand) defaults to smart scan ──
@main.command(name="check", context_settings={"ignore_unknown_options": True})
@click.option("--fix", is_flag=True, help="Exit with error if fatal bugs found (for CI/git hooks)")
def check_cmd(fix):
    """Pre-commit check: scan staged files, fail on fatal bugs"""
    import subprocess
    from pathlib import Path

    _register_builtin_rules()

    # Get staged files
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True, text=True, timeout=10
        )
        staged = [f.strip() for f in result.stdout.split("\n") if f.strip()]
    except Exception:
        click.echo("Not a git repository or git not available")
        sys.exit(1)

    if not staged:
        click.echo("No staged files to check")
        return

    # Filter to code files
    scanner = FileScanner()
    cwd = Path.cwd()
    code_files = [cwd / f for f in staged if (cwd / f).exists()]
    code_files = [f for f in code_files if scanner.get_language(f) != "unknown"]

    if not code_files:
        click.echo("No code files staged")
        return

    click.echo(f"Checking {len(code_files)} staged file(s)...")

    # Run static analysis
    language_map = {fp: scanner.get_language(fp) for fp in code_files}
    analyzer = StaticAnalyzer(rule_registry)
    bugs = analyzer.analyze_files(code_files, language_map)

    # Count fatal bugs
    fatal_count = sum(1 for b in bugs if b.severity == Severity.FATAL)
    severe_count = sum(1 for b in bugs if b.severity == Severity.SEVERE)

    if fatal_count == 0 and severe_count == 0:
        click.echo(f"Clean! 0 fatal, 0 severe bugs. Ready to commit.")
    else:
        click.echo(f"Found: {fatal_count} fatal, {severe_count} severe bugs")
        for b in bugs:
            if b.severity in (Severity.FATAL, Severity.SEVERE):
                click.echo(f"  [{b.severity.name}] {Path(b.file_path).name}:{b.line_start} - {b.title}")

    if fix and (fatal_count > 0 or severe_count > 0):
        click.echo(f"\nBlocking commit: {fatal_count} fatal + {severe_count} severe bugs")
        click.echo("Fix them or use --no-verify to skip")
        sys.exit(1)


@main.command()
@click.option("--cached", "staged_only", is_flag=True, help="Only scan staged files")
def diff(staged_only):
    """Scan changed files (since last commit)"""
    import subprocess
    from pathlib import Path

    _register_builtin_rules()

    cwd = Path.cwd()
    try:
        if staged_only:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True, text=True, timeout=10
            )
        else:
            result1 = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True, text=True, timeout=10
            )
            result2 = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True, text=True, timeout=10
            )
            changed = set(result1.stdout.split("\n") + result2.stdout.split("\n"))
            result = type("obj", (object,), {"stdout": "\n".join(changed)})()
    except Exception:
        click.echo("Not a git repository")
        return

    changed_files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
    if not changed_files:
        click.echo("No changed files")
        return

    scanner = FileScanner()
    code_files = [cwd / f for f in changed_files if (cwd / f).exists()]
    code_files = [f for f in code_files if scanner.get_language(f) != "unknown"]

    if not code_files:
        click.echo("No code files changed")
        return

    click.echo(f"Changed: {len(code_files)} file(s)")
    language_map = {fp: scanner.get_language(fp) for fp in code_files}
    analyzer = StaticAnalyzer(rule_registry)
    bugs = analyzer.analyze_files(code_files, language_map)

    fatal = [b for b in bugs if b.severity == Severity.FATAL]
    severe = [b for b in bugs if b.severity == Severity.SEVERE]
    moderate = [b for b in bugs if b.severity == Severity.MODERATE]

    click.echo(f"Bugs: {len(fatal)} fatal | {len(severe)} severe | {len(moderate)} moderate")
    for b in fatal + severe[:10]:
        click.echo(f"  [{b.severity.name}] {Path(b.file_path).name}:{b.line_start} - {b.title}")

    if len(severe) > 10:
        click.echo(f"  ... and {len(severe) - 10} more severe bugs")


@main.command()
@click.option("--output", "-o", default="fix.md", help="Output file path for fix instructions")
@click.option("--json", "json_output", is_flag=True, help="Output JSON format")
@click.option("--report", "-r", "report_path", default="qvc-report.md", help="Path to existing QVC report")
def fix(output, json_output, report_path):
    """Generate AI-consumable fix instructions from scan results"""
    from pathlib import Path
    from qvc.scanner import FileScanner
    from qvc.analyzers.static_analyzer import StaticAnalyzer
    from qvc.rules.registry import registry as rule_registry
    from qvc.reporters.markdown_reporter import AIFixPromptGenerator

    _register_builtin_rules()

    cwd = Path.cwd()
    scanner = FileScanner()
    file_paths = scanner.scan(str(cwd))
    if not file_paths:
        click.echo("No code files found in current directory")
        return

    language_map = {fp: scanner.get_language(fp) for fp in file_paths}
    analyzer = StaticAnalyzer(rule_registry)
    bugs = analyzer.analyze_files(file_paths, language_map)

    if not bugs:
        click.echo("No bugs found. Nothing to fix.")
        return

    if json_output:
        import json
        fix_data = []
        actionable = [b for b in bugs if b.confidence >= AIFixPromptGenerator.MIN_CONFIDENCE]
        actionable.sort(key=lambda b: b.confidence, reverse=True)
        actionable = actionable[:AIFixPromptGenerator.MAX_ITEMS]
        for b in actionable:
            fix_data.append({
                "file": b.file_path,
                "line": b.line_start,
                "confidence": b.confidence,
                "title": b.title,
                "description": b.description,
                "fix_suggestion": b.fix_suggestion,
            })
        result = json.dumps(fix_data, indent=2, ensure_ascii=False)
        with open(output, 'w', encoding='utf-8') as f:
            f.write(result)
        click.echo(f"Fix instructions (JSON): {output}")
        click.echo(result)
    else:
        fix_lines = AIFixPromptGenerator.generate(bugs)
        if not fix_lines:
            click.echo("No high-confidence bugs to fix (all < 70% confidence)")
            return
        result = chr(10).join(fix_lines)
        with open(output, 'w', encoding='utf-8') as f:
            f.write(result)
        click.echo(f"Fix instructions: {output}")
        click.echo()
        click.echo(result)




@main.command()
@click.option("--interval", "-i", default=5, type=int, help="Polling interval in seconds")
@click.option("--auto-fix", is_flag=True, help="Auto-write tasks for AI Agent consumption")
def watch(interval, auto_fix):
    """Watch project for changes and auto-scan (daemon mode)"""
    import time
    from pathlib import Path
    
    _register_builtin_rules()
    
    cwd = Path.cwd()
    scanner = FileScanner()
    
    click.echo(f"QVC Watch started (interval: {interval}s)")
    click.echo(f"Watching: {cwd}")
    click.echo("Press Ctrl+C to stop")
    click.echo()
    
    # Initial scan
    file_paths = scanner.scan(str(cwd))
    if not file_paths:
        click.echo("No code files found")
        return
    
    # Track file mtimes
    mtimes = {}
    for fp in file_paths:
        try:
            mtimes[str(fp)] = fp.stat().st_mtime
        except OSError:
            pass
    
    language_map = {fp: scanner.get_language(fp) for fp in file_paths}
    analyzer = StaticAnalyzer(rule_registry)
    
    try:
        while True:
            time.sleep(interval)
            
            # Check for changes
            changed = []
            current_files = set(scanner.scan(str(cwd)))
            
            for fp in current_files:
                try:
                    new_mtime = fp.stat().st_mtime
                    if str(fp) not in mtimes or new_mtime > mtimes[str(fp)]:
                        changed.append(fp)
                        mtimes[str(fp)] = new_mtime
                except OSError:
                    pass
            
            if not changed:
                continue
            
            click.echo(f"[{datetime.now().strftime('%H:%M:%S')}] {len(changed)} file(s) changed")
            
            # Scan changed files
            bugs = analyzer.analyze_files(changed, language_map)
            bugs = post_process(bugs)
            
            # Filter to actionable
            actionable = [b for b in bugs if b.confidence >= 0.70]
            
            if actionable:
                click.echo(f"  Found {len(actionable)} new issues")
                
                if auto_fix:
                    pool = TaskPoolWriter(cwd)
                    n = pool.write_pending(actionable)
                    if n > 0:
                        click.echo(f"  Tasks: {n} -> .qvc/tasks/pending.md")
                        click.echo(f"  Say 'fix qvc tasks' to your AI Agent")
                else:
                    for b in actionable[:3]:
                        click.echo(f"  [{b.confidence:.0%}] {b.title}")
            else:
                click.echo("  No new issues")
                
    except KeyboardInterrupt:
        click.echo()
        click.echo("QVC Watch stopped.")

if __name__ == "__main__":
    _friendly_error_wrapper()
