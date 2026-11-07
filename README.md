# astrbot_plugin_memlite

> [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的 memlite 因果树本地记忆插件。
> 基于 [memlite CLI](https://github.com/risense-ai/respire-memlite)（Rust sidecar），与 DSH 插件、memlite-js 共享同一份 JSONL 库。

## 功能

- **自动召回注入**：每轮按用户消息 `memlite recall`，标题档以临时 content part 注入（不污染会话历史，不阻塞当前轮）
- **4 个 LLM 工具**：`memlite_recall`（召回）/ `memlite_show`（全文+因果邻居）/ `memlite_remember`（存记忆）/ `memlite_chain`（因果链全文）
- **`/memlite` 指令组**：help / status / recall / remember / show / forget / tree / chain / sync
- **敏感闸**：写闸由 CLI 内置（口令/密钥/身份证/银行卡/手机号/JWT/PEM 拒绝），文案原样透传
- **fail-open**：CLI 缺失、超时、回执异常一律不阻断聊天
- **互通**：与 Rust memlite CLI / dsh-memlite / memlite-js 共享 `memory.jsonl`；project 字段软隔离

## 安装

```bash
# 前置：memlite CLI（Rust，构建或下载）
cargo build --release --manifest-path respire-memlite/rust/Cargo.toml

# AstrBot 插件目录
git clone https://github.com/risense-ai/astrbot_plugin_memlite <astrbot_data>/data/plugins/astrbot_plugin_memlite
```

WebUI 插件市场接入待 npm/市场审核。配置项见 `_conf_schema.json`（`memlite_path` 留空自动探测；`data_dir` 建议显式填写）。

## 测试

```bash
source /tmp/astrbot-venv/bin/activate  # 需 AstrBot 依赖环境
python -m pytest tests/ -q             # 17 例全绿（stub CLI + 真 CLI 端到端 + 真机装载）
```

## 协议

MIT。
