#!/usr/bin/env python3
"""Stateful `memlite` stub for plugin tests.

The plugin spawns this file directly (shebang + exec bit).  State lives in
``$MEMLITE_STUB_STATE/state.json``; every invocation appends argv to
``state["log"]``.  Output shapes mirror the real memlite CLI (--json).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _load(state_dir: Path) -> dict:
    path = state_dir / "state.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"records": {}, "log": []}


def _save(state_dir: Path, state: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def _flag(argv: list[str], name: str, default: str = "") -> str:
    if name in argv:
        i = argv.index(name)
        if i + 1 < len(argv):
            return argv[i + 1]
    for token in argv:
        if token.startswith(name + "="):
            return token.split("=", 1)[1]
    return default


def main() -> int:
    state_dir = Path(os.environ.get("MEMLITE_STUB_STATE", "/tmp/memlite-stub-state"))
    state = _load(state_dir)
    records: dict = state.setdefault("records", {})
    state.setdefault("log", []).append(sys.argv[1:])
    argv = sys.argv[1:]

    if argv and argv[0] == "recall":
        query = argv[1] if len(argv) > 1 else ""
        hits = []
        for rid, rec in records.items():
            if query[:4] in rec["content"] or query[:4] in rec["title"]:
                hits.append({
                    "score": 0.9,
                    "id": rid,
                    "ts": rec.get("ts", 1.0),
                    "title": rec["title"],
                    "content": rec["content"],
                    "tags": [],
                    "project": rec.get("project", ""),
                    "ancestors": [],
                    "children": [],
                })
        print(json.dumps({"backend": "bm25", "fallback": "", "hits": hits}, ensure_ascii=False))
        return 0

    if argv and argv[0] == "remember":
        content = argv[1] if len(argv) > 1 else ""
        if "敏感" in content and "password" in content:
            print("拒绝入库：命中敏感信息（明文口令）。改存位置指针后重试。", file=sys.stderr)
            return 3
        rid = f"{len(records) + 1:012d}"[:12]
        records[rid] = {
            "title": _flag(argv, "--title") or content[:10],
            "content": content,
            "tags": _flag(argv, "--tags"),
            "project": _flag(argv, "--project"),
            "parent": _flag(argv, "--parent"),
            "ts": 1.0,
        }
        state["records"] = records
        _save(state_dir, state)
        print(json.dumps({
            "id": rid,
            "title": records[rid]["title"],
            "embedded": False,
            "records": len(records),
            "parent": _flag(argv, "--parent"),
        }, ensure_ascii=False))
        return 0

    if argv and argv[0] == "show":
        rid = argv[1]
        rec = records.get(rid)
        if rec is None:
            print(f"memlite exited 1: 记忆不存在: {rid}", file=sys.stderr)
            return 1
        print(json.dumps({
            "id": rid, "ts": 1.0, "title": rec["title"], "content": rec["content"],
            "tags": [], "project": rec.get("project", ""), "ancestors": [], "children": [],
        }, ensure_ascii=False))
        return 0

    if argv and argv[0] == "chain":
        rid = argv[1]
        rec = records.get(rid)
        if rec is None:
            print(f"记忆不存在: {rid}", file=sys.stderr)
            return 1
        print(json.dumps({
            "entry": {"id": rid, "title": rec["title"], "content": rec["content"]},
            "ancestors": [], "descendants": [],
        }, ensure_ascii=False))
        return 0

    if argv and argv[0] == "forget":
        rid = argv[1] if len(argv) > 1 else ""
        if rid not in records:
            print(f"记忆不存在: {rid}", file=sys.stderr)
            return 1
        records.pop(rid)
        state["records"] = records
        _save(state_dir, state)
        print(json.dumps({"deleted": rid}))
        return 0

    if argv and argv[0] == "status":
        print(json.dumps({
            "data_dir": "/tmp/memlite-stub",
            "records": len(records),
            "lines": len(records),
            "bad_lines": 0,
            "vectors": 0,
            "embedding": {"provider": "none", "model": ""},
            "sync": {"repo": None},
        }, ensure_ascii=False))
        return 0

    if argv and argv[0] == "tree":
        lines = [f"[{rid[:8]}] {rec['title']}" for rid, rec in records.items()]
        print(json.dumps({"nodes": [{"i": i, "line": ln} for i, ln in enumerate(lines)]},
                         ensure_ascii=False))
        return 0

    if argv and argv[0] == "sync":
        print(json.dumps({"committed": False, "local_sha": "a" * 40,
                          "remote_sha": "a" * 40, "verified": True}))
        return 0

    print(f"stub: unknown argv {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
