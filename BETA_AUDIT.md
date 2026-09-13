# 中国象棋 AI 教学软件 Beta 审计

审计日期：2026-09-14

## 结论

基础 MVP 和人机对弈架构已通过自动验收，但完整 Beta 仍被真实 Pikafish 与真实导师质量矩阵阻断。Fake UCI 结果只证明协议、并发、自动走棋和状态机接线，不代表真实棋力。

## PASS

| 范围 | 结果 |
|---|---|
| FEN 基础验证 | 双方各一枚将帅、时钟、行棋方、九路十行、未知棋子 |
| FEN strict | 九宫、相象河界、将帅照面 |
| GameStatus | 走棋、undo、redo、load 后统一重算；redo 终局重新触发 |
| 人机状态机 | 红黑选择、AI 首着/回应、输入锁定、过期与非法 bestmove 拒绝 |
| 人机悔棋 | AI 已回应撤两步；AI 思考中撤用户一步；redo 按决策回合 |
| UCI 可靠性 | 常驻进程、取消标记、同深度完整 MultiPV、CP/Mate 模型 |
| PV | 逐步规则验证，非法尾部截断，保留中文着法和前后 FEN |
| 教学结构 | MoveAssessment、任务路由、渐进提示、请求局面绑定 |
| 视觉结构 | TutorResponse Pydantic 校验，非法坐标丢弃，箭头/高亮绘制 |
| 缓存 | Engine/Tutor 参数化 SQLite 缓存 |
| 工程质量 | 57 tests、Ruff、MyPy、73% coverage、三版本 Windows CI |
| 原生 GUI | 启动、渲染、退出通过 |
| 百炼 API | qwen-plus 真实连接成功，约 0.65 秒 |

## 本轮发现并修复

- FEN 允许“两枚同色将帅”的漏洞。
- 负时钟和 fullmove=0 未拒绝。
- redo 恢复终局时状态和终局信号不一致。
- MultiPV 混用不同深度候选。
- GUI 每次分析重启引擎。
- 黑方评分、Mate 与 None 展示语义不完整。
- 原始 PV 未经过规则层逐步验证。
- 所有导师问题落入 FREE_QUESTION，提示永远停在 Hint 1。
- SQLite with 事务块不自动关闭连接，造成 ResourceWarning。
- AI 只支持 HTTPS，无法接入 localhost Ollama/vLLM。

## 尚未解决

1. 真实 Pikafish 20 FEN 验收。
2. 10 个真实次优着 MoveAssessment 与自然语言解释验收。
3. 20 个真实引擎局面的导师事实抽查。
4. 完整沙盘 UI、分支比较和主线入口。
5. 正式长将/长捉判罚规则。
6. 对局保存、自动复盘和流式 AI 输出。

## 技术债务

- MainWindow 仍偏大，应在沙盘 UI 前拆分人机、分析和导师控制器。
- EngineManager 退出时为保证无残留进程会等待当前任务结束；后续可增强 UCI 中断确认。
- 中文记谱的多兵“前中后”复杂消歧和反向解析未完成。
- 真实引擎版本目前用可执行文件路径和修改时间参与缓存，尚未读取 id name/version。
