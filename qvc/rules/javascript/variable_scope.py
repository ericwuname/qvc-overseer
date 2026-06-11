"""JavaScript/TypeScript 变量作用域检查 V3 — JSX 语义识别"""

import re
from pathlib import Path
from qvc.models.bug import Severity, BugCategory, RootCause
from qvc.models.severity import RuleLayer
from ..base import BaseRule


class JSVariableScopeRule(BaseRule):
    rule_id = "JS_VAR_SCOPE_001"
    name = "JavaScript 变量作用域检查"
    description = "检测 JSX/TSX 中使用了未声明的变量（V3：JSX语义识别）"
    severity = Severity.SEVERE
    category = BugCategory.VAR_SCOPE
    languages = ["javascript", "typescript"]
    layer = RuleLayer.HEURISTIC
    base_confidence = 0.30

    # ── 已知全局 ──
    KNOWN_GLOBALS = {
        "undefined", "null", "true", "false", "this", "console",
        "window", "document", "navigator", "localStorage", "sessionStorage",
        "fetch", "JSON", "Math", "Date", "Array", "Object", "String",
        "Number", "Boolean", "Promise", "Set", "Map", "Error", "Symbol",
        "React", "useState", "useEffect", "useRef", "useMemo", "useCallback",
        "useContext", "useReducer", "useLayoutEffect", "useImperativeHandle",
        "props", "children", "key", "ref",
        "event", "e", "target", "value", "index", "item", "i", "j", "k",
        "setTimeout", "setInterval", "clearTimeout", "clearInterval",
        "require", "module", "exports", "__dirname", "__filename",
        "process", "Buffer", "global", "Intl",
        "alert", "confirm", "prompt", "history", "location",
        "FormData", "Blob", "File", "FileReader", "URL", "URLSearchParams",
        "atob", "btoa", "encodeURIComponent", "decodeURIComponent",
    }

    # ── JSX 属性名（不作为变量检查）──
    JSX_ATTRS = {
        "className", "style", "onClick", "onChange", "onSubmit", "onKeyDown",
        "onKeyUp", "onFocus", "onBlur", "onMouseEnter", "onMouseLeave",
        "onScroll", "onLoad", "onError", "disabled", "placeholder",
        "type", "name", "id", "href", "src", "alt", "title", "role",
        "aria-label", "data-", "maxLength", "minLength", "autoComplete",
        "autoFocus", "readOnly", "checked", "defaultValue", "defaultChecked",
    }

    def analyze(self, file_path: Path, source: str, ast_tree=None) -> list:
        bugs = []
        lines = source.split("\n")

        # ── 收集所有声明 ──
        declared = self._collect_declarations(lines)

        # ── 收集 .map() 迭代参数 ──
        map_params = self._collect_map_params(source)

        # ── 扫描 JSX 表达式 ──
        # 找 JSX 中的 {expression}
        jsx_expr = re.compile(r'\{([^}]+)\}')

        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            # 跳过注释
            if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                continue

            for match in jsx_expr.finditer(line):
                expr = match.group(1).strip()

                # 跳过空表达式
                if not expr:
                    continue

                # 提取顶层标识符（可能在复杂表达式中）
                identifiers = self._extract_identifiers(expr)

                for var_name in identifiers:
                    # 跳过已知全局、声明、迭代参数
                    if var_name in self.KNOWN_GLOBALS:
                        continue
                    if var_name in declared:
                        continue
                    if var_name in map_params:
                        continue
                    if var_name.isdigit():
                        continue
                    if len(var_name) <= 1:
                        continue

                    # 跳过 JSX 属性值（style={outputStyle} 中的 outputStyle 才检查）
                    # 但 className="foo" 不进入这里，只有 {expr} 才进来
                    # 跳过属性赋值键（<div onClick={...}> 中 onClick 不是变量）
                    if any(var_name == attr or var_name.startswith(attr) 
                           for attr in self.JSX_ATTRS if var_name == attr.split('-')[0]):
                        continue

                    bugs.append(self._create_bug(
                        file_path=file_path,
                        line_start=line_no,
                        line_end=line_no,
                        title=f"变量 '{var_name}' 可能未声明",
                        description=f"在 JSX 模板中使用了 '{var_name}'，但在当前作用域内未找到声明",
                        code_snippet=stripped[:200],
                        fix_suggestion=f"确认 '{var_name}' 已在组件作用域内声明（useState/变量声明/props解构）",
                        root_cause=RootCause.COPY_PASTE,
                        confidence=0.30,
                        extra_id=var_name,
                    ))

        return bugs

    def _collect_declarations(self, lines: list[str]) -> set:
        """收集所有变量/函数/导入声明"""
        declared = set()

        full_text = "\n".join(lines)

        # const/let/var 声明（含解构）
        for m in re.finditer(r'\b(?:const|let|var)\s+(\w+)\s*[:=]', full_text):
            declared.add(m.group(1))
        for m in re.finditer(r'\b(?:const|let|var)\s*[{\[]([^}=]+)[}\]]', full_text):
            for name in re.findall(r'(\w+)', m.group(1)):
                declared.add(name)

        # 函数声明
        for m in re.finditer(r'\bfunction\s+(\w+)', full_text):
            declared.add(m.group(1))

        # 箭头函数赋值
        for m in re.finditer(r'\b(?:const|let|var)?\s*(\w+)\s*=\s*(?:\([^)]*\)|[^=])\s*=>', full_text):
            declared.add(m.group(1))
        for m in re.finditer(r'\b(?:const|let|var)?\s*(\w+)\s*=\s*async\s*(?:\([^)]*\))\s*=>', full_text):
            declared.add(m.group(1))

        # 普通函数赋值
        for m in re.finditer(r'\b(?:const|let|var)?\s*(\w+)\s*=\s*function', full_text):
            declared.add(m.group(1))

        # 导入
        for m in re.finditer(r'\bimport\s+(\w+)\s+from', full_text):
            declared.add(m.group(1))
        for m in re.finditer(r'\bimport\s*\{([^}]+)\}', full_text):
            for name in re.findall(r'(\w+)', m.group(1)):
                if name not in ("import", "from", "as"):
                    declared.add(name)
        for m in re.finditer(r'\bimport\s+(\w+)', full_text):
            if m.group(1) not in ("React", "type"):
                declared.add(m.group(1))

        # Hook 解构
        for m in re.finditer(r'(?:const|let|var)?\s*\[([^\]]+)\]\s*=\s*use(?:State|Reducer)\b', full_text):
            for name in re.findall(r'(\w+)', m.group(1)):
                declared.add(name)
        for m in re.finditer(r'\b(?:const|let|var)?\s*(\w+)\s*=\s*use(?:Ref|Memo|Callback|Context)\b', full_text):
            declared.add(m.group(1))

        # 函数参数（含解构）
        for m in re.finditer(r'(?:function\s+\w+)?\s*\(([^)]*)\)\s*(?:=>|\{)', full_text):
            params = m.group(1)
            # 解构: ({ a, b }) =>
            for name in re.findall(r'(\w+)\s*[,:})]', params):
                if name not in ("const", "let", "var"):
                    declared.add(name)
            # 简单参数: (a, b) =>
            for name in re.findall(r'^\s*(\w+)\s*$|,\s*(\w+)\s*', params):
                n = name[0] or name[1]
                if n:
                    declared.add(n)

        return declared

    def _collect_map_params(self, source: str) -> set:
        """收集 .map() 回调参数"""
        params = set()
        # items.map((item) => ...), items.map((item, idx) => ...)
        for m in re.finditer(r'\.map\s*\(\s*\(([^)]*)\)\s*=>', source):
            for name in re.findall(r'(\w+)', m.group(1)):
                params.add(name)
        # items.map(function(item) {...})
        for m in re.finditer(r'\.map\s*\(\s*function\s*\(([^)]*)\)', source):
            for name in re.findall(r'(\w+)', m.group(1)):
                params.add(name)
        # forEach, filter, reduce, some, every
        for method in ("forEach", "filter", "reduce", "some", "every", "find", "flatMap"):
            for m in re.finditer(rf'\.{method}\s*\(\s*\(([^)]*)\)\s*=>', source):
                for name in re.findall(r'(\w+)', m.group(1)):
                    params.add(name)
        return params

    def _extract_identifiers(self, expr: str) -> set:
        """从 JSX 表达式中提取顶层标识符，跳过明显的函数调用和属性访问"""
        identifiers = set()

        # 拆分为逻辑片段
        # 跳过字符串字面量内容
        expr_clean = re.sub(r'["\'](?:[^"\\]|\\.)*["\']', '', expr)
        expr_clean = re.sub(r'["\'](?:[^"\\]|\\.)*["\']', '', expr_clean)
        expr_clean = re.sub(r'`[^`]*`', '', expr_clean)
        expr_clean = re.sub(r'//[^\n]*', '', expr_clean)

        # 按运算符和标点分割
        tokens = re.split(r'[+\-*/%<>=!&|?:;,()\[\]{}\s]+', expr_clean)

        for token in tokens:
            token = token.strip()
            if not token or not token[0].isalpha():
                continue
            # 跳过属性访问 obj.prop → 只检查 obj，但这里 token 如果是完整 obj.prop 则跳过
            if '.' in token:
                # 取第一段
                first = token.split('.')[0]
                if first.isidentifier():
                    identifiers.add(first)
                continue
            # 跳过数组索引 arr[0]
            if '[' in token:
                first = token.split('[')[0]
                if first.isidentifier():
                    identifiers.add(first)
                continue
            # 纯标识符
            if token.isidentifier() and token[0].islower():
                identifiers.add(token)

        return identifiers
