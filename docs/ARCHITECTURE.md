# 技术架构

## 核心数据流

棋盘输入 → MatchService → GameService → Position/规则 → EngineManager → AnalysisResult → MoveAssessment/TutorEvidence → AI 导师 → UI

规则层是唯一事实来源；Pikafish 负责棋力判断；LLM 只解释结构化证据。外部耗时工作由 QThread 执行，结果携带 FEN，旧局面结果不会覆盖新局面。

## 权威模型与坐标

- Position 是唯一权威局面，采用不可变更新；棋盘按 rank × 9 + file 存储。
- 内部 file=0..8 对应 UCI/Pikafish 的 a..i；rank=0 是红方底线，rank=9 是黑方底线。
- FEN 从黑方底线（rank 9）写到红方底线（rank 0），行棋方为 w（红）或 b（黑）。
- GUI 正向显示时红方在下，内部 a 路显示在右；翻转只转换屏幕行列，不改变逻辑坐标、FEN 或引擎走法。

## 模块边界

| 模块 | 职责 |
|---|---|
| board | Piece/Position、伪合法着、合法着、将军与终局 |
| services | 当前对局、历史、undo/redo、FEN 用例编排 |
| notation | 引擎坐标与中文走法显示 |
| engine | UCI 进程、握手、配置、MultiPV、评分归一化 |
| tutor | 强类型证据、Prompt、OpenAI-compatible Provider |
| ui | 原生棋盘、交互、设置与后台任务呈现 |
| database | SQLite 初始化，后续承载棋谱与学习记录 |

MatchService 是对局控制权与状态的唯一来源，管理 GameMode、human_side、engine_side、position_version 和 MatchState。EngineManager 在单一后台执行器中复用一个 UCI 进程；所有任务绑定 request_id、FEN 与 position_version。

MoveAssessmentService 对比走前/走后分析并转换为用户视角损失。PVValidator 逐步执行引擎 PV，只有规则层验证成功的步骤才进入 TutorEvidence。VariationTree 独立于主对局 undo/redo 栈，确保未来沙盘分支不破坏主线。

## 评分规范

UCI score 先记录为行棋方视角，再生成 score_for_red：正值始终代表红方较优，负值始终代表黑方较优。红走、黑走分别有协议测试。

## 进程与密钥

引擎启动后完成 uci/uciok、isready/readyok，退出时依次尝试 stop、quit，必要时终止进程。引擎缓存键包含 FEN、程序路径/修改时间、NNUE、Threads、Hash、MultiPV、depth 和 movetime。

API Key 只从 Windows keyring 或临时环境读取，不进入日志、QSettings、缓存键或 Git。远程端点要求 HTTPS；localhost/127.0.0.1 可使用 HTTP。
