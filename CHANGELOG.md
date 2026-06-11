# QVC Changelog

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
