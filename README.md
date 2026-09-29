# 智能交通创新实践 · 学生实验框架

本分支用于课堂讲解和学生本地实验：提供实验平台、公开 SDK、停车模板，以及两个只输出轨迹点的教学示例。学生自行实现图像识别与局部路径，上传 ZIP 后由统一执行器控制车辆。

所有新仿真直接从路线起点沿箭头出发，12 级预设地图均无障碍物。保留手动驾驶、前向摄像头、图像/视频输入、自定义地图与障碍物、惯性运动和倒车、运行回放、评分及批量对比。局部路径模式保留统一的路径执行器，用于将学生输出的路径转换为车辆动作。

## 本地启动

学生使用 Linux 或 macOS；Windows 同学先配置 WSL 2 或 Ubuntu 虚拟机。不同系统、发行包与框架目录的完整步骤见 [学生使用手册](docs/student-local.md)。算法练习以输出局部引导线为主，见 [接口、直行示例与巡线原理](docs/student-guide.md)。

源码版首次配置（Python 3.10～3.13）：

```bash
python scripts/setup.py
python run.py
```

打开 **http://127.0.0.1:8000**。无需手动激活虚拟环境；首次安装需要联网，安装完成后可离线运行。

需要同学从其他电脑访问时：

```bash
python run.py serve --lan
```

访问 `http://运行电脑的内网IP:8000`。默认只监听本机，`--lan` 显式开放内网；本平台执行上传代码，只用于可信内网。同一实例共享工作台和数据，推荐每人运行一份。

端口占用时使用 `python run.py serve --port 8001`；指定本机数据目录用 `--data-dir /your/path`。默认数据保存在项目下的 `artifacts/`，切换本分支不会删除已有实验和地图。

## 课堂演示

算法栏选择「教学示例 · 车前直线」或「课堂演示 · 时序拓扑轨迹」，执行依据为「车辆坐标系局部路径」。地图按 01～12 递增难度，最后三关为密集螺旋。直线示例只在直线地图展示接口。

[课堂演示说明](docs/classroom-demo.md) 介绍算法过程、路径执行器、地图难点和验证结果。

## 向学生下发

推荐下发编译后的发行 ZIP，而不是这个 Git 仓库：

```bash
python scripts/build_student.py
```

脚本将后端编译为原生扩展并打包 Python、依赖和网页；生成 `release/PathLab-<系统>-<架构>.zip`。学生无需安装运行环境。源码、Git 历史、教师数据和测试脚本不进入发行包，公开 SDK、空白模板和教学示例源码保留，实验框架仍编译为原生模块。

每个平台须在对应操作系统构建。当前 Ubuntu 构建产生 Linux 包，不产生 Windows 可执行文件。构建条件和黑盒边界见 [发行说明](docs/distribution.md)，学生收到包后的操作见 [本地使用说明](docs/student-local.md)。

**这个分支仍继承 Git 历史，历史提交含教师参考算法。不要向学生分发 `.git` 或该仓库的完整克隆。** 原始教师版本保留在 `master`。

## 接口和维护

- [学生算法开发指南](docs/student-guide.md)：输入、输出、坐标及 ZIP 提交。
- [SDK 协议](docs/protocol.md)：类型和执行约定。
- [评测说明](docs/evaluation.md)：指标、评分与可比条件。
- [架构](docs/architecture.md)、[验收](docs/acceptance.md)：教师维护使用。

主要目录：`pathlab/` 实验后端，`frontend/` 网页，`algorithms/` 两个教学示例，`student_template/` 空白接口，`scenarios/` 固定回归地图，`tests/` 平台测试。运行记录和生成发行包均不纳入 Git。
