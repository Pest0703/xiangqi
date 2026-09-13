# 中国象棋私人导师

面向初学者到中级棋手的 Windows 中国象棋学习软件。产品原则是先引导思考，再逐级给出思路、候选方向、候选走法，最后才显示最佳着。

当前版本为 **Phase 1 可运行工程骨架**：包含配置、日志、SQLite 初始化、核心数据结构、Pikafish 自动发现与 UCI 输出解析、LLM Provider 边界和最小桌面界面。完整象棋规则将在 Phase 2 实现。

## 运行

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m xiangqi_tutor
```

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

复制 `.env.example` 为 `.env` 可配置外部服务。API Key 不应写入源码或提交版本库；正式设置页将优先使用 Windows Credential Manager。

## Pikafish

本项目不捆绑 Pikafish 或 NNUE。可将 `pikafish.exe` 与匹配的 `.nnue` 放入 `engines/`，或用 `XIANGQI_PIKAFISH_PATH` 和 `XIANGQI_PIKAFISH_NNUE_PATH` 指定。Pikafish 本体为 GPLv3；官方网络权重有单独许可，尤其需在商业分发前取得相应授权。

详细设计见 [架构](docs/ARCHITECTURE.md) 与 [开发计划](docs/DEVELOPMENT_PLAN.md)。

