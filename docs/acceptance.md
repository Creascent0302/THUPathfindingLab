# 实际验收记录

## 2026-09-19：复杂场景、惯性与网页批量测评

本轮在原平台上实现三维场景物件、可编辑惯性模型与后台多方法评分。未新增基础运行依赖；PyTorch 仍为独立可选依赖。普通 CPU、Linux、项目内 Python/Node 环境下已实际执行：

- 全套 Python 测试 **136 passed，63.15 s**，1 条已有 Starlette/AnyIO 弃用警告；原始输出：[inertial-pytest.txt](../artifacts/inertial-pytest.txt)。
- TypeScript 检查、Prettier 检查、Vite 生产构建与 Ruff 通过。
- 新真实浏览器流程 **9 项通过、0 页面异常**：默认三维 RGB、惯性设置、自动布置、自定义地图保存、后台配对测评、导出、回放与取消不排名。脚本 `scripts/browser_evaluation.py` 使用随机本地端口和临时数据目录，结束自动清理。
- 原有真实浏览器 `scripts/browser_authoring.py` **13 组流程通过、0 页面异常**，覆盖四算法选择、ZIP 提交、地图编辑、结果删除与回放。
- 数值与运行测试新增速度向量/预测一致性、jerk/横向加速度约束、连续制动、旧档兼容、极小制动力保护、制动不收敛保护、终点后碰撞推翻成功、所有结束滑行不增加完成度。
- 批次测试覆盖作业错误、取消、共享容量、重启、配额、不同执行模式的测试集标识、保存地图快照与完整配对。

场景截图与浏览器报告在 `artifacts/browser-evaluation/`。摄像头和算法画面均使用实际三维物件的 RGB 渲染；默认 640×360 单独测量约 40 ms/帧，完整闭环还包含算法、通信与评分，不能把它理解为端到端帧率保证。

算法已重新适配并实际训练新版 CNN 权重；独立场景成功率、样本量与失败案例见 [新版算法报告](inertial-results.md)。下面保留之前平台阶段的历史检查。

## 2026-09-18：历史平台验收

日期：2026-09-18。范围：用户要求先验收的 A/B 阶段平台，以及验证链路所需的最小探针。未开发正式模块化算法或端到端模型。

## 实际环境

| 项目 | 实际版本 |
|---|---|
| 系统 | Linux x86_64，内核 5.15.0-139，glibc 2.31 |
| Python | 3.13.9，项目独立 venv |
| NumPy / OpenCV | 2.2.6 / 4.11.0.86 headless |
| FastAPI / Pydantic / Uvicorn | 0.115.12 / 2.11.5 / 0.34.3 |
| Node / React / TypeScript / Vite | 22.16.0 / 19.1.0 / 5.8.3 / 6.3.5 |
| 浏览器 | Playwright 1.52.0，Chromium 136.0.7103.25 |
| 加速硬件 | 未使用 GPU，不需要 PyTorch |

已完成的真实操作：

- 从空项目虚拟环境安装固定版本运行和测试依赖。
- 在另一个全新 `/tmp/pathlab-clean-acceptance` 环境按 `requirements.lock` 安装依赖并执行测试。
- 实际运行 `python scripts/setup.py --mirror`：依赖检查、项目内 Node、`npm ci`、TypeScript 检查、Vite 生产构建全部通过。
- 实际启动 HTTP 服务，访问静态工作台、上传素材、WebSocket 收取状态并操作车辆。
- `python run.py doctor` 显示前端已构建、四个注册插件可用。
- `pip check` 无依赖冲突；Ruff 检查通过；前端 `npm run check` 通过。

## 自动回归

本轮完整回归结果为 **78 passed，25.76 s**（已扩展 ZIP、地图编辑和删除回归），无失败；有 1 条 Starlette 对上游 AnyIO 类型别名的弃用警告，不影响测试。

原始输出保存在 [artifacts/pytest.txt](../artifacts/pytest.txt)。初版交付在全新锁定环境的检查为 **54 passed，11.88 s**；本轮未新增依赖，见 [clean-environment-tests.txt](../artifacts/clean-environment-tests.txt)。

覆盖内容：

- 相机投影/反投影、车辆/世界坐标变换、RGB 编解码及尺寸一致性。
- 自行车转弯方程、速度/转角/变化率约束、零速不能原地旋转。
- 八类场景、多个种子的几何合法性、起点可见性、同种子重复渲染。
- 合法连续推进可成功，停车不能成功；终点瞬移、回头弯跳跃、沿干扰线换线被拒绝。
- 协议版本、NaN、错误形状、空结果、缺失动作、消息超限、输出/参数大小上限。
- 初始化异常、推理异常、进程退出、死循环超时；worker 被回收且下一次实验正常执行。
- 纯视觉接口检查，无场景名称、种子、目标路径、位姿或未来帧。
- 实例重置、手动单步、暂停、取消、物理制动、租约过期和并发限制。
- 单帧、自然排序图像序列、真实 MJPEG 视频解码；跨帧状态计数和回放随机跳转。
- HTTP / WebSocket、结果持久化、JSON / CSV 导出、仿真图像重建。
- 重启时恢复中断记录，同时不覆盖仍在运行的 CLI 评测。
- 无标注素材的误差、进度、成功和换线等真值指标保持 null。

## 真实浏览器验收

`scripts/browser_smoke.py` 启动真实服务和 Chromium，执行 **15 项流程检查**，无页面 JavaScript 异常：

1. 初始中文页面、真实首帧与地图。
2. 手动速度输入导致真实位移及图像变化。
3. 暂停后仿真帧数稳定。
4. 单步只增加一帧。
5. 停止后任务取消并完成制动。
6. 保存结果的首尾跳转。
7. 重置后新 UUID、零历史帧。
8. 图片上传。
9. 单帧探针推理。
10. 已保存实验列表。
11. 勾选结果生成对比表。
12. 390 px 窄屏不发生整页横向溢出。
13. 切换场景后不再被旧 WebSocket 快照覆盖。
14. 录制素材回放不借用当前仿真预览的真值地图或标定。
15. 1920 px 宽屏下，点击提示的坐标正确换算为原图像素，包含留白造成的缩放偏移。

工作截图与日志位于 `artifacts/browser/`；其中中文字体在没有系统中文字体的 Linux 环境中也能正确显示。项目保留了一份 [工作台截图](../artifacts/workbench.png)。

维护者复现浏览器验收（学生正常使用不需要安装）：

```bash
# Linux，在项目根目录
.venv/bin/python -m pip install playwright==1.52.0
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/browsers" .venv/bin/python -m playwright install chromium
.venv/bin/python scripts/browser_smoke.py
```

脚本会启动并关闭自己的临时端口服务。Windows 需将 Python 路径换成 `.venv\Scripts\python.exe`，并在环境中设置同样的 `PLAYWRIGHT_BROWSERS_PATH`；此浏览器脚本的 Windows 路径尚未实测。

## 实际批量运行

命令：

```bash
python run.py benchmark --algorithms stop constant --seeds 101 102 --steps 400
```

初版地图上的历史批量结果共 **32 回合、10750 帧**（早于本轮多段场景扩展，不能作为新地图的算法成绩），实际墙钟耗时 **540.7 s**。所有预登记组合均执行，未删除失败场景。

| 探针 | 样本量 | 驾驶成功 | 结束原因 |
|---|---:|---:|---|
| stop | 16 | 0 | 16 次到达回合时限 |
| constant | 16 | 0 | 15 次持续偏离、1 次非法换线 |

固定动作平均进度按场景族为 20.5%–38.7%，但没有完整成功回合。典型非法换线发生在 `close_lines / seed 101`；完整导出样例为 [artifacts/example-run.json](../artifacts/example-run.json)。该探针不读取图像决策，其失败不能被解读为正式寻迹算法的表现。

报告：[Markdown](../artifacts/benchmark/report.md)、[JSON](../artifacts/benchmark/report.json)、[CSV](../artifacts/benchmark/report.csv)。原始逐帧记录保留在 `artifacts/runs/`。

## 具体环境限制与未验证项

- 该执行环境的沙箱禁止创建本地套接字，导致异步 TestClient 和浏览器启动受限；这部分检查已在获得允许后的非沙箱执行环境中通过，未跳过测试。
- 官方 PyPI / npm 源下载在本环境中很慢，改用 `--mirror` 后实际安装成功。安装脚本仍保留官方源方式。
- Windows、macOS 及 Python 3.10–3.12 未实际运行，不能声明已通过。代码使用跨平台入口，Windows 进程回收与 PID 查询仍需要该系统上的验收。
- 未测真实摄像头、真实车辆、硬件执行器、轮胎侧滑、三维障碍或复杂纹理域差异。
- 当前素材不支持人工真值标注导入和可变帧率 PTS；因此不能产出感知准确率或录制视频的真实米制误差。
- 场景检查针对教学场景，并非完整的自相交/可达性求解器。任意路口、重叠和真实分叉需要额外规则，不能直接纳入核心集合。
- 当前仅支持公开车辆限制和纯视觉观察；额外传感器权限、学习训练、模型 checkpoint、正式目标关联算法均未实现。

平台验收后，再开发模块化时序寻迹算法及其消融，最后开发端到端训练链路。不会将现有探针替代这两项交付。

## 本轮平台功能验收（2026-09-18）

新增运行记录单条 / 批量删除、复杂同线多段地图、ZIP 算法上传、图形地图编辑器与 SVG 立体场景；移除前端「接入与使用」。正式算法继续暂缓。

新增后端回归覆盖：活动记录删除保护、终态记录与图像清理、上传模板真实运行与服务重启、子模块导入和相对路径资源读取、上传时不执行代码、路径穿越 / 符号链接 / 重复路径 / 大小限制 / 语法错误拒绝、提交目录隔离、上传暂存状态不可见、地图曲率和相机可见性、车辆参数变化、退化折返与交叉拒绝、保存地图后仿真与回放、复杂地图几何、旧渲染版本兼容。

`scripts/browser_authoring.py` 使用独立临时数据目录和真实 Chromium，完成 9 组端到端流程：移除帮助导航、复杂场景 / 立体视角 / 俯视切换、半径和车辆限制、鼠标拖点 / 保存 / 导出、390 px 窄屏、加载 / 导入 / 应用地图、ZIP 上传后在自定义地图上真实运行、批量删除并清除回放、非法 ZIP 错误展示。页面异常为 0。原有 `scripts/browser_smoke.py` 的 15 项流程同样通过。

新增浏览器验收命令：

```bash
.venv/bin/python scripts/browser_authoring.py
```

原始记录与截图位于 `artifacts/browser-authoring/`；旧流程截图位于 `artifacts/browser/`。前端 TypeScript 检查、Prettier 和生产构建通过，Python Ruff 检查通过。未额外测试 Windows / macOS；上传接口不具备恶意代码沙箱或多用户认证。
