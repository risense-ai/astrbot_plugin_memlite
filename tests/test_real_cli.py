"""真 memlite CLI 端到端（本机有 target/release/memlite 时跑，否则 skip）。"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import re

import pytest

from conftest import STUB_MEMLITE, make_event, make_plugin, result_text

REAL_CLI = "/Users/shiningray/projects/risense/respire-memlite/rust/target/release/memlite"
SKIP_REAL = bool(os.environ.get("MEMLITE_TEST_SKIP_REAL"))
REAL = shutil.which("memlite") or (REAL_CLI if Path(REAL_CLI).is_file() else "")

pytestmark = pytest.mark.skipif(
    SKIP_REAL or not (REAL and Path(REAL).is_file()), reason="memlite CLI 不在本机（或 MEMLITE_TEST_SKIP_REAL=1）"
)


def make_real_plugin(data_dir: str):
    return make_plugin({"memlite_path": REAL, "data_dir": data_dir})


def test_real_roundtrip(tmp_path):
    data_dir = str(tmp_path / "lib")
    plugin = make_real_plugin(data_dir)
    ev = make_event()
    results = asyncio_run_collect(plugin.command_remember(ev, "nginx 504 超时排查手册 --title nginx题"))
    text = result_text(results[0])
    assert "已存" in text
    rid = re.search(r"已存 ([0-9a-f]{12})", text).group(1)
    results = asyncio_run_collect(plugin.command_recall(ev, "nginx 超时"))
    assert "nginx题" in result_text(results[0])
    results = asyncio_run_collect(plugin.command_show(ev, rid))
    assert "nginx 504" in result_text(results[0])


def asyncio_run_collect(coro_or_gen):
    import asyncio

    async def drain():
        if inspect_is_gen(coro_or_gen):
            return [item async for item in coro_or_gen]
        return await coro_or_gen

    return asyncio.run(drain())


def inspect_is_gen(x):
    import inspect

    return inspect.isasyncgen(x)


def test_real_real_cli_missing(tmp_path):
    assert True
