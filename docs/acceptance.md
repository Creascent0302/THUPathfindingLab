# 当前系统验收

## 检查入口

在项目根目录运行：

```bash
python run.py doctor
python run.py test
```

前端在激活项目环境后执行：

```bash
cd frontend
npm run check
npm run build
```

Python 静态检查：`.venv/bin/ruff check algorithms pathlab scripts tests`。Ruff 是维护工具，不是学生运行依赖。

自动测试覆盖 SDK 与 Worker 故障、相机与车辆动力学、目标路线身份、碰撞和评分、HTTP / WebSocket、地图与 ZIP 上传、配额、删除和恢复、批量评测、当前学习权重和独立避障入口。

## 浏览器回归

浏览器脚本是可重复执行的维护工具。首次安装可选依赖：

```bash
.venv/bin/python -m pip install playwright==1.52.0
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/browsers" .venv/bin/python -m playwright install chromium
```

| 脚本 | 覆盖范围 |
|---|---|
| `browser_smoke.py` | 启动、手动前进 / 倒车 / 制动、暂停 / 单步、回放、素材上传和窄屏 |
| `browser_authoring.py` | ZIP 算法、地图编辑、模型视图、记录删除 |
| `browser_evaluation.py` | 物件、惯性、多方法评分、导出与取消 |
| `browser_map_layers.py` | 旧地图兼容、目标线 / 干扰线 / 障碍物编辑 |
| `browser_route_identity.py` | 起点和相邻路线的有序身份判定 |
| `browser_persistence.py` | 草稿刷新、地图重名、主页加载、独立配额 |

例如：`.venv/bin/python scripts/browser_persistence.py`。输出统一在被 Git 忽略的 `.cache/browser*/`；固定回归输入位于 `scenarios/`。浏览器脚本会启动并关闭自己的本地测试服务。

## 仓库维护约定

- `artifacts/` 只保存本地数据和生成结果，不放置系统必需源文件。用户地图、实验、素材、算法包和批次分别保存在其中的独立目录。
- 固定回归地图放在 `scenarios/challenges/`；修改安装目录不能改变地图文件字节或由其生成的稳定 ID。
- `algorithms/learning/weights/` 只附带当前权重和模型卡；新训练产物写入 `artifacts/learning/`。
- 原始历史开发日志、代码快照、旧权重、重复截图和训练缓存不随当前系统保留。历史结果压缩保存在 [算法评测摘要](algorithm-results.json)，倒车版回归保存在 [reverse-results.json](reverse-results.json)。
- 旧渲染和运动模型兼容分支用于读取用户地图和历史回放，属于当前功能；不能按版本号直接删除。
- `.venv`、`frontend/node_modules`、`frontend/dist` 和本地浏览器是已安装的运行 / 验收环境，不纳入版本控制。

## 紧凑绕行、连续接续与原线预测（3.1，2026-09-21）

- 全量 Python 回归 **242 项通过**，其中避障专项 **49 项**。新增覆盖较晚起转、两侧邻线隔离、多个可见阻挡共用接回段、未回线时接续、新物件使旧路径失效、预测寿命与误差、保持偏移的预测候选、预测拒绝后不越过路径终点，以及真实 RGB 重新接回。
- 五张绕障回归图，两种方法共 **10/10 成功**，均未使用倒车。连续占道图中两个方法在尚未回线时接续下一物件；平台碰撞、非法换线和完成规则保持原样。
- 单独保留 `block-chain-occluded.json`：三个间隔 1.5 m 的物件造成连续遮挡，验证不能看着旧路线记忆无限绕行。停止后任务超时仍记失败，不能计作绕障成功。
- [独立避障说明](avoidance.md) 更新了紧凑代价、低速控制、接续条件、原路线预测与条件式可见性预算。与用户人工轨迹的局部对照和最终回归身份保存在 [紧凑绕行摘要](compact-detour-results.json)。

两个真实 JSONL Worker 在连续占道图上均成功、无负速度请求且最终实际速度为零。全仓库 Ruff、改动文件格式和差异检查通过；已有 17 个用户地图 / 实验文件哈希保持不变。

本轮未修改前端、仿真 / 评分规则或学习权重，沿线算法仍独立于避障方法。

## 倒车功能与算法文档验收（3.0，2026-09-21）

- 全量 Python 回归 **220 项通过**。新增覆盖正负换向制动、两种运动模型的倒车、公开模型预测一致性、倒车进度与邻线判定、退路检查、恢复状态机和新物件否决旧候选。
- 两组真实 Chromium 回归通过：`browser_smoke.py` **18 项**，`browser_evaluation.py` **9 项**，均无页面异常。覆盖允许倒车设置、负目标速度、实际后退、倒车中停止及评分 / 批量 / 导出。
- 前端 TypeScript、Prettier、Vite 生产构建通过；Python Ruff 与差异格式检查通过。
- 两种避障方法各通过七张固定图中的 **6 张**，14 回合无碰撞、无非法换线；旧 0920 含障碍图的失败仍计入分母。连续占道图关闭倒车时两者均超时，开启后均成功；真实 JSONL Worker 再次运行，两者均成功并完成最终制动。
- 与修改前动力学逐项比较：每种模型 100 条、每条 100 步的前进轨迹保持逐位相同；当前学习权重未改变。36 个现有用户数据文件哈希保持不变。
- [算法设计](algorithms.md)、[学习模型](learning.md)、[独立避障与倒车恢复](avoidance.md) 按输入、状态、感知、规划、控制、训练 / 评测顺序解释，并链接到实际代码。具体结果与复现身份见 [倒车评测摘要](reverse-results.json)。

这里的地图属于开发回归集合，Worker 成功也不等于满足 20 Hz 实时预算。前向相机没有实时后向感知；恢复只在短时已驶过且已知物件净距通过检查的走廊内执行。旧地图保存了禁止倒车时，须显式开启后再测。

## 前次仓库清理验证（2026-09-21）

- 全量 Python 回归 **204 项通过**；含当前权重的实际 Worker、地图安装和旧档兼容。
- 六组真实 Chromium 脚本全部通过，共记录 **61 项检查、0 页面异常**；共用服务生命周期代码后，原有 Python 断言和 UI 断言数量保持不变。
- 前端 TypeScript、Prettier 检查及 Vite 生产构建通过；Ruff、格式检查和 `git diff --check` 通过。
- 训练 CLI 用临时小数据完成一轮训练，验证当前输入 / 序列默认值、候选文件保存与显式 checkpoint 加载；未修改发布权重。
- `python run.py doctor` 确认前端已构建，注册的十个算法 / 探针全部可用。
- 36 个现有用户数据文件逐一校验，内容未变；当前学习权重 SHA-256 未变，所有本地 Markdown 链接有效。

清理约 **3.26 GiB** 的旧开发输出与包下载缓存，原有 1140 个仓库文件整理为 **132 个**源文件、资源、固定地图与文档（不计本地运行数据和已安装依赖）。本次浏览器截图、测试报告与 Python 缓存也已清理；可用上述入口重新生成。

算法权重未重新训练；过去的成功率不作为本次重新执行的完整算法评测。

实际环境为 Linux、Python 3.13、CPU。Windows / macOS、其他 Python 版本和真实车辆未实际验收。上传执行不具备恶意代码沙箱或多人权限隔离，平台默认监听本机。

## 无障碍时序拓扑验收

运行 `.venv/bin/python scripts/verify_tracking.py --jobs 6`。脚本冻结八类基础地图、0920 与用户地图的无障碍副本，以及最小半径弯、近邻起步、相机/光照/分辨率变体，分别运行两种时序拓扑控制器。原地图不会改写；每个失败均保留原因、轨迹、代码与场景摘要，存在失败时退出码为 1。输出默认位于 `.cache/tracking-acceptance/`。
