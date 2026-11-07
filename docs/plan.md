# astrbot_plugin_memlite 计划

| 阶段 | 产出 | 状态 |
|---|---|---|
| P1 骨架 | metadata.yaml + _conf_schema.json + main.py（find/run/注入/4 工具/指令组） | 📌 本次 |
| P2 测试 | pytest：stub CLI 单测（格式化/守卫/超时）+ 真 CLI 端到端 + test_real_load | 📌 本次 |
| P3 文档发布 | README + CHANGELOG + GitHub 推送 | 📌 本次 |
| P4 嵌入档暴露 | embedding 配置透传（CLI reembed/环境变量） | 后续 |

## P1/P2 细节

- main.py ≤ 1000 行：find_memlite / _run(json) / format_* / Plugin 类 / on_llm_request / 4×llm_tool / command_group
- metadata.yaml：name=astrbot_plugin_memlite, version 0.1.0, astrbot_version >=4.16,<5
- _conf_schema.json：enabled / memlite_path / data_dir / project_prefix / scope_mode / auto_recall / recall_limit / min_prompt_chars / budget_chars / max_show_chars / max_tool_chars / timeouts / admin_only 忘记/群聊开关
- tests：conftest + stub_memlite（可执行 shell 脚本按 argv 回 JSON）+ test_plugin.py（格式化/守卫/fail-open）+ test_real_cli.py（真 CLI 端到端，本机缺失 skip）+ test_real_load.py（AstrBot PluginManager 装载）
