# QVC — AI Agent Code Quality External Overseer

<p align="center">
  <img src="https://img.shields.io/pypi/v/qvc-overseer?color=a6e3a1&label=PyPI" alt="PyPI">
  <img src="https://img.shields.io/pypi/pyversions/qvc-overseer?color=89b4fa" alt="Python">
  <img src="https://img.shields.io/pypi/l/qvc-overseer?color=f9e2af" alt="License MIT">
  <img src="https://img.shields.io/badge/code--review-external%20overseer-cba6f7" alt="External Overseer">
</p>

<p align="center"><b>Review only. Never modify. Your AI writes code. QVC watches.</b></p>

<p align="center">
  <a href="docs/QVC_用户使用手册.md">中文文档</a> |
  <a href="docs/QVC_User_Guide_EN.md">English Guide</a> |
  <a href="docs/QVC_Business_Pitch_EN.md">Business Pitch</a> |
  <a href="docs/QVC_vs_AI_Self_Review_EN.md">vs AI Self-Review</a>
</p>

---

## 30 Second Demo

![Demo](docs/QVC_terminal_demo.html)

`ash
pip install qvc-overseer
cd your-project
qvc scan .          # Scan -> Report
qvc fix             # Generate AI fix instructions -> Give to your Agent
`

**What QVC does NOT do**: Modify code, generate patches, replace your AI Agent.
**What QVC DOES**: Tell your AI Agent "you missed this."

## Why QVC?

AI Agents have **structural blind spots** when self-reviewing code:

| Blindspot | Why AI Can't See It | How QVC Sees It |
|-----------|--------------------|-----------------|
| Cross-file amnesia | Reviews file A, forgot file B | Full-project scan with reference graph |
| Memory residue | Generation logic contaminates review | No generation memory, sees final code only |
| Boundary blindness | Checks happy path, skips edges | Rules target edge cases specifically |

> **Real data**: ai-corp V7.1 — AI self-review found **0 bugs**. QVC found **4**. Miss rate = **100%**.

## Quick Start

`ash
pip install qvc-overseer
cd your-project
qvc scan .
`

`ash
qvc fix              # Generate fix-instructions.md
# Copy -> Paste to AI Agent -> Enter
`

## Features

- **Full-project scanning** — Python / JavaScript / TypeScript / React / Go
- **Three-layer confidence engine** — Deterministic / Pattern / Heuristic
- **Blindspot classification** — Why your AI missed each bug
- **AI miss rate quantification** — What percentage did your AI miss?
- **AI-consumable fix instructions** — qvc fix generates prompts for your Agent
- **Task pool** — Scan → Dispatch → Verify closed loop
- **Self-evolution** — Learns new bug patterns from every scan
- **Community gene pool** — Shared fingerprint database
- **VS Code extension** — Right-click scan
- **GitHub Actions** — Auto-scan on push/PR

## All Commands

| Command | Description |
|---------|------------|
| qvc scan . | Full project scan |
| qvc diff | Scan changed files only |
| qvc fix | Generate AI fix instructions |
| qvc tasks | View task pool |
| qvc watch | Auto-scan daemon |
| qvc setup | Initialize QVC in project |
| qvc contribute | Share fingerprints |
| qvc update | Sync community pool |
| qvc guide | Open user guide |
| qvc list-rules | List all detection rules |

## Comparison

| | QVC | ESLint/Pylint | SonarQube | CodeQL |
|---|---|---|---|---|
| **Positioning** | AI external overseer | Code style | Quality platform | Security |
| **Cross-file consistency** | Yes | No | Partial | No |
| **AI miss rate** | Yes (quantified) | No | No | No |
| **AI fix instructions** | Yes | No | No | No |
| **Self-evolution** | Yes | No | No | No |
| **Install** | pip install | npm/pip | Docker | Complex |

## Documentation

| Document | Language |
|----------|----------|
| User Guide | [中文](docs/QVC_用户使用手册.md) \| [English](docs/QVC_User_Guide_EN.md) |
| Business Pitch | [English](docs/QVC_Business_Pitch_EN.md) |
| vs AI Self-Review | [English](docs/QVC_vs_AI_Self_Review_EN.md) |
| Project Report | [中文](docs/V6.1_完整项目报告.md) \| [English](docs/QVC_Project_Report_EN.md) |
| Execution Guide | [中文](docs/项目执行指导书_V6.md) \| [English](docs/QVC_Execution_Guide_EN.md) |
| Retrospective | [English](docs/QVC_Retrospective_EN.md) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome for new rules, fingerprints, and translations.

## License

MIT — Free, open source, forever.
