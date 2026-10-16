# ROS 1 实车视觉巡线与参考路径输出

这个目录是一套独立的 ROS 1 包，只实现一种方法：**利用真实定位补偿的时序拓扑巡线**。节点读取已校正的相机图像，识别原来的地面引导线，输出你提供的 `Goal.msg` / `RefPoint.msg` 定义的参考路径。底盘已有控制器负责跟踪路径，本节点不直接发送油门、制动踏板或转向角。

代码从平台的时序拓扑感知模块移植，使用 NumPy 和 OpenCV，不依赖网页、仿真器、训练数据或模型权重。当前默认检测浅色地面上的深色细线，也可配置为深色地面上的浅色细线。车辆起步时应放在目标引导线上，并沿目标线方向摆正。

实车原工程的结构、输入输出和 CUDA 地图处理流程见 [实车工程阅读与接口说明](REAL_VEHICLE_GUIDE.md)。本文介绍新增节点的安装、接口和运行。

## 1. 目录里有什么

```text
ros_line_follower/
├── README.md                    本文：安装、接口、算法和运行
├── REAL_VEHICLE_GUIDE.md         原实车工程的详细讲解
├── package.xml / CMakeLists.txt / setup.py
├── config/line_follower.yaml    需要按实车填写的配置
├── launch/line_follower.launch  ROS 启动入口
├── scripts/line_follower_node   Python 节点入口
├── src/ros_line_follower/
│   ├── ros_node.py              订阅、时间同步、TF、限频发布和失效停止
│   ├── geometry.py              位姿插值、相对运动、地面投影、发布节拍
│   ├── vision.py                鸟瞰图、骨架、时序身份和拓扑排序
│   ├── planning.py              路径长度、采样、曲率、速度和时间
│   └── messages.py              真实 Goal / RefPoint 消息的字段校验和填充
└── tests/                      核心测试、离线ROS状态测试、隔离ROS联调
```

## 2. 接车前要填哪些信息

原工程已经提供 `/vehicle/vehicle_state` 和 `cav_msgs/VehicleState`。当前提供的源码中没有相机驱动，也没有找到 `Goal` 的正式消息包和接收它的路径跟踪控制器。因此 [配置文件](config/line_follower.yaml) 把以下项目留空，节点发现缺失会直接报告错误。

| 配置项 | 要填写什么 |
| --- | --- |
| `image_topic` | 实际已去畸变、已校正的彩色图像话题，类型 `sensor_msgs/Image` |
| `camera_info_topic` | 对应的 `sensor_msgs/CameraInfo` 话题 |
| `goal_type` | 实车真实生成消息类型，形式为 `实际包名/Goal` |
| `goal_topic` | 实车路径跟踪控制器订阅 Goal 的话题 |
| `vehicle_frame` | 实际车体参考坐标系名称；原点必须与 `VehicleState.x/y/heading` 的参考点一致 |
| `output_frame` | 控制端接受 `world` 还是 `vehicle` 坐标 |
| `point_time_mode` | 控制端接受 `absolute` 还是 `relative` 路径点时间 |
| `ground_z_m` | 地面在 `vehicle_frame` 中的 z 坐标，单位 m |

`ground_z_m` 不是“相机离地高度”。例如车体参考点在地面上方 0.45 m、z 轴向上，地面就是 `-0.45`；相机的安装高度和姿态另外由 TF 给出。

不要把配置中的空项换成猜测的话题或消息包名。用实际启动系统检查：

```bash
rostopic list
rostopic type /vehicle/vehicle_state
rosmsg show cav_msgs/VehicleState
```

再对已经确认的相机话题和 Goal 话题执行 `rostopic type`，对真实 `包名/Goal` 执行 `rosmsg show`。Goal 的发布端和接收端必须使用同一套生成消息及其 ROS MD5；仅有两个 `.msg` 文本还不够。

### Goal 依赖的 Object 消息

`Goal.msg` 包含 `Object[] objects`。虽然本巡线节点始终输出 `objects=[]`，ROS 仍需要真实的 `Object.msg` 才能生成、导入和序列化 Goal。**这里不新建或猜测 Object 的结构，也不拿其他感知包中同名 Object 代替。** 请使用控制端已经采用的完整消息包，其中应包含相互匹配的 Goal、RefPoint 和 Object。

节点启动时由 `goal_type` 加载真实 Goal，再从其 `refPath` 字段加载真实 RefPoint，并逐项核对字段名称、顺序和类型。错误的自定义消息不会被静默接受。已有实车 `cav_msgs` 包负责定位输入；不能据此认定 Goal 也在该包中。

## 3. 环境和最简启动步骤

目标环境是 **Ubuntu 上的 ROS 1 Noetic，使用系统 Python 3.8**。不要激活网页平台的 Python 3.13 `.venv` 来运行这个 ROS 节点；`rospy`、`cv_bridge` 和生成消息需要来自同一套 ROS/Python 环境。此节点本身无需 CUDA、GPU、PyTorch 或训练 checkpoint。

下面假设 ROS Noetic 已在实车环境中安装。安装新增节点的常用依赖：

```bash
sudo apt update
sudo apt install python3-numpy python3-opencv python3-catkin-pkg \
  ros-noetic-rospy ros-noetic-roslib ros-noetic-cv-bridge ros-noetic-tf2-ros \
  ros-noetic-sensor-msgs ros-noetic-geometry-msgs ros-noetic-nav-msgs ros-noetic-std-msgs
```

**先加载实车消息工作区，再构建本包。** 下面 `VEHICLE_WS` 必须换成已经在当前机器编译完成的实际工作区。若 Goal 消息在另一个工作区，也要 source 那个工作区；不能用目录里的旧 `build/devel` 缓存代替当前机器的构建。

```bash
source /opt/ros/noetic/setup.bash

# 改成包含 cav_msgs、且已在当前机器正确构建的实车工作区。
VEHICLE_WS=/实际路径/实车工作区
source "$VEHICLE_WS/devel/setup.bash"

# 如果真实 Goal 消息来自其他工作区，在此 source 它的 devel/setup.bash。

LAB_ROOT=/home/liuzonghao/THUPathfindingLab
mkdir -p "$HOME/line_follower_ws/src"
ln -s "$LAB_ROOT/ros_line_follower" "$HOME/line_follower_ws/src/ros_line_follower"
cd "$HOME/line_follower_ws"
catkin_make -DPYTHON_EXECUTABLE=/usr/bin/python3
source devel/setup.bash

cp "$LAB_ROOT/ros_line_follower/config/line_follower.yaml" "$HOME/line_follower.yaml"
```

如果 `src/ros_line_follower` 已经存在，跳过 `ln -s`，确认它指向本目录即可。原目录 `YHS_cuda_drivable` 的旧生成文件包含其他机器的绝对路径，重建原工程的注意事项见 [实车工程文档](REAL_VEHICLE_GUIDE.md)。

编辑 `~/line_follower.yaml`，填完上一节的空项，保持 `enable_motion: false`。启动实车已有 ROS master、相机、定位和 TF 发布节点后，运行：

```bash
roslaunch ros_line_follower line_follower.launch config:="$HOME/line_follower.yaml"
```

新开终端时重新 source ROS、实际消息工作区和 `~/line_follower_ws/devel/setup.bash`。相机或定位在其他机器上时，沿用车辆现有的 `ROS_MASTER_URI` / ROS 网络配置；本包不改变它们。

### 先预览，再接控制器

默认 `enable_motion: false` 时，节点仍然识别并生成调试路径，但发到 Goal 话题的是明确的停驶消息。可在 RViz 查看 `/line_follower/reference_path`，并检查：

```bash
rostopic echo /line_follower/status
rostopic hz /line_follower/reference_path
```

状态 JSON 包含 `state`、`reason`、`motion_enabled`、`image_stamp`、`points`、`length_m` 和 `prediction_only`。预览时 `state=STOP`、Goal 的 `points=0` 是预期行为；有效的调试路径仍可有长度。发到控制器话题的停止指令是真实消息，预览时可以把 `goal_topic` 配成一个明确不被底盘订阅的测试话题。

确认图像标定、路径坐标、时间约定、车辆尺寸/速度限制，以及控制器的过期路径处理后，才将配置改为 `enable_motion: true` 并重启节点。本参数在启动时读取，不是运行中 `rosparam set` 后立即生效的动态开关。首次运动应在封闭场地低速验证，由车辆现有急停和控制器承担最终停车执行。

## 4. 输入和坐标约定

### 4.1 图像和标定

节点通过 `cv_bridge` 将输入转成 `rgb8`，要求输入话题本身已经去畸变、校正。这里不会把原始带畸变图片仅靠一张单应矩阵变成正确的米制鸟瞰图。

图像和 CameraInfo 必须满足：

- `header.frame_id` 相同，指向实际相机 optical frame。
- 宽高一致；裁剪/缩放必须同时更新标定。
- CameraInfo 的 `P`、`R` 有效，并已归一化到当前图像分辨率；当前不接受额外的 ROI/binning。
- TF 可以查询**图像时间戳**时从 `vehicle_frame` 到相机 optical frame 的刚体变换。
- 图像 `header.stamp`、VehicleState 的 `timestamp` 和 ROS 时钟同源。

几何约定是车体系 x 向前、y 向左、z 向上；相机 optical frame 使用光学坐标约定。TF 必须提供真实外参，不能把车体系和光学系当作同一个坐标系。

此版假设可见路线位于配置的局部平面 `z=ground_z_m`。`roll/pitch` 用于拒绝过大倾斜，并没有从雷达重建坡面，也不自动补偿车身俯仰造成的地面变化；适用范围是低速、局部平坦且相机安装稳定的场地。明显坡道、坑洼或悬架晃动需要进一步引入地面估计，不能靠调大倾角门限解决尺度误差。

### 4.2 定位输入

默认订阅 `/vehicle/vehicle_state`，类型固定为现有 `cav_msgs/VehicleState`。当前使用的字段如下：

| 字段 | 单位 / 作用 |
| --- | --- |
| `timestamp` | 秒，必须对应定位测量时间，并与 ROS/相机时间一致 |
| `x`, `y` | m，固定的 ENU 对齐/UTM 平面位置 |
| `heading` | rad，世界 +x 为零、逆时针为正 |
| `roll`, `pitch` | rad，检查平地投影是否仍适用 |
| `speed_x`, `speed_y` | m/s，车体纵向/横向速度，用于运动有效性和停车距离检查 |

缓存用包围图像时刻的两条定位做位置线性插值，航向沿最短角差插值；不拿“最近收到的一条定位”替代图像时刻，也不在缓存范围外外推定位。默认插值区间不超过 0.2 s。

### 4.3 世界系和车体系不能混用

- `output_frame: vehicle`：每个点以**本次图像时刻**的车辆参考点为原点，x 前、y 左，单位 m；heading 也是相对该时刻车头的角度。
- `output_frame: world`：使用该图像时刻的 `VehicleState.x/y/heading`，转换成固定世界坐标；heading 为世界方向。`world_frame` 默认 `utm`，用于调试 Path 的 frame_id，应与真实定位坐标系名称一致。

原实车地图中的 `camera_init` 是随车辆移动的滚动栅格原点，不能当作本节点的固定世界系或定位参考车体系。节点会拒绝这种配置。

**Goal.msg 没有 Header / frame_id。** `output_frame` 是本节点与接收控制器之间必须共同遵守的约定，消息不会自行告诉接收端它属于哪个坐标系。选择 vehicle 输出时，控制端还要按消息时间处理车体系变化，不能把延迟收到的点当成发布时刻的新局部坐标。

## 5. 识别到参考路径的完整过程

### 第一步：把相机图像投影到米制地面

`geometry.ground_homography()` 使用 CameraInfo 的校正内参、校正旋转 R、图像时刻 TF，以及 `ground_z_m`，构造地面到图像的单应矩阵 H。将地面点代入：

```text
[a,b,c]ᵀ = H · [x,y,1]ᵀ
图像像素 u=a/c，v=b/c
```

双目相机的 `P[:,3]` 包含另一相机基线；TF 已经定位到当前光学中心，本实现不再重复叠加这项基线。

`BirdEye` 在车前铺设米制网格，默认前方 15 m、左右各 4 m、0.04 m/格，再从图像采样得到鸟瞰图。改变范围会重新计算网格尺寸。相机看不到或投影到相机背面的地面被排除，**网格设置为15 m不代表相机真实看到了15 m**。

### 第二步：提取细线和骨架

暗线模式检查亮度、局部背景对比和颜色中性；亮线模式使用对应的亮色局部对比。背景形态学运算只用于估计背景，不对最终线路掩膜大范围补缝。

随后细化掩膜，按八邻域提取骨架连通域。断开的平行线保留为不同候选，不为了“让线更长”把它们粘到一起。这里没有起点颜色或橙色终点触发分支。

### 第三步：从已知起点建立身份，再利用真实运动延续身份

首帧已知车辆在原线上且朝向沿线。算法比较候选能否从这个起点通过直线加可行圆弧连接，并使用与规划器相同的最小转弯半径。

后续帧先计算两图像时刻之间的真实位姿增量，再把旧路径转到新车体系：

```text
旧车体系中的平移 = (新世界位置 - 旧世界位置) · R(旧航向)
转角增量 = 新航向 - 旧航向，归一化到 [-π,π]
新局部路径 = (旧局部路径 - 平移) · R(转角增量)
```

这里使用行向量记法。与仿真原版不同，实车版不根据自己“打算输出的控制命令”猜测车辆运动。

匹配使用旧路线的一段支持点到当前候选的距离及切向一致性，同时检查最佳代价和最佳/次佳代价差。候选太接近无法区分时返回歧义状态，不自动换到最近的另一条线。历史进度只在有序前缀内搜索，减少跳到近邻回程路段的风险。

### 第四步：沿连接关系排成有序路径

从匹配锚点沿骨架相邻节点向前、向后追踪，用局部方向与有限分支前瞻选择后继，合成有序路线。不能直接按 x 排序：U形弯的正确路线本来就会出现 x 先增后减。

这仍是局部骨架方法。真实交叉、分割粘连、强阴影或不可见分支不一定可区分；此实现没有读取隐藏地图，也没有提供避障规划。

### 第五步：生成足够长、车辆可行的参考路径

`planning.build_reference()` 删除重复点，只使用连续的原路线前缀，并做有位移上限的平滑。然后按**累计弧长**采样，计算方向与曲率；不因首尾靠近就把U形弯误认为短线。

图像边缘的骨架端点容易出现单个斜向像素台阶。平滑时先用一小段局部点拟合端点切向，再为卷积补齐边界，避免把一个像素的方向误差放大成急弯。补齐点只参与平滑，不会成为输出中的未观测远程路线。

默认目标长度10 m，至少5 m，采样间隔不超过0.15 m；完整10 m参考路径约68个点。可见路径不足时不把末端无限外推成长直线，路段不连续、曲率超出最小转弯半径、平滑偏移过大也会停止。

速度同时受配置上限、置信度、横向加速度和剩余路径制动距离约束。每条路径最后一点 `v=0`，速度从后向前满足制动约束。发布时先保守扣除图像延迟期间可能已经行驶的距离，再按最新测得车速、发布间隔和定位延迟检查停车空间。真正的速度跟踪、起步加速度和终点停车仍由下游控制器执行。

每点时间用相邻弧长和该段两端速度积分，因此调整速度时必须同步重算时间。路径点不包含倒车请求。

### 第六步：感知与发布采用不同节拍

默认感知处理10 Hz，正常 Goal 发布2 Hz，输出队列长度1。不逐相机帧发布完整参考路径，也不给同一份旧行驶路径换上新时间戳反复发布。

短时丢线只允许沿已经观测、由定位补偿的原路线预测，默认最多0.35 s；置信度会衰减，规划器的置信度门槛可能让它更早停止。它不是向未知远处补路的许可。标定、图像或外部TF/解码异常会撤销旧路径继续预测的资格，只有重新观测到原线才能恢复。

普通图像断流、标定更新不会授权算法重新选择另一条邻线；已经建立的米制路线身份继续保留。定位发生不合理突跳、定位时间倒退或ROS时钟倒退时，路线身份已无法可靠补偿，节点会保持停止；需要将车辆重新放在目标线上、检查定位或回放时钟后重启节点。这与普通相机/定位短时断流后自动恢复不同。

从有效状态转为失效时，首条停驶消息不等待正常2 Hz周期；持续失效后按发布周期维持停驶消息。发布线程仍有调度延迟，不能把它等同于硬件急停。下游控制器必须有自己的消息超时停车机制，因为进程或网络完全中断时，节点无法保证再发出最后一条停止消息。

## 6. Goal / RefPoint 输出数据规范

### Goal 顶层字段

| 字段 | 正常行驶输出 | 停驶 / 预览输出 |
| --- | --- | --- |
| `timestamp: float64` | 来源图像时刻，ROS秒 | 有有效观测时保留其时刻；无有效观测时使用当前ROS秒 |
| `Estop: int16` | `0` | `runtime.stop_estop_level`，默认`1`；允许1/2/3 |
| `Go: bool` | `true` | `false` |
| `Signal: int16` | `0` | `0` |
| `refPath: RefPoint[]` | 有序参考路径 | 空数组 |
| `mode: int16` | 配置值，默认`3` | 同样保留配置值 |
| `objects: Object[]` | 空数组 | 空数组 |

mode允许1、2、3；选择含义按真实控制端与原消息定义核对。`Signal=0`表示本巡线节点不输出转向灯决策，并不表示路径没有弯道。

### 每个 RefPoint 的全部字段

| 字段 | 单位 / 填写规则 |
| --- | --- |
| `t: float64` | 秒；见下面的绝对/相对时间约定 |
| `x`, `y: float64` | m；由 `output_frame` 确定世界系或图像时刻车体系 |
| `v: float64` | m/s，非负参考速度；末点为0 |
| `heading: float64` | rad，路径切向，归一化到 `[-π,π)`；+x为零、逆时针为正 |
| `cr: float64` | `1/m`，带符号曲率；在x前y左约定下左弯为正 |
| `left_width: float64` | m，配置的左侧参考走廊宽度 |
| `right_width: float64` | m，配置的右侧参考走廊宽度 |
| `turning_flag: int16` | `abs(cr) >= planner.turning_threshold_per_m` 时为1，否则0 |

宽度不是本算法检测到的道路边界，也不是对无障碍空间的保证，必须按接收控制器含义和现场路线填写。

两种点时间均严格递增：

- `point_time_mode: relative`：首点 `t=0`，其余为距本次图像时刻的预计行驶秒数。
- `point_time_mode: absolute`：首点 `t=Goal.timestamp`，其余为 `Goal.timestamp + 相对秒数`。

接收端必须与配置使用同一种模式。absolute使用ROS秒；若系统采用 `/use_sim_time` 回放，它随ROS仿真时钟，并不一定是当前UTC墙钟。

这些时间是参考路径的速度积分时标。首点来自最近的可靠可见路段，不保证与车辆当前位置重合，因此它不是包含起步接入过程的完整时间约束轨迹。若实际控制器把 `t` 解释为必须严格到达该点的时刻，应先提供控制器接口约定再完成对应适配，不能仅凭字段名推断这一语义。

## 7. 常用参数怎样调整

| 参数 | 默认 | 调整依据 |
| --- | --- | --- |
| `vision.line_polarity` | `dark` | 浅色细线改为`light`；当前不同时追两种极性的线 |
| `vision.bev_forward_m` / `bev_half_width_m` | 15 / 4 m | 覆盖真实可见区域；扩大网格不能增加相机信息 |
| `vision.resolution_m` | 0.04 m | 应能分辨实际线宽和近邻线间距，同时考虑处理耗时 |
| `vision.association_gate_m` | 0.25 m | 按标定、定位误差调整；过宽更容易混淆邻线 |
| `vision.memory_s` | 0.35 s | 只允许短时原线预测，不宜靠放宽它掩盖长期丢线 |
| `planner.target_length_m` / `min_length_m` | 10 / 5 m | 结合控制器前视需求、视野和当前速度制动距离 |
| `planner.spacing_m` | 0.15 m | 最大采样间距，不是控制更新周期 |
| `planner.minimum_radius_m` | 2.0 m | 填车辆实际可行半径；节点自动同步给视觉起步约束 |
| `planner.max_speed_mps` | 0.6 m/s | 低速联调起点，按实测能力调整 |
| `planner.braking_mps2` | 0.6 m/s² | 使用实际保守制动能力，不要把数值设大假装能更快停车 |
| `runtime.process_hz` / `publish_hz` | 10 / 2 Hz | 分别是感知目标频率和正常路径发布上限 |

`runtime.max_speed_mps` 默认2 m/s，是拒绝不可信/超出适用范围定位的门限，**不是**给控制器的巡航速度。图像有效期0.75 s、定位有效期0.35 s、两感知帧最大间隔0.6 s；时间倒退、定位突跳、倒车或过大倾斜会使旧路径失效。

若一直报告“路径太短”，先检查前方有效视野、相机姿态、TF、地面高度和图像上的真实连续线段；不要通过大幅降短路径门槛或外推未见路线来绕过问题。若路径整体镜像、缩放不对或转向相反，先修坐标和标定，再调关联参数。

## 8. 测试和验收边界

核心模块可以脱离ROS离线测试，例如在当前仓库已安装pytest的环境中：

```bash
cd /home/liuzonghao/THUPathfindingLab
.venv/bin/python -m pytest ros_line_follower/tests -q
```

这里使用网页仓库`.venv`只是运行无ROS的NumPy/OpenCV核心测试；启动实车ROS节点仍使用前述系统Python环境。

核心测试覆盖米制投影、真实运动坐标变换、近邻不跨线、弯道顺序、遮挡过期、路径长度与曲率、速度时间一致性、消息字段和发布门限。透视相机贯通测试使用真实宽度的线带、0.4 m邻近干扰线、直线/弯线/缓变曲线、明暗两种极性及车辆运动，检查从图像生成10 m参考路径。

有Noetic时，再运行不连接任何master的ROS状态回归：

```bash
source /opt/ros/noetic/setup.bash
PYTHONPATH="$PWD/ros_line_follower/src:$PYTHONPATH" /usr/bin/python3 \
  -m unittest discover -s ros_line_follower/tests -p test_ros_node.py -v
```

下面的完整联调会自动在 `/tmp` 创建并编译临时catkin工作区，使用随机localhost端口的独立master；不使用原有 `ROS_MASTER_URI`，不连接实车话题。需要本仓库中的原消息文件和 `YHS_cuda_drivable/src/cav_msgs`：

```bash
/usr/bin/python3 ros_line_follower/tests/ros_smoke.py
```

实际验证包括生成消息的TCPROS传输与序列化、世界坐标、时间戳、路径长度、2 Hz限频、图像/定位断流停止及恢复。结果和日志写入仓库 `.cache/ros-smoke/`。测试原样复制提供的Goal/RefPoint；缺少的Object仅在临时测试包中使用明确标注的替身，所以**不代表生产Goal的MD5或真实控制器已经验证**。

本次验证结果（2026-10-13）：

| 检查 | 结果 |
| --- | --- |
| 无ROS核心测试 | 72项通过；ROS专用模块在此解释器中跳过 |
| Python 3.8 / Noetic离线状态测试 | 12项通过 |
| 临时catkin工作区从零构建与TCPROS联调 | 通过；收到8条正常行驶Goal，路径均为10 m |
| 正常消息最小间隔 | 0.504 s，满足2 Hz限频 |
| 停止注入图像 / 定位后的首条停驶消息 | 约0.707 / 0.333 s，随后恢复测试通过 |

以上耗时来自本机合成数据联调，不能作为车辆端通信延迟或实际刹停距离。

这些测试不等于完成实车验收。当前还需要真实相机话题、标定/外参、Goal完整消息包和接收控制器，才能完成真实接口联通、录制数据回放、目标硬件耗时和封闭场地低速跟踪验证。没有实车图像/rosbag的情况下，不能把它宣称为已在实车中对比证明最优的方法。

坐标和相机投影约定参考ROS官方定义：[REP-103](https://github.com/ros-infrastructure/rep/blob/master/rep-0103.rst)、[CameraInfo.msg](https://github.com/ros/common_msgs/blob/noetic-devel/sensor_msgs/msg/CameraInfo.msg)。
