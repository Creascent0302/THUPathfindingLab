#include <message_filters/subscriber.h>
#include <message_filters/sync_policies/approximate_time.h>
#include <message_filters/time_synchronizer.h>
#include <mutex>
#include <queue>
#include <deque>
#include <thread>
#include <string>
#include <vector>
#include <limits>
#include <cmath>
#include <cstring>
#include <algorithm>
#include <tf/transform_broadcaster.h>
#include "drivable_detect.h"
#include "occ_labeler.h"
#include "CVaRcal.h"
#include "tic_toc.h"
#include "LocalMap_msgs/LocalMap_Element.h"
#include "LocalMap_msgs/LocalMap.h"
#include "cav_msgs/VehicleState.h"
#include "opencv2/opencv.hpp"
#include "perception_ros_msg/CoreInfo.h"
#include "perception_ros_msg/RsPerceptionMsg.h"
#include "perception_ros_msg/LidarFrameMsg.h"
#include "perception_ros_msg/SupplementInfo.h"
#include "perception_ros_msg/Objects.h"
#include "perception_ros_msg/Object.h"
#include "xperception_msgs/Object.h"
#include "xperception_msgs/ObjectList.h"
#include "xperception_msgs/ObjectListCombined.h"

//------------------------------------------------------------------------------
// 全局对象与状态变量
//------------------------------------------------------------------------------

// LiDAR 可通行区域检测核心类实例（实现见 drivable_detect.cpp）
DRIVABLE_DETECT_MAPPED detect_mapped;

// 动态车辆感知消息缓存（由 veh_sub 回调写入，主循环中 read_vehCB 消费）
xperception_msgs::ObjectListCombined veh_msg;

// 雷达点云消息缓存（由 lidar_sub 回调写入，主循环中 lidarmappedCB 消费）
sensor_msgs::PointCloud2 lidar_msg;

// 地图尺寸 / 分辨率 / 参数
static int   MAP_SIZE,      // 地图栅格边长（MAP_SIZE x MAP_SIZE）
             N_FRAME;       // 多帧融合数量（mapping 滑窗大小）

static float MAP_RESOLUTION,// 栅格分辨率（m）
             RANGE,         // 点云最大有效半径
             VOXEL_SIZE,    // 体素下采样尺寸
             roll, yaw, pitch, // 车辆姿态（VehicleState 提供）
             yaw_rate = 0.0f, // 横摆角速度 rad/s（VehicleState.yaw_rate）
             time_stamp,    // 时间戳（VehicleState）
             X_high, Y_low, X_low, Y_high, // 前后/左右 ROI 区域
             Z_thre;        // 高度阈值

// 当前 UTM 位姿（由 VehicleState 提供）
static double utm_x,
              utm_y,
              utm_z,
              timeRtk;      // RTK 时间戳（与雷达/感知同步）

// OpenCV 栅格，用于绘制车辆/障碍物掩膜（pixel → sub_map）
cv::Mat grid;

// 有序位姿缓冲（按时间递增），供 LiDAR/感知做时间插值；禁止 pop 破坏历史
static std::deque<cav_msgs::VehicleState> vh_states;
static std::mutex vh_states_mutex;
static const size_t VH_STATES_MAX = 200;
static const double VH_STATES_MAX_AGE_SEC = 2.0;
// 定位 heading 计算/传输延迟（秒）；仅 heading_from_gps=true 时用于 yaw_rate 前向补偿
static double heading_latency_sec = 0.06;
// false: 定位模块 heading，timestamp 与点云一致，不补偿
// true:  GPS heading，启用 heading_latency_sec 延迟补偿
static bool heading_from_gps = false;
// 10Hz 流：两帧间插值；边缘外推需覆盖 heading 延迟 + 一帧抖动
static const double LIDAR_POSE_EXACT_MAX_DT = 0.002;
static const double LIDAR_POSE_BRACKET_MAX_GAP = 0.15;
static const double LIDAR_POSE_EXTRAP_MAX_DT = 0.12;

// 运动畸变去除：一帧扫描约 100ms，快速转向时首尾点对应的航向差可达十几度，
// 若整帧用同一个 heading 投影，静态墙会被摊成以车为心的扇形。
static bool deskew_enable = true;
// header.stamp 与“参考时刻”的偏移（扫描起点/终点约定不同时用于标定）
static double lidar_time_offset_sec = 0.0;
// 单点时间与参考时刻的最大允许偏差，超出视为异常丢弃补偿
static const double DESKEW_MAX_DT = 0.2;

// Eigen 形式的 UTM 位姿向量
static Eigen::Vector3d utm_loc;

// sub_map：drivable/occ_map 的底层 float 数组，大小 MAP_SIZE^2
// inx_set：预留的辅助数组（目前主要用于标记用途，实际逻辑基本未用）
float* sub_map = nullptr;
float* inx_set = nullptr;

// 点云缓存：当前映射帧点云 / 处理后输出点云
pcl::PointCloud<PointType>::Ptr cloud_mapped(new pcl::PointCloud<PointType>);
pcl::PointCloud<PointType>::Ptr cloud_mapped_out(new pcl::PointCloud<PointType>);

static double snapToGridLine(double value)
{
    return std::floor(value / static_cast<double>(MAP_RESOLUTION)) * static_cast<double>(MAP_RESOLUTION);
}

static double wrapAngleRad(double a)
{
    while (a > M_PI) a -= 2.0 * M_PI;
    while (a < -M_PI) a += 2.0 * M_PI;
    return a;
}

static double lerpAngleRad(double a0, double a1, double t)
{
    return wrapAngleRad(a0 + t * wrapAngleRad(a1 - a0));
}

static void lerpVehicleState(const cav_msgs::VehicleState& s0,
                             const cav_msgs::VehicleState& s1,
                             double t,
                             double query_time,
                             cav_msgs::VehicleState& out)
{
    out = s1;
    out.timestamp = query_time;
    out.x = s0.x + t * (s1.x - s0.x);
    out.y = s0.y + t * (s1.y - s0.y);
    out.z = s0.z + t * (s1.z - s0.z);
    out.heading = lerpAngleRad(s0.heading, s1.heading, t);
    out.yaw_rate = s0.yaw_rate + t * (s1.yaw_rate - s0.yaw_rate);
    out.roll = s0.roll + t * (s1.roll - s0.roll);
    out.pitch = s0.pitch + t * (s1.pitch - s0.pitch);
}

// 在缓冲中按 query_time 做 bracket 插值（位置/原始 heading/yaw_rate）
static bool lookupVehicleStateAtTime(double query_time, cav_msgs::VehicleState& out)
{
    std::lock_guard<std::mutex> lock(vh_states_mutex);
    if (vh_states.empty() || query_time <= 0.0) {
        return false;
    }

    for (const auto& s : vh_states) {
        if (std::fabs(s.timestamp - query_time) <= LIDAR_POSE_EXACT_MAX_DT) {
            out = s;
            out.timestamp = query_time;
            return true;
        }
    }

    if (query_time <= vh_states.front().timestamp) {
        if (vh_states.size() >= 2) {
            const double dt_seg = vh_states[1].timestamp - vh_states[0].timestamp;
            const double lead = vh_states.front().timestamp - query_time;
            if (dt_seg > 1e-6 && lead <= LIDAR_POSE_EXTRAP_MAX_DT) {
                const double t = (query_time - vh_states[0].timestamp) / dt_seg;
                lerpVehicleState(vh_states[0], vh_states[1], t, query_time, out);
                return true;
            }
        }
        return false;
    }

    if (query_time >= vh_states.back().timestamp) {
        if (vh_states.size() >= 2) {
            const auto& s0 = vh_states[vh_states.size() - 2];
            const auto& s1 = vh_states.back();
            const double dt_seg = s1.timestamp - s0.timestamp;
            const double lag = query_time - s1.timestamp;
            if (dt_seg > 1e-6 && lag <= LIDAR_POSE_EXTRAP_MAX_DT) {
                const double t = (query_time - s0.timestamp) / dt_seg;
                lerpVehicleState(s0, s1, t, query_time, out);
                return true;
            }
        }
        return false;
    }

    for (size_t i = 1; i < vh_states.size(); ++i) {
        const auto& s0 = vh_states[i - 1];
        const auto& s1 = vh_states[i];
        if (query_time < s0.timestamp || query_time > s1.timestamp) {
            continue;
        }
        const double dt_seg = s1.timestamp - s0.timestamp;
        if (dt_seg <= 1e-6) {
            out = s1;
            out.timestamp = query_time;
            return true;
        }
        if (dt_seg > LIDAR_POSE_BRACKET_MAX_GAP) {
            return false;
        }
        const double t = (query_time - s0.timestamp) / dt_seg;
        lerpVehicleState(s0, s1, t, query_time, out);
        return true;
    }
    return false;
}

// 由缓冲中 query_time 附近的相邻帧差分 yaw_rate（报文字段常为 0）
static double estimateYawRateAtTime(double query_time)
{
    std::lock_guard<std::mutex> lock(vh_states_mutex);
    if (vh_states.size() < 2) {
        return 0.0;
    }
    for (size_t i = 1; i < vh_states.size(); ++i) {
        const auto& s0 = vh_states[i - 1];
        const auto& s1 = vh_states[i];
        if (query_time < s0.timestamp || query_time > s1.timestamp) {
            continue;
        }
        const double dt = s1.timestamp - s0.timestamp;
        if (dt <= 1e-6) {
            return 0.0;
        }
        return wrapAngleRad(s1.heading - s0.heading) / dt;
    }
    const auto& s0 = vh_states[vh_states.size() - 2];
    const auto& s1 = vh_states.back();
    const double dt = s1.timestamp - s0.timestamp;
    if (dt <= 1e-6) {
        return 0.0;
    }
    return wrapAngleRad(s1.heading - s0.heading) / dt;
}

// 雷达时刻位姿：xyz/heading 均在 t_lidar 插值；GPS 模式下对 heading 做延迟补偿
static bool syncPoseForLidar(double lidar_time,
                             cav_msgs::VehicleState& out,
                             double& heading_raw,
                             double& yaw_rate_used)
{
    if (!lookupVehicleStateAtTime(lidar_time, out)) {
        return false;
    }

    heading_raw = out.heading;
    yaw_rate_used = out.yaw_rate;
    if (heading_from_gps) {
        if (std::fabs(yaw_rate_used) < 1e-6) {
            yaw_rate_used = estimateYawRateAtTime(lidar_time);
        }
        out.heading = wrapAngleRad(heading_raw + yaw_rate_used * heading_latency_sec);
    }
    out.timestamp = lidar_time;
    return true;
}

// 车辆角速度上限；超过基本是定位跳变，用它做畸变补偿只会造出新的扇形
static const double DESKEW_MAX_YAW_RATE = 2.0; // rad/s

// query_time 附近的角速度与 ENU 线速度，用于单帧内的运动补偿。
// bracketed_out=false 表示 query_time 落在缓冲末尾之后，ω 是外推值（滞后、不可靠）。
static void estimateTwistAtTime(double query_time,
                                double& yaw_rate_out,
                                double& ve_out,
                                double& vn_out,
                                bool& bracketed_out)
{
    yaw_rate_out = 0.0;
    ve_out = 0.0;
    vn_out = 0.0;
    bracketed_out = false;

    std::lock_guard<std::mutex> lock(vh_states_mutex);
    if (vh_states.size() < 2) {
        return;
    }

    size_t i1 = vh_states.size() - 1;
    for (size_t i = 1; i < vh_states.size(); ++i) {
        if (query_time >= vh_states[i - 1].timestamp && query_time <= vh_states[i].timestamp) {
            i1 = i;
            bracketed_out = true;
            break;
        }
    }

    const auto& s0 = vh_states[i1 - 1];
    const auto& s1 = vh_states[i1];
    const double dt = s1.timestamp - s0.timestamp;
    if (dt <= 1e-6) {
        return;
    }
    yaw_rate_out = wrapAngleRad(s1.heading - s0.heading) / dt;
    ve_out = (s1.x - s0.x) / dt;
    vn_out = (s1.y - s0.y) / dt;
}

static int pointFieldOffset(const sensor_msgs::PointCloud2& msg,
                            const std::string& name,
                            uint8_t* datatype = nullptr)
{
    for (const auto& f : msg.fields) {
        if (f.name == name) {
            if (datatype != nullptr) {
                *datatype = f.datatype;
            }
            return static_cast<int>(f.offset);
        }
    }
    return -1;
}

// 逐点时间字段：速腾/禾赛/Ouster 命名各异，绝对秒或帧内相对秒都要支持
static int findPointTimeField(const sensor_msgs::PointCloud2& msg, uint8_t& datatype)
{
    static const char* kNames[] = {"timestamp", "time", "t", "time_offset", "point_time", "time_stamp"};
    for (const char* name : kNames) {
        const int offset = pointFieldOffset(msg, name, &datatype);
        if (offset >= 0) {
            return offset;
        }
    }
    return -1;
}

static double readPointTime(const uint8_t* p, int offset, uint8_t datatype)
{
    switch (datatype) {
        case sensor_msgs::PointField::FLOAT32: {
            float v = 0.0f;
            std::memcpy(&v, p + offset, sizeof(float));
            return static_cast<double>(v);
        }
        case sensor_msgs::PointField::FLOAT64: {
            double v = 0.0;
            std::memcpy(&v, p + offset, sizeof(double));
            return v;
        }
        case sensor_msgs::PointField::UINT32: {
            uint32_t v = 0;
            std::memcpy(&v, p + offset, sizeof(uint32_t));
            return static_cast<double>(v) * 1e-9;
        }
        default:
            return std::numeric_limits<double>::quiet_NaN();
    }
}

// deskew 诊断信息：不确认这些数值就无法判断补偿是在减小还是在制造畸变
struct DeskewInfo {
    double dt_min_ms = 0.0;
    double dt_max_ms = 0.0;
    double yaw_rate = 0.0;
    double span_deg = 0.0;
    bool bracketed = false;
};

// 把整帧点按各自采集时刻的位姿投影回参考时刻 t_ref 的雷达系（一阶匀速匀角速度模型）。
// ve/vn 是 VehicleState 差分出来的“车辆中心”速度，而点在雷达系，两者中心相差杠杆臂
// lever = 雷达在车体系下的位置，因此旋转必须绕车辆中心做：
//   p_ref = R(w*dt) * (p_raw + lever) - lever + R(-heading_ref) * (v*dt)
static bool deskewCloud(const sensor_msgs::PointCloud2& msg,
                        double t_ref,
                        double heading_ref,
                        double lever_x,
                        double lever_y,
                        pcl::PointCloud<PointType>::Ptr out,
                        DeskewInfo& info)
{
    info = DeskewInfo();

    const int off_x = pointFieldOffset(msg, "x");
    const int off_y = pointFieldOffset(msg, "y");
    const int off_z = pointFieldOffset(msg, "z");
    uint8_t i_type = 0;
    int off_i = pointFieldOffset(msg, "intensity", &i_type);
    if (i_type != sensor_msgs::PointField::FLOAT32) {
        off_i = -1;
    }
    if (off_x < 0 || off_y < 0 || off_z < 0) {
        return false;
    }

    uint8_t t_type = 0;
    const int off_t = findPointTimeField(msg, t_type);
    if (off_t < 0) {
        return false;
    }
    if (t_type != sensor_msgs::PointField::FLOAT32 &&
        t_type != sensor_msgs::PointField::FLOAT64 &&
        t_type != sensor_msgs::PointField::UINT32) {
        return false;
    }

    double yaw_rate = 0.0;
    double ve = 0.0;
    double vn = 0.0;
    bool bracketed = false;
    estimateTwistAtTime(t_ref, yaw_rate, ve, vn, bracketed);
    yaw_rate = std::max(-DESKEW_MAX_YAW_RATE, std::min(DESKEW_MAX_YAW_RATE, yaw_rate));
    info.yaw_rate = yaw_rate;
    info.bracketed = bracketed;

    const double stamp = msg.header.stamp.toSec();
    const double ch = std::cos(heading_ref);
    const double sh = std::sin(heading_ref);
    const size_t n_pts = static_cast<size_t>(msg.width) * static_cast<size_t>(msg.height);

    out->clear();
    out->points.resize(n_pts);
    out->width = static_cast<uint32_t>(n_pts);
    out->height = 1;
    out->is_dense = false;

    double dt_min = std::numeric_limits<double>::max();
    double dt_max = -std::numeric_limits<double>::max();

    #pragma omp parallel for reduction(min:dt_min) reduction(max:dt_max)
    for (long idx = 0; idx < static_cast<long>(n_pts); ++idx) {
        const uint8_t* p = msg.data.data() + static_cast<size_t>(idx) * msg.point_step;

        float x = 0.0f, y = 0.0f, z = 0.0f, inten = 0.0f;
        std::memcpy(&x, p + off_x, sizeof(float));
        std::memcpy(&y, p + off_y, sizeof(float));
        std::memcpy(&z, p + off_z, sizeof(float));
        if (off_i >= 0) {
            std::memcpy(&inten, p + off_i, sizeof(float));
        }

        double t_raw = readPointTime(p, off_t, t_type);
        // 大于 1e8 认为是绝对 UNIX 秒，否则是相对 header.stamp 的帧内偏移
        double dt = std::isfinite(t_raw)
                        ? ((t_raw > 1e8) ? (t_raw - t_ref) : (stamp + t_raw - t_ref))
                        : 0.0;
        if (!std::isfinite(dt) || std::fabs(dt) > DESKEW_MAX_DT) {
            dt = 0.0;
        }
        if (dt < dt_min) dt_min = dt;
        if (dt > dt_max) dt_max = dt;

        const double dtheta = yaw_rate * dt;
        const double cd = std::cos(dtheta);
        const double sd = std::sin(dtheta);
        const double de = ve * dt;
        const double dn = vn * dt;

        // 先移到以车辆中心为原点，绕中心转 dtheta，再移回雷达系
        const double xc = static_cast<double>(x) + lever_x;
        const double yc = static_cast<double>(y) + lever_y;

        PointType& q = out->points[idx];
        q.x = static_cast<float>(cd * xc - sd * yc - lever_x + (ch * de + sh * dn));
        q.y = static_cast<float>(sd * xc + cd * yc - lever_y + (-sh * de + ch * dn));
        q.z = z;
        q.intensity = inten;
    }

    if (dt_max >= dt_min) {
        info.dt_min_ms = dt_min * 1000.0;
        info.dt_max_ms = dt_max * 1000.0;
        info.span_deg = std::fabs(yaw_rate) * (dt_max - dt_min) * 180.0 / M_PI;
    }
    return true;
}

static bool findNearestVehicleState(double query_time,
                                    cav_msgs::VehicleState& out,
                                    double max_dt = 0.1)
{
    std::lock_guard<std::mutex> lock(vh_states_mutex);
    if (vh_states.empty()) {
        return false;
    }
    double best_dt = std::numeric_limits<double>::max();
    const cav_msgs::VehicleState* best = nullptr;
    for (const auto& s : vh_states) {
        const double dt = std::fabs(s.timestamp - query_time);
        if (dt < best_dt) {
            best_dt = dt;
            best = &s;
        }
    }
    if (best == nullptr || best_dt > max_dt) {
        return false;
    }
    out = *best;
    return true;
}

// 状态标志位：表明是否有新的车辆状态 / 点云消息
bool veh_state = false, lidar_state = false;

// ROS 发布器：不同 topic 的输出
ros::Publisher pubGround;    // /drivable/ground_point_cloud（当前流程中未启用）
ros::Publisher pubFiltered;  // /drivable/filtered_point_cloud（滤波后点云）
ros::Publisher pubOccmap;    // /drivable/occ_map（占据栅格）
ros::Publisher pubHeimap;    // /drivable/Hei_map（高度栅格）
ros::Publisher pub_LocalMap; // /cav_local_map（本地代价地图）
ros::Publisher pub_MultiMap; // /grid_map（多层 grid_map，包括 CVaR 等）

//------------------------------------------------------------------------------
// 坐标变换辅助函数（Eigen 形式）
//------------------------------------------------------------------------------

// 仅平移：UTM 整数与小数部分的拆分/对齐
static void transform_translation(Eigen::Vector3d pi, Eigen::Vector3d & po, float x_div, float y_div){
    /*
     * 功能：
     *   - 对 Eigen 点 pi 做平移，映射到以当前 UTM 小数部分为原点的本地坐标
     *   - 主要用于感知输出转换到本地栅格中（read_objCB / read_vehCB）
     */
    po.x() = pi.x() + x_div;
    po.y() = pi.y() + y_div;
}

// 仅旋转：按 yaw（heading）绕 z 轴旋转
static void transform_rotation(Eigen::Vector3d pi, Eigen::Vector3d & po, float heading){
    /*
     * 功能：
     *   - 把传感器坐标系下的点 pi 绕 z 轴旋转 heading（车辆航向），对齐到车体坐标系/世界坐标系
     *   - 用极坐标方式：distance + atan2 得到初始角，再加上 heading
     */
    float distance = std::sqrt(std::pow(pi.x(),2) + std::pow(pi.y(),2));
    float target_angle = atan2(pi.y(), pi.x());
    float yaw_target = heading + target_angle;

    po.x() = distance * cos(yaw_target);
    po.y() = distance * sin(yaw_target);
    po.z() = pi.z();
}

//------------------------------------------------------------------------------
// Loc_mapPB：发布本地可通行区域 LocalMap（float → 离散 driveable_index）
//------------------------------------------------------------------------------
void Loc_mapPB(float* sub_map){
    /*
     * 功能：
     *   - 构造 LocalMap_msgs::LocalMap 消息
     *   - 使用 detect_mapped.drivable_value_grid：driveable_value 连续值 [0,1]；driveable_index 由阈值二值化
     *   - 坐标必须与 drivable_value_grid 生成时使用的栅格锚点一致（不能用实时 utm_x 重算）
     */

    if (!detect_mapped.map_history_initialized) {
        return;
    }

    LocalMap_msgs::LocalMap loc_map;
    loc_map.timestamp   = detect_mapped.frame_time;
    loc_map.box_size_x  = MAP_RESOLUTION;
    loc_map.box_size_y  = MAP_RESOLUTION;
    loc_map.boxes_num_x = MAP_SIZE;
    loc_map.boxes_num_y = MAP_SIZE;

    // 与 ini() 中滚动/点云落格使用的锚点完全一致，避免定位抖动或 LiDAR 帧间位姿漂移导致全局跳变
    const double map_anchor_x = detect_mapped.grid_anchor_x;
    const double map_anchor_y = detect_mapped.grid_anchor_y;

    loc_map.map_cx = map_anchor_x;
    loc_map.map_cy = map_anchor_y;

    int row, column;
    for(int i = 0; i < MAP_SIZE * MAP_SIZE; ++i){
        LocalMap_msgs::LocalMap_Element element_info;
        row    = std::floor((float)i / MAP_SIZE);
        column = i - row * MAP_SIZE;

        // 栅格索引
        element_info.x_id = std::floor((float)i / MAP_SIZE);
        element_info.y_id = std::floor(i - element_info.x_id * MAP_SIZE);

        // 栅格中心 UTM：锚点 + IJ2xy 局部格心，与内部 xy2IJ/movePC2Grid 同一套索引
        float local_cx = 0.0f;
        float local_cy = 0.0f;
        detect_mapped.IJ2xy(i, local_cx, local_cy);
        element_info.ct_x = map_anchor_x + local_cx;
        element_info.ct_y = map_anchor_y + local_cy;

        // A. driveable_index: 由 sub_map 粗略标记为“是否可通行”
        // if (sub_map[i] > 80){
        //     element_info.driveable_index = 1;
        // }
        // else{
        //     element_info.driveable_index = 0;
        // }
        // driveable_value: 连续值 [0,1]，1=最佳可通行（来自 compute_drivable_passability）
        const float DRIVABLE_THRESHOLD = 0.5f;
        float* drivable_value = detect_mapped.drivable_value_grid;
        element_info.driveable_value = (drivable_value != nullptr) ? drivable_value[i] : 0.5f;
        element_info.driveable_value = std::max(0.0, std::min(1.0, static_cast<double>(element_info.driveable_value)));
        // B.driveable_value: 使用 CVaR 层的风险结果做进一步度量（值越大越安全）
        // element_info.driveable_value =
        //     1 - multi_map.get("CVaR").data()[(MAP_SIZE - 1 - (i / MAP_SIZE)) * MAP_SIZE + (i % MAP_SIZE)];        
        // driveable_index: 由 driveable_value 阈值二值化
        element_info.driveable_index = (element_info.driveable_value > DRIVABLE_THRESHOLD) ? 1 : 0;

        loc_map.local_map.push_back(element_info);
    }

    pub_LocalMap.publish(loc_map);
}

//------------------------------------------------------------------------------
// Occ_mapPB：发布占据栅格地图 nav_msgs::OccupancyGrid
//------------------------------------------------------------------------------
void Occ_mapPB(float* sub_map)
{
    /*
     * 功能：
     *   - 把 sub_map 映射为 nav_msgs::OccupancyGrid 形式的 /drivable/occ_map
     *   - 目前直接将 float 值写入 data（0~100），可作为代价/占据率
     *   - 同时把 sub_map 拷贝到 detect_mapped.pre_occ_grid，作为下一帧先验
     */

    nav_msgs::OccupancyGrid occ_map;
    occ_map.header.stamp = ros::Time().fromSec(timeRtk);
    occ_map.header.frame_id = "camera_init";
    occ_map.info.resolution = MAP_RESOLUTION;
    occ_map.info.width  = MAP_SIZE;
    occ_map.info.height = MAP_SIZE;

    // 与内部 xy2IJ/IJ2xy 保持一致：中心格格心在 0.5*resolution，而不是 0
    occ_map.info.origin.position.x = -MAP_SIZE / 2 * MAP_RESOLUTION;
    occ_map.info.origin.position.y = -MAP_SIZE / 2 * MAP_RESOLUTION;

    // 通过四元数把 OccupancyGrid 在 RViz 中转成“地图平面”
    Eigen::Quaterniond tf1(-sqrt(2)/2, 0, 0, sqrt(2)/2);
    Eigen::Quaterniond tf2(0, 1, 0, 0);
    tf1 = tf2 * tf1;
    occ_map.info.origin.orientation.x = tf1.x();
    occ_map.info.origin.orientation.y = tf1.y();
    occ_map.info.origin.orientation.z = tf1.z();
    occ_map.info.origin.orientation.w = tf1.w();

    // 遍历 sub_map，直接写入栅格
    for(int i = 0; i < occ_map.info.width * occ_map.info.height; ++i){
        occ_map.data.push_back(sub_map[i]);
    }

    pubOccmap.publish(occ_map);

    // 把当前的 sub_map 作为 pre_occ_grid 传给核心检测模块
    std::memcpy(detect_mapped.pre_occ_grid, sub_map, MAP_SIZE * MAP_SIZE * sizeof(float));
}

//------------------------------------------------------------------------------
// Hei_mapPB：发布高度栅格图（灰度编码）
//------------------------------------------------------------------------------
void Hei_mapPB(float* Hei_map)
{
    /*
     * 功能：
     *   - 将 detect_mapped.hei_grid（或其它传入的高度图）映射到 0~100 灰度值
     *   - 当前用固定的高度范围 [-2.0, 0.0] 进行归一化
     *   - 发布为 /drivable/Hei_map，便于调试地面高度/台阶信息
     */

    nav_msgs::OccupancyGrid occ_map;
    occ_map.header.stamp = ros::Time().fromSec(timeRtk);
    occ_map.header.frame_id = "camera_init";
    occ_map.info.resolution = MAP_RESOLUTION;
    occ_map.info.width  = MAP_SIZE;
    occ_map.info.height = MAP_SIZE;
    occ_map.info.origin.position.x = -MAP_SIZE / 2 * MAP_RESOLUTION;
    occ_map.info.origin.position.y = -MAP_SIZE / 2 * MAP_RESOLUTION;

    Eigen::Quaterniond tf1(-sqrt(2)/2, 0, 0, sqrt(2)/2);
    Eigen::Quaterniond tf2(0, 1, 0, 0);
    tf1 = tf2 * tf1;
    occ_map.info.origin.orientation.x = tf1.x();
    occ_map.info.origin.orientation.y = tf1.y();
    occ_map.info.origin.orientation.z = tf1.z();
    occ_map.info.origin.orientation.w = tf1.w();

    // 高度归一化区间（可视化用）
    float min_height = -2.0;
    float max_height =  0.0;

    for(int i = 0; i < occ_map.info.width * occ_map.info.height; ++i){
        float clamped_height = std::max(min_height, std::min(max_height, Hei_map[i]));
        float normalized_height = (clamped_height - min_height) / (max_height - min_height);
        int greyscale_value = static_cast<int>(normalized_height * 100.0f);
        greyscale_value = std::max(0, std::min(100, greyscale_value));
        occ_map.data.push_back(greyscale_value);
    }

    pubHeimap.publish(occ_map);
}

//------------------------------------------------------------------------------
// Pc_outputPB：发布点云（用于调试 ground_point_cloud）
//------------------------------------------------------------------------------
void Pc_outputPB(pcl::PointCloud<PointType>::Ptr pc)
{
    /*
     * 功能：
     *   - 将输入点云 pc 转为 ROS 消息并发布到 /drivable/ground_point_cloud
     *   - 当前主流程中未实际调用，可作为调试/扩展使用
     */

    sensor_msgs::PointCloud2 msg_ground;
    pcl::toROSMsg(*pc, msg_ground);
    msg_ground.header.stamp = ros::Time().fromSec(timeRtk);
    msg_ground.header.frame_id = "camera_init";
    pubGround.publish(msg_ground);
}

//------------------------------------------------------------------------------
// Filter_pcPB：发布滤波后点云（cloud_prcs）
//------------------------------------------------------------------------------
void Filter_pcPB(pcl::PointCloud<PointType>::Ptr pc){
    /*
     * 功能：
     *   - 发布过滤/预处理后的点云（detect_mapped.cloud_prcs）
     *   - topic: /drivable/filtered_point_cloud
     */

    sensor_msgs::PointCloud2 msg_ground;
    pcl::toROSMsg(*pc, msg_ground);
    msg_ground.header.stamp = ros::Time().fromSec(timeRtk);
    msg_ground.header.frame_id = "camera_init";
    pubFiltered.publish(msg_ground);
}

//------------------------------------------------------------------------------
// read_stateCB：车辆状态回调（VehicleState → 全局 UTM & 姿态）
//------------------------------------------------------------------------------
void read_stateCB(cav_msgs::VehicleState v_s){
    /*
     * 功能：
     *   - 从 /vehicle/vehicle_state 订阅消息
     *   - 更新全局 UTM 位姿、姿态角（roll/yaw/pitch）
     *   - 将该状态推入有序缓冲 vh_states，供雷达/感知按时间戳插值
     */

    timeRtk = v_s.timestamp;
    utm_x = v_s.x;
    utm_y = v_s.y;
    utm_z = v_s.z;

    utm_loc.x() = utm_x;
    utm_loc.y() = utm_y;
    utm_loc.z() = utm_z;

    time_stamp = v_s.timestamp;
    roll  = v_s.roll;
    yaw   = v_s.heading;
    pitch = v_s.pitch;

    {
        std::lock_guard<std::mutex> lock(vh_states_mutex);
        // 保持时间非递减；乱序则丢弃
        if (!vh_states.empty() && v_s.timestamp + 1e-6 < vh_states.back().timestamp) {
            return;
        }
        // 报文 yaw_rate 常为 0：仅用于日志/调试，不参与点云旋转
        if (!vh_states.empty()) {
            const auto& prev = vh_states.back();
            const double dt = v_s.timestamp - prev.timestamp;
            if (dt > 1e-3 && dt < 0.5 && std::fabs(v_s.yaw_rate) < 1e-6) {
                const double dh = wrapAngleRad(v_s.heading - prev.heading);
                v_s.yaw_rate = dh / dt;
            }
        }
        yaw_rate = static_cast<float>(v_s.yaw_rate);
        vh_states.push_back(v_s);
        while (vh_states.size() > VH_STATES_MAX) {
            vh_states.pop_front();
        }
        while (!vh_states.empty() &&
               (v_s.timestamp - vh_states.front().timestamp) > VH_STATES_MAX_AGE_SEC) {
            vh_states.pop_front();
        }
    }
}

//------------------------------------------------------------------------------
// read_vehCB：车辆感知回调（ObjectListCombined → sub_map 动态障碍掩膜）
//------------------------------------------------------------------------------
void read_vehCB(xperception_msgs::ObjectListCombined ObjLstCom){
    /*
     * 功能：
     *   - 将车辆感知结果投影到当前栅格坐标系，填充 sub_map 中的“车辆占据”区域
     *   - 步骤：
     *       1) 从 vh_states 中只读查找与 ObjLstCom.timestamp 最接近的 VehicleState（时间对齐）
     *       2) 对每个 Object 计算车辆外接矩形的四个顶点（车体坐标系）
     *       3) 转到栅格坐标（像素坐标），用 cv::fillPoly 在 grid 上画满
     *       4) 将 grid 中为 255 的像素对应的 sub_map[i] 设为 100（强占据）
     */

    cav_msgs::VehicleState v_s;
    float utm_x , utm_y;
    bool state = false;
    float heading;

    // 1) 只读查找最近位姿，禁止 pop 破坏 LiDAR 所需的历史缓冲
    if (findNearestVehicleState(ObjLstCom.timestamp, v_s, 0.1)) {
        utm_x = v_s.x;
        utm_y = v_s.y;
        heading = v_s.heading;
        state = true;
    }

    if(!state){
        // 没找到合适的状态，直接返回
        return;
    }

    // 重置网格图像（单通道 8-bit）
    grid.setTo(cv::Scalar(0));

    std::vector<std::vector<cv::Point>> fill_contours;
    std::vector<cv::Point> contour;

    const double map_anchor_x = snapToGridLine(utm_x);
    const double map_anchor_y = snapToGridLine(utm_y);
    float v_x, v_y, L, W, theta;
    Eigen::Vector3d p1, p2, p3, p4;

    // 2) 遍历所有传感器组合的 ObjectList
    for (xperception_msgs::ObjectList ObjLst : ObjLstCom.object_list_combined){
        for(xperception_msgs::Object Obj : ObjLst.sensor_info){
            // 将障碍物中心位置转换到当前 GRID_LEN 吸附锚点坐标系下
            v_x = Obj.x - map_anchor_x;
            v_y = Obj.y - map_anchor_y;

            L = Obj.size_x + 0.5;  // 适当扩张车辆长
            W = Obj.size_y + 0.4;  // 适当扩张车辆宽
            theta = Obj.heading;

            // 在车体坐标系下计算矩形四个顶点（p1~p4）
            p1.x() = v_x + L/2 *std::cos(theta) - W/2 * std::sin(theta); p1.y() = v_y + L/2 *std::sin(theta) + W/2 * std::cos(theta);
            p2.x() = v_x + L/2 *std::cos(theta) + W/2 * std::sin(theta); p2.y() = v_y + L/2 *std::sin(theta) - W/2 * std::cos(theta);
            p3.x() = v_x - L/2 *std::cos(theta) + W/2 * std::sin(theta); p3.y() = v_y - L/2 *std::sin(theta) - W/2 * std::cos(theta);
            p4.x() = v_x - L/2 *std::cos(theta) - W/2 * std::sin(theta); p4.y() = v_y - L/2 *std::sin(theta) + W/2 * std::cos(theta);

            // 转为像素坐标（以 MAP_SIZE/2 为中心，分辨率 MAP_RESOLUTION）
            float pt1_x = MAP_SIZE/2 - (p1.y()/MAP_RESOLUTION);
            float pt1_y = MAP_SIZE/2 - (p1.x()/MAP_RESOLUTION);
            if (pt1_x < 0 || pt1_x >= grid.cols || pt1_y < 0 || pt1_y >= grid.rows) {
                contour.clear();
                break;
            }

            float pt2_x = MAP_SIZE/2 - (p2.y()/MAP_RESOLUTION);
            float pt2_y = MAP_SIZE/2 - (p2.x()/MAP_RESOLUTION);
            if (pt2_x < 0 || pt2_x >= grid.cols || pt2_y < 0 || pt2_y >= grid.rows) {
                contour.clear();
                break;
            }

            float pt3_x = MAP_SIZE/2 - (p3.y()/MAP_RESOLUTION);
            float pt3_y = MAP_SIZE/2 - (p3.x()/MAP_RESOLUTION);
            if (pt3_x < 0 || pt3_x >= grid.cols || pt3_y < 0 || pt3_y >= grid.rows) {
                contour.clear();
                break;
            }

            float pt4_x = MAP_SIZE/2 - (p4.y()/MAP_RESOLUTION);
            float pt4_y = MAP_SIZE/2 - (p4.x()/MAP_RESOLUTION);
            if (pt4_x < 0 || pt4_x >= grid.cols || pt4_y < 0 || pt4_y >= grid.rows) {
                contour.clear();
                break;
            }

            // 构造四边形轮廓
            contour.push_back(cv::Point(std::round(pt1_x),std::round(pt1_y)));
            contour.push_back(cv::Point(std::round(pt2_x),std::round(pt2_y)));
            contour.push_back(cv::Point(std::round(pt3_x),std::round(pt3_y)));
            contour.push_back(cv::Point(std::round(pt4_x),std::round(pt4_y)));

            if(!contour.empty()){
                fill_contours.push_back(contour);
            }
            contour.clear();
        }
    }

    // 3) 在 grid 上画满车辆区域，像素值=255
    cv::fillPoly(grid, fill_contours ,cv::Scalar(255));
    fill_contours.clear();

    // 上下左右翻转，使地图坐标和可视化方向一致
    cv::Mat flipped_image;
    cv::flip(grid, flipped_image, -1);

    // 4) 将被标记为 255 的像素对应的 sub_map 置为 100（强占据）
    for(int i = 0; i < flipped_image.rows; i++){
        for(int j = 0; j < flipped_image.cols; j++){
            if(flipped_image.at<uchar>(i,j) == 255){
                sub_map[i*flipped_image.rows +  j] = 100;
            }
        }
    }
}

//------------------------------------------------------------------------------
// read_objCB：激光雷达感知多边形回调（RsPerceptionMsg → sub_map 掩膜）
//------------------------------------------------------------------------------
void read_objCB(perception_ros_msg::RsPerceptionMsg RsPerMsg){
    /*
     * 功能：
     *   - 类似 read_vehCB，但数据来源是 RsPerceptionMsg.lidarframe.attention_objects
     *   - 用多边形顶点（SupInfo.polygon）投影到栅格平面，填充 grid，再映射到 sub_map
     *   - 当前主流程中注释掉订阅（sub_Obj），可根据需要启用
     */

    cav_msgs::VehicleState v_s;
    float utm_x , utm_y;
    bool state = false;
    float heading;

    // 只读查找最近位姿，禁止 pop 破坏历史缓冲
    if (findNearestVehicleState(RsPerMsg.lidarframe.timestamp.data, v_s, 0.1)) {
        utm_x = v_s.x;
        utm_y = v_s.y;
        heading = v_s.heading;
        state = true;
    }

    if(!state){
        return;
    }

    const double map_anchor_x = snapToGridLine(utm_x);
    const double map_anchor_y = snapToGridLine(utm_y);
    float x_div = static_cast<float>(utm_x - map_anchor_x);
    float y_div = static_cast<float>(utm_y - map_anchor_y);

    grid.setTo(cv::Scalar(0));

    perception_ros_msg::Objects Objects;
    perception_ros_msg::SupplementInfo SupInfo;
    std::vector<std::vector<cv::Point>> fill_contours;
    std::vector<cv::Point> contour;

    Objects = RsPerMsg.lidarframe.attention_objects;

    Eigen::Vector3d po;
    for(perception_ros_msg::Object obj : Objects.objects){
        SupInfo = obj.supplementinfo;
        for( auto pt  : SupInfo.polygon){
            Eigen::Vector3d pi(pt.x.data, pt.y.data, pt.z.data);
            transform_rotation(pi, po, heading);
            pi = po;
            transform_translation(pi, po, x_div, y_div);

            // 与 read_vehCB 类似的像素变换
            int pt_x = MAP_SIZE/2 - std::round(po.y()/MAP_RESOLUTION);
            int pt_y = MAP_SIZE/2 - std::round(po.x()/MAP_RESOLUTION);
            if (pt_x < 0 || pt_x >= grid.cols || pt_y < 0 || pt_y >= grid.rows) {
                contour.clear();
                break;
            }
            contour.push_back(cv::Point(std::round(pt_x),std::round(pt_y)));
        }

        if(!contour.empty()){
            fill_contours.push_back(contour);
        }
        contour.clear();
    }

    cv::fillPoly(grid, fill_contours ,cv::Scalar(255));

    cv::Mat flipped_image;
    cv::flip(grid, flipped_image, -1);

    // 将多边形区域对应的 sub_map 赋值为 1（弱占据/标记）
    for(int i = 0; i < flipped_image.rows; i++){
        for(int j = 0; j < flipped_image.cols; j++){
            if(flipped_image.at<uchar>(i,j) == 255){
                sub_map[i*flipped_image.rows +  j] = 1;
            }
        }
    }
}

//------------------------------------------------------------------------------
// veh_sub：车辆列表订阅回调（只缓存消息，不做计算）
//------------------------------------------------------------------------------
void veh_sub(const xperception_msgs::ObjectListCombinedConstPtr &ObjLstCom){
    /*
     * 功能：
     *   - 将最新的车辆列表消息缓存到全局 veh_msg
     *   - 设置 veh_state = true，主循环中据此调用 read_vehCB
     */
    veh_msg = *ObjLstCom;
    veh_state = true;
}

//------------------------------------------------------------------------------
// lidar_sub：点云订阅回调（只缓存消息，不做计算）
//------------------------------------------------------------------------------
void lidar_sub(const sensor_msgs::PointCloud2ConstPtr &msg){
    /*
     * 功能：
     *   - 将最新雷达点云缓存到全局 lidar_msg
     *   - 设置 lidar_state = true，主循环中据此调用 lidarmappedCB
     */
    lidar_msg = *msg;
    lidar_state = true;
}

//------------------------------------------------------------------------------
// lidarmappedCB：LiDAR 主处理函数（调用 DRIVABLE_DETECT_MAPPED 全流水线）
//------------------------------------------------------------------------------
void lidarmappedCB(const sensor_msgs::PointCloud2 msg)
{
    /*
     * 功能：
     *   - 将输入点云转换为 PCL 格式，传入 detect_mapped
     *   - 执行完整的可通行区域检测流程：
     *       1) data_read: 绑定输入点云/输出点云/当前位姿
     *       2) filterPC: 预处理（ROI 过滤、移除 NaN 等）
     *       3) ini: 地图滚动/状态初始化/点云旋转平移
     *       4) mapping: 多帧融合（若 N_FRAME > 1）
     *       5) movePC2Grid: 点云投影到栅格数组（grid_array）
     *       6) checkFlatness: PCA / 平坦性分析 / 占据率更新
     *       7) checkHeight: 利用高度差标记非地面栅格
     *       8) make_final_decision: 写 multi_map / 更新 pre_*，并准备 CVaR
     *   - 发布：
     *       * Filter_pcPB(detect_mapped.cloud_prcs)
     *       * Hei_mapPB(detect_mapped.hei_grid)
     *       * grid_map_msgs::GridMap（multi_map）
     */

    TicToc t_whole;
    double t_cur = 0.0;

    ROS_WARN("Multi_map run");

    cloud_mapped_out->clear();

    // 将 sub_map 地址传给 detect_mapped，内部可以当作一个外部先验/接口
    detect_mapped.getGridMapPtr(sub_map);

    // 定位 heading 有约 heading_latency 的计算延迟：位置按 t_lidar 插值，heading 用 yaw_rate 前推
    Eigen::Vector3d lidar_utm_loc = utm_loc;
    float lidar_yaw = yaw;
    double lidar_time = msg.header.stamp.toSec();
    if (lidar_time <= 0.0) {
        lidar_time = timeRtk;
    }
    lidar_time += lidar_time_offset_sec;

    {
        cav_msgs::VehicleState synced;
        double heading_raw = 0.0;
        double yaw_rate_used = 0.0;
        if (!syncPoseForLidar(lidar_time, synced, heading_raw, yaw_rate_used)) {
            ROS_WARN_THROTTLE(1.0,
                "Skip lidar frame: cannot interpolate VehicleState at stamp %.3f "
                "(need bracketing states within %.0f ms / %.0f ms gap).",
                lidar_time,
                LIDAR_POSE_EXTRAP_MAX_DT * 1000.0,
                LIDAR_POSE_BRACKET_MAX_GAP * 1000.0);
            return;
        }
        lidar_utm_loc.x() = synced.x;
        lidar_utm_loc.y() = synced.y;
        lidar_utm_loc.z() = synced.z;
        lidar_yaw = static_cast<float>(synced.heading);
        if (heading_from_gps) {
            ROS_INFO_THROTTLE(1.0,
                "Lidar pose sync [GPS]: heading=%.1f deg (compensated), raw=%.1f deg, "
                "yaw_rate=%.3f rad/s, latency=%.0f ms, frame=%s",
                synced.heading * 180.0 / M_PI,
                heading_raw * 180.0 / M_PI,
                yaw_rate_used,
                heading_latency_sec * 1000.0,
                detect_mapped.lidar_in_body_frame ? "body->ENU" : "ENU+UTM");
        } else {
            ROS_INFO_THROTTLE(1.0,
                "Lidar pose sync [loc]: heading=%.1f deg, t_lidar-aligned, frame=%s",
                synced.heading * 180.0 / M_PI,
                detect_mapped.lidar_in_body_frame ? "body->ENU" : "ENU+UTM");
        }
    }

    static bool fields_logged = false;
    if (!fields_logged) {
        fields_logged = true;
        std::string field_list;
        for (const auto& f : msg.fields) {
            field_list += f.name + "(t" + std::to_string(static_cast<int>(f.datatype)) + ") ";
        }
        ROS_WARN("PointCloud2 fields: %s| point_step=%u", field_list.c_str(), msg.point_step);
    }

    // sensor_msgs → PCL。整帧共用一个 heading 会让快速转向时的墙面摊成扇形，
    // 因此优先按逐点时间戳把点补偿回 lidar_time 对应的雷达系。
    bool deskewed = false;
    if (deskew_enable) {
        // 外参开启时 VehicleState 是车辆中心，雷达在车体系下的位置为 -offset；
        // 外参关闭时位姿即雷达位姿，杠杆臂为 0
        const double lever_x = detect_mapped.apply_lidar_extrinsic
                                   ? -static_cast<double>(detect_mapped.lidar_offset_x) : 0.0;
        const double lever_y = detect_mapped.apply_lidar_extrinsic
                                   ? -static_cast<double>(detect_mapped.lidar_offset_y) : 0.0;
        DeskewInfo info;
        deskewed = deskewCloud(msg, lidar_time, lidar_yaw, lever_x, lever_y, cloud_mapped, info);
        if (deskewed) {
            // dt 区间揭示 header.stamp 的约定：[0,+100ms]=扫描起点打戳，[-100,0]=终点打戳。
            // omega_src=extrap 表示角速度是滞后外推值，此时补偿可能反而放大扇形。
            ROS_INFO_THROTTLE(1.0,
                "Deskew ON: dt=[%.1f, %.1f] ms, yaw_rate=%.3f rad/s (%s), span=%.2f deg, points=%zu",
                info.dt_min_ms, info.dt_max_ms, info.yaw_rate,
                info.bracketed ? "interp" : "EXTRAP",
                info.span_deg, cloud_mapped->points.size());
        } else {
            ROS_WARN_THROTTLE(5.0,
                "Deskew OFF: point cloud has no per-point time field "
                "(timestamp/time/t). Fast turns will smear walls into a fan.");
        }
    }
    if (!deskewed) {
        pcl::fromROSMsg(msg, *cloud_mapped);
    }

    // 绑定输入/输出点云与当前位姿（frame_time = 雷达时刻，与 heading/utm 同源）
    detect_mapped.data_read(cloud_mapped,
                            cloud_mapped_out,
                            lidar_utm_loc,
                            lidar_yaw,
                            lidar_time);

    // 点云预处理（ROI 剪裁、距离/高度过滤、体素降采样）
    detect_mapped.filterPC(X_low,
                           X_high,
                           Y_low,
                           Y_high,
                           Z_thre,
                           RANGE,
                           VOXEL_SIZE);

    // 维护滚动栅格地图，并将当前点云旋转/平移到 local grid 坐标
    detect_mapped.ini();

    // 多帧映射融合（如果 N_FRAME > 1 有效）
    detect_mapped.mapping(N_FRAME);

    // 点云 → 栅格（grid_array）
    detect_mapped.movePC2Grid();

    // 当前版本中 checkUnocclusion 被注释掉，未启用
    // detect_mapped.checkUnocclusion();

    // [已注释] 原有可通过性计算函数，由 compute_drivable_passability 替代
    // detect_mapped.checkFlatness();
    // detect_mapped.checkHeight();
    // detect_mapped.make_final_decision();

    // 新的可通过性评价函数：基于点云分析计算 driveable_value / driveable_index
    detect_mapped.compute_drivable_passability();

    // 发布过滤后点云（用于可视化处理后的 LiDAR）
    Filter_pcPB(detect_mapped.cloud_prcs);

    // 发布 hei_grid（高度图）
    Hei_mapPB(detect_mapped.hei_grid);

    // 发布 multi_layer grid_map（包括 elevation / slope / step / collision / CVaR 等）
    grid_map_msgs::GridMap message;
    grid_map::GridMapRosConverter::toMessage(multi_map, message);
    pub_MultiMap.publish(message);

    printf("using mapped frame, time %f ms *************\n", t_whole.toc());
    if(t_whole.toc() > 100)
        ROS_WARN("scan registration process over 100ms");
}

//------------------------------------------------------------------------------
// main：ROS 节点入口（drivableArea）
//------------------------------------------------------------------------------
int main(int argc, char **argv)
{
    /*
     * 功能：
     *   - 初始化 ROS 节点 /drivableArea
     *   - 加载参数：
     *       * map_size / grid_size / down_sample / mapping_frame_num ...
     *   - 初始化 sub_map / inx_set / detect_mapped 内部地图尺寸
     *   - 建立订阅关系：
     *       * /vehicle/vehicle_state        → read_stateCB
     *       * /rslidar_points               → lidar_sub
     *       * /cav_vehicle_list             → veh_sub
     *       * （可选）/percept_topic        → read_objCB（当前注释）
     *   - 建立发布器：
     *       * /drivable/occ_map, /drivable/Hei_map,
     *         /drivable/filtered_point_cloud, /cav_local_map, /grid_map
     *   - 主循环：
     *       * ros::spinOnce()
     *       * 若 lidar_state → lidarmappedCB(lidar_msg)
     *       * 若 veh_state   → read_vehCB(veh_msg)
     *       * Loc_mapPB(sub_map), Occ_mapPB(sub_map)
     *       * 清零 veh_state / lidar_state
     */

    printf("enter drivable area\n");
    ros::init(argc, argv, "drivableArea");
    ros::NodeHandle nh;

    nav_msgs::Odometry::ConstPtr heading_msgs = nullptr;
    tf::TransformBroadcaster static_broadcaster;
    tf::Transform transform;

    //---------------------- 参数加载 ----------------------//
    nh.param<int>("map_size", MAP_SIZE, 505);
    nh.param<float>("grid_size", MAP_RESOLUTION, 1.0);
    nh.param<float>("down_sample", VOXEL_SIZE, 0.2);
    nh.param<int>("mapping_frame_num", N_FRAME, 1);
    nh.param<float>("X_LOW",  X_low,  1.0);
    nh.param<float>("Y_LOW",  Y_low,  0.5);
    nh.param<float>("X_HIGH", X_high, 1.0);
    nh.param<float>("Y_HIGH", Y_high, 0.5);
    nh.param<float>("RANGE",  RANGE,  30.0);
    nh.param<float>("Z_THD",  Z_thre, 0.15);
    float lidar_offset_x = -0.6f;
    float lidar_offset_y = 0.0f;
    bool lidar_in_body_frame = true;
    nh.param<float>("lidar_offset_x", lidar_offset_x, -0.6f);
    nh.param<float>("lidar_offset_y", lidar_offset_y, 0.0f);
    // true:  /rslidar_points 为自车坐标，用 heading 旋到 ENU 再输出 UTM（默认）
    // false: 点云已是相对车辆 ENU
    nh.param<bool>("lidar_in_body_frame", lidar_in_body_frame, true);
    double obstacle_ttl_sec = 5.0;
    nh.param<double>("obstacle_ttl_sec", obstacle_ttl_sec, 5.0);
    nh.param<double>("heading_latency_sec", heading_latency_sec, 0.06);
    nh.param<bool>("heading_from_gps", heading_from_gps, false);
    // 位姿为车辆中心时需要外参（实车雷达在中心前方 0.6m）；位姿即雷达位姿时置 false
    bool apply_lidar_extrinsic = true;
    nh.param<bool>("apply_lidar_extrinsic", apply_lidar_extrinsic, true);
    nh.param<bool>("deskew_enable", deskew_enable, true);
    nh.param<double>("lidar_time_offset_sec", lidar_time_offset_sec, 0.0);
    // 可切到 /lio_sam/deskew/cloud_deskewed 用 SLAM 已去畸变的点云做对照
    std::string lidar_topic = "/rslidar_points";
    nh.param<std::string>("lidar_topic", lidar_topic, std::string("/rslidar_points"));

    //---------------------- 内部缓存初始化 ----------------------//
    sub_map = (float*)malloc(MAP_SIZE * MAP_SIZE * sizeof(float));
    inx_set = (float*)malloc(MAP_SIZE * MAP_SIZE * sizeof(float));

    // 初始 sub_map 全部设为 50（未知），inx_set 设为 0
    std::fill(sub_map, sub_map + MAP_SIZE * MAP_SIZE, 50.0f);
    std::fill(inx_set, inx_set + MAP_SIZE * MAP_SIZE, 0.0f);

    // 初始化 detect_mapped 的栅格地图尺寸等内部参数
    detect_mapped.set_map(MAP_SIZE, MAP_RESOLUTION);
    detect_mapped.set_lidar_offset(lidar_offset_x, lidar_offset_y);
    detect_mapped.set_apply_lidar_extrinsic(apply_lidar_extrinsic);
    detect_mapped.set_obstacle_ttl_sec(obstacle_ttl_sec);
    detect_mapped.set_lidar_frame_mode(lidar_in_body_frame);
    ROS_WARN("lidar_in_body_frame=%s (true=ego body -> ENU/UTM with heading)",
             lidar_in_body_frame ? "true" : "false");
    ROS_WARN("heading_from_gps=%s (false=loc/lidar same stamp, no delay; true=GPS+yaw_rate latency comp %.0f ms)",
             heading_from_gps ? "true" : "false",
             heading_latency_sec * 1000.0);
    ROS_WARN("apply_lidar_extrinsic=%s, lidar->body offset(%.2f, %.2f)",
             apply_lidar_extrinsic ? "true" : "false", lidar_offset_x, lidar_offset_y);
    ROS_WARN("lidar_topic=%s", lidar_topic.c_str());
    ROS_WARN("deskew_enable=%s, lidar_time_offset_sec=%.3f",
             deskew_enable ? "true" : "false", lidar_time_offset_sec);
    std::cout << "main function " << detect_mapped.slope_map[MAP_SIZE * MAP_SIZE / 2] << std::endl;

    // OpenCV grid 图像（单通道 8-bit），用于绘制车辆/物体掩膜
    int type = CV_8UC1;
    grid.create(MAP_SIZE, MAP_SIZE, type);

    //---------------------- 订阅器 ----------------------//

    ros::Rate loop_rate(10);

    // 车辆状态（UTM+姿态）订阅
    ros::Subscriber sub_Utm = nh.subscribe<cav_msgs::VehicleState>(
        "/vehicle/vehicle_state", 100, read_stateCB);

    // RsPerceptionMsg 感知多边形（当前注释，可按需启用）
    // ros::Subscriber sub_Obj = nh.subscribe<perception_ros_msg::RsPerceptionMsg>(
    //     "/percept_topic", 100, read_objCB);

    // LiDAR 点云订阅
    ros::Subscriber subAllCloud = nh.subscribe<sensor_msgs::PointCloud2>(
        lidar_topic, 100, lidar_sub);

    // 车辆检测结果（ObjectListCombined）订阅
    ros::Subscriber sub_Veh = nh.subscribe<xperception_msgs::ObjectListCombined>(
        "/cav_vehicle_list", 100, veh_sub);

    //---------------------- 发布器 ----------------------//

    pubOccmap   = nh.advertise<nav_msgs::OccupancyGrid>("/drivable/occ_map", 100);
    pubGround   = nh.advertise<sensor_msgs::PointCloud2>("/drivable/ground_point_cloud", 100);
    pubHeimap   = nh.advertise<nav_msgs::OccupancyGrid>("/drivable/Hei_map", 100);
    pub_LocalMap= nh.advertise<LocalMap_msgs::LocalMap>("/cav_local_map", 100);
    pubFiltered = nh.advertise<sensor_msgs::PointCloud2>("/drivable/filtered_point_cloud", 100);
    pub_MultiMap= nh.advertise<grid_map_msgs::GridMap>("grid_map", 100, true);

    //---------------------- 主循环 ----------------------//
    while(ros::ok()){
        // 一次 spin 处理所有回调
        ros::spinOnce();

        // 有新点云就跑一次检测流程
        if(lidar_state)
            lidarmappedCB(lidar_msg);

        // 有新的车辆检测就更新 sub_map 的动态障碍物掩膜
        if(veh_state)
            read_vehCB(veh_msg);

        // 每次循环都基于最新 sub_map 发布 LocalMap 和 OccMap
        Loc_mapPB(sub_map);
        Occ_mapPB(sub_map);

        // 标志位复位
        veh_state = false;
        lidar_state = false;

        loop_rate.sleep();
    }

    return 0;
}