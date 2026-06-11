# QVC V6.1 — Complete Project Report

> **Status**: Published on PyPI | **Version**: 0.6.5 | **License**: MIT

---

## Project Overview

QVC (QA of Vebe Coding) is an **AI Agent code quality external overseer** — a static analysis tool designed specifically to find bugs that AI coding agents structurally cannot detect during self-review.

### Core Principle
> **Review only. Never modify.** QVC maintains external independence to preserve its unique value: it's not another AI Agent writing code — it's an overseer watching from outside.

---

## Architecture

`
qvc/
├── cli.py              # 13 CLI commands (Click)
├── config.py           # Configuration management
├── scanner/            # File + Git scanning engine
│   ├── file_scanner.py
│   └── git_scanner.py
├── rules/              # Detection rules by language
│   ├── python/         # 7 rules (import, scope, null, API, etc.)
│   ├── javascript/     # 4 rules
│   ├── react/          # 2 rules
│   ├── typescript/     # 1 rule
│   ├── go/             # 1 rule
│   └── universal/      # 5 rules (BOM, secrets, dead code)
├── analyzers/          # Post-processing + LLM review
│   ├── static_analyzer.py
│   ├── blindspot_analyzer.py
│   ├── post_process.py
│   └── llm_reviewer.py
├── evolution/          # Self-learning fingerprint engine
│   ├── gene_pool.py
│   ├── fingerprint_store.py
│   ├── pattern_abstractor.py
│   ├── gap_detector.py
│   ├── contributor.py
│   ├── syncer.py
│   └── seeds/          # 50 seed fingerprints
├── reporters/          # Output formats
│   ├── markdown_reporter.py
│   ├── json_reporter.py
│   └── sarif_reporter.py
├── task_pool/          # AI Agent task dispatch
│   ├── protocol.py
│   └── writer.py
└── models/             # Data models
    ├── bug.py
    ├── report.py
    └── severity.py
`

---

## Key Features

| Feature | Description |
|---------|------------|
| **Three-Layer Confidence Engine** | L1: >=95% (deterministic), L2: 60-85% (pattern), L3: 20-50% (heuristic) |
| **Blindspot Classifier** | Labels each bug by WHY AI can't see it (CONTEXT_LOST, BOUNDARY_CONDITION, MEMORY_TRAP) |
| **AI Miss Rate** | Quantifies what AI self-review missed (e.g., "AI missed 100% of real bugs") |
| **AI Fix Instructions** | Generates copy-paste prompts for AI Agents to fix bugs |
| **Task Pool** | Scans → writes tasks → AI Agent consumes → verification loop |
| **Self-Evolution** | Learns new bug patterns from every scan |
| **Community Gene Pool** | Share/sync fingerprint databases |
| **Multi-Format Output** | Markdown, JSON, SARIF |

---

## Quality Metrics

| Metric | V1 | V2 | V3 | V4 | V5 | V6.1 |
|--------|----|----|----|----|----|------|
| Candidates per scan | 281 | 645 | ~800 | ~600 | ~2100 | ~2100 |
| After filtering | 281 | 8 | ~15 | ~5 | ~8 | ~8 |
| High-confidence (>=90%) | 0 | 2 | 3 | 3 | 3 | 3 |
| Hit rate @ >=90% | N/A | 66% | 85% | 100% | 100% | 100% |
| AI miss rate | N/A | N/A | 100% | 100% | 100% | 100% |

---

## Tech Stack

- **Language**: Python 3.11+
- **CLI Framework**: Click
- **Build System**: Hatchling
- **Package**: PyPI (qvc-overseer)
- **CI**: GitHub Actions
- **VS Code Extension**: JavaScript

---

## Deliverables

| Item | Path |
|------|------|
| PyPI Package | [qvc-overseer](https://pypi.org/project/qvc-overseer/) |
| GitHub Repo | [ericwuname/qvc-overseer](https://github.com/ericwuname/qvc-overseer) |
| User Guide (CN) | docs/QVC_用户使用手册.md |
| User Guide (EN) | docs/QVC_User_Guide_EN.md |
| Business Pitch (EN) | docs/QVC_Business_Pitch_EN.md |
| Comparison Report | docs/QVC_vs_AI_Self_Review_EN.md |
| Retrospective | docs/QVC_Retrospective_EN.md |
| One-Click Installer | install.bat + install.sh |
| Terminal Demo | docs/QVC_terminal_demo.html |

---

## Next Steps

- **V7**: Multi-Agent parallel scanning, Python AST-level analysis
- **Community**: Build contributor base, accept rule/fingerprint PRs
- **Ecosystem**: JetBrains plugin, GitLab CI, pre-commit hook
