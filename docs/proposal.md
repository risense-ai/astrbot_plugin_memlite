# astrbot_plugin_memlite 方案

> **仓库**：`risense/astrbot_plugin_memlite`
> **形态**：AstrBot 插件（Python），`memlite` CLI sidecar 薄壳
> **依赖**：memlite CLI ≥0.2.0（Rust 二进制，与 TS/Rust 版数据互通）
> **参考**：astrbot_plugin_respire 0.2.0（成熟 sidecar 模式）、astrbot-plugin-notes（AstrBot 4.29.4 API 实测）
> **日期**：2026-11-07

---

## 一、定位

让 AstrBot 拥有 memlite 的因果树本地记忆：每轮自动召回注入、LLM 工具（召回/存取/因果链）、`/memlite` 指令组。数据与 Rust CLI、DSH 插件（dsh-memlite）、memlite-js **同一份 JSONL 库互通**。

与 respire 插件（同宿主先例）的差异：
| 维度 | respire | 本插件 |
|---|---|---|
| sidecar | rsrs CLI（加密/persona/space） | memlite CLI（JSONL/因果树/项目隔离，无加密概念） |
| 因果 | attach/merge 判后即存流程重 | 轻量：remember 认因 + chain/tree 直接可查 |
| 隔离 | bot 硬隔离 space + persona 软隔离 | project 字段软隔离（scope_mode: global/sender/session） |
| 互通 | rsrs 专用 | memlite 全家（Rust CLI / dsh-memlite / Kimi 等） |

## 二、核心机制

1. **自动召回注入**：`@filter.on_llm_request` 里 `memlite recall <query> --json --limit N`，格式化为标题档（分数+短id+标题+摘要），append 到 `req.extra_user_content_parts`（`TextPart(...).mark_as_temp()`，不污染会话历史）。fail-open：CLI 缺失/超时/坏 JSON 一律静默跳过。
2. **LLM 工具**（`@filter.llm_tool`，docstring Args 段声明参数）：
   - `memlite_recall(query, limit)`——标题召回；提示空结果≠不存在
   - `memlite_show(id, chain_depth)`——全文+因果视界
   - `memlite_remember(content, title, tags, parent)`——存记忆；敏感信息由 CLI 敏感闸拒绝（返回拒绝文案引导改存指针）
   - `memlite_chain(id, depth)`——因果链全文
3. **指令组 `/memlite`**：help/status/recall/remember/show/forget/tree/chain/sync
4. **敏感闸**：CLI `remember` 内置扫描（口令/密钥/身份证/银行卡/手机号/JWT/PEM）命中即拒（退出码 3 + 文案），插件原样透传文案——插件侧不重复实现。
5. **project 隔离**：`scope_mode`（global/sender/session）决定每次调用的 `--project` 值（`<project_prefix>:<scope值>`）；global 即全部共享。

## 三、sidecar 调用

- `find_memlite()`：配置路径 > PATH > `~/.cargo/bin` > respire-memlite 构建产物常见位置
- `_run(args, timeout)`：`asyncio.subprocess` + `--json` + 超时杀进程；超时/非零/坏 JSON → 返回 None（调用方 fail-open）或抛错（命令面转 error 文案）
- 数据目录：`data_dir` 配置留空 = CLI 默认分层解析；AstrBot 进程 cwd 不保证工作区，**建议用户显式配置**（hint 说明）
- 超时：recall 14s / write 20s / status 10s（照 respire 先例）

## 四、非目标

- 不做 Web 管理台、不做嵌入档配置（memlite CLI 嵌入属可选，后续版本暴露）
- 不做自动会话捕获（memlite 是判存/指令驱动的策展记忆）
- 不做 bot 硬隔离（单 bot 场景为主；多 bot 共库是 memlite 互通卖点）

## 五、风险

| 项 | 对策 |
|---|---|
| CLI 缺失 | find_memlite 探测失败 → 插件禁用态 + /memlite 提示安装 |
| CLI 版本漂移 | --json 契约锁定（compat.md）；插件按宽容解析（缺字段容忍） |
| AstrBot 版本 API 变化 | TextPart/GreedyStr try-import 兜底（respire 同款） |
| 群聊记忆跨用户 | 默认群聊关、scope_mode 默认 global（memlite 是个人记忆模型），管理员可开 session 隔离 |

## 六、验收

- pytest 全绿（stub CLI 单测 + 真 CLI 端到端，真 CLI 缺失则 skip）
- 真机装载：AstrBot 本体 PluginManager 加载零报错（test_real_load）
- 手动验收：recall 注入命中、工具调用、敏感拒绝文案
