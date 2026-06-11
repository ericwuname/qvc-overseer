# QVC V8 Execution Guide

> Version: 1.0.0 | Codename: "Delivery" | Date: 2026-06-12
>
> **V8 positioning**: Not a feature version — a delivery version. Fulfill every promise made from V1-V7, then ship as 1.0.0.

---

## I. V8'is Mission

V7 delivered the gene pool, but 4 promises remain unfulfilled:

| # | Promise | Source | V7 Status |
|---|---------|--------|:--:|
| 1 | "50 rules" | V6.5 target | 49, 1 short |
| 2 | "Python AST-level analysis" | V3 guide | Regex only, not implemented |
| 3 | "GitHub Actions auto-fix PR" | V6 business pitch | Scan only, no auto-PR |
| 4 | "VS Code extension" | V5 blueprint | Exists but unpublished |

**V8 does only these 4 things. No new features, no language expansion, no fingerprint growth.**

---

## II. Technical Design

### Task 1: 50th Rule — `django_sql_injection`

**Why this rule**:
- Django is Python`s most popular web framework
- SQL injection is OWASP #1 security risk
- `extra()` / `raw()` / `RawSQL` are well-known Django injection vectors
- This rule has clear determinism (CERTIFICATE tier) — won`t add false positives

**Detection patterns**:
```python
# 1. Model.objects.raw(f"...{var}...")
# 2. Model.objects.extra(where=[f"...{var}..."])
# 3. RawSQL(f"...{var}...")
# 4. cursor.execute(f"...{var}...")
```

**Files**: 1 new rule file + registry registration

### Task 2: Python AST Analysis Engine

**Current problem**: static_analyzer.py uses only regex matching, causing:
- No knowledge that `app/` has `__init__.py` (root cause of import false positives)
- Can`t distinguish function calls from variable references
- Can`t track variable scopes

**Solution**:
```python
# qvc/analyzers/ast_analyzer.py (new)
class ASTAnalyzer:
    def analyze(self, file_path: str) -> ASTContext:
        """Parse Python AST and return semantic context"""
        tree = ast.parse(source)
        return ASTContext(
            imports=self._resolve_imports(tree),
            functions=self._extract_functions(tree),
            classes=self._extract_classes(tree),
            variable_scopes=self._build_scope_tree(tree),
            call_graph=self._build_call_graph(tree),
        )
```

**Integration with existing flow**:
```
scan_file() 
  → regex static analysis (existing, fast preliminary)
  → AST analysis (new, provides semantic context)
  → rule engine (uses AST context to filter false positives)
  → confidence engine
  → report
```

**Files**: New `qvc/analyzers/ast_analyzer.py`, modify `static_analyzer.py`

### Task 3: GitHub Actions Auto-PR

**Current state**: `.github/workflows/qvc.yml` only scans + reports

**Goal**: Auto-create fix PR when scan finds issues

**Implementation**:
```yaml
# Enhanced .github/workflows/qvc.yml
jobs:
  scan:
    steps:
      - run: qvc scan . --format json --output qvc-result.json
      - name: Auto-fix PR
        if: failure()
        uses: qvc/create-fix-pr@v1
        with:
          scan-result: qvc-result.json
          auto-fix: true
```

**Workflow**:
```
push/PR → QVC scan → Issues found?
                      ├─ No → Pass ✅
                      └─ Yes → High confidence (≥90%)?
                              ├─ Yes → Generate fix suggestions → Create Fix PR
                              └─ No → Report warning, no PR created
```

**Critical**: QVC NEVER auto-modifies code. PRs contain "fix suggestion descriptions", not auto-generated patches. Developers/AI Agents fix manually based on suggestions.

### Task 4: VS Code Extension Marketplace Prep

**Current state**: `/vscode-extension/` exists but not published

**Pre-publish checklist**:
1. Complete `package.json` marketplace metadata
2. Design extension icon (128x128 PNG)
3. English README
4. `.vscodeignore` for packaging
5. Ready for `vsce publish` (actual publish in V8.1 or manual trigger)
6. Test: right-click → "Scan with QVC" → terminal output

---

## III. Phased Execution Plan

```
V8 total: ~5 days

Phase 0: V7 retrospective + this guide .............. 0.5 day
Phase 1: Rule 50 + Python AST engine ............... 1 day
Phase 2: GitHub Actions auto-PR .................... 1 day
Phase 3: VS Code extension prep .................... 0.5 day
Phase 4: Self-scan + bug fixes ..................... 1 day
Phase 5: Complete docs (CN+EN) + CHANGELOG .......... 0.5 day
Phase 6: GitHub push + PyPI 1.0.0 .................. 0.5 day
```

### Phase 1: Rule 50 + AST Engine

**Acceptance criteria**:
- [ ] Total rules = 50
- [ ] `django_sql_injection` detects `Model.objects.raw(f"...")`
- [ ] `django_sql_injection` does NOT flag safe SQL (no variable injection)
- [ ] AST analyzer correctly parses package structure with `__init__.py`
- [ ] Existing 49 rules unaffected

### Phase 2: GitHub Actions Auto-PR

**Acceptance criteria**:
- [ ] Push code with bugs → CI triggers QVC scan
- [ ] High-confidence bugs found → auto-create PR
- [ ] PR title: `[QVC] Found N high-confidence issues`
- [ ] PR body contains bug details + fix suggestions
- [ ] No high-confidence bugs → no PR created

### Phase 3: VS Code Extension Prep

**Acceptance criteria**:
- [ ] `vsce package` succeeds without errors
- [ ] Generated `.vsix` installs locally
- [ ] Right-click menu shows "Scan with QVC"
- [ ] Scan results output correctly in terminal

### Phase 4: Self-Scan + Bug Fixes

**Acceptance criteria**:
- [ ] Self-scan high-confidence hit rate ≥ 80%
- [ ] 0 false positives in "top 3" results
- [ ] All 50 rules load successfully
- [ ] BOM check passes (no BOM files)

### Phase 5: Complete Documentation

| Document | Filename | Lang |
|----------|----------|:--:|
| V8 Complete Report | `docs/V8_完整项目报告.md` | CN |
| V8 Project Report | `docs/V8_Project_Report_EN.md` | EN |
| Updated User Guide | `docs/QVC_用户使用手册.md` | CN |
| Updated User Guide | `docs/QVC_User_Guide_EN.md` | EN |
| Changelog | `CHANGELOG.md` | CN+EN |
| Updated README | `README.md` | CN+EN |

### Phase 6: GitHub + PyPI Ship

**Acceptance criteria**:
- [ ] GitHub master = V8 code
- [ ] PyPI shows version 1.0.0
- [ ] `pip install qvc-overseer` works
- [ ] `qvc scan .` outputs correctly

---

## IV. Anti-Scope (Iron Rules)

| Won`t Do | Why |
|-----------|-----|
| ❌ New languages (Rust, C++, etc.) | Cut in V4, moved to future |
| ❌ New rules beyond 50 | V8 only hits 50, promise fulfilled |
| ❌ Fingerprint expansion (146+) | 145 is enough for now |
| ❌ Auto-fix patches | Violates "external overseer" positioning |
| ❌ Cloud service/API | V8 stays local tool |
| ❌ Community operations | V8 is tech-only, no ops |

---

## V. Risks & Mitigations

| Risk | Probability | Mitigation |
|------|:--:|------|
| AST analyzer conflicts with existing rules | Medium | Non-destructive integration — AST results as extra context, not regex replacement |
| GitHub Actions auto-PR creates noise | Medium | Only auto-PR for ≥90% confidence bugs, PR clearly labeled "Suggestions" |
| 50th rule adds false positives | Low | CERTIFICATE tier rule, high determinism |
| VS Code extension packaging fails | Medium | Local packaging test first, no actual publish |

---

## VI. Success Criteria

V8 success = 5 YES answers:

1. Rules ≥ 50? → YES
2. Python files parsed with AST, not pure regex? → YES
3. Auto-PR created on GitHub push? → YES
4. VS Code extension locally installable? → YES
5. `pip install qvc-overseer==1.0.0` + `qvc scan .` → valuable report in <2 minutes? → YES

---

> **V8 is not the most feature-complete version. It is the most promise-complete version.**
