# 教师发行说明

## 交付结构

`student/local-lab` 是教师维护的框架分支，包含直线接口与时序拓扑轨迹两个课堂示例，没有避障方法、训练模型或部署网关。学生拿到匹配系统与架构的 `release/PathLab-<系统>-<架构>.zip`，解压启动即可，不需要安装 Python、Node.js 或服务器。课程学生使用 Linux / macOS；Windows 同学通过 WSL 2 或 Ubuntu 虚拟机使用 Linux 版。当前已验收的发行包只有 Linux x86_64。

发行包包含原生后端、Python 运行时、NumPy/OpenCV、构建后的网页、公开 SDK、空白算法模板、两个课堂示例源码和学生说明。`artifacts/` 在首次启动时创建，不从教师工作区复制。源码与生成的 C 文件留在教师 `.cache/student-build/` 中，不放入发行包。

## 怎样构建

1. 在目标系统准备 Python 3.10～3.13 和 C 编译器。Ubuntu 可使用 `build-essential`、与解释器匹配的 Python 开发头文件；Windows 使用 Visual Studio Build Tools 的 C++ 工具链；macOS 使用 Xcode Command Line Tools。
2. 执行 `python scripts/setup.py`，准备前端和维护环境。
3. 执行 `python scripts/build_student.py`。脚本创建独立的打包虚拟环境、安装锁定依赖、构建网页、编译后端、冻结程序，最后生成 ZIP 和 SHA-256 文件。
4. 执行 `.venv/bin/python scripts/check_release.py release/PathLab-linux-x86_64/PathLab` 验证真实发行包。Windows 中替换解释器与程序路径。

构建需要联网；运行不需要。构建工具版本固定在脚本中，运行依赖在 `requirements.lock`。不从日常开发环境复制 Torch 等无关依赖。构建包按系统和架构区分，Linux 建议在希望支持的最旧发行版上构建，再在目标机器实测。

脚本自动检查所有私有后端模块已编译，并检查 PyInstaller 归档不含这些模块的 Python 字节码；SDK 特意公开，不计入私有模块。`manifest.json` 记录文件摘要及构建环境，用于交付核对，不是防篡改签名。

## 黑盒能力的边界

仅用 PyInstaller 会把 Python 字节码打包进去。这里先用 Cython 将后端编译为 `.so` / `.pyd`，再用 PyInstaller 打包运行环境，降低直接恢复 Python 实现的便利程度。[PyInstaller 官方说明](https://pyinstaller.org/en/stable/operating-mode.html) 也明确区分字节码打包和 Cython 编译保护。

这能做到**不下发后端源码、开箱运行**，不能做到绝对保密：原生程序仍可以被反汇编，浏览器中的 JavaScript 和接口始终可查看，用户对自己电脑具有控制权。不要在客户端埋入密钥或依赖隐藏评分规则防作弊；最终成绩由教师在可信环境重新运行学生提交代码产生。

公开 Observation 不携带真值，属于算法输入约定，并非本地强隔离沙箱。插件在学生本机账户下执行；内网共享时所有访问者使用同一实例，没有多租户隔离。请使用可信内网，每位同学独立运行最简单。

## 依赖和版本维护

发行包固定提供 NumPy、OpenCV、Pydantic 和 SDK。常用标准库支持以发行包验收结果为准；额外动态导入依赖需要在打包环境安装并通过隐藏导入列表收集。上传 ZIP 不执行 pip 安装。

若课程需要新增第三方库，教师应更新依赖与 `build_student.py` 的收集范围，重新构建并验证。学生升级前停止服务、备份 `artifacts/`，然后将数据迁移到新包；不同实例不能同时写同一数据目录。

分支历史仍含教师算法，因此下发生成 ZIP，不下发 `.git`。原来的 `master` 不受学生分支清理影响。
