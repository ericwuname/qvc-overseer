# QVC Changelog

## [0.9.0] — 2026-06-12 — V7 "Gene Pool"

### Added
- **145 seed fingerprints** (55 -> 145, +90 new)
- **Gene pool repository**: qvc-fingerprints with verified/ and candidates/
- **Incremental sync**: sync_incremental() pulls only new/updated fingerprints
- **Contribution validator**: validate_fingerprint() checks schema before submission
- **PR body generator**: generate_pr_body() creates structured contribution PRs
- **New fingerprint fields**: ai_blindspot + verified_projects on all fingerprints
- **Go fingerprints**: 15 Go-specific patterns (goroutine leak, defer error, etc.)
- **CWE coverage**: 15 -> 35 CWE patterns
- **V6.5 retrospective** (CN + EN)
- **V7 execution guide** (CN + EN)
- **V7 project report** (CN + EN)

### Changed
- fingerprint_store.py: loads go_seeds.json + seed_fingerprints.json
- syncer.py: sync_incremental() method for delta-only updates
- contributor.py: validate + generate PR body methods
- All fingerprints normalized with V7 schema fields

## [0.8.0] — 2026-06-11 — V6.5 "Rule Expansion"

### Added
- **29 new detection rules** (21 -> 50 total rules)
- **Python (12 new)**: sql_injection, mutable_default_args, resource_leak,
  unsafe_pickle, assert_in_prod, http_no_timeout, race_condition,
  path_traversal, subprocess_injection, unsafe_yaml, os_system, socket_no_timeout
- **JavaScript/TypeScript (8 new)**: eval_usage, dom_xss, unhandled_promise,
  unsafe_json_parse, prototype_pollution, nosql_injection, path_traversal_js,
  floating_promise
- **React (3 new)**: missing_list_key, dangerous_html, unused_state_setter
- **Go (2 new)**: goroutine_leak, defer_error_ignored
- **TypeScript (1 new)**: ts_any_type
- **Universal (3 new)**: hardcoded_credentials, insecure_random, todo_no_ticket
- **International documentation**: 7 English docs (User Guide, Business Pitch,
  Project Report, Execution Guide, Comparison Report, Retrospective, Terminal Demo)
- **Bilingual README** with language switcher
- **One-click install scripts**: install.bat (Windows) + install.sh (Mac/Linux)
- **CONTRIBUTING.md** international edition

### Changed
- Rule count: 21 -> 50
- Self-scan false positive rate: improved via BOM fix
- All GitHub URLs unified to ericwuname/qvc-overseer

### Fixed
- UTF-8 BOM stripped from cli.py
- Version number sync between pyproject.toml and qvc/__init__.py

## [0.6.0a1] — 2026-06-11 — V6 "Closed Loop"

### Added
- **Task Pool Engine**: `.qvc/tasks/pending.md` — AI Agent automatically consumes QVC findings
- **qvc setup**: One command to initialize QVC protocol in any project (AGENTS.md + .cursorrules)
- **qvc tasks**: View and manage the task pool from CLI
- **Community Gene Pool**: End-to-end contribute/update with local fallback (no git required)
- **VS Code Extension**: Right-click scan, status bar bug count, problem panel integration
- **GitHub Actions**: `qvc-review` workflow — PR comments with scan summaries
- **--no-pool flag**: Opt-out of task pool generation on scan

### Changed
- `qvc scan` now automatically writes tasks to `.qvc/tasks/pending.md` after scanning
- Gene pool syncer gracefully falls back to local directory when git is unavailable
- Protocol generator creates both AGENTS.md and .cursorrules for broader AI Agent support
- Version bumped to 0.6.0a1

### Fixed
- Pre-existing test_core.py version mismatches (0.1.0 → 0.5.0a1)
- Pre-existing severity label assertion
- Multiple PowerShell `\n` encoding issues in test files

## [0.5.0a1] — 2026-06-11 — V5 "Self-Propagating"

### Added
- API_DRIFT rule (PY_API_DRIFT_001): cross-file function signature consistency
- STALE_REFERENCE rule (PY_STALE_REF_001): deleted/renamed symbol references
- AHA moment on first scan: "Your AI cannot see these"
- Propagation hook: one-click share after scan
- AI Fix Instructions: report bottom + --fix-prompt flag + qvc fix command
- Progress bar with real-time file counter
- Regression tests expanded: 11 → 45

### Changed
- REVIEW_GAP defaults to Mode B (industry baseline) without requiring --self-review-report
- README 4 claim corrections for accuracy

## [0.4.0a1] — 2026-06 — V4 "Trust Version"

### Added
- V4-alpha → V4-stable → V4-beta three-stage pipeline
- PyPI alpha release (pip install qvc-overseer)
- Go nil safety rule (GO_NIL_SAFETY_001)
- Incremental scan (--diff mode)
- SARIF output format
- Hit rate validation report across 5 projects: 100% at >=90% confidence
- 3 external user beta tests

## [0.3.0a1] — 2026-05 — V3 "External Overseer"

### Added
- Blind spot classifier (memory_trap, context_lost, self_harvest)
- Self-review miss rate estimation (Mode A/B/C)
- Industry baseline comparison without requiring self-review report
- 50 seed fingerprints (CWE Top 25 + real-world patterns)
- Self-evolution: learns from every scan
- Gene pool infrastructure (local)

## [0.2.0a1] — 2026-05 — V2 "Signal Priority"

### Added
- Three-layer confidence engine (L1: >=95%, L2: 60-85%, L3: 20-50%)
- Dedup aggregation: 169 identical import warnings → 1 suggestion
- UTF-8 BOM detection
- Forced severity distribution model
- Post-processing pipeline (noise reduction, dedup, severity normalization)

## [0.1.0] — 2026-04 — V1 "Proof of Concept"

### Added
- Static analysis engine with 11 rules
- File scanner with language auto-detection
- Markdown report generator
- Python import checking
- Variable scope analysis
- Null safety detection
