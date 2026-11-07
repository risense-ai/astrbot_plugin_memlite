#!/usr/bin/env python3
"""Standalone structure/metadata validator for astrbot_plugin_memlite.

No third-party dependency is required.  When PyYAML is present the validator
uses it for stricter checks; otherwise it falls back to a small top-level YAML
reader.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = (
    "metadata.yaml",
    "main.py",
    "_conf_schema.json",
    "README.md",
    "LICENSE",
    "requirements.txt",
    "CHANGELOG.md",
)
TOOL_NAMES = {
    "memlite_recall",
    "memlite_show",
    "memlite_remember",
    "memlite_chain",
}
COMMANDS = {"help", "status", "recall", "remember", "show", "forget", "tree", "chain", "sync"}
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

failures: list[str] = []
passes: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    if condition:
        passes.append(label)
    else:
        failures.append(f"{label}{': ' + detail if detail else ''}")


def read_top_level_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    data: dict = {}
    current = None
    for line in text.splitlines():
        if not line or line.startswith((" ", "\t", "#")):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            current = key.strip()
            data[current] = value.strip().strip('"').strip("'")
    return data


def main() -> int:
    meta_path = ROOT / "metadata.yaml"
    if not meta_path.is_file():
        failures.append("metadata.yaml missing")
        print_report()
        return 1
    try:
        import yaml  # type: ignore

        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        yaml_mode = "pyyaml"
    except ImportError:
        meta = read_top_level_yaml(meta_path)
        yaml_mode = "fallback"
    passes.append(f"metadata read ({yaml_mode})")

    for key in ("name", "desc", "version", "author"):
        if not str(meta.get(key) or "").strip():
            failures.append(f"metadata.{key} missing")
    passes.append("metadata required keys")

    if str(meta.get("name") or "") != "astrbot_plugin_memlite":
        failures.append(f"metadata.name = {meta.get('name')!r}")
    passes.append("metadata.name")

    for rel in REQUIRED_FILES:
        check((ROOT / rel).is_file(), f"file present: {rel}")

    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(main_text)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    check(any(c.name == "MemliteAstrBotPlugin" for c in classes), "plugin class")
    funcs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for tool in TOOL_NAMES:
        check(f"tool_{tool.split('_', 1)[1]}" in funcs, f"llm tool: {tool}")
    for cmd in COMMANDS:
        check(f"command_{cmd}" in funcs, f"command: {cmd}")
    check("on_llm_request" in funcs, "hook: on_llm_request")

    schema_path = ROOT / "_conf_schema.json"
    try:
        import json

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        for key in ("enabled", "memlite_path", "data_dir", "scope_mode", "recall_limit"):
            check(key in schema, f"config schema: {key}")
    except Exception as exc:
        failures.append(f"_conf_schema.json parse: {exc}")

    for pattern in SECRET_PATTERNS:
        for rel in ("main.py", "_conf_schema.json"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            if pattern.search(text):
                failures.append(f"possible secret in {rel}")
    passes.append("no secrets in shipped files")

    print_report()
    return 1 if failures else 0


def print_report() -> None:
    for label in passes:
        print(f"PASS {label}")
    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{len(passes)} passed, {len(failures)} failed")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    raise SystemExit(main())
