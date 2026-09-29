# 框架验收

在项目根目录：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/browser_student.py
.venv/bin/python scripts/verify_classroom.py
python run.py doctor
```

浏览器验收需要可选的 `playwright==1.52.0` 和 Chromium。脚本只操作临时数据目录，不修改教师实验。前端用 `npm --prefix frontend run check` 和 `npm --prefix frontend run build` 检查。

测试覆盖 SDK、真实 Worker 通信与故障、图片/视频、WebSocket、惯性及倒车、路线身份、碰撞、评分、地图保存与重名、ZIP 校验、配额、删除和批量队列。`tests/faults.py` 中固定动作与停车对象只用于协议测试，不注册到实际平台，不包含视觉或规划算法，不进入发行包。

发行包还须独立验证：

```bash
.venv/bin/python scripts/check_release.py release/PathLab-linux-x86_64/PathLab
```

该检查从临时工作目录启动真实可执行文件，清除 PYTHONPATH，使用独立数据目录，验证初始目录、学生 ZIP 和辅助导入、逐帧运行、回放、批量结果和重启持久化。构建脚本另行审计原生模块和冻结字节码归档，防止误把后端源码放入包中。

固定回归地图位于 `scenarios/`；兼容旧地图的逻辑仍属于当前框架。`.venv/`、`.cache/`、`artifacts/`、`frontend/dist/`、`release/` 均是本地环境或输出，不纳入版本控制。只向学生分发经过验证的生成包。

## 历史学生版本验证（2026-09-27）

- 当前 Ubuntu / Python 3.13：153 项框架测试通过。
- 编译后的原生模块：68 项渲染、动力学、评测与道路身份回归通过。
- 源码服务和 Linux 发行程序分别通过真实 Chromium 学生流程，均为 0 页面异常。
- 真实发行程序完成 ZIP 上传、辅助模块与相对资源读取、WebSocket、回放、批量对比、删除和重启持久化验收。
- TypeScript、Prettier、Ruff 和生产前端构建通过。

Windows、macOS 发行程序未在本环境构建或验收；需要在目标系统执行打包脚本和相同验收。

## 课堂轨迹版验证（2026-09-29）

- 当前 Ubuntu / Python 3.13：185 项自动测试通过，覆盖接口故障、路径控制、惯性制动、旧地图迁移、直接起步、合法性检查、存储和批量评测。
- 12 张无障碍地图 × 3 个种子（7、1009、42），时序拓扑轨迹示例 **36/36 成功**；左右镜像均覆盖，**非法换线 0 次**，最大横向误差 **12.74 cm**。
- 直线接口示例在 seed=7、42 的直线地图均成功；它不用于弯道识别。
- 所有闭环测试均使用真实算法 Worker、RGB 图像和平台路径执行器；每帧 `action` 为空，停止阶段也保留真实惯性滑行。
- 源码版与 Linux 编译版均通过 Chromium：两个示例从算法栏选择后以路径模式运行，另验证手动前进/倒车、单步、上传、地图保存与重名、导入导出、刷新恢复、回放和窄屏；均为 0 页面异常。
- Ruff、TypeScript、Prettier 和生产前端构建通过。
- Linux x86_64 新发行 ZIP 通过独立临时目录验收：两个内置路径示例完整闭环、上传及辅助模块、WebSocket、回放、批量评分、删除和重启持久化。
- 18 个私有后端模块编译，包内只公开 SDK 与 5 个教学 Python 文件；无教师数据、旧算法缓存或私有后端 Python 字节码。

这是一组工程回归结果，不代表任意自定义地图或任意相机配置必然成功。改变相机、车体、纹理、采样分辨率或增加延迟后，需要重新评测。

| 地图族 | 成功次数 | 三次测试中最大的 P95 横向误差 / cm | 最大横向误差 / cm |
|---|---:|---:|---:|
| `straight` | 3/3 | 0.00 | 0.00 |
| `bend` | 3/3 | 5.37 | 6.27 |
| `s_curve` | 3/3 | 6.52 | 8.37 |
| `sharp` | 3/3 | 6.67 | 7.66 |
| `hairpin` | 3/3 | 6.31 | 8.13 |
| `parallel` | 3/3 | 0.00 | 0.00 |
| `close_lines` | 3/3 | 1.78 | 1.91 |
| `repeated` | 3/3 | 6.86 | 8.62 |
| `tight_s` | 3/3 | 10.32 | 12.74 |
| `spiral` | 3/3 | 3.74 | 4.06 |
| `spiral_reverse` | 3/3 | 3.96 | 4.17 |
| `spiral_dense` | 3/3 | 3.70 | 4.16 |

本次完整证据在 `.cache/classroom-acceptance/trial-kohka8ak`（7、1009）和 `trial-4fxqv3z9`（42），每例均保留参数、代码摘要、逐帧记录和终止原因。早期试验保留在其他 trial 目录，不覆盖失败或早期版本。旧的 23 个 Git 跟踪测试地图先经过逐字节备份到 `.cache/student-legacy-scenarios.zip`，再由新课程地图替换；原来的 `artifacts/maps` 与运行记录未改动。
