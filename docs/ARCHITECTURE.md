# 技术架构

## 核心约束

- Pikafish 决定候选着与局面评分；LLM 只能根据结构化引擎证据做教学解释。
- GUI、规则、状态、引擎、导师、数据与训练通过明确接口解耦。
- 所有耗时操作放入后台任务；Qt 主线程只负责界面更新。
- 没有 Pikafish 或 API 时应用仍可打开，已有棋谱与规则功能仍可使用。
- 棋谱和训练数据必须记录来源与许可，无法确认再分发权的数据只允许用户导入。

## 模块边界

| 模块 | 职责 | 不负责 |
|---|---|---|
| `ui` | 棋盘绘制、交互、时间线、导师面板 | 规则判断和搜索 |
| `board` | 九路十行规则、合法着生成、将军/将死 | UI 和引擎通信 |
| `models` | Position、Move、分析结果等稳定数据结构 | 持久化与业务流程 |
| `notation` | 象棋 FEN、引擎坐标、中文记谱转换 | 搜索 |
| `engine` | Pikafish 发现、UCI 会话、输出解析、超时恢复 | 教学措辞 |
| `tutor` | Provider、PromptBuilder、证据校验、结构化视觉指令 | 最佳着计算 |
| `database` | 迁移、棋谱、缓存、学习记录 | UI |
| `training` | 残局、猜棋、渐进提示、统计 | 未验证题目生成 |
| `services` | 用例编排、异步任务、复盘流水线 | 具体控件 |

## 主要数据流

`GUI 操作 → GameService → Rules/Position → EngineService → AnalysisResult → TutorService → 文字 + 可视化 JSON → GUI`

复盘先由引擎逐步筛选关键局面，再只把关键证据交给模型。缓存键包含 FEN 与完整引擎设置；导师缓存还包含问题、引擎证据和模型名。

## Pikafish 接入

采用长生命周期独立进程和标准输入输出管道。启动握手为 `uci/uciok` 与 `isready/readyok`；配置使用 `setoption name Threads/Hash/MultiPV/EvalFile value ...`；分析使用中国象棋 FEN 的 `position fen` 和 `go depth` 或 `go movetime`。解析每个 MultiPV 的最后完整深度结果，在 `bestmove` 后发布不可变结果对象。

异常策略：启动前验证路径；握手和分析分别限时；stderr 写日志；退出时尝试 `stop`/`quit`；进程崩溃后允许重启；无合法着、将死和无 PV 作为正常终局结果表示。

## 并发模型

Phase 4 使用一个串行 EngineWorker 管理单个引擎进程，界面通过信号提交可取消任务。数据库连接按线程创建。HTTP 调用使用独立异步客户端，并有超时、有限重试和取消。

