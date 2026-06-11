# QVC User Guide — A Complete Walkthrough

> For AI Agent programmers who want their AI to stop lying about code quality.

## Table of Contents
1. [Why QVC?](#1-why-qvc)
2. [Installation](#2-installation)
3. [First Scan](#3-first-scan)
4. [Reading the Report](#4-reading-the-report)
5. [Using AI Fix Instructions](#5-using-ai-fix-instructions)
6. [All Commands](#6-all-commands)
7. [Advanced: Unlock More Power](#7-advanced-unlock-more-power)
8. [FAQ](#8-faq)

---

## 1. Why QVC?

Your AI Agent writes code, then reviews its own work. But AI self-review has **structural blind spots**:

- **Cross-file amnesia**: When reviewing file A, your AI has already forgotten file B
- **Memory residue**: The generation memory contaminates the review
- **Boundary blindness**: AI checks the happy path, skips edge cases

**QVC is an external overseer.** It doesn't write code. It doesn't fix code. It just tells your AI Agent: "You missed this."

> Real data: On ai-corp V7.1 (120 files), AI self-review found **0 bugs**. QVC found **4 real bugs**. That's a **100% miss rate**.

---

## 2. Installation

### Step 1: Open Terminal
- **Windows**: Press Win+R, type cmd, Enter
- **Mac**: Press Cmd+Space, type 	erminal, Enter

### Step 2: Install QVC
`ash
pip install qvc-overseer
`

### Step 3: Verify
`ash
qvc --version
`
Expected: qvc, version 0.6.5

---

## 3. First Scan

### Step 1: Navigate to Your Project
`ash
cd your-project-folder
`

### Step 2: Scan
`ash
qvc scan .
`

In less than 2 minutes, you'll see:

`
Scanning: .
Found 120 files, 19,705 lines
Done! 1.1s, 4 bugs

  [AHA] Your AI cannot see these
  [90%] create_session() signature mismatch (22 sites)
  [85%] Silent exception swallowing (23 sites)
  AI missed rate: 100%

  Full report: qvc-report.md
`

### Step 3: Open the Report
The report qvc-report.md is in your project root. Open it in VS Code or any editor.

---

## 4. Reading the Report

The report has 5 sections:

### Section 1: External Overseer Summary
Shows what QVC found vs what your AI self-review missed.

### Section 2: Blindspot Classification
Each bug is tagged by WHY your AI couldn't see it:
- **CONTEXT_LOST**: Cross-file consistency issue
- **BOUNDARY_CONDITION**: Edge case / null safety
- **MEMORY_TRAP**: Generated code with internal contradictions

### Section 3: AI Fix Instructions
Copy-paste ready prompts for your AI Agent to fix each bug.

### Section 4: Limitations
What QVC isn't confident about, and how to increase confidence (LLM verification).

### Section 5: Unlock More Power
Capabilities available with additional setup (free).

---

## 5. Using AI Fix Instructions

`ash
qvc fix
`

This generates ix-instructions.md. Copy the content, paste into your AI coding assistant (Codex, Cursor, ChatGPT), press Enter. Your AI will fix the bugs one by one.

---

## 6. All Commands

| Command | What it does |
|---------|-------------|
| qvc scan . | Full project scan |
| qvc scan . --full | Include low-confidence suggestions |
| qvc scan . --min-severity fatal | Only fatal issues |
| qvc diff | Scan only changed files |
| qvc fix | Generate AI fix instructions |
| qvc tasks | View task pool |
| qvc watch | Auto-scan on file changes |
| qvc setup | Initialize QVC in project |
| qvc evolve | Check evolution status |
| qvc contribute | Share fingerprints |
| qvc update | Sync community gene pool |
| qvc guide | Open this guide |
| qvc list-rules | List all detection rules |

---

## 7. Advanced: Unlock More Power

### LLM Verification (Free with Ollama)
`ash
# Install Ollama first, then:
qvc scan . --llm --llm-provider local
`
LLM verifies each finding, pushes 60-85% confidence bugs to 90%+.

### AI Self-Review Comparison
`ash
qvc scan . --self-review-report agent-review.md
`
Tells you exactly how many bugs your AI missed.

### Watch Mode
`ash
qvc watch
`
QVC runs in background, scans whenever files change.

---

## 8. FAQ

**Q: Does QVC modify my code?**
A: Never. QVC only reports problems. Use qvc fix to generate instructions for your AI Agent.

**Q: What languages does QVC support?**
A: Python, JavaScript, TypeScript, React (JSX), Go. More coming.

**Q: Do I need an API key?**
A: No. Basic scanning is 100% offline. LLM verification needs Ollama (free) or OpenAI key (~.02/scan).

**Q: How is QVC different from ESLint/Pylint?**
A: Linters check code style. QVC checks what your AI Agent structurally cannot see — cross-file consistency, boundary conditions, memory traps. It's an external overseer, not a linter.

**Q: Can I use QVC in CI/CD?**
A: Yes. GitHub Actions workflow included. See .github/workflows/qvc.yml.

---

> **QVC — Your AI writes code. QVC watches.**
