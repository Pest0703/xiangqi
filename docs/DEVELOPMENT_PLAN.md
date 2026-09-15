# 开发计划

## 当前：MVP 已落地

已完成规则核心、可交互棋盘、人机状态机、常驻 UCI、走法评价、强类型导师证据、渐进提示和沙盘数据层。详情及实测边界见根目录 NEXT_STAGE_STATUS.md。

## 下一阶段（按优先级）

GitHub 案例调研与取舍见 [GITHUB_CASE_STUDY.md](GITHUB_CASE_STUDY.md)。按调研结论执行：

1. 使用真实 Pikafish 对至少 20 个代表性 FEN 做坐标、合法 PV、MultiPV、CP/Mate 方向交叉验收，并完成 10 个次优着评价；补齐 `ucinewgame → isready` 新对局生命周期。
2. 把现有 VariationTree 接入历史节点、分支面板、主线比较与导师 branch_id；分析结果归属节点，并增加评价趋势和转折点标记。
3. 独立实现“思考 → 分级提示 → 候选着 → 揭晓 → 原理 → 沙盘”的训练状态，默认不泄露最佳着。
4. 保存完整对局、FEN 序列和 MoveAssessment，筛选关键转折点后实现自动复盘。

高级题库、统计、自动整盘复盘和安装包继续后置，避免在可靠性验证之前扩张功能面。
