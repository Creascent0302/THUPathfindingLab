# 学生使用手册：安装与运行

课程统一在 **Linux 或 macOS** 上运行平台。Windows 同学先配置 **WSL 2（推荐）或 Ubuntu 虚拟机**，然后在其中按 Linux 步骤操作。浏览器仍可以使用 Windows 上的 Edge 或 Chrome。

阅读顺序：先按本篇启动平台，再阅读 [算法接口与基本巡线教程](student-guide.md)，完成“读取摄像头 → 输出引导线 → 驱动车辆”的第一次实验。

## 1. 先确认你拿到哪种文件

| 拿到的文件 | 运行方式 | 是否需要安装开发环境 |
|---|---|---|
| `PathLab-linux-x86_64.zip`，解压后有 `PathLab` | Linux / WSL 中运行 `./PathLab` | 不需要，已自带 Python、NumPy、OpenCV 和 SDK |
| 教师提供的框架目录，有 `run.py`、`scripts/` | 安装依赖后运行 `python3 run.py` | 需要 Python 3.10～3.13；其余依赖由安装脚本准备 |
| 教师提供的 macOS 原生发行包 | 在匹配架构的 Mac 上运行包内程序 | 按随包说明操作 |

**目前已提供并验证的是 Linux x86_64 发行包，尚未提供已验收的 macOS 原生包。** Mac 同学目前使用教师提供的框架目录；如果课程只下发黑盒包，需要教师先构建对应 macOS 包。Linux 包不能在 Mac 中直接运行。`x86_64` 包也不能直接用于 ARM64 Linux / Windows ARM 的 WSL；这些设备需要对应架构的包，或使用框架目录安装。

下面只执行与你拿到的文件对应的一种安装方式，不需要两种都做。

## 2. Windows：先安装 WSL 2

### 第一步：安装 Ubuntu

使用 Windows 11，或满足 WSL 要求的 Windows 10（版本 2004、内部版本 19041 及以上）。以**管理员身份打开 PowerShell**，运行：

```powershell
wsl --install -d Ubuntu-24.04
```

按提示重启电脑，然后从开始菜单打开 **Ubuntu 24.04**。第一次打开时等待初始化，并设置 Linux 用户名与密码；该密码可以与 Windows 密码不同。输入密码时终端不显示字符，正常输入后按回车即可。安装步骤可对照 [Ubuntu WSL 教程](https://documentation.ubuntu.com/wsl/latest/howto/install-ubuntu-wsl2/)，账户说明见 [微软 WSL 环境配置](https://learn.microsoft.com/zh-cn/windows/wsl/setup/environment)。

如果提示找不到这个发行版，先在 PowerShell 中运行 `wsl --list --online` 查看实际名称；如果下载一直停在 0%，可尝试：

```powershell
wsl --install --web-download -d Ubuntu-24.04
```

### 第二步：确认使用 WSL 2

在 **PowerShell** 中运行：

```powershell
wsl -l -v
```

确认 `Ubuntu-24.04` 所在行的 `VERSION` 为 `2`。如果为 `1`，按 [微软 WSL 安装说明](https://learn.microsoft.com/zh-cn/windows/wsl/install) 转换：

```powershell
wsl --set-version Ubuntu-24.04 2
```

如果安装提示虚拟化未开启，需要在 BIOS / UEFI 中启用硬件虚拟化；实验室管理的电脑请联系管理员处理，具体报错见 [WSL 安装排错](https://learn.microsoft.com/zh-cn/windows/wsl/troubleshooting)。安装成功后，后面的 `sudo apt`、`python3`、`./PathLab` 等命令都在 **Ubuntu 终端**执行，不在 PowerShell 执行。

### 第三步：把课程文件放进 Linux 目录

在 Ubuntu 终端运行：

```bash
mkdir -p ~/pathlab
cd ~/pathlab
explorer.exe .
```

这会打开当前 Linux 目录对应的 Windows 文件管理器窗口。把教师提供的 ZIP 或框架目录复制到这里。建议在 Linux 主目录中解压和运行，不要把虚拟环境直接放在 `/mnt/c` 下。[微软文件存放建议](https://learn.microsoft.com/zh-cn/windows/wsl/filesystems)

然后按下一节的 Linux 步骤启动。启动后，在 **Windows 浏览器**打开 `http://localhost:8000` 即可，通常不需要查询 WSL 的 IP。[微软 WSL 网络说明](https://learn.microsoft.com/zh-cn/windows/wsl/networking)

若无法使用 WSL，也可以安装 Ubuntu 虚拟机，建议分配至少 2 核 CPU、4 GiB 内存和 30 GiB 虚拟磁盘空间；在虚拟机内按 Linux 步骤安装，并先用虚拟机里的浏览器访问平台。Windows 主机访问虚拟机还需要配置虚拟机网络。

## 3. Linux / WSL：安装并启动

### 方式 A：使用 Linux 发行包（推荐）

以下以 Ubuntu 和 `PathLab-linux-x86_64.zip` 为例。在存放 ZIP 的目录中打开终端：

```bash
sudo apt update
sudo apt install -y unzip zip
unzip PathLab-linux-x86_64.zip
cd PathLab-linux-x86_64
chmod +x PathLab
./PathLab
```

后续启动只需进入该目录运行 `./PathLab`。**不需要安装 Python、Node.js，也不需要运行 `setup.py`。** 必须保留整个解压目录，不能只复制 `PathLab` 文件；`_internal/` 是运行所需的依赖。

这份包适用于 `uname -m` 输出为 `x86_64` 的 Linux 环境。平台本身无需 GPU。下载和安装系统工具时需要联网，解压后的平台可离线使用。

### 方式 B：使用教师提供的框架目录

建议使用 Ubuntu 22.04 或 24.04，其默认 Python 分别属于本项目支持的版本范围。进入包含 `run.py` 的目录，执行：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip zip
python3 --version
python3 scripts/setup.py
python3 run.py
```

`python3 --version` 应为 **3.10～3.13**。安装脚本创建项目内的 `.venv`，安装锁定的 Python 依赖、项目内的 Node.js，并构建网页。首次安装需要联网，之后无需反复安装，也无需手动激活虚拟环境。

国内网络安装较慢时，可以将安装命令换成：

```bash
python3 scripts/setup.py --mirror
```

安装完成后可运行 `python3 run.py doctor`，确认 `frontend_built` 为 `true`。新安装的 `algorithms` 是空列表，这是正常的：平台不附带参考算法，学生需要自行上传代码。

## 4. macOS：配置环境并启动

目前使用**教师提供的框架目录**完成以下步骤，不使用 Linux 发行包。

1. 从 [Python 官方 macOS 下载页](https://www.python.org/downloads/macos/) 选择 **Python 3.13.x 的 macOS 64-bit universal2 installer** 并安装。该安装器支持 Intel 和 Apple Silicon；不要修改系统自带 Python。本项目暂不使用 Python 3.14 及以上版本。[Python 官方安装说明](https://docs.python.org/3.13/using/mac.html)
2. 打开新的“终端”窗口，进入教师提供的框架目录，例如 `cd ~/Downloads/THUPathfindingLab`；该目录中应能看到 `run.py`。
3. 执行：

```bash
python3.13 --version
python3.13 scripts/setup.py
python3.13 run.py
```

这里显式使用 `python3.13`，避免终端误用其他 Python。安装脚本同样会准备 `.venv`、Python 依赖、Node.js 和网页，不需要手动安装 npm。若遇到 Python 下载依赖时的证书错误，可先运行 `/Applications/Python 3.13/Install Certificates.command`，再重试安装；国内网络也可以给安装命令加 `--mirror`。

首次配置完成后，每次只需运行 `python3.13 run.py`，然后在 Safari、Chrome 或其他浏览器打开 `http://127.0.0.1:8000`。

如果之后收到教师构建的 macOS 原生包，应按 Intel / Apple Silicon 架构选择匹配的包并按随包说明启动。不要为运行来历不明的软件关闭系统安全保护。当前 macOS 安装步骤依据项目脚本及官方文档整理，尚未在本实验室 Linux 环境中实机验收。

## 5. 第一次运行与提交代码

终端显示服务启动后，打开 **http://127.0.0.1:8000**；WSL 用户在 Windows 浏览器打开 **http://localhost:8000**。

1. 在“实验工作台”选择“直线”和“手动驾驶”，点击“启动实验”，先确认画面会随车辆运动变化。可以前进、转向、倒车、制动，也可以暂停或单步。
2. 停止手动实验，打开“算法提交”，下载代码模板。模板只会停车，直接上传后不动属于正常现象。
3. 阅读 [算法接口与基本巡线教程](student-guide.md)，修改 `algorithm.py`。本教程推荐先输出**车辆坐标系局部路径**，由平台执行转向和速度控制。
4. 在 `algorithm.py` 所在目录执行 `zip -r my_algorithm.zip algorithm.py`；如有辅助模块或资源，将它们的文件名也加在命令后。不要把整个平台目录打包。
5. 上传 ZIP 时选择“车辆坐标系局部路径”，点击“上传并选用”。确认工作台“执行依据”为局部路径，选择场景后启动。
6. 观察原始摄像头、算法叠加画面和运行记录；在“批量评测”中选择自己上传的不同版本，使用相同地图和种子比较。

**不要直接运行 `python algorithm.py` 来启动实验。** 算法文件提供一个类，由平台创建实例并逐帧调用。编译发行包内已经提供运行学生代码所需的 Python、NumPy、OpenCV、Pydantic 和 `pathlab.sdk`；单纯编辑和上传代码无需另装 Python。

如需在编辑器里本地导入 SDK 做单独调试，可另外创建自己的 Python 3.10～3.13 虚拟环境，安装 `numpy==2.2.6`、`opencv-python-headless==4.11.0.86`、`pydantic==2.11.5`，并把发行包的 `sdk/` 加入该环境的模块搜索路径。这个开发环境不会改变发行包的运行依赖；正常网页实验不需要此步骤。

## 6. 数据、内网访问与常见问题

数据默认保存在运行程序旁的 `artifacts/`，包括地图、代码、素材和实验记录。关闭或刷新网页不会清空数据。先停止平台再备份该目录；同一数据目录不要同时启动多个实例。

| 操作 | Linux 发行包 | 框架目录（macOS 把 `python3` 换成 `python3.13`） |
|---|---|---|
| 更换占用的端口 | `./PathLab serve --port 8001` | `python3 run.py serve --port 8001` |
| 指定数据目录 | `./PathLab serve --data-dir "$HOME/PathLabData"` | `python3 run.py serve --data-dir "$HOME/PathLabData"` |
| 开放可信内网 | `./PathLab serve --lan` | `python3 run.py serve --lan` |
| 停止服务 | 在启动终端按 Ctrl+C | 在启动终端按 Ctrl+C |

更换端口后，浏览器地址也要改成相应端口。内网访问地址为 `http://运行电脑的内网IP:8000`；Ubuntu 用 `hostname -I` 查看 IP，macOS 在“系统设置 → 网络”中查看当前连接的 IP。其他电脑访问时，数据仍保存在运行程序的电脑上。

WSL 2 默认网络和虚拟机网络有额外转发边界，单独使用 `--lan` 不保证其他电脑能访问 Windows 主机中的服务。个人实验使用本机浏览器即可；确需共享时按 [WSL 网络文档](https://learn.microsoft.com/zh-cn/windows/wsl/networking) 配置转发或镜像网络及防火墙。

- 网页打不开：先确认启动终端没有退出，检查网址和端口；不要同时启动两份占用同一端口的服务。
- Linux 提示 `Permission denied`：在程序所在目录运行 `chmod +x PathLab`；提示 `Exec format error` 则检查操作系统和 CPU 架构是否匹配。
- 编辑器提示找不到 `pathlab`：发行包会在执行算法时提供 SDK。可以先上传验证，或按上一节配置单独开发环境。
- 上传后不动：检查输出类型和状态；`centerline_px` 只画线，局部路径模式需要 `local_path_m`；`UNINITIALIZED`、`LOST` 等状态会请求制动。
- 运行记录达到 2 GiB：在运行记录页删除不需要的实验；地图和算法代码使用独立存储。

每位同学自己运行一份最简单。内网共享的是同一个工作台；上传的 Python 代码以启动程序的账户权限执行，只向可信同学开放。最终成绩以教师重新运行提交代码的结果为准。
