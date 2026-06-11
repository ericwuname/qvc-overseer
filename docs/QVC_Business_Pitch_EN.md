# QVC — The AI Code Quality External Overseer

## One-Liner
> **Your AI Agent writes code. QVC finds what it can't see.**

---

## The Problem

AI coding agents (Codex, Cursor, Copilot, ChatGPT) are writing more code than ever. But when they review their own work, they have **structural blind spots**:

| Blind Spot | Why It Happens | Impact |
|-----------|---------------|--------|
| Cross-file amnesia | AI reviews file A, forgets file B | API mismatches, broken imports |
| Memory residue | Generation logic contaminates self-review | "I wrote it, so it's correct" |
| Boundary blindness | AI checks happy path, skips edges | Null safety, exception handling |

**Real data**: AI self-review missed **100%** of real bugs in a production project (4 bugs in 120 files).

---

## The Solution: QVC

QVC is an **external code quality overseer** designed specifically for the AI Agent programming era.

- **Only reviews. Never modifies code.** (Preserves external independence)
- **Cross-file consistency checks** (What your AI forgets)
- **Three-layer confidence engine** (You know which bugs to trust)
- **AI-consumable fix instructions** (Copy → Paste → Fixed)
- **Self-evolving fingerprint database** (Learns from every scan)

---

## Market Position

| | QVC | ESLint/Pylint | SonarQube | CodeQL |
|---|---|---|---|---|
| **Position** | AI external overseer | Code style | Quality platform | Security |
| **Cross-file consistency** | Yes | No | Partial | No |
| **AI miss rate quantified** | Yes | No | No | No |
| **AI fix instructions** | Yes | No | No | No |
| **Self-evolution** | Yes | No | No | No |
| **Install** | pip install | npm/pip | Docker | Complex |

QVC doesn't compete with linters. It does what AI Agents structurally cannot do for themselves.

---

## Target Users

**Heavy AI Agent programmers** — developers who:
- Use AI coding assistants (Codex, Cursor, Copilot) daily
- Have medium-to-large projects (100+ files)
- Are tired of AI saying "looks good" when it's not
- Want proof that their AI-reviewed code is actually correct

---

## Business Model

**Core (Free, Open Source)**:
- Static analysis with three-layer confidence engine
- Blindspot classification
- AI fix instruction generation
- Self-evolving fingerprints
- MIT License

**Growth Path**:
- LLM verification (Ollama free / OpenAI ~.02/scan)
- Community gene pool (shared fingerprints)
- VS Code extension
- GitHub Actions integration

---

## Traction

- **7 major versions** (V1 → V6.1) in active development
- **13 CLI commands**, 5 language support
- **Published on PyPI**: pip install qvc-overseer
- **Open source** (MIT) on GitHub

---

## Why Now?

1. **AI Agent adoption is exploding** — but agent self-review is an unsolved problem
2. **No tool exists** for external oversight of AI-generated code
3. **Position advantage** — QVC's "external overseer" positioning is unique and defensible
4. **Low barrier** — pip install + 0 config = 2 minutes to first value

---

## Vision

> QVC becomes the standard quality gate in the AI Agent programming workflow.
> Every time an AI writes code and says "it's fine", QVC says "check here."

---

**Contact**: GitHub [ericwuname/qvc-overseer](https://github.com/ericwuname/qvc-overseer)
