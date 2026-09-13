# 技术架构

## 核心数据流

棋盘输入 → GameService → Position/规则 → EngineService → AnalysisResult → TutorEvidence → AI 导师 → UI

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

## 评分规范

UCI score 先记录为行棋方视角，再生成 score_for_red：正值始终代表红方较优，负值始终代表黑方较优。红走、黑走分别有协议测试。

## 进程与密钥

引擎启动后完成 uci/uciok、isready/readyok，退出时依次尝试 stop、quit，必要时终止进程。API Key 只从 Windows keyring 或开发环境读取，不进入日志、QSettings 或 Git。
