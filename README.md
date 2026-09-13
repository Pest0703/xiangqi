# 中国象棋私人导师

Windows 10/11 上可本地运行的中国象棋学习软件。当前 MVP 已支持完整基础规则、真实棋盘、点击走棋、中文棋谱、FEN、悔棋/重做，以及可选的 Pikafish 和 OpenAI-compatible AI 导师。

## 本地运行

    py -3.13 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
    .\.venv\Scripts\python.exe -m xiangqi_tutor

已配置好的当前工作目录可直接运行最后一条命令。测试命令：

    .\.venv\Scripts\python.exe -m pytest

## 已有能力

- 完整基础规则：马腿、象眼、炮架、过河、九宫、将帅照面、将军与应将、牵制、将死/困毙。
- QPainter 原生棋盘，32 枚文字棋子，选择与合法落点、最后一步、将军状态、翻转显示。
- 新对局、吃子、悔棋、重做、中文走棋历史、FEN 复制与载入。
- UCI EngineService、后台分析、MultiPV、固定红方视角评分和过期结果丢弃。
- 强类型导师证据包、渐进提示约束、后台 OpenAI-compatible 调用。
- 设置保存在 QSettings；API Key 进入 Windows 凭据库，不写入仓库。

## 外部服务

软件不捆绑 Pikafish/NNUE。可在“设置”中选择 pikafish.exe、配置参数并测试连接。没有引擎时，基础对局仍完全可用。

AI 导师支持 OpenAI-compatible API。设置 Base URL、模型和 API Key 后可测试连接。没有 AI 配置不影响下棋或引擎分析。

更精确的验收边界见 MVP_STATUS.md 和 BETA_AUDIT.md。
