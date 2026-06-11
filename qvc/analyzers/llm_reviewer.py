"""LLM V2 - multi-provider: OpenAI / Ollama / compatible APIs"""

import json
from pathlib import Path
from qvc.models.bug import Bug, Severity, BugCategory


class LLMReviewer:
    """Multi-backend LLM reviewer"""

    SYSTEM_PROMPT = """You are a senior code reviewer specializing in AI-generated code.
Find: variable scope errors, null safety issues, API mismatches, state sync failures,
fragile parsing, broken dependency chains, incomplete features, security risks.
Return JSON array. Each bug: severity(FATAL/SEVERE/MODERATE/MINOR), category, title, description, line, fix_suggestion, confidence(0-1).
Empty array if no bugs. Return ONLY JSON."""

    def __init__(self, provider="openai", model="gpt-5.2", api_key=None, api_base=None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("pip install openai")
            if self.provider == "local":
                self._client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            else:
                kwargs = {}
                if self.api_key:
                    kwargs["api_key"] = self.api_key
                if self.api_base:
                    kwargs["base_url"] = self.api_base
                self._client = OpenAI(**kwargs)
        return self._client

    def review_file(self, file_path, source, language):
        source = source[:15000]
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Review {language} file:\n```\n{source}\n```"},
        ]
        try:
            extra = {} if self.provider == "local" else {"response_format": {"type": "json_object"}}
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0.2, max_tokens=4096, **extra
            )
            content = resp.choices[0].message.content or "[]"
            if self.provider == "local":
                content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return self._parse(content, file_path)
        except Exception:
            return []

    def review_files(self, contexts):
        bugs = []
        for ctx in contexts:
            bugs += self.review_file(ctx["path"], ctx["source"], ctx.get("language", "unknown"))
        return bugs

    def _parse(self, content, file_path):
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        items = data if isinstance(data, list) else data.get("bugs", data.get("issues", []))
        bugs = []
        for i, item in enumerate(items):
            try:
                sev = Severity.from_string(item.get("severity", "MODERATE"))
                try:
                    cat = BugCategory[item.get("category", "STYLE")]
                except KeyError:
                    cat = BugCategory.STYLE
                bugs.append(Bug(
                    id=f"LLM-{Path(file_path).stem}-{i+1}", severity=sev, category=cat,
                    title=item.get("title", ""), description=item.get("description", ""),
                    file_path=str(file_path), line_start=item.get("line", 1), line_end=item.get("line", 1),
                    code_snippet=item.get("code_snippet", ""), fix_suggestion=item.get("fix_suggestion", ""),
                    confidence=float(item.get("confidence", 0.6)), rule_id="LLM_REVIEW",
                ))
            except Exception:
                continue
        return bugs
