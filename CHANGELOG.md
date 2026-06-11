# QVC Changelog

## [1.0.0] — 2026-06-12 — "Delivery"

### Added
- **50th rule**: `django_sql_injection` — detects Django ORM raw()/extra()/RawSQL with injectable SQL patterns
- **Python AST semantic analyzer**: `qvc/analyzers/ast_analyzer.py` — resolves imports, functions, classes, scopes, call graphs
- **GitHub Actions auto-PR**: `qvc/task_pool/auto_pr.py` — generates fix suggestion PRs for ≥90% confidence bugs
- **VS Code extension Marketplace-ready**: metadata, icon, gallery banner, keywords

### Changed
- `qvc/analyzers/static_analyzer.py`: Integrated ASTAnalyzer for Python files
- `qvc/cli.py`: Registered DjangoSQLInjectionRule (50 rules total)
- `.github/workflows/qvc.yml`: Added auto-PR generation job
- `.github/action.yml`: Added `auto_pr` input + fix suggestion generation
- `vscode-extension/package.json`: Bumped to 1.0.0, added marketplace metadata
- Version bump: 0.9.0 → 1.0.0

### Fixed
- Stripped BOM from 8 files (docs + new source files)

---

## [0.9.0] — 2026-06-12 — "Gene Pool"

### Added
- Gene pool independent repository: `ericwuname/qvc-fingerprints`
- Fingerprints expanded: 55 → 145 (+90)
- Incremental sync engine: `GenePoolSyncer.sync_incremental()`
- Community contribution loop: `qvc contribute` + `qvc update`
- New fields per fingerprint: `ai_blindspot`, `verified_projects`
- Evolution module: contributor, evolution_cycle, gap_detector, gene_pool, pattern_abstractor, syncer
- CWE coverage: 15 → 35
- Language coverage: 4 → 6 (+Go +TypeScript fingerprints)

---

## [0.8.0] — 2026-06-11 — "V6.5"

### Added
- Rules expanded: 21 → 49 (+28 rules across Python, JS, React, Go, TypeScript, Universal)
- Bilingual documentation: 7 English docs (User Guide, Business Pitch, Project Report, Execution Guide, Comparison Report, Retrospective, Demo)
- Installation scripts: `install.bat` (Windows) + `install.sh` (Mac/Linux)
- 50 seed fingerprints with CWE/OWASP coverage

### Fixed
- BOM stripped from project source files
- Rule file self-referencing false positives marked as known

---

## [0.7.0] — 2026-06-10 — "V3-V5"

### Added
- Three-tier confidence engine (CERTIFICATE/PATTERN/HEURISTIC)
- Blind spot classifier: boundary_condition, memory_trap, context_lost
- External overseer summary in reports
- Self-review miss rate comparison
- Task pool: scan → dispatch → AI fix → verify
- Progressive capability unlock hints
- Config system: zero-config startup + graded capability discovery

---

## [0.6.0] — 2026-06-09 — "V1-V2"

### Added
- Initial 21 rules across Python, JavaScript, React, TypeScript
- Static analysis engine with multi-threading
- Markdown report generator
- CLI: scan, diff, tasks, setup commands
- Fingerprint data structure with evolution support
- Self-evolution cycle: scan → detect gap → abstract pattern → verify → deploy

---

## [Initial] — 2026-06-08 — "V0"

### Added
- Project scaffold
- Basic static analysis: variable scope, null safety, import check, BOM detection
- Core models: Bug, Report, Severity
- First self-scan on ai-corp V7.1

---

*QVC — External overseer for AI Agent code. Review only, never modify.*
