"""Shared test setup. ASTRBOT_ROOT points at a throwaway dir so plugin import
doesn't litter the repo with data/."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

PLUGIN_DIR = Path(__file__).resolve().parent.parent
STUB_MEMLITE = Path(__file__).resolve().parent / "stub_memlite.py"

os.environ.setdefault("ASTRBOT_ROOT", tempfile.mkdtemp(prefix="astrbot-memlite-test-"))
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))


def make_event(
    text: str = "hello",
    *,
    admin: bool = True,
    group: bool = False,
    sender_id: str = "user1",
    platform: str = "test",
    session: str = "sess1",
):
    """Build a real AstrMessageEvent without a platform adapter."""
    from astrbot.core.platform.astr_message_event import AstrMessageEvent
    from astrbot.core.platform.astrbot_message import AstrBotMessage, MessageMember
    from astrbot.core.platform.message_type import MessageType
    from astrbot.core.platform.platform_metadata import PlatformMetadata

    message = AstrBotMessage()
    message.type = MessageType.GROUP_MESSAGE if group else MessageType.FRIEND_MESSAGE
    message.self_id = "bot"
    message.session_id = session
    message.message_id = "m1"
    message.sender = MessageMember(user_id=sender_id, nickname="Alice")
    message.message = []
    message.message_str = text
    message.raw_message = None
    message.timestamp = int(time.time())

    metadata = PlatformMetadata(name=platform, description="stub", id=platform)
    event = AstrMessageEvent(text, message, metadata, session)
    event.role = "admin" if admin else "member"
    return event


def make_plugin(config_overrides: dict | None = None):
    """Instantiate the plugin with a bare context and dict config."""
    import main as plugin_module

    config = {"memlite_path": str(STUB_MEMLITE), **(config_overrides or {})}
    return plugin_module.MemliteAstrBotPlugin(SimpleNamespace(), config)


def stub_state(tmp: str) -> Path:
    """Per-test stub state dir configured via env."""
    return Path(tmp)


async def collect_results(handler):
    """Drain an async-generator command handler into a list."""
    return [item async for item in handler]


def result_text(result) -> str:
    """Extract plain text from a MessageEventResult."""
    chain = getattr(result, "chain", None)
    if chain:
        parts = []
        for component in chain:
            text = getattr(component, "text", None)
            if isinstance(text, str):
                parts.append(text)
        if parts:
            return "".join(parts)
    return str(result)


def part_text(part) -> str:
    if isinstance(part, dict):
        return str(part.get("text") or "")
    return str(getattr(part, "text", "") or "")


def recall_parts(req) -> list[str]:
    """All injected user content parts carrying a recall block."""
    texts = [part_text(part) for part in (req.extra_user_content_parts or [])]
    return [text for text in texts if "<memlite_memory>" in text]
