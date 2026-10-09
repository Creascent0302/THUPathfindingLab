# 公网多人实验平台

公网模式为每个账号提供独立的地图、上传算法、素材、运行记录和批量任务。教师创建账号或发邀请码，学生登录后只能访问自己的工作区。学生之间可以同时运行实验；全站容量不足时，交互实验显示忙碌提示，批量任务自动等待容量。

本地单用户模式仍使用 `python run.py`。**公网应使用下面的 `--accounts` 模式，不能只把单用户服务的监听地址改成 `0.0.0.0`。** 两种模式使用不同的数据目录，现有单用户实验不会自动公开或迁入任何账号。

## 1. 安装服务器环境

建议使用 Ubuntu 22.04 / 24.04 的独立服务器或虚拟机。当前多人后端使用 Linux 文件锁，采用一个 HTTP 服务进程管理多个用户；不要启动多个 uvicorn worker，也不要让多个服务实例共用同一个公网数据目录。

先在项目目录配置 Python 依赖和网页：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 scripts/setup.py
```

再按 [Docker 官方 Ubuntu 安装文档](https://docs.docker.com/engine/install/ubuntu/) 安装 Docker Engine。建议使用单独的非 root 服务账户，并参照 [Docker rootless 模式](https://docs.docker.com/engine/security/rootless/) 设置守护进程。Rootless 模式的内存、CPU、进程数限制需要正确配置 cgroup v2 / systemd，参见 [资源限制说明](https://docs.docker.com/engine/security/rootless/tips/#limiting-resources)。平台启动时会检查相关能力；缺少 Docker、镜像或资源限制时拒绝启动，不会改用宿主机运行学生代码。

在运行平台的同一个账户下构建镜像：

```bash
docker info
docker build -f deploy/Dockerfile.worker -t pathlab-worker:local .
```

框架或内置算法更新后需要重新构建镜像。默认镜像提供 NumPy、OpenCV 和 SDK；学生提交算法 ZIP 即可，暂不支持网页安装任意 pip 依赖。需要 PyTorch 的可选学习方法在默认公网镜像中不可用。

首次创建算法容器最多等待 30 秒；每帧推理仍使用实验设置里的算法超时，不会因容器启动而放宽。

算法运行容器使用独立进程、只读文件系统、禁用网络、非 root 用户、移除 Linux capabilities 和禁止提权；每个算法最多使用 1 核 CPU、512 MiB 内存、64 个进程、64 MiB 临时空间。容器只挂载本次算法代码，不挂载其他用户数据、账号数据库或 Docker socket。每次实验结束或超时会删除容器，服务重启也会清理带有本工作区标签的遗留容器。容器参数依据 [Docker 运行参数](https://docs.docker.com/engine/containers/run/) 设置。

Docker 是隔离边界之一，不等同于独立内核虚拟机；请持续更新 Docker 和宿主机。不要在存有实验室密钥、私人数据的高权限账户下开放任意学生代码执行。

## 2. 创建管理员

在项目目录执行：

```bash
.venv/bin/python run.py create-admin --username teacher
```

按提示输入两遍至少 12 位密码。密码不放在命令行参数、Git 文件或默认配置中。管理员忘记密码时，可以在服务器终端执行：

```bash
.venv/bin/python run.py reset-password --username teacher
```

如果使用自定义数据目录，上述两个命令及启动命令都必须使用同一个 `--data-dir`。

## 3. 先在服务器本机验收

```bash
.venv/bin/python run.py serve --accounts --public-url http://127.0.0.1:8000
```

打开 `http://127.0.0.1:8000`，用管理员账号登录，进入侧栏的“账号与用户管理”。先创建两个学生账号，分别在普通浏览器和无痕窗口登录，验证：

1. 学生可以保存地图、上传算法、运行实验及批量评测。
2. 两个人的数据列表各自独立，同时运行不会覆盖对方的任务。
3. 教师可以生成有使用次数和有效期限制的邀请码、停用/启用账号、重置密码、停止用户的任务。
4. 新建账号的临时密码及教师重置的密码都要求学生首次登录后修改。

停用账号会撤销登录会话并停止该用户的实验和批量任务，数据保留。重置密码会撤销所有会话。管理员操作记录可以通过登录后的 `/api/admin/audit` 查询，普通账号无权读取。

## 4. 通过公网 IP 或域名访问

IP 也可以作为访问地址，无需先有域名。但账号密码应通过 **HTTPS** 传输，证书的 SAN 必须包含你实际使用的域名或 IP。域名证书不能自动用于直接访问 IP；只有 IP 时，需要取得支持该 IP 的证书，或由实验室统一配置并让学生信任实验室证书。

正式启动示例（将地址换成真实公网地址）：

```bash
.venv/bin/python run.py serve --accounts \
  --public-url https://lab.example.edu \
  --host 127.0.0.1 --port 8000
```

`--public-url` 必须与浏览器访问地址一致，包括协议和非默认端口。它用于请求来源校验及 WebSocket 保护；换地址后应更新参数并重启。

使用 `deploy/nginx.conf` 作为 Nginx 配置模板：替换访问地址和证书路径，运行 `sudo nginx -t` 检查，再重载服务。配置已经包含 WebSocket 转发、请求大小限制和基本限流。只向公网开放 443（及用于跳转的 80）；后端 8000 保持监听回环地址，不必开放数据库和 Docker API 端口。校园网出口或路由器如果有 NAT，还需要实验室网管配置端口映射。

如果只做短时间联调且尚无 TLS，可以显式使用明文 HTTP：

```bash
.venv/bin/python run.py serve --accounts \
  --public-url http://你的公网IP:8000 \
  --host 0.0.0.0 --port 8000 --allow-http
```

这会允许明文传输密码和会话，不能作为正式学生服务的配置。正式环境应改用 HTTPS，随后关闭公网的 8000 端口。平台不自动操作服务器防火墙、证书或路由器。

## 5. 并发与存储配置

默认值：每人 2 个实验，全站 8 个实验，每人 2 GiB 工作区，全站 20 GiB，最多 200 个账号。单次实验最长实际运行 600 秒，包含等待和暂停，可通过 `--run-timeout` 调整（最多 3600 秒）。所有已保存数据都计入工作区用量，创建实验/上传时还会预留写入空间；剩余空间不足时，平台会在开始前拒绝操作。因此“磁盘还未完全用满”时也可能提示配额不足。

按机器能力调整，例如 8 GiB 内存的服务器可以先从全站 4 个实验开始：

```bash
.venv/bin/python run.py serve --accounts \
  --public-url https://lab.example.edu \
  --user-runs 1 --total-runs 4 \
  --user-storage-gb 2 --total-storage-gb 40 --max-users 100
```

真实吞吐量还取决于地图复杂度、算法速度和机器 CPU，配置的并发上限不是性能保证。学生可以在“账号与存储”里清理自己的算法和素材，在原有页面删除运行记录和地图。正在运行或仍被批量任务使用的算法不能删除。

### 10～30 人同时实验的课堂配置

课程采用**教师创建账号或发邀请码**。在线人数与实验并发数不同：30 人能登录，不代表默认的 8 个运行名额能让 30 人同时实验。课堂部署模板按每人 1 个、全站 30 个运行名额设置，批量任务也占用该用户的名额；这样单个学生不能同时占用两个名额。命令行未指定参数时仍使用上面的保守默认值。

30 人配置的启动命令：

```bash
.venv/bin/python run.py serve --accounts \
  --public-url https://lab.example.edu \
  --user-runs 1 --total-runs 30 \
  --user-storage-gb 2 --total-storage-gb 80
```

10 人课堂可以将 `--total-runs` 改成 `10`，其余相同。全站 80 GiB 是允许使用的上限，不会预先占用磁盘；它为 30 人各 2 GiB 的数据额度及运行中的写入预留留出余量。账号总数与同时运行人数无关，可以提前为整班学生创建账号。

按当前每个容器的限制计算，30 个算法容器的内存上限合计 15 GiB、CPU 配额合计 30 核；这还不包含仿真、渲染、网页后端与操作系统。容器上限不是实际平均消耗，也不是性能保证。`pathlab.service` 的 `MemoryMax=6G` 只限制平台服务，不能代替这些独立容器的内存预算。实际开放课堂前，在目标服务器分别用 10、20、30 个账号运行代表性算法和困难地图，检查帧率、算法超时和内存，再确定最终并发数；仅通过账号并发测试不能证明 30 路算法达到实时速度。

同一教室通常共享公网出口。Nginx 模板允许每个出口 IP 每秒 300 个 HTTP 请求、600 个突发请求和 400 条连接，以容纳 30 路手动驾驶的定时控制及正常页面请求。登录还分别按账号和 IP 限流；同一 IP 每 5 分钟允许 120 次登录尝试，邀请码注册每 10 分钟允许 120 次请求。学生仍须有效邀请码，运行和存储仍受个人配额限制。

登录采用带随机盐的 PBKDF2-HMAC-SHA256（600,000 次迭代）；会话使用随机令牌，数据库只保存令牌摘要。Cookie 使用 HttpOnly、SameSite，HTTPS 模式启用 Secure。修改密码、重置密码和停用账号会撤销会话；写请求要求同源校验及自定义请求头，WebSocket 也检查来源和会话。密码存储参考 [OWASP 指南](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)。

## 6. 持久运行与备份

默认数据结构：

```text
artifacts/portal/
  accounts.sqlite3       # 账号、会话、邀请码、操作记录
  users/<随机用户ID>/    # 该用户的地图、算法、素材、记录和批次
```

工作区路径使用服务端随机 ID，不使用用户输入的名字。退出登录不删除实验数据；交互实验失去浏览器心跳后自动停止，批量任务可以在后台继续执行。

生产环境建议使用独立数据目录，例如 `/var/lib/pathlab`，并让服务账户拥有该目录。`deploy/pathlab.service` 提供 systemd 模板：替换账户、代码路径，将 `deploy/pathlab.env.example` 复制为 `/etc/pathlab.env`，修改访问地址和课堂容量：

```text
PATHLAB_PUBLIC_URL=https://lab.example.edu
PATHLAB_USER_RUNS=1
PATHLAB_TOTAL_RUNS=30
PATHLAB_USER_STORAGE_GB=2
PATHLAB_TOTAL_STORAGE_GB=80
```

10 人规模可先把 `PATHLAB_TOTAL_RUNS` 改为 `10`。修改环境文件后重启服务使配置生效；正在运行的实验会结束，请在课前调整。管理员也计入运行名额，若要求 30 名学生和教师同时演示，可将总名额设为 `31`，并按相应资源需求验收。

使用 rootless Docker 时，还要为这个服务设置对应账户的 `DOCKER_HOST` 和 `XDG_RUNTIME_DIR`，并保证该账户的 Docker 守护进程能随系统启动。先在服务账户下验证 `docker info` 和资源限制，再启用 systemd 服务。

备份时停止服务，然后备份整个公网数据目录；恢复时也恢复整份目录，并使用原启动配置。仅备份用户文件夹会丢失账号对应关系。若在线备份，必须使用 SQLite 的 backup API，并协调用户文件的快照；不能只复制正在写入的 `accounts.sqlite3`。

本次功能包含接口、隔离与并发回归测试。没有 Docker 的开发环境无法验收真实容器执行；实际开放公网之前，应在目标服务器完成第 3 节的双账号验收和一次上传算法运行。
