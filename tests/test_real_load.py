"""Real `PluginManager.load()` verification.

Fresh subprocess with ASTRBOT_ROOT pointed at a throwaway dir; the plugin is
installed into <root>/data/plugins/ the way AstrBot would, loaded through the
real manager, then one hook and one command are exercised on the instance.
Skipped when the interpreter cannot import astrbot (set ASTRBOT_PYTHON).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import STUB_MEMLITE

PLUGIN_DIR = Path(__file__).resolve().parent.parent
MODULE_PATH = "data.plugins.astrbot_plugin_memlite.main"

LOADER_SCRIPT = r"""
import asyncio
import json
import os
import sys

root = sys.argv[1]
os.environ["ASTRBOT_ROOT"] = root
sys.path.insert(0, root)

def fail(message):
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    raise SystemExit(1)

try:
    import astrbot  # noqa: F401
except Exception as exc:
    print(json.dumps({"skipped": f"astrbot not importable: {exc}"}))
    raise SystemExit(0)

from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
from astrbot.core.platform.message_type import MessageType
from astrbot.core.platform.platform_metadata import PlatformMetadata
from astrbot.core.provider.entities import ProviderRequest
from astrbot.core.provider.register import llm_tools
from astrbot.core.star.star import star_map
from astrbot.core.star.star_handler import star_handlers_registry
from astrbot.core.star.star_manager import PluginManager

MODULE_PATH = "data.plugins.astrbot_plugin_memlite.main"


def build_event(text):
    message = AstrBotMessage()
    message.type = MessageType.FRIEND_MESSAGE
    message.self_id = "bot"
    message.session_id = "sess1"
    message.message_id = "m1"
    message.sender = MessageMember(user_id="user1", nickname="Alice")
    message.message = []
    message.message_str = text
    message.raw_message = None
    message.timestamp = 1700000000
    metadata = PlatformMetadata(name="test", description="stub", id="test")
    event = AstrMessageEvent(text, message, metadata, "sess1")
    event.role = "admin"
    return event


class StubContext:
    def get_all_stars(self):
        return []


async def run() -> dict:
    manager = PluginManager(StubContext(), None)
    ok, error = await manager.load(specified_dir_name="astrbot_plugin_memlite")
    if not ok:
        fail(f"PluginManager.load failed: {error}")

    metadata = star_map.get(MODULE_PATH)
    if metadata is None:
        fail(f"{MODULE_PATH} missing from star_map")
    star_cls = metadata.star_cls
    if metadata.name != "astrbot_plugin_memlite":
        fail(f"metadata.name = {metadata.name!r}")
    if metadata.version != "0.1.0":
        fail(f"metadata.version = {metadata.version!r}")
    if not metadata.activated:
        fail("plugin is not activated")

    config = metadata.config
    if not isinstance(config, AstrBotConfig):
        fail(f"config is {type(config).__name__}, expected AstrBotConfig")
    for key, expected in (
        ("enabled", True),
        ("recall_limit", 5),
        ("scope_mode", "global"),
        ("auto_recall", True),
        ("allow_groups", False),
    ):
        if config.get(key) != expected:
            fail(f"config[{key}] = {config.get(key)!r}, expected {expected!r}")

    handlers = star_handlers_registry.get_handlers_by_module_name(MODULE_PATH)
    if len(handlers) != 16:
        fail(f"expected 16 bound handlers, found {len(handlers)}")

    tools = [tool for tool in llm_tools.func_list if tool.name.startswith("memlite_")]
    if len(tools) != 4:
        fail(f"expected 4 llm tools, found {len(tools)}")
    inactive = [tool.name for tool in tools if not tool.active]
    if inactive:
        fail(f"llm tools inactive: {inactive}")

    req = ProviderRequest(prompt="真实加载后的召回")
    await star_cls.on_llm_request(build_event("真实加载后的召回"), req)
    if "<memlite_rules>" not in (req.system_prompt or ""):
        fail("system rules were not injected by the loaded instance")
    texts = [
        part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "")
        for part in (req.extra_user_content_parts or [])
    ]
    if not any("<memlite_memory>" in text and "真实加载" in text for text in texts):
        fail(f"recall block missing from injected parts: {texts!r}")

    help_text = ""
    async for result in star_cls.command_help(build_event("/memlite help")):
        chain = getattr(result, "chain", None) or []
        help_text += "".join(getattr(part, "text", "") for part in chain)
    if "/memlite status" not in help_text:
        fail(f"command_help produced unexpected output: {help_text!r}")

    return {"ok": True, "handlers": len(handlers), "tools": sorted(t.name for t in tools)}


print(json.dumps(asyncio.run(run()), ensure_ascii=False))
"""


def _astrbot_python() -> str | None:
    candidate = os.environ.get("ASTRBOT_PYTHON", sys.executable)
    return candidate if Path(candidate).exists() else None


@pytest.mark.skipif(_astrbot_python() is None, reason="no interpreter with AstrBot installed")
def test_plugin_manager_load(tmp_path, monkeypatch):
    python = _astrbot_python()

    root = tmp_path / "astrbot-root"
    plugin_dest = root / "data" / "plugins" / "astrbot_plugin_memlite"
    config_dir = root / "data" / "config"
    plugin_dest.mkdir(parents=True)
    config_dir.mkdir(parents=True)

    shutil.copytree(
        PLUGIN_DIR,
        plugin_dest,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            "tests", "docs", "__pycache__", ".git", "data", ".pytest_cache"
        ),
    )

    state_dir = tmp_path / "memlite-stub-state"
    state_dir.mkdir()
    monkeypatch.setenv("MEMLITE_STUB_STATE", str(state_dir))
    STUB_MEMLITE.chmod(0o755)
    (state_dir / "state.json").write_text(
        json.dumps(
            {
                "records": {
                    "aaaaaaaa1111": {
                        "title": "真实加载召回验证",
                        "content": "真实加载召回验证正文",
                        "project": "",
                    }
                },
                "log": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "astrbot_plugin_memlite_config.json").write_text(
        json.dumps({"memlite_path": str(STUB_MEMLITE)}), encoding="utf-8"
    )

    environment = dict(os.environ)
    environment["MEMLITE_STUB_STATE"] = str(state_dir)
    environment.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [python, "-c", LOADER_SCRIPT, str(root)],
        capture_output=True,
        text=True,
        timeout=180,
        env=environment,
        cwd=str(tmp_path),
    )

    stdout = proc.stdout.strip()
    try:
        payload = json.loads(stdout.splitlines()[-1]) if stdout else {}
    except (json.JSONDecodeError, IndexError):
        payload = {}
    if "skipped" in payload:
        pytest.skip(payload["skipped"])
    assert proc.returncode == 0, (
        f"loader failed ({proc.returncode}):\n{stdout}\n{proc.stderr[-3000:]}"
    )
    assert payload.get("ok") is True, payload
    assert payload["handlers"] == 16
    assert payload["tools"] == [
        "memlite_chain",
        "memlite_recall",
        "memlite_remember",
        "memlite_show",
    ]
