# Changelog

## 0.1.0 (2026-11-07)

首版。

- 自动召回注入（on_llm_request，temp content part，fail-open）
- 4 个 LLM 工具（memlite_recall/show/remember/chain，docstring Args 契约）
- /memlite 指令组 9 命令（help/status/recall/remember/show/forget/tree/chain/sync）
- scope_mode 三档隔离（global/sender/session，project 字段承载）
- 敏感闸透传（CLI rc=3 文案）
- 17 例测试：stub CLI 单测 + 真 CLI 端到端 + PluginManager 真装载（16 handlers/4 tools）
