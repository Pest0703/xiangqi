# MVP 状态

更新日期：2026-09-14

## 当前可用

- 完整基础规则、真实棋盘、点击走棋、吃子、红黑轮换、将军/应将、终局。
- 新对局、悔棋、重做、翻转、FEN 导入导出、中文棋谱。
- 人机、双人、分析三种模式；人机模式可选红黑方和四档强度。
- MatchService 明确管理 human_side、engine_side 和等待/思考/终局状态。
- 执红后电脑自动回应；执黑时电脑自动走红方首着；思考期间棋盘锁定。
- 人机悔棋/重做按完整用户决策回合处理。
- 常驻 EngineManager、同深度 MultiPV 聚合、CP/Mate 评分、PV 合法性验证。
- MoveAssessment、合法/棋力双路径走法询问、重复局面提示。
- TutorEvidence 局面版本绑定、明确任务路由、四级渐进提示、结构化 TutorResponse。
- 推荐/威胁/计划箭头与关键/危险格坐标校验后绘制。
- Engine/Tutor SQLite 缓存、API 有限重试、本机 HTTP 服务兼容。
- 独立 VariationTree 数据模型支持多分支和节点 FEN；尚未接入完整沙盘 UI。

## 验证

- pytest：57 项通过。
- Ruff：通过。
- MyPy 核心模块：通过。
- 覆盖率：73%。
- ResourceWarning 严格回归：通过；已修复 SQLite 连接泄漏。
- 原生 Windows GUI：1366×820 实际启动、截图和退出通过。
- Fake UCI 人机闭环：执红自动回应、执黑自动首着均通过。
- 百炼 qwen-plus：本轮真实连接成功，约 0.65 秒；密钥未输出或写入仓库。

## 明确未通过

- 本机没有 Pikafish，真实引擎 20 FEN、真实棋力和 Mate 局面矩阵未执行。
- 没有真实 Pikafish 证据，因此 10 个次优着与 20 个导师事实质量验收未执行。
- VariationTree 尚无历史节点入口、分支列表和比较面板。
- 自动保存对局、自动复盘、棋谱库和正式长将/长捉判罚未实现。
- 流式 AI 输出尚未实现。

## 已知限制

- GUI 首次等待用户局面的后台基线分析完成后，才具备完整的走前/走后 MoveAssessment；用户过快落子时会安全跳过评价。
- AI 强度当前映射 depth/movetime；低档仍使用 bestmove，没有刻意随机降智。
- API 客户端在一次导师任务内复用并重试；跨多次 TutorThread 的全局连接池尚未实现。
