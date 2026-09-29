# 寻迹实验室 · THU Pathfinding Lab

面向「智能交通创新实践」课程的四轮车视觉寻迹平台。支持手动驾驶、六种参考算法、ZIP 算法提交、自定义地图、惯性运动、批量评分及回放。Python / FastAPI 后端，React / TypeScript 前端，普通 CPU 即可运行。

## 安装与启动

需要 Python **3.10–3.13**，在项目目录执行：

```bash
python scripts/setup.py --mirror
python run.py
```

浏览器访问 **http://127.0.0.1:8000**。Linux 没有 `python` 命令时改用 `python3`；使用官方软件源时省略 `--mirror`。

安装脚本创建 `.venv`，安装固定版本依赖、项目内 Node.js 22 并构建前端。无需手动激活环境或另开 npm 服务；首次安装需要联网，之后平台离线运行。中文字体随前端提供。

CNN + GRU 需要额外安装一次 CPU 运行库，其余方法不需要 PyTorch：

```bash
python scripts/setup_learning.py
python run.py
```

端口占用时可以执行 `python run.py serve --port 8001`。无图形界面的环境可用 `python scripts/setup.py --skip-frontend --mirror`。

## 本地完整版本与起点规则

使用 `python run.py` 启动完整平台；内网访问可使用 `python run.py serve --host 0.0.0.0`。
车辆直接放在目标路线第一个点，朝向与起点箭头一致，初始速度为零。无需寻找起点，也不再需要点选或框选。
旧地图在预览、运行和批量评测时自动采用新规则，原地图文件和历史实验记录不被改写。
修复细节、102 次闭环验收和复现步骤见 [本地恢复与寻迹验收](docs/tracking-restoration.md)。
本分支包含时序拓扑、扫描线和学习基线。此前 `release/` 下的学生黑盒包不含内置算法，不代表当前完整版本，请从本目录启动。

## 使用

- **手动驾驶**：选择场景与「手动驾驶」，启动后调整速度、前轮转角。方向键控制，向下减速至负数即可倒车，空格制动；支持暂停、单步、停止与重置。制动遵守惯性模型，换向先停稳。可在「车辆惯性与制动」设置倒车许可和最高倒车速度；旧地图若禁用倒车，需手动开启后另存。
- **参考算法**：扫描线 PD、时序拓扑 + Pure Pursuit、时序拓扑 + MPC、CNN + GRU，以及独立的 PP / MPC 避障版。原版与避障版分别选择、评分，见 [算法说明](docs/algorithms.md)。
- **学生提交**：在「算法提交」下载模板和随附的接口文档，实现 `StudentAlgorithm`，将代码与所需资源打包成 ZIP 后上传并选用。无需编辑 `algorithms.json`；额外依赖由教师统一安装。先读 [学生算法开发指南](docs/student-guide.md)，底层协议见 [SDK 协议](docs/protocol.md)。
- **地图编辑**：通过「目标路线」「干扰线」「障碍物」三种模式点按、拖动或输入坐标。可设置车辆、相机、材质及物件尺寸、颜色和碰撞开关。目标路线受车辆最小转弯半径等几何约束。
- **地图保存**：保存后自动加入主页场景选择；重名追加 `(1)`、`(2)`。浏览器自动保存编辑草稿和实验设置；跨设备使用请保存到地图库或导出 JSON。
- **评测与回放**：批量选择方法、地图与种子，查看完整配对的评分、排行和失败原因。记录可回放、导出或删除；图片和视频模式用于感知分析，不生成缺少真值的闭环成绩。

内置八类基础场景由代码生成。另附 0920 困难地图，可安装到地图库：

```bash
.venv/bin/python scripts/install_challenges.py
```

Windows 使用 `.venv\Scripts\python.exe`。安装重复执行会跳过已有地图，不覆盖用户编辑。更多回归地图在 [scenarios/challenges](scenarios/challenges)，可在编辑器导入 JSON。

## 数据与目录

```text
pathlab/            SDK、仿真、评分、Worker 与 HTTP 服务
frontend/src/       工作台、地图编辑和可视化
algorithms/         六种参考算法、训练工具与当前发布权重
student_template/   学生算法模板与独立进程示例
scenarios/          固定挑战 / 回归地图与压力场景
scripts/            安装、算法评测、浏览器回归
tests/             自动化回归测试
docs/               当前架构、接口、算法、训练与验收说明
artifacts/          本地数据和生成输出，不纳入版本控制
```

`artifacts/maps` 保存地图，`runs` 保存实验，`uploads` 保存素材，`submissions` 保存算法包，`benchmarks` 保存网页批次。删除运行不会删除共用素材、算法包或地图。完整迁移实验时应同时保留这些目录。

运行记录和算法包各有独立的 2 GiB 配额；训练数据、地图和报告不计入运行配额。实验记录保存场景、版本、参数、原始输出和实际动作。回放保留旧地图的渲染及运动模型兼容性。

历史开发快照、训练缓存和重复报告已清理。仓库只附带当前 `driver-complex.pt`；训练、评测及截图输出写入 `artifacts/`，新生成的基础场景默认写入 `artifacts/scenes/`。已安装的 `.venv`、前端依赖和构建结果保留在本地。

## 开发与验证

```bash
python run.py doctor
python run.py test
python run.py scenes --seeds 7 8
python run.py benchmark --algorithms temporal_pursuit temporal_mpc --families straight bend --seeds 201 --steps 4000
```

前端修改后执行 `python scripts/setup.py --mirror`，或在激活 `.venv` 后进入 `frontend` 运行 `npm run build`。热更新使用 `npm run dev`，同时启动后端。

详细文档：

- [架构与运行边界](docs/architecture.md)
- [评分与公平比较](docs/evaluation.md)
- [算法与评测](docs/algorithms.md)、[避障逻辑](docs/avoidance.md)
- [时序引导线识别与局部路径教程](docs/temporal-path-tutorial.md)
- [学习模型与训练](docs/learning.md)
- [自动化和浏览器验收](docs/acceptance.md)

这是平面场地、单目相机、静态物件与低速惯性模型的教学仿真。几何合法不保证所有算法都能完成地图；已知失败保留在 [评测摘要](docs/algorithm-results.json)。上传执行面向教师本机的受控代码，Worker 提供超时与故障清理，不是恶意代码安全沙箱。默认监听 `127.0.0.1`；Windows / macOS 尚未实际验收。
