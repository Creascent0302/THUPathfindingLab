#include <iostream>
#include <limits>
#include "ros/ros.h"
#include "drivable_detect.h"
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <grid_map_msgs/GridMap.h>
#include <fstream>
#include <stdio.h>
#include "CVaRcal_cuda.h"

//---------------------- 一些辅助数学函数（正态分布 / erf 逆）----------------------//

// 正态分布的 PDF（均值 0，方差 1）
inline float normalPDF(float x) {
    return std::exp(-0.5f * x * x) / std::sqrt(2.0f * M_PI);
}

// 简单近似 inverse erf，用于把置信度 alpha 转成标准高斯分位数
inline float approx_erfinv(float x) {
    float a = 0.147;
    float ln = std::log(1 - x * x);
    float t1 = 2 / (M_PI * a) + ln / 2.0;
    float t2 = ln / a;
    return std::copysign(std::sqrt(std::sqrt(t1 * t1 - t2) - t1), x);
}

//---------------------- 全局栅格地图（multi_map）定义 ----------------------//
// multi_map 是 grid_map::GridMap，用来承载多层栅格信息：
// elevation / unocc / hei_diff / mean_x / mean_y / mse_cover / slope / step / collision / CVaR / drivable
grid_map::GridMap multi_map({ "elevation","unocc","hei_diff","mean_x","mean_y",
                              "mse_cover", "slope","step","collision","CVaR","drivable"});

//------------------------------------------------------------------------------
//                          DRIVABLE_DETECT_MAPPED 类实现
//------------------------------------------------------------------------------

DRIVABLE_DETECT_MAPPED::DRIVABLE_DETECT_MAPPED()
{
    /*
     * 构造函数：
     * - 初始化内部点云指针
     * - 为每个栅格单元分配 GRID_INFO 对象
     * - 预申请激光雷达线束点云容器（laserCloudScans）
     */
    cloud_prcs.reset(new pcl::PointCloud<PointType>);   // 处理后的点云（过滤、坐标变换等）
    cloud_in.reset(new pcl::PointCloud<PointType>);     // 输入点云（lidar）
    cloud_out.reset(new pcl::PointCloud<PointType>);    // 输出的可行驶区域点云（未使用或可作扩展）
    cloud_frames.reset(new pcl::PointCloud<PointType>); // 多帧融合点云缓存

    // 为栅格数组分配 GRID_INFO 对象
    for (int i = 0; i < ARRAY_SIZE; i++){
        grid_array.push_back(new GRID_INFO());
    }

    // 预留 32 条线束的点云容器（目前主体逻辑未使用，保留扩展能力）
    for(int i = 0; i < 32; i++){
        pcl::PointCloud<PointType>::Ptr  pc(new pcl::PointCloud<PointType>);
        laserCloudScans.push_back(*pc);
    }
}

//------------------------------------------------------------------------------
// 坐标变换：平移
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::transform_translation(PointType const *const pi,
                                                    PointType *const po,
                                                    float x_div, float y_div, float z_div)
{
    /*
     * 旋转到 ENU 对齐后，加上 UTM 相对栅格锚点的余量，映射到 local grid 坐标系。
     * 平移必须沿 ENU 两轴对称施加；此前在 x 上硬减 0.2 会在非东向行驶时
     * 投影到车体左右方向，造成“右侧更近、左侧更远”的假不对称。
     */
    po->x = pi->x + x_div;
    po->y = pi->y + y_div;
    (void)z_div;
}

//------------------------------------------------------------------------------
// 坐标变换：旋转（根据当前 heading）
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::transform_rotation(PointType const *const pi,
                                                PointType *const po)
{
    /*
     * 自车坐标 → ENU：heading(东偏北) + atan2(y,x)
     * 之后加 UTM 锚点余量；Loc_mapPB 的 ct = anchor + local 为 UTM 绝对坐标。
     */
    Eigen::Vector3d point(pi->x, pi->y, pi->z);
    float distance = std::sqrt(std::pow(pi->x,2) + std::pow(pi->y,2));
    float target_angle = atan2(pi->y, pi->x);
    float yaw_target = heading + target_angle;

    po->x = distance * cos(yaw_target);
    po->y = distance * sin(yaw_target);
    po->z = point.z();
    po->intensity = frameCount;
}

//------------------------------------------------------------------------------
// 数据读入：绑定输入 / 输出点云以及当前位姿
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::data_read(pcl::PointCloud<PointType>::Ptr _cloud_in,
                                       pcl::PointCloud<PointType>::Ptr _cloud_out,
                                       Eigen::Vector3d _utm_loc,
                                       float _heading,
                                       double _frame_time)
{
    /*
     * dr_detect.cpp 中 lidarmappedCB() 会调用此函数：
     *   - cloud_in  指向当前雷达帧
     *   - cloud_out 指向输出点云（由上层创建）
     *   - utm_loc   为当前 UTM 坐标
     *   - heading   当前车头朝向
     */
    cloud_in = _cloud_in;
    cloud_out = _cloud_out;
    utm_loc = _utm_loc;
    heading = _heading;
    frame_time = _frame_time;
}

//------------------------------------------------------------------------------
// 点云预处理：ROI 剪裁、距离筛选、体素降采样等
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::filterPC(float x_low,
                                      float x_high,
                                      float y_low,
                                      float y_high,
                                      float z_th,
                                      float far_thres,
                                      float voxel)
{
    /*
     * 功能：
     *   - 移除 NaN 点
     *   - 基于前后/左右范围过滤过远、过近的点（包括车身附近遮挡部分）
     *   - 不做严格高度滤除（高点后续可能用于其它分析）
     *   - 若 cloud_frames 非空，对过去多帧点云做一次体素滤波
     *   - 统计 near_ground_height 与 min_ground_height，用于后续地面估计
     */
    float dist;
    z_thred = z_th;
    std::vector<int> indices;
    cloud_prcs->clear();

    // 对多帧累积点云做体素滤波（可选）
    if(cloud_frames->size() != 0){
        pass_vox.setLeafSize(voxel,voxel,voxel);
        pass_vox.setInputCloud(cloud_frames);
        pass_vox.filter(*cloud_frames);
    }

    // 移除 NaN 点
    pcl::removeNaNFromPointCloud(*cloud_in, *cloud_in, indices);

    near_ground_height = 0;
    min_ground_height = std::numeric_limits<float>::max();
    int pt_num = 0;

    // ENU 点云做车体 ROI 时，先转到车体坐标（x 前 y 左）再判断
    const float c = std::cos(heading);
    const float s = std::sin(heading);

    // 主过滤循环
    for (size_t i = 0; i < cloud_in->points.size(); ++i)
    {
        auto pt = &cloud_in->points[i];
        float bx = pt->x;
        float by = pt->y;
        if (!lidar_in_body_frame) {
            // ENU (E,N) → body (forward, left): R(-heading)
            bx =  c * pt->x + s * pt->y;
            by = -s * pt->x + c * pt->y;
        }
        dist = bx * bx + by * by;

        // 过滤规则（始终按车体前后左右）：
        //   - 超出视距 RANGE（far_thres）或在车身附近的盲区
        //   - z > 2.0
        //   - x,y 在车辆周围某矩形区域内（车身附近）
        if ((bx > far_thres ||
            bx < -far_thres/4 ||
            by > far_thres/2 ||
            by < -far_thres/2) ||
            pt->z > 2.0 ||
            (bx < x_high &&
            bx > -x_low &&
            by < y_high &&
            by > -y_low))
        {
                // 丢弃该点
                continue;
        }
        else {
            // 更新整体最低地面高度 min_ground_height
            if( pt->z < min_ground_height){
                min_ground_height = pt->z;
            }
            // 在车前方一小块区域统计近地面的高度，用于近似当前路面高度
            if( bx < x_high + 0.50 &&
                bx > x_high  &&
                by < y_high  &&
                by > -y_low ){
                near_ground_height += pt->z;
                pt_num++;
            }
            // 将有效点加入 cloud_prcs（保持原始坐标系，ENU 或 body，由 ini 统一落到 UTM 栅格）
            cloud_prcs->push_back(*pt);
        }
    }

    // 若统计数不为 0，则计算近地面平均高度；否则沿用上一帧，避免 NaN 进入地图初始化
    if (pt_num > 0) {
        near_ground_height = near_ground_height / pt_num;
    } else if (std::isfinite(pre_near_ground_height)) {
        near_ground_height = pre_near_ground_height;
    } else {
        near_ground_height = 0.0f;
    }

    if (!std::isfinite(min_ground_height) || min_ground_height == std::numeric_limits<float>::max()) {
        min_ground_height = std::isfinite(pre_min_ground_height) ? pre_min_ground_height : near_ground_height;
    }
    // 也可以固定为某个经验高度，例如 -1.06，当前使用动态估计
}

//------------------------------------------------------------------------------
// 帧初始化 / 滚动栅格维护 / 点云坐标对齐
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::ini(){
    /*
     * 功能：
     *   - 清空当前帧的栅格状态集合（available_grid, feasible_grid 等）
     *   - 根据 UTM 坐标变化决定是否需要移位滚动栅格
     *   - 把上一帧的 occ / 高度 / slope 等 map 数据拷贝或平移到当前帧
     *   - 对 cloud_prcs 里的点进行旋转 + 平移，映射到当前 local grid 坐标系
     */

    // 清空栅格索引集合
    available_grid.clear();
    feasible_grid.clear();
    non_flat_grid.clear();
    non_ground_grid.clear();

    // CVaR 层先清零，后续由 compute_cvar 填充
    multi_map["CVaR"].setZero();

    auto snap_to_grid_line = [this](double v) -> double {
        return std::floor(v / static_cast<double>(GRID_LEN)) * static_cast<double>(GRID_LEN);
    };

    const double cur_anchor_x = snap_to_grid_line(utm_loc.x());
    const double cur_anchor_y = snap_to_grid_line(utm_loc.y());
    grid_anchor_x = cur_anchor_x;
    grid_anchor_y = cur_anchor_y;

    // 航向由 VehicleState.heading 经时间对齐后传入。
    // 栅格内容是 ENU：静态墙在 UTM 中方向应固定。但实车 yaw_rate 常为 0、
    // 航向与点云仍可能有数度误差；若继续叠加障碍记忆，就会出现“竖墙+斜墙”。
    // 因此航向变化超过阈值时，切断历史障碍/可通行记忆，只信本帧点云。
    large_heading_change = false;
    float delta_heading = 0.0f;
    if (map_history_initialized) {
        delta_heading = heading - pre_heading;
        while (delta_heading > static_cast<float>(M_PI)) delta_heading -= 2.0f * static_cast<float>(M_PI);
        while (delta_heading < -static_cast<float>(M_PI)) delta_heading += 2.0f * static_cast<float>(M_PI);
        // ~3°/帧：对应中等转向；再叠记忆就会扩张
        const float HEADING_CLEAR_RAD = 3.0f * static_cast<float>(M_PI) / 180.0f;
        if (std::fabs(delta_heading) > HEADING_CLEAR_RAD) {
            large_heading_change = true;
            ROS_WARN_THROTTLE(0.3,
                "Heading delta=%.2f deg (pre=%.2f -> cur=%.2f): clear obstacle memory to avoid tilted-wall smear",
                delta_heading * 180.0f / static_cast<float>(M_PI),
                pre_heading * 180.0f / static_cast<float>(M_PI),
                heading * 180.0f / static_cast<float>(M_PI));
        }
    }

    // 根据 GRID_LEN 吸附后的全局栅格锚点计算整格平移量。
    // 点云和历史地图必须使用同一个锚点，否则会出现 0.02m 定位抖动引起多格跳变/拖影。
    const bool has_map_history = map_history_initialized;
    int shift_row = 0;
    int shift_col = 0;
    bool change_coordinate = false;

    if (has_map_history) {
        const double pre_anchor_x = snap_to_grid_line(pre_utm_loc.x());
        const double pre_anchor_y = snap_to_grid_line(pre_utm_loc.y());
        shift_row = static_cast<int>(std::llround((cur_anchor_x - pre_anchor_x) / static_cast<double>(GRID_LEN)));
        shift_col = static_cast<int>(std::llround((cur_anchor_y - pre_anchor_y) / static_cast<double>(GRID_LEN)));
        change_coordinate = (shift_row != 0 || shift_col != 0);
    }

    // 初始化每个栅格单元，并根据 UTM 位移平移上一帧 pre_* 到当前帧
    #pragma omp parallel for
    for (int i = 0; i < ARRAY_SIZE; ++i){
        grid_array[i]->ini();                          // 重置 GRID_INFO 内部状态
        grid_array[i]->avage_z = near_ground_height;   // 初始平均高度设为 near_ground_height

        if (!has_map_history) {
            continue;
        }

        if (change_coordinate) {
            // 车辆移动后：当前格 i 的数据来自上一帧中“沿运动反方向”偏移的源格
            const int row = i / ARRAY_NX;
            const int col = i % ARRAY_NX;
            const int src_row = row + shift_row;
            const int src_col = col + shift_col;

            if (src_col >= 0 && src_col < ARRAY_NX && src_row >= 0 && src_row < ARRAY_NY) {
                const int src_i = src_col + src_row * ARRAY_NX;
                *(occ_grid+i)              = *(pre_occ_grid              + src_i);
                *(hei_grid+i)              = *(pre_hei_grid              + src_i);
                *(hei_diff_grid+i)         = *(pre_hei_diff_grid         + src_i);
                *(unocc_grid+i)            = *(pre_unocc_grid            + src_i);
                *(mean_xy+i)               = *(pre_mean_xy               + src_i);
                *(mse_cover+i)             = *(pre_mse_cover             + src_i);
                *(slope_map+i)             = *(pre_slope_map             + src_i);
                *(rough_map+i)             = *(pre_rough_map             + src_i);
                *(step_map+i)              = *(pre_step_map              + src_i);
                if (large_heading_change) {
                    // 转向：不继承可通行/障碍记忆，避免斜墙与竖墙叠加
                    *(drivable_value_grid+i) = 0.5f;
                    *(obstacle_stamp_grid+i) = 0.0;
                    *(obstacle_value_grid+i) = 0.0f;
                } else {
                    *(drivable_value_grid+i)   = *(pre_drivable_value_grid   + src_i);
                    *(obstacle_stamp_grid+i)   = *(pre_obstacle_stamp_grid   + src_i);
                    *(obstacle_value_grid+i)   = *(pre_obstacle_value_grid   + src_i);
                }
            } else {
                *(occ_grid+i)              = 50.0f;
                *(hei_grid+i)              = 0.0f;
                *(hei_diff_grid+i)         = 0.0f;
                *(unocc_grid+i)            = 0.0f;
                *(mean_xy+i)               = std::pair<float,float>{0.0f, 0.0f};
                *(mse_cover+i)             = 0.0f;
                *(slope_map+i)             = 0.0f;
                *(rough_map+i)             = 1.0f;
                *(step_map+i)              = 1.0f;
                *(drivable_value_grid+i)   = 0.5f;
                *(obstacle_stamp_grid+i)   = 0.0;
                *(obstacle_value_grid+i)   = 0.0f;
            }
        } else {
            *(occ_grid+i)              = *(pre_occ_grid              + i);
            *(hei_grid+i)              = *(pre_hei_grid              + i);
            *(hei_diff_grid+i)         = *(pre_hei_diff_grid         + i);
            *(unocc_grid+i)            = *(pre_unocc_grid            + i);
            *(mean_xy+i)               = *(pre_mean_xy               + i);
            *(mse_cover+i)             = *(pre_mse_cover             + i);
            *(slope_map+i)             = *(pre_slope_map             + i);
            if (large_heading_change) {
                *(drivable_value_grid+i) = 0.5f;
                *(obstacle_stamp_grid+i) = 0.0;
                *(obstacle_value_grid+i) = 0.0f;
            } else {
                *(drivable_value_grid+i)   = *(pre_drivable_value_grid   + i);
                *(obstacle_stamp_grid+i)   = *(pre_obstacle_stamp_grid   + i);
                *(obstacle_value_grid+i)   = *(pre_obstacle_value_grid   + i);
            }
        }
    }

    // 将滚动后的 drivable 同步到 multi_map，避免 Pass4 读到未平移的旧全局层
    if (has_map_history) {
        auto& drv_layer = multi_map.get("drivable");
        #pragma omp parallel for
        for (int i = 0; i < ARRAY_SIZE; ++i) {
            const int r = i / ARRAY_NX;
            const int c = i % ARRAY_NX;
            const int grid_i = (ARRAY_NY - 1 - r) * ARRAY_NX + c;
            drv_layer.data()[grid_i] = *(drivable_value_grid + i);
        }
    }

    // 将当前帧过滤后的点云 cloud_prcs 转换到 local grid 坐标系（先旋转后平移）
    PointType * pt;
    long pc_size = cloud_prcs->points.size();
    float x_div = static_cast<float>(utm_loc.x() - cur_anchor_x);
    float y_div = static_cast<float>(utm_loc.y() - cur_anchor_y);
    float z_div = 0.0;

    for (long i = 0; i < pc_size; ++i)
    {
        pt = &cloud_prcs->points[i];
        pt->intensity = INTENSITY_DRIVABLE;  // 先标记为“可行驶”强度标签

        if (lidar_in_body_frame) {
            // 自车坐标 → ENU → UTM局部栅格
            // 1) 外参：雷达到车辆中心（自车系）
            // 2) heading: 自车系旋到 ENU（东/北）
            // 3) + (utm - anchor): 落到 UTM 吸附锚点下的局部坐标，供 xy2IJ 落格
            // 输出 Loc_mapPB: ct = anchor + local = UTM 绝对坐标
            pt->x -= lidar_offset_x;
            pt->y -= lidar_offset_y;
            transform_rotation(pt, pt);
            transform_translation(pt, pt, x_div, y_div, z_div);
        } else {
            // 兼容：点云已是相对车辆 ENU 时，不再乘 heading，只补偿外参并平移到 UTM
            const float c = std::cos(heading);
            const float s = std::sin(heading);
            const float off_e = c * lidar_offset_x - s * lidar_offset_y;
            const float off_n = s * lidar_offset_x + c * lidar_offset_y;
            pt->x = pt->x - off_e + x_div;
            pt->y = pt->y - off_n + y_div;
            pt->intensity = frameCount;
        }
    }

    // 计算当前栅格中心索引
    int I = 0 ,J = 0;
    xy2IJ(x_div , y_div , I , J);
    int center = I* ARRAY_NX + J;
}

//------------------------------------------------------------------------------
// 多帧融合 / 点云滑窗管理
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::mapping(int frame_num){
    /*
     * 功能：
     *   - 使用 intensity 中的帧编号，在 cloud_frames 中利用 PCL PassThrough 把旧帧滤掉
     *   - 再将当前 cloud_prcs 叠加到 cloud_frames，实现简单的多帧融合
     *   - 通过 frameCount 计数器控制滑窗（frameCount % frame_num）
     */
    if(frame_num == 1){
        // N_FRAME = 1 时，不进行多帧融合，直接返回
        return;
    }
    else{
        // 去除过旧帧（intensity 不在当前 frameCount 的点）
        pass.setFilterFieldName("intensity");
        pass.setFilterLimits(-0.5+frameCount,0.5+frameCount);
        pass.setInputCloud(cloud_frames);
        pass.setNegative(true);
        pass.filter(*cloud_frames);

        auto snap_to_grid_line = [this](double v) -> double {
            return std::floor(v / static_cast<double>(GRID_LEN)) * static_cast<double>(GRID_LEN);
        };

        // 历史点云与地图使用同一个 GRID_LEN 锚点；这里只做纯平移，不能复用带传感器偏置的 transform_translation。
        const float x_shift = -static_cast<float>(snap_to_grid_line(utm_loc.x()) - snap_to_grid_line(pre_utm_loc.x()));
        const float y_shift = -static_cast<float>(snap_to_grid_line(utm_loc.y()) - snap_to_grid_line(pre_utm_loc.y()));
        const float z_shift = -static_cast<float>(utm_loc.z() - pre_utm_loc.z());
        long pc_size = cloud_frames->points.size();
        PointType * pt;

        #pragma omp parallel for
        for (long i = 0; i < pc_size; ++i)
        {
            pt = &cloud_frames->points[i];
            pt->x += x_shift;
            pt->y += y_shift;
            pt->z += z_shift;
        }

        // 将当前帧 cloud_prcs 累加到 cloud_frames，实现时序融合
        *cloud_prcs += *cloud_frames;

        // 更新 frameCount，控制滑动窗口生效
        frameCount++;
        int tem_count = frameCount;
        frameCount = frameCount % frame_num;
        if(frameCount != tem_count){
            // frameCount 发生回绕，说明窗口已满，之后会开始“丢弃最旧帧”
            start_desample = true;
        }
    }
    return;
}

//------------------------------------------------------------------------------
// 将点云分配到栅格（grid_array），为后续 PCA/平坦性分析做准备
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::movePC2Grid(){
    /*
     * 功能：
     *   - 清理 grid_array 内每个 grid 的点云（在 ini() 中已调用 grid_array[i]->ini()）
     *   - 遍历 cloud_prcs 中的每个点：
     *       * 利用 xy2IJ 计算其在栅格中的索引 (grid_I, grid_J)
     *       * 丢弃高度过高的点 (z >= 4)
     *       * 添加到对应栅格的 grid_array[index]->pc_ptr
     */
    int grid_I, grid_J, index;
    PointType pt;
    int Ring = 32;   // 预留线束数量，当前主体逻辑未使用
    long pc_size = cloud_prcs->points.size();

    for (long i = 0; i < pc_size; ++i)
    {
        pt = cloud_prcs->points[i];
        int num_ring = i % cloud_prcs->width;
        pt.intensity = num_ring;      // 这里重写 intensity 为线束编号（可用于边缘/曲率分析）

        // 高度过高的点直接丢弃
        if (pt.z >= 4) continue;

        // 根据 x,y 映射到栅格坐标
        if (xy2IJ(pt.x, pt.y, grid_I, grid_J))
        {
            index = grid_I*ARRAY_NY + grid_J;
            pt.intensity = INTENSITY_DRIVABLE;
            grid_array[index]->pc_ptr->push_back(pt);
        }
    }
}

//------------------------------------------------------------------------------
// checkFlatness：核心几何分析，判断地面/非地面，更新栅格属性和占据概率
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::checkFlatness()
{
    /*
     * 核心步骤（对每个栅格 i）：
     *   1) 如果点数不足：用已有高度信息和 log-odds 轻微更新 occ_grid，降低可信度
     *   2) 如果点数足够：
     *      - 统计点云高度和极值 z_min / z_max
     *      - 若高度差 > 0.15：认为是非地面，加入 non_ground_grid / non_flat_grid
     *      - 否则：
     *          * 调用 PCL 的 computeMeanAndCovarianceMatrix + eigen33 做 PCA
     *          * 提取法向量 normal
     *          * 计算 slope_map（基于 normal.z）
     *          * 计算 rough_map（基于点到平面距离的 RMS）
     *          * 根据 grid_state（这里固定为 -1，视为地面）更新 occ_grid 的 log-odds
     *          * 根据地面/障碍/草地给点云 intensity 上色
     */

    Eigen::Vector4d centroid;               // 质心
    Eigen::Matrix3d covariance_matrix;      // 协方差矩阵
    Eigen::Matrix3d eigenVectors;           // 特征向量
    Eigen::Vector3d eigenValues;            // 特征值
    Eigen::Vector3d::Index minRow, minCol;  // 最小特征值索引
    Eigen::Vector3d::Index maxRow, maxCol;

    float grass_lmt, obs_lmt;

    #pragma omp parallel for
    for (int i = 0; i < ARRAY_SIZE; ++i)
    {
        int grid_i = (ARRAY_NY - 1 - (i / ARRAY_NX)) * ARRAY_NX + (i % ARRAY_NX);
        auto grid = grid_array[i];

        float occ_pred, pre_pred, ori_p, occ;
        PointType * pt;
        grid->avage_z = 0;
        grid->avage_x = 0;
        grid->avage_y = 0;
        int Nj = grid->pc_ptr->size();

        // 如果该栅格点数不足（<5），视为观测不足，只做轻微的占据概率更新
        if (Nj < 5){
            grid->feasible = false;

            if(*(hei_grid+i) != 0.0){
                // step_map 用高度和近地面高度的差异构造（这里给出示例，实际公式可以调整）
                *(step_map + i) = static_cast<float>(
                    std::min(static_cast<float>(
                        1-abs(2*( *(hei_grid+i) )-  min_ground_height -near_ground_height)/(2*0.3)),
                        1.0f));
            }

            // 使用 log-odds 更新 occ_grid，使占据概率略微向 0.3 偏移（偏向可行驶）
            occ_pred = 0.3;
            if(*(occ_grid+i) == 100){
                *(occ_grid+i) = 99;
            }
            if(*(occ_grid+i) == 0){
                *(occ_grid+i) = 1;
            }
            pre_pred = std::log((100- *(occ_grid+i)) / *(occ_grid+i));
            occ = pre_pred + std::log(occ_pred/(1-occ_pred));
            *(occ_grid+i) =100 - 100/(1+std::exp(-occ));
            continue;
        }

        // 有足够点：统计平均高度/坐标，记录最小/最大高度
        grid->feasible = true;
        feasible_grid.insert(i);
        grid->avage_z = 0;

        for (int j = 0; j < Nj; ++j)
        {
            pt = &grid->pc_ptr->points[j];
            grid->avage_z += pt->z;
            grid->avage_y += pt->y;
            grid->avage_x += pt->x;
            grid->z_min = MIN(grid->z_min, pt->z);
            grid->z_max = MAX(grid->z_max, pt->z);
        }

        grid->avage_z /= Nj;
        grid->avage_y /= Nj;
        grid->avage_x /= Nj;

        // 记录每个栅格的最低高度和高度差
        *(hei_grid+i)      = grid->z_min;
        *(hei_diff_grid+i) = grid->z_max - grid->z_min;

        // 高度差过大：直接视为非地面，加入 non_ground_grid / non_flat_grid
        if(*(hei_diff_grid+i) > 0.15){
            non_ground_grid.insert(i);
            non_flat_grid.insert(i);
            continue;
        }

        // 对该栅格点云做 PCA（均值 + 协方差）
        pcl::computeMeanAndCovarianceMatrix(*grid_array[i]->pc_ptr, covariance_matrix, centroid);

        // 求特征值 / 特征向量
        pcl::eigen33(covariance_matrix, eigenVectors, eigenValues);

        eigenValues.minCoeff(&minRow, &minCol);
        eigenValues.maxCoeff(&maxRow, &maxCol);

        // Q 为最小特征值占比，可作为平面度指标（当前未直接使用）
        grid->Q = eigenValues[minRow]/(
            eigenValues[minRow] + eigenValues[maxRow] +
            eigenValues[3-maxRow-minRow]);

        float vertaility = 1 - std::abs(eigenVectors.col(minRow).z());

        // 法向量
        Eigen::Vector3d normal = eigenVectors.col(minRow);
        double D = -normal.dot(centroid.head<3>());  // 平面方程 AX+BY+CZ+D=0 的 D

        // 计算 roughness：点到平面距离的 RMS（主要用 z 分量）
        float d_temp = 0.0f;
        float d_sum  = 0.0f;
        grid->d_avg = 0.0f;

        for (int j = 0; j < Nj; ++j)
        {
            pt = &grid->pc_ptr->points[j];
            // 这里简单用 normal.z * |z - centroid.z| 作为近似距离
            d_temp = normal.z()*ABS(pt->z-centroid.z());
            d_sum += std::pow(d_temp,2);
        }

        grid->d_avg = sqrt(d_sum/(Nj-1));
        // rough_map：将 d_avg 归一化到某个范围，这里用 0.15 的尺度
        *(rough_map + i) =  grid->d_avg/0.15f * 2;

        // slope_map：用法向量 z 分量的夹角粗略表示坡度
        *(slope_map + i) = static_cast<float>(std::acos(std::abs(normal.z())));

        // grid_state: 当前实现中固定为 -1，表示地面
        // 如需引入草地 / 障碍，可用 roughness / slope / Q 等构造分类器
        int grid_state = -1; // 0: grass, 1: obstacle, -1: ground
        grass_lmt = 0.08f;
        obs_lmt   = 0.13f;

        if(grid_state == -1){
            // 地面：给予较低占据先验
            occ_pred = 0.2;     // is ground
            grid->flat = true;
        }
        else if(grid_state == 1){
            // 障碍：给予极高的占据先验
            occ_pred = 0.999;   // is obstacle
            grid->flat = false;
            non_flat_grid.insert(i);
        }
        else{
            // 草地或不确定区域
            grid->flat = false;
            occ_pred = 0.5;     // uncertain
            non_flat_grid.insert(i);
        }

        // 维护 occ_grid 在 (0,100) 范围内
        if(*(occ_grid+i) == 100){
            *(occ_grid+i) = 99;
        }
        if(*(occ_grid+i) == 0){
            *(occ_grid+i) = 1;
        }

        // log-odds 更新 occ_grid
        pre_pred = std::log((100- *(occ_grid+i)) / *(occ_grid+i));
        ori_p    = *(occ_grid+i);
        occ      = pre_pred + std::log(occ_pred/(1-occ_pred));
        *(occ_grid+i) = 100 - 100/(1+std::exp(-occ));

        // 根据 grid_state 给当前栅格内所有点重新赋 intensity，用于可视化：
        //   - DRIVABLE（地面）
        //   - OBSTACLE（障碍）
        //   - GRASS（草地/不确定）
        for (int j = 0; j < Nj; ++j)
        {
            if (grid_state == -1){
                grid->pc_ptr->points[j].intensity = INTENSITY_DRIVABLE;
            }
            else if(grid_state == 1){
                grid->pc_ptr->points[j].intensity = INTENSITY_OBSTACLE;
            }
            else{
                grid->pc_ptr->points[j].intensity = INTENSITY_GRASS;
            }
        }
    }
}

//------------------------------------------------------------------------------
// compute_drivable_passability：多特征可通过性评价函数（稀疏点云“线束间空洞”修复版）
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::compute_drivable_passability(){
    /*
     * 修复目标：
     *   - 远处点云稀疏导致“线束间空洞”栅格 Nj < MIN_POINTS，被误显示为不可通行（黄条纹）
     * 解决思路：
     *   1) 对“有足够点”的栅格正常计算多特征可通行性；
     *   2) 对“点数不足”的栅格不直接判为不可通行，而视为“未知”，
     *      通过邻域传播/插值（hole-filling）补全可通行性，使远处变连续；
     *   3) 仍保留占据与可通行性反向映射，时序融合交给你框架内其他函数。
     *
     * 使用特征（对有点栅格）：
     *   - 坡度 slope：法向与z轴夹角
     *   - 平面残差 RMS rough：点到拟合平面距离的RMS
     *   - 局部高度起伏 relief：P95-P5（抗离群点）
     *   - 8邻域高差 step：与8邻域均值高程差
     *   - 平面性 planar：λmin/(λ0+λ1+λ2)
     */

    // -------------------- 参数 --------------------
    const int   MIN_POINTS = 5;

    // 特征惩罚映射阈值（线性 ramp 到 [0,1]）
    const float SLOPE_T0  = 8.0f  * static_cast<float>(M_PI) / 180.0f;   // rad
    const float SLOPE_T1  = 20.0f * static_cast<float>(M_PI) / 180.0f;   // rad
    const float ROUGH_T0  = 0.015f;   // m
    const float ROUGH_T1  = 0.080f;   // m
    const float RELIEF_T0 = 0.030f;   // m
    const float RELIEF_T1 = 0.200f;   // m
    const float STEP_T0   = 0.040f;   // m
    const float STEP_T1   = 0.180f;   // m
    const float PLANAR_T0 = 0.020f;
    const float PLANAR_T1 = 0.180f;

    // 权重（和约为1）
    const float W_SLOPE   = 0.30f;
    const float W_ROUGH   = 0.24f;
    const float W_RELIEF  = 0.16f;
    const float W_STEP    = 0.20f;
    const float W_PLANAR  = 0.10f;

    // Pass3 地面引导空洞补全（仅向无点格扩散高可通行值，不膨胀障碍）
    const int   FILL_ITERS          = 4;
    const float FILL_DECAY          = 1.0f;
    const float FILL_DRIVABLE_MIN   = 0.65f; // 种子门槛：仅较高可通行邻居参与扩散
    const float FILL_MAX_DZ         = 0.08f;
    const int   FILL_MIN_GOOD_NB    = 2;
    const int   FILL_RELAX_ITER     = 4;
    const float OBSTACLE_FILL_THRESH = 0.5f;
    const double fill_now_time = (frame_time > 0.0) ? frame_time : ros::Time::now().toSec();
    const double OBSTACLE_FILL_TTL = large_heading_change ? 0.0 : 0.5;
    auto& drivable_layer_fill = multi_map.get("drivable");

    auto clamp01 = [](float x) -> float {
        return std::max(0.0f, std::min(1.0f, x));
    };
    auto ramp_penalty = [](float x, float t0, float t1) -> float {
        if (x <= t0) return 0.0f;
        if (x >= t1) return 1.0f;
        return (x - t0) / (t1 - t0);
    };

    // 缓存每格均值高程（用于 step）
    std::vector<float> mean_z(ARRAY_SIZE, std::numeric_limits<float>::quiet_NaN());
    // 标记该格是否“有足够点”可计算
    std::vector<uint8_t> has_points(ARRAY_SIZE, 0);

    // pass1：仅融合除 step 外的分数（有点格）
    std::vector<float> pass1_score(ARRAY_SIZE, std::numeric_limits<float>::quiet_NaN());
    // raw_score：包含 step 的分数（有点格）
    std::vector<float> raw_score(ARRAY_SIZE, std::numeric_limits<float>::quiet_NaN());

    // -------------------- Pass 1：单栅格特征（slope/rough/relief/planar） --------------------
    #pragma omp parallel for
    for (int i = 0; i < ARRAY_SIZE; ++i)
    {
        auto grid = grid_array[i];
        const int Nj = static_cast<int>(grid->pc_ptr->size());

        if (Nj < MIN_POINTS) {
            has_points[i] = 0;
            continue; // 先视为“未知”，后续用邻域补全
        }
        has_points[i] = 1;

        // 统计均值与z集合
        double sx = 0.0, sy = 0.0, sz = 0.0;
        std::vector<float> zvals;
        zvals.reserve(Nj);

        for (int j = 0; j < Nj; ++j) {
            const PointType& pt = grid->pc_ptr->points[j];
            sx += pt.x; sy += pt.y; sz += pt.z;
            zvals.push_back(pt.z);
        }

        const float avg_x = static_cast<float>(sx / Nj);
        const float avg_y = static_cast<float>(sy / Nj);
        const float avg_z = static_cast<float>(sz / Nj);

        grid->avage_x = avg_x;
        grid->avage_y = avg_y;
        grid->avage_z = avg_z;
        mean_z[i] = avg_z;

        // 特征：局部高度起伏 relief = P95 - P5（抗离群点）
        const int id05 = static_cast<int>(0.05f * (Nj - 1));
        const int id95 = static_cast<int>(0.95f * (Nj - 1));
        std::nth_element(zvals.begin(), zvals.begin() + id05, zvals.end());
        const float z05 = zvals[id05];
        std::nth_element(zvals.begin(), zvals.begin() + id95, zvals.end());
        const float z95 = zvals[id95];
        const float relief = z95 - z05;

        // PCA：法向与特征值
        Eigen::Vector4d centroid;
        Eigen::Matrix3d cov;
        Eigen::Matrix3d evec;
        Eigen::Vector3d eval;
        pcl::computeMeanAndCovarianceMatrix(*grid->pc_ptr, cov, centroid);
        pcl::eigen33(cov, evec, eval);

        Eigen::Index minIdx;
        eval.minCoeff(&minIdx);

        Eigen::Vector3d normal = evec.col(minIdx);
        if (normal.z() < 0.0) normal = -normal;  // 统一朝上
        normal.normalize();

        const double D = -normal.dot(centroid.head<3>());

        // 特征：坡度 slope（法向与z轴夹角）
        const float nz = static_cast<float>(std::max(-1.0, std::min(1.0, normal.z())));
        const float slope = std::acos(nz);

        // 特征：平面残差 rough（真实点到平面距离RMS）
        double d2_sum = 0.0;
        for (int j = 0; j < Nj; ++j) {
            const PointType& pt = grid->pc_ptr->points[j];
            const double d = std::abs(normal.x() * pt.x + normal.y() * pt.y + normal.z() * pt.z + D);
            d2_sum += d * d;
        }
        const float rough = static_cast<float>(std::sqrt(d2_sum / std::max(1, Nj - 1)));

        // 特征：平面性 planar = λmin / sum(λ)
        const double ev_sum = std::max(1e-9, eval[0] + eval[1] + eval[2]);
        const float planar = static_cast<float>(std::abs(eval[minIdx]) / ev_sum);

        // 惩罚项（归一化到 [0,1]）
        const float p_slope  = ramp_penalty(slope,  SLOPE_T0,  SLOPE_T1);
        const float p_rough  = ramp_penalty(rough,  ROUGH_T0,  ROUGH_T1);
        const float p_relief = ramp_penalty(relief, RELIEF_T0, RELIEF_T1);
        const float p_planar = ramp_penalty(planar, PLANAR_T0, PLANAR_T1);

        float penalty = W_SLOPE  * p_slope
                      + W_ROUGH  * p_rough
                      + W_RELIEF * p_relief
                      + W_PLANAR * p_planar;

        pass1_score[i] = clamp01(1.0f - penalty);
    }

    // -------------------- Pass 2：8邻域高差 step（仅对有点格） --------------------
    #pragma omp parallel for
    for (int i = 0; i < ARRAY_SIZE; ++i)
    {
        if (!has_points[i]) continue;

        float score = pass1_score[i];
        if (!std::isfinite(score) || !std::isfinite(mean_z[i])) {
            raw_score[i] = score;
            continue;
        }

        const int r = i / ARRAY_NX;
        const int c = i % ARRAY_NX;

        float step_sum = 0.0f;
        int valid_nb = 0;

        for (int dr = -1; dr <= 1; ++dr) {
            for (int dc = -1; dc <= 1; ++dc) {
                if (dr == 0 && dc == 0) continue;
                const int rr = r + dr;
                const int cc = c + dc;
                if (rr < 0 || rr >= ARRAY_NY || cc < 0 || cc >= ARRAY_NX) continue;

                const int ni = rr * ARRAY_NX + cc;
                if (ni < 0 || ni >= ARRAY_SIZE) continue;
                if (!std::isfinite(mean_z[ni])) continue;   // 邻居无点/未知则跳过

                step_sum += std::abs(mean_z[i] - mean_z[ni]);
                ++valid_nb;
            }
        }

        // 特征：邻域高差 step
        const float step = (valid_nb > 0) ? (step_sum / static_cast<float>(valid_nb)) : 0.0f;
        const float p_step = ramp_penalty(step, STEP_T0, STEP_T1);

        score = clamp01(score - W_STEP * p_step);
        raw_score[i] = score;
    }

    // -------------------- Pass 3：地面引导空洞补全（仅补无点格，障碍不扩散、不接收填充） --------------------
    // 环状伪障碍成因（线束间无点）：Nj<MIN_POINTS 的格无 raw_score，若未补全则 Pass4 回退为
    // 低分/中性值；旧版若用任意邻居均值会把障碍分传开。现用“仅高可通行种子 + 多轮 8 邻域扩散”。
    std::vector<float> filled = raw_score;

    auto is_obstacle_for_fill = [&](int idx) -> bool {
        // 本帧观测为障碍
        if (has_points[idx]) {
            const float obs = std::isfinite(raw_score[idx]) ? raw_score[idx] : pass1_score[idx];
            if (std::isfinite(obs) && obs < OBSTACLE_FILL_THRESH) return true;
        }
        // 5s 障碍记忆中仍有效。这里使用 ini() 后已滚动到当前帧的 obstacle_*，不能再读 pre_* 旧索引。
        const double stamp = *(obstacle_stamp_grid + idx);
        if (stamp > 0.0 && (fill_now_time - stamp <= OBSTACLE_FILL_TTL)) return true;
        return false;
    };

    // 障碍及其 8 邻域：尽量不补全，避免障碍周围“半占”光晕
    auto is_near_obstacle_for_fill = [&](int idx) -> bool {
        if (is_obstacle_for_fill(idx)) return true;
        const int r0 = idx / ARRAY_NX;
        const int c0 = idx % ARRAY_NX;
        for (int dr = -1; dr <= 1; ++dr) {
            for (int dc = -1; dc <= 1; ++dc) {
                if (dr == 0 && dc == 0) continue;
                const int rr = r0 + dr;
                const int cc = c0 + dc;
                if (rr < 0 || rr >= ARRAY_NY || cc < 0 || cc >= ARRAY_NX) continue;
                const int ni = rr * ARRAY_NX + cc;
                if (ni < 0 || ni >= ARRAY_SIZE) continue;
                if (is_obstacle_for_fill(ni)) return true;
            }
        }
        return false;
    };

    auto fill_baseline = [&](int idx, int grid_i) -> float {
        float b = 0.5f;
        const float global_v = drivable_layer_fill.data()[grid_i];
        if (std::isfinite(global_v) && global_v >= 0.0f && global_v <= 1.0f) {
            b = std::max(b, global_v);
        }
        const float current_history = *(drivable_value_grid + idx);
        if (std::isfinite(current_history)) {
            b = std::max(b, current_history);
        }
        return b;
    };

    for (int iter = 0; iter < FILL_ITERS; ++iter)
    {
        std::vector<float> next = filled;
        const int min_good_nb = (iter >= FILL_RELAX_ITER) ? 1 : FILL_MIN_GOOD_NB;

        #pragma omp parallel for
        for (int i = 0; i < ARRAY_SIZE; ++i)
        {
            if (has_points[i]) continue;               // 有点格：只用本帧观测，不被填充改写
            if (is_near_obstacle_for_fill(i)) continue; // 障碍及邻域不补全
            if (std::isfinite(filled[i])) continue;

            const int r = i / ARRAY_NX;
            const int c = i % ARRAY_NX;
            const int grid_i_fill = (ARRAY_NY - 1 - r) * ARRAY_NX + c;

            float sum = 0.0f;
            int cnt = 0;
            const bool have_self_z = std::isfinite(mean_z[i]);

            for (int dr = -1; dr <= 1; ++dr) {
                for (int dc = -1; dc <= 1; ++dc) {
                    if (dr == 0 && dc == 0) continue;
                    const int rr = r + dr;
                    const int cc = c + dc;
                    if (rr < 0 || rr >= ARRAY_NY || cc < 0 || cc >= ARRAY_NX) continue;

                    const int ni = rr * ARRAY_NX + cc;
                    if (ni < 0 || ni >= ARRAY_SIZE) continue;
                    if (is_obstacle_for_fill(ni)) continue; // 障碍邻居不参与扩散

                    const float v = filled[ni];
                    if (!std::isfinite(v)) continue;
                    if (v < FILL_DRIVABLE_MIN) continue;  // 只从高可通行种子向外扩散

                    if (have_self_z && std::isfinite(mean_z[ni])) {
                        if (std::abs(mean_z[i] - mean_z[ni]) > FILL_MAX_DZ) continue;
                    }

                    sum += v;
                    ++cnt;
                }
            }

            if (cnt >= min_good_nb) {
                const float proposed = clamp01((sum / cnt) * FILL_DECAY);
                const float baseline = fill_baseline(i, grid_i_fill);
                // 无点格补全只抬高、不压低历史/全局可通行度
                next[i] = std::max(proposed, baseline);
            }
        }

        filled.swap(next);
    }
    // -------------------- Pass 4：写回输出 + 障碍记忆叠加 --------------------
    auto& drivable_layer = multi_map.get("drivable");

    const float OBSTACLE_THRESHOLD = 0.5f;
    // 转向帧关闭记忆；直行时也只用很短 TTL，避免航向微误差叠出斜墙
    const double OBSTACLE_TTL_SEC  = large_heading_change ? 0.0 : 0.5;
    const double now_time = (frame_time > 0.0) ? frame_time : ros::Time::now().toSec();

    #pragma omp parallel for
    for (int i = 0; i < ARRAY_SIZE; ++i)
    {
        float v = filled[i];

        // 映射到 grid_map 的行列/一维索引（与 make_final_decision 中保持一致）
        const int r      = i / ARRAY_NX;
        const int c      = i % ARRAY_NX;
        const int grid_i = (ARRAY_NY - 1 - r) * ARRAY_NX + c;

        const bool observed_this_frame = (has_points[i] != 0);

        // 无点格历史基线（用于“只抬高、不压低”）
        auto pass4_baseline = [&]() -> float {
            // 转向：不用历史/全局基线锁死障碍，只信本帧观测与补全
            if (large_heading_change) {
                return 0.5f;
            }
            float b = 0.6f;
            const float global_v = drivable_layer.data()[grid_i];
            if (std::isfinite(global_v) && global_v >= 0.0f && global_v <= 1.0f) {
                b = std::max(b, global_v);
            }
            const float current_history = *(drivable_value_grid + i);
            if (std::isfinite(current_history)) {
                b = std::max(b, current_history);
            }
            return b;
        };

        // 有本帧新观测：使用当前帧计算值
        if (observed_this_frame) {
            if (!std::isfinite(v)) {
                v = std::isfinite(raw_score[i]) ? raw_score[i] : pass1_score[i];
            }
        } else {
            const float baseline = pass4_baseline();
            if (std::isfinite(v)) {
                // 补全结果不得低于 global/prev 基线
                v = std::max(v, baseline);
            } else {
                v = baseline;
            }
        }

        v = clamp01(v);

        // 本帧新观测：刷新或清除障碍记忆（仅来自真实观测，不含空洞补全）
        if (observed_this_frame) {
            float obs_score = std::isfinite(raw_score[i]) ? raw_score[i] : pass1_score[i];
            if (std::isfinite(obs_score) && obs_score < OBSTACLE_THRESHOLD) {
                *(obstacle_stamp_grid + i) = now_time;
                *(obstacle_value_grid + i) = obs_score;
            } else if (std::isfinite(obs_score) && obs_score > OBSTACLE_THRESHOLD + 0.05f) {
                // 同一格再次明确观测为可通行：清除旧障碍记忆，避免拖影叠加
                *(obstacle_stamp_grid + i) = 0.0;
                *(obstacle_value_grid + i) = 0.0f;
            }
        }

        // 释放生命周期到期的障碍记忆
        const double obs_stamp = *(obstacle_stamp_grid + i);
        if (obs_stamp > 0.0 && (now_time - obs_stamp > OBSTACLE_TTL_SEC)) {
            *(obstacle_stamp_grid + i) = 0.0;
            *(obstacle_value_grid + i) = 0.0f;
        }

        // 叠加仍有效的历史障碍；转向帧跳过，防止竖墙+斜墙并存
        if (!large_heading_change) {
            const double active_stamp = *(obstacle_stamp_grid + i);
            if (active_stamp > 0.0 && (now_time - active_stamp <= OBSTACLE_TTL_SEC)) {
                const float mem_v = *(obstacle_value_grid + i);
                if (std::isfinite(mem_v)) {
                    v = std::min(v, mem_v);
                }
            }
        }

        v = clamp01(v);
        *(drivable_value_grid + i) = v;

        // 同步更新全局 drivable 地图（multi_map 中的 "drivable" layer）
        drivable_layer.data()[grid_i] = v;

        // 仍保持可通行度与 occ_grid 的反向映射，供 /drivable/occ_map 使用
        float occ = 100.0f * (1.0f - v);
        *(occ_grid + i) = std::max(1.0f, std::min(99.0f, occ));
    }

    // 更新缓存（保持原流程一致）
    std::memcpy(pre_drivable_value_grid, drivable_value_grid, ARRAY_SIZE * sizeof(float));
    std::memcpy(pre_occ_grid, occ_grid, ARRAY_SIZE * sizeof(float));
    std::memcpy(pre_obstacle_stamp_grid, obstacle_stamp_grid, ARRAY_SIZE * sizeof(double));
    std::memcpy(pre_obstacle_value_grid, obstacle_value_grid, ARRAY_SIZE * sizeof(float));
    pre_utm_loc = utm_loc;
    pre_utmx = static_cast<int>(std::floor(pre_utm_loc.x()));
    pre_utmy = static_cast<int>(std::floor(pre_utm_loc.y()));
    pre_heading = heading;
    map_history_initialized = true;
    cloud_frames->clear();
    *cloud_frames += *cloud_prcs;
}

//------------------------------------------------------------------------------
// updateUnocclusion：更新可见空闲区域统计（用于 unocc / mean_xy / mse_cover）
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::updateUnocclusion(int i,int tx, int ty, int cx, int cy, float d_neg_obs ){
    /*
     * 功能：
     *   - 在 checkUnocclusion 中被调用，用于沿 Bresenham 射线更新某个栅格 i 的“可见空闲”信息
     *   - pre_unocc_grid 标记该栅格已经被射线访问过
     *   - unocc_grid 计数访问次数
     *   - mean_xy / mse_cover 用于记录射线终点在该栅格内的平均位置和覆盖方差
     *   - d_neg_obs 表示某种负障碍物距离，可用于调整 mse_cover
     */
    *(pre_unocc_grid+i) = 1;
    *(unocc_grid+i) += 1;
    (mean_xy+i)->first  += ((tx-cx)*GRID_LEN - (mean_xy+i)->first)  / *(unocc_grid+i);
    (mean_xy+i)->second += ((ty-cy)*GRID_LEN - (mean_xy+i)->second) / *(unocc_grid+i);
    *(mse_cover+i) = std::pow(((tx-cx)*GRID_LEN - (mean_xy+i)->first),2)
                   + std::pow(((ty-cy)*GRID_LEN - (mean_xy+i)->second),2)
                   - d_neg_obs * d_neg_obs;
}

//------------------------------------------------------------------------------
// compute_cvar：基于 slope / step / collision 计算栅格 CVaR（通过 CUDA）
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::compute_cvar(const std::vector<std::string>& layers,
                                          const std::vector<float>& weights,
                                          const float& alpha)
{
    /*
     * 功能：
     *   - 对指定的 layer 组合（如 slope / step / collision）进行风险聚合
     *   - 使用 CVaR（Conditional Value at Risk）度量每个栅格的尾部风险
     *   - 这里采用了 CUDA 的 computeCVaRCUDAWrapper，对 multi_map 中的各层进行加权计算
     *
     *  当前实现：
     *   - 用 approx_erfinv(alpha) 近似反解高斯分位数
     *   - 计算 cvarFactor = phi / (1 - alpha)
     *   - 把 weights / layers / cvarFactor 传给 CUDA 封装
     */

    float z   = approx_erfinv(alpha);
    float phi = normalPDF(z);
    float cvarFactor = phi/(1.0f - alpha);

    // 由 CUDA 实现具体的 CVaR 计算，将结果写入 multi_map["CVaR"]
    computeCVaRCUDAWrapper(multi_map, weights, layers, cvarFactor);
}

//------------------------------------------------------------------------------
// checkUnocclusion：基于 Bresenham 射线的可见空闲区域推断（当前主链路中注释掉）
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::checkUnocclusion(){
    /*
     * 功能（逻辑上）：
     *   - 从栅格中心出发（车辆位置所在栅格），对每一个存在高度信息的栅格，使用 Bresenham 画一条射线
     *   - 射线经过的栅格，根据是否已有标记，调用 updateUnocclusion 更新 unocc_grid / mean_xy / mse_cover
     *   - 若某栅格 mse_cover > 0 且没有高度信息（hei_grid == 0），则把其占据率初始化为 50（未知）
     *
     * 注意：
     *   - 当前在 lidarmappedCB 中调用 checkUnocclusion() 的代码被注释掉，
     *     因此这一步在实际运行路径中是关闭的。
     */

    // 首先用 pre_unocc_grid 记录当前帧 unocc 的结果，先全部置零
    std::memset(pre_unocc_grid,0.0,ARRAY_SIZE*sizeof(float));

    int rows = ARRAY_NX;
    int cols = ARRAY_NY;
    int tx, ty, cx, cy, dx, dy, sx, sy, err;
    int target_inx = 0;
    int d_neg_obs = 5;  // 负障碍物距离阈值（在 updateUnocclusion 中使用）

    // 栅格中心索引（车辆所在栅格）
    const int center_idx = (ARRAY_SIZE - 1) / 2;
    const int c_x0 = center_idx / ARRAY_NY;
    const int c_y0 = center_idx % ARRAY_NY;

    for(int i = 0; i < ARRAY_SIZE; i++){
        GRID_INFO* grid = grid_array[i];

        tx = i / ARRAY_NY;
        ty = i % ARRAY_NY;
        cx = c_x0;
        cy = c_y0;
        dx = std::abs(tx - cx);
        dy = std::abs(ty - cy);
        sx = (tx < cx) ? 1 : -1;
        sy = (ty < cy) ? 1 : -1;
        err = dx - dy;

        // 特殊处理中心列一个栅格，用于调试
        if(i == (ARRAY_NX-1)/2){
            ROS_INFO("target_y: %d, center_y : %d",ty, cy);
            updateUnocclusion( i, tx, ty, cx, cy, d_neg_obs );
            continue;
        }

        // 只有有高度信息的栅格才作为射线终点
        if( *(hei_grid + i) !=0.0){
            // Bresenham 算法，从 (cx, cy) 走到 (tx, ty)
            while((cx != tx || cy != ty)){

                if(tx < 0 || ty < 0 || tx >= rows || ty >= cols){
                    break;
                }
                target_inx = tx+ty*ARRAY_NX;

                if(*(pre_unocc_grid+target_inx) != 1){
                    updateUnocclusion( target_inx, tx, ty, cx, cy, d_neg_obs );
                }

                int e2 = 2 * err;
                if (e2 > -dy) {
                    err -= dy;
                    tx += sx;
                }
                if (e2 < dx) {
                    err += dx;
                    ty += sy;
                }
            }
        }

        // 若某栅格 mse_cover > 0 且没有高度信息，则设为未知区域（占据率 50）
        if(*(mse_cover+i) > 0 && (*(hei_grid+i) == 0)){
            *(occ_grid+i )= 50;
        }
    }
}

//------------------------------------------------------------------------------
// make_final_decision：将栅格分析结果写入 multi_map，并缓存为 pre_* 供下一帧使用
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::make_final_decision(){
    /*
     * 功能：
     *   - 遍历所有栅格：
     *       * 如果该栅格非平坦（flat == false），将其点云加入 cloud_out（可视化障碍）
     *       * 把各类栅格属性写入 multi_map 相应 layer：
     *           elevation   ← hei_diff_grid
     *           unocc       ← unocc_grid
     *           mean_x/y    ← mean_xy
     *           mse_cover   ← mse_cover
     *           hei_diff    ← hei_diff_grid
     *           slope       ← slope_map
     *           step        ← step_map
     *           collision   ← 1 - occ_grid/100
     *   - 调用 compute_cvar，基于 slope/step/collision 计算 CVaR，填入 multi_map["CVaR"]
     *   - 更新 pre_* 缓存（用于下一帧 ini() 时做滚动 map）
     *   - 同时维护 cloud_frames（多帧融合点云）
     */

    TicToc f_time;
    float cur_x, cur_y;

    for (int i = 0; i < ARRAY_SIZE; ++i){
        int grid_i = (ARRAY_NY - 1 - (i / ARRAY_NX)) * ARRAY_NX + (i % ARRAY_NX);
        GRID_INFO* grid = grid_array[i];
        IJ2xy(i,cur_x, cur_y);

        // 若该栅格不可行（feasible == false）但被标记为 flat（地面），则跳过
        if(!grid->feasible && grid->flat){
            // 有观测但未被检测为障碍，视为未遮挡可行区域
            continue;
        }

        // 非平坦区域（障碍、草地等）点云加入 cloud_out，可供上层发布或可视化
        if( grid->flat == false){
            *cloud_out += *grid->pc_ptr;
        }

        // 写入 multi_map 各层（不同可视化 topic 或下游模块使用）
        multi_map.get("elevation").data()[grid_i] = *(hei_diff_grid+i);
        multi_map.get("unocc").data()[grid_i]     = *(unocc_grid+i);
        multi_map.get("mean_x").data()[grid_i]    = (mean_xy+i)->first;
        multi_map.get("mean_y").data()[grid_i]    = (mean_xy+i)->second;
        multi_map.get("mse_cover").data()[grid_i] = *(mse_cover+i);
        multi_map.get("hei_diff").data()[grid_i]  = *(hei_diff_grid+i);
        multi_map.get("slope").data()[grid_i]     = *(slope_map+i);
        multi_map.get("step").data()[grid_i]      = *(step_map+i);
        multi_map.get("collision").data()[grid_i] = 1- *(occ_grid+i)/100;
    }

    // 使用 CUDA 计算 CVaR，当前固定：
    //   layers  = {"slope","step","collision"}
    //   weights = {0.5, 0.4, 1}
    //   alpha   = 0.05
    std::vector<std::string> layers{"slope","step","collision"};
    std::vector<float> weights{0.5,0.4,1};
    compute_cvar(layers,weights,0.05);

    // 更新上一帧位姿 / 点云缓存 / 栅格缓存
    pre_utm_loc = utm_loc;
    pre_utmx    = static_cast<int>(std::floor(pre_utm_loc.x()));
    pre_utmy    = static_cast<int>(std::floor(pre_utm_loc.y()));
    pre_heading = heading;
    map_history_initialized = true;

    cloud_frames->clear();
    *cloud_frames += *cloud_prcs;

    pre_near_ground_height = near_ground_height;
    pre_min_ground_height  = min_ground_height;

    std::memcpy(pre_occ_grid,      occ_grid,      ARRAY_SIZE*sizeof(float));
    std::memcpy(pre_hei_grid,      hei_grid,      ARRAY_SIZE*sizeof(float));
    std::memcpy(pre_hei_diff_grid, hei_diff_grid, ARRAY_SIZE*sizeof(float));
    std::memcpy(pre_unocc_grid,    unocc_grid,    ARRAY_SIZE*sizeof(float));
    std::memcpy(pre_mean_xy,       mean_xy,       ARRAY_SIZE*sizeof(std::pair<float,float>));
    std::memcpy(pre_mse_cover,     mse_cover,     ARRAY_SIZE*sizeof(float));
    std::memcpy(pre_slope_map,     slope_map,     ARRAY_SIZE*sizeof(float));
    std::memcpy(pre_step_map,      step_map,      ARRAY_SIZE*sizeof(float));
    std::memcpy(pre_rough_map,     rough_map,     ARRAY_SIZE*sizeof(float));

    printf("output pc size: %ld \n", cloud_out->size());
}

//------------------------------------------------------------------------------
// xy2IJ：根据点坐标 (x,y) 找到其所在栅格索引 (grid_I, grid_J)
//------------------------------------------------------------------------------
bool DRIVABLE_DETECT_MAPPED::xy2IJ(float x, float y, int &grid_I, int &grid_J)
{
    /*
     * 功能：
     *   - 把连续坐标 (x, y) 映射到离散栅格坐标 grid_I, grid_J
     *   - 栅格原点在数组中心 ((ARRAY_NX-1)/2, (ARRAY_NY-1)/2)
     *   - 每个栅格尺寸为 GRID_LEN
     */
    const int center_i = (ARRAY_NX - 1) / 2;
    const int center_j = (ARRAY_NY - 1) / 2;

    // 与 UTM 栅格锚点一致：先按 GRID_LEN 对连续坐标取 floor 落格。
    // 例如 GRID_LEN=0.2 时，格心固定在 0.1/0.3/0.5...，避免半格附近来回跳。
    grid_I = static_cast<int>(std::floor(static_cast<double>(x) / static_cast<double>(GRID_LEN))) + center_i;
    grid_J = static_cast<int>(std::floor(static_cast<double>(y) / static_cast<double>(GRID_LEN))) + center_j;

    // 若超出栅格边界则返回 false
    if (grid_I <0 || grid_I >=ARRAY_NX ||
        grid_J <0 || grid_J >=ARRAY_NY)
        return false;
    else
        return true;
}

//------------------------------------------------------------------------------
// IJ2xy：根据栅格索引 idx 反算栅格中心坐标 (c_x, c_y)
//------------------------------------------------------------------------------
void DRIVABLE_DETECT_MAPPED::IJ2xy(const int & idx, float & c_x, float& c_y){
    /*
     * 功能：
     *   - 输入一维索引 idx（0 ~ ARRAY_SIZE-1）
     *   - 反推出所在的 (grid_I, grid_J)
     *   - 再转成栅格中心的真实坐标 (c_x, c_y)
     */
    const int grid_I = idx / ARRAY_NY;
    const int grid_J = idx % ARRAY_NY;
    const int center_i = (ARRAY_NX - 1) / 2;
    const int center_j = (ARRAY_NY - 1) / 2;
    c_x = (static_cast<float>(grid_I - center_i) + 0.5f) * GRID_LEN;
    c_y = (static_cast<float>(grid_J - center_j) + 0.5f) * GRID_LEN;
}