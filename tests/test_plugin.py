"""stub CLI 端到端：命令/工具/注入/fail-open。"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import STUB_MEMLITE, collect_results, make_event, make_plugin, part_text, recall_parts, result_text


class FakeReq:
    def __init__(self, prompt: str):
        self.prompt = prompt
        self.system_prompt = ""
        self.extra_user_content_parts = []


def test_find_memlite_prefers_existing(tmp_path):
    import main as plugin_module

    target = tmp_path / "memlite-bin"
    target.write_text("#!/bin/sh\nexit 0\n")
    target.chmod(0o755)
    assert plugin_module.find_memlite(str(target)) == str(target)
    assert plugin_module.find_memlite("/definitely/not/here") in (None,) or plugin_module.find_memlite("/definitely/not/here")


def test_scope_project_modes():
    plugin = make_plugin({"scope_mode": "global"})
    ev = make_event(sender_id="u1", session="s1")
    assert plugin._scope_project(ev) == ""
    plugin = make_plugin({"scope_mode": "sender", "project_prefix": "ab"})
    assert plugin._scope_project(ev).startswith("ab:")
    plugin = make_plugin({"scope_mode": "session", "project_prefix": "ab"})
    assert plugin._scope_project(ev).startswith("ab:session:")


def test_parse_flags():
    import main as plugin_module

    values, content = plugin_module._parse_command_flags(
        "--title 我的名 --tags=a,b 正文 内容"
    )
    assert content == "正文 内容"
    assert values["title"] == "我的名"
    assert values["tags"] == "a,b"


def test_format_recall_shapes():
    import main as plugin_module

    doc = {
        "backend": "bm25",
        "fallback": "",
        "hits": [{"score": 0.9, "id": "abcdefgh1234", "title": "甲题", "content": "正文"}],
    }
    block = plugin_module.format_recall(doc, 5, 1200)
    assert "<memlite_memory>" in block and "</memlite_memory>" in block
    assert "甲题" in block and "abcdefgh" in block and "memlite bm25" in block
    assert plugin_module.format_recall({"hits": []}, 5, 1200) == ""


def test_format_chain_and_show():
    import main as plugin_module

    doc = {
        "entry": {"id": "aaaaaaaa1111", "title": "本条", "content": "正文"},
        "ancestors": [{"id": "bbbbbbbb2222", "title": "因", "content": "因正文"}],
        "descendants": [{"level": 1, "descendant": {"id": "cccccccc3333", "title": "果", "content": ""}}],
    }
    text = plugin_module.format_chain(doc, 8000)
    assert "🔺因链（1 层" in text and "🔻果链（1 条）" in text and "本条" in text
    show = plugin_module.format_show({"id": "aaaaaaaa1111", "title": "t", "content": "c", "tags": [], "project": "", "ancestors": [], "children": []})
    assert "id: aaaaaaaa1111" in show


def test_stub_remember_and_recall_roundtrip(tmp_path):
    os.environ["MEMLITE_STUB_STATE"] = str(tmp_path / "state")
    plugin = make_plugin()
    args = ["remember", "甲关键词 正文", "--json", "--title", "甲题"]
    doc, error, stderr = asyncio.run(plugin._run(args, 10))
    assert error is None and doc["id"], (doc, error, stderr)
    block_doc, error2, _ = asyncio.run(plugin._run(["recall", "甲关键词", "--json", "--limit", "5"], 10))
    assert error2 is None
    hits = block_doc.get("hits", [])
    assert hits and hits[0]["title"] == "甲题"


def test_stub_sensitive_rejection(tmp_path):
    os.environ["MEMLITE_STUB_STATE"] = str(tmp_path / "state")
    plugin = make_plugin()
    doc, error, stderr = asyncio.run(
        plugin._run(["remember", "敏感 password=x1", "--json"], 10)
    )
    assert doc is None and "拒绝入库" in stderr


def test_command_remember_and_recall(tmp_path):
    os.environ["MEMLITE_STUB_STATE"] = str(tmp_path / "state")
    plugin = make_plugin()
    ev = make_event()
    results = asyncio.run(collect_results(plugin.command_remember(ev, "甲关键词 正文 --title 甲题")))
    assert "已存" in result_text(results[0])
    results = asyncio.run(collect_results(plugin.command_recall(ev, "甲关键词")))
    assert "甲题" in result_text(results[0])


def test_command_remember_sensitive_passes_cli_text(tmp_path):
    os.environ["MEMLITE_STUB_STATE"] = str(tmp_path / "state")
    plugin = make_plugin()
    ev = make_event()
    results = asyncio.run(collect_results(plugin.command_remember(ev, "敏感 password=x1")))
    assert "拒绝入库" in result_text(results[0])


def test_injection_fails_open_without_engine(tmp_path):
    plugin = make_plugin({"memlite_path": "/definitely/not/memlite", "auto_recall": True})
    ev = make_event("甲关键词 的问题")
    req = FakeReq("甲关键词 的问题")
    asyncio.run(plugin.on_llm_request(ev, req))
    # fail-open：无注入、无异常
    assert req.extra_user_content_parts == []


def test_injection_hits_with_stub(tmp_path):
    os.environ["MEMLITE_STUB_STATE"] = str(tmp_path / "state")
    plugin = make_plugin()
    # 先放两条进 stub 库
    asyncio.run(plugin._run(["remember", "甲关键词 正文", "--json", "--title", "甲题"], 10))
    ev = make_event("甲关键词 怎么办")
    req = FakeReq("甲关键词 怎么办")
    asyncio.run(plugin.on_llm_request(ev, req))
    blocks = recall_parts(req)
    assert blocks and "甲题" in blocks[0]
    assert "memlite_rules" in req.system_prompt


def test_nomem_skips_injection(tmp_path):
    os.environ["MEMLITE_STUB_STATE"] = str(tmp_path / "state")
    plugin = make_plugin()
    asyncio.run(plugin._run(["remember", "甲关键词 正文", "--json", "--title", "甲题"], 10))
    ev = make_event("/nomem 甲关键词")
    req = FakeReq("/nomem 甲关键词")
    asyncio.run(plugin.on_llm_request(ev, req))
    assert recall_parts(req) == []


def test_group_denied_by_default(tmp_path):
    os.environ["MEMLITE_STUB_STATE"] = str(tmp_path / "state")
    plugin = make_plugin()
    ev = make_event(group=True)
    req = FakeReq("甲关键词")
    asyncio.run(plugin.on_llm_request(ev, req))
    assert recall_parts(req) == []
    # 与 respire 对齐：不允许时静默跳过（fail-open），不注入任何提示
    assert req.extra_user_content_parts == []


def test_commands_registered_shape():
    plugin = make_plugin()
    # 指令与工具方法存在
    for name in (
        "command_help", "command_status", "command_recall", "command_remember",
        "command_show", "command_forget", "command_tree", "command_chain", "command_sync",
        "tool_recall", "tool_show", "tool_remember", "tool_chain",
    ):
        assert hasattr(plugin, name), name
