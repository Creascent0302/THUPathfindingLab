# 框架验收

在项目根目录：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/browser_student.py
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

## 此次学生版本验证（2026-09-27）

- 当前 Ubuntu / Python 3.13：153 项框架测试通过。
- 编译后的原生模块：68 项渲染、动力学、评测与道路身份回归通过。
- 源码服务和 Linux 发行程序分别通过真实 Chromium 学生流程，均为 0 页面异常。
- 真实发行程序完成 ZIP 上传、辅助模块与相对资源读取、WebSocket、回放、批量对比、删除和重启持久化验收。
- TypeScript、Prettier、Ruff 和生产前端构建通过。

Windows、macOS 发行程序未在本环境构建或验收；需要在目标系统执行打包脚本和相同验收。
