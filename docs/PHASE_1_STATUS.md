# Phase 1 验收记录

日期：2026-09-14

## 已完成

- 建立 `src/xiangqi_tutor` 分层包、数据目录、配置目录、测试和文档。
- 提供 Python 入口、全局异常边界、UTF-8 文件日志与高 DPI 策略。
- 建立 SQLite 首次初始化与引擎/导师缓存、棋谱、学习事件基础表。
- 建立不可变坐标/走法/候选分析数据结构。
- 建立 Pikafish 路径与 NNUE 自动发现、UCI MultiPV `info` 行解析。
- 建立厂商无关 `LLMProvider` 边界。
- 接入导师核心系统提示词与分任务 `PromptBuilder`，包含证据边界、渐进提示、水平适配和可视化 JSON 约束。
- 建立 1366×768 最小主窗口，缺少 Pikafish 时明确降级而不崩溃。

## 环境检查

- Windows 10/11 兼容的 64 位环境；CPU 为 12 核 16 线程 Intel Core i7-1260P。
- 可用 Python：3.13.0，满足项目要求的 3.11+；系统 `python` 别名不可用，应使用 `py -3.13` 或项目 `.venv`。
- Git 2.54.0 可用。
- Pikafish 与 PyInstaller 尚未安装；PyInstaller 留到打包阶段加入。
- 项目虚拟环境已经安装 PySide6、pytest、httpx、pydantic-settings 与 keyring。

## 验证结果

- `pytest`：包含工程骨架及导师提示词构造测试。
- `compileall`：通过。
- Qt 离屏启动：成功创建并显示 1366×768 主窗口，事件循环可处理。
- 截图：`phase1-gui.png`。离屏 Qt 平台未枚举到 Windows 中文字体，因此截图中文字显示为方框；这是离屏测试环境限制，Phase 3 必须在原生 Windows 平台按 1366×768、1920×1080 和高 DPI 再次实测。

## 下一阶段入口

Phase 2 从 `board` 模块开始，先定义 Piece/Position、完整伪合法着和合法着过滤，再完成将军、应将、将死、将帅照面及全部棋子专项测试。
