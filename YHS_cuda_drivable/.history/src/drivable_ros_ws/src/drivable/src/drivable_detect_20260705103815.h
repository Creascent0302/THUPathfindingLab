
#ifndef DD_MAPPED
#define DD_MAPPED

#include <cmath>
#include <vector>
#include <string>
#include <iostream>
#include <set>
#include <unordered_map>
#include <algorithm>
#include <eigen3/Eigen/Dense>
#include "eigen3/Eigen/Dense"
#include <Eigen/Dense>
#include <tf/transform_broadcaster.h>

// #include <opencv/cv.h>
#include <opencv2/opencv.hpp>
#include <opencv2/core/eigen.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/highgui.hpp>

#include <pcl/common/transforms.h>
#include <pcl/common/eigen.h>
#include <pcl/common/centroid.h>
#include <pcl_conversions/pcl_conversions.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/filters/uniform_sampling.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/io/pcd_io.h>
#include <pcl/filters/extract_indices.h>
#include <pcl/search/organized.h>
#include <pcl/search/kdtree.h>
#include <pcl/features/normal_3d_omp.h>
#include <pcl/features/don.h>
#include <pcl/filters/conditional_removal.h>
#include <pcl/surface/mls.h>
#include <pcl/segmentation/progressive_morphological_filter.h>
#include <pcl/visualization/pcl_visualizer.h>
#include <pcl/console/parse.h>
#include <pcl/filters/passthrough.h>
#include <pcl/filters/statistical_outlier_removal.h>
#include <pcl/filters/radius_outlier_removal.h>
#include <pcl/octree/octree_pointcloud_changedetector.h>
#include <pcl/octree/octree_pointcloud_adjacency.h>
#include <pcl/filters/normal_space.h>
#include <pcl/surface/gp3.h>
#include <pcl/surface/organized_fast_mesh.h>
#include <pcl/surface/reconstruction.h>
#include <pcl/surface/mls.h>
#include <pcl/features/normal_3d.h>
#include <ros/ros.h>
#include <sensor_msgs/Imu.h>
#include <sensor_msgs/NavSatFix.h>
#include <sensor_msgs/PointCloud2.h>
#include <tf/transform_datatypes.h>
#include <tf/transform_broadcaster.h>
#include <grid_map_ros/grid_map_ros.hpp>
#include <grid_map_core/grid_map_core.hpp>

#include <numeric>
#include <iomanip>

#include <sensor_msgs/point_cloud_conversion.h>
#include <nav_msgs/Odometry.h>
#include <nav_msgs/OccupancyGrid.h>
#include "tic_toc.h"
#include "common.h"
#include "CVaRcal.h"
extern grid_map::GridMap multi_map;
extern grid_map::GridMap Pre_state;
class GRID_INFO
{
public:
    pcl::PointCloud<PointType>::Ptr pc_ptr;

    float avage_x = 0.0;
    float avage_y = 0.0;
    float avage_z = 0.0;
    float z_max = -1e5;
    float z_min = 1e5;

    float d_max = 0.0;
    float d_avg = 0.0;

    float num_pc_single = 0.0;

    bool feasible = false;
    bool flat = true;
    float Q = 1.0;
    int drivable = 0; //-1: no  1: yes, 0: not sure
    const int* ob_id = nullptr;
    std::unordered_set<const int *> neighbor_ids;
    GRID_INFO()
    {
        pc_ptr.reset(new pcl::PointCloud<PointType>);
        avage_x = avage_y = avage_z = 0.0;
        z_max = -1e5;
        z_min = 1e5;
        d_max = d_avg = 1e5;
        num_pc_single = 0.0;
        feasible = false;
        flat = true;
        Q = 1.0;
        drivable = 0;
        ob_id = nullptr;
        neighbor_ids.clear();
    }
    GRID_INFO(pcl::PointCloud<PointType>::Ptr ptr) : pc_ptr(ptr) {}
    GRID_INFO(float x, float y, float z) : avage_x(x), avage_y(y), avage_z(z) {}
    virtual ~GRID_INFO() = default;
    void ini()
    {
        pc_ptr->clear();
        avage_x = avage_y = avage_z = 0.0;
        z_max = -1e5;
        z_min = 1e5;
        d_max = d_avg = 1e5;
        num_pc_single = 0.0;
        feasible = false;
        flat = true;
        Q = 1.0;
        drivable = 0; //-1: no  1: yes, 0: not sure
        neighbor_ids.clear();
        ob_id = nullptr;
    }
};

class DRIVABLE_DETECT_MAPPED
{
public:
    DRIVABLE_DETECT_MAPPED();
    ~DRIVABLE_DETECT_MAPPED(){};
    void data_read( pcl::PointCloud<PointType>::Ptr _cloud_in,
                    pcl::PointCloud<PointType>::Ptr _cloud_out,
                    Eigen::Vector3d _utm_loc,
                    float _heading,
                    double _frame_time = 0.0);
    void ini();
    void filterPC(  float x_low,
                    float x_high,
                    float y_low,
                    float y_high,
                    float z_th,
                    float far_thres,
                    float voxel_size);
    void mapping(   int frame_num);
    void movePC2Grid();
    void checkFlatness();
    void checkHeight();
    void checkUnocclusion();
    void compute_drivable_passability();  // 新的可通过性评价函数
    void make_final_decision();
    void compute_cvar(const std::vector<std::string>& layers, const std::vector<float>& weights, const float& alpha = 0.95f);

    bool xy2IJ( float x, 
                float y, 
                int &grid_I, 
                int &grid_J);

    void IJ2xy( const int &idx, 
                float &c_x, 
                float &c_y);
    void occ_updating();
    void getGridMapPtr(float * sub_map){
        occ_grid = sub_map;
    }
    void set_map(int MAP_SIZE,float MAP_RESOLUTION){
        int o_ARRAY_SIZE = ARRAY_SIZE;
        GRID_LEN = MAP_RESOLUTION;
        ARRAY_NX = MAP_SIZE; // 必须是奇数
        ARRAY_NY = MAP_SIZE; // 必须是奇数
        ARRAY_SIZE = ARRAY_NX * ARRAY_NY;
        //Initialization of the grid.
        pre_occ_grid = (float*)malloc(ARRAY_SIZE*sizeof(float));
        pre_hei_grid = (float*)malloc(ARRAY_SIZE*sizeof(float));
        hei_grid = (float*)malloc(ARRAY_SIZE*sizeof(float));
        pre_hei_diff_grid = (float*)malloc(ARRAY_SIZE*sizeof(float));
        hei_diff_grid = (float*)malloc(ARRAY_SIZE*sizeof(float));
        pre_unocc_grid = (float*)malloc(ARRAY_SIZE*sizeof(float));
        unocc_grid = (float*)malloc(ARRAY_SIZE*sizeof(float));
        pre_mean_xy = (std::pair<float,float>*)malloc(ARRAY_SIZE*sizeof(std::pair<float,float>));
        mean_xy = (std::pair<float,float>*)malloc(ARRAY_SIZE*sizeof(std::pair<float,float>));
        pre_mse_cover = (float*)malloc(ARRAY_SIZE*sizeof(float));
        mse_cover = (float*)malloc(ARRAY_SIZE*sizeof(float));
        pre_slope_map = (float*)malloc(ARRAY_SIZE*sizeof(float));
        slope_map = (float*)malloc(ARRAY_SIZE*sizeof(float));
        pre_rough_map = (float*)malloc(ARRAY_SIZE*sizeof(float));
        rough_map = (float*)malloc(ARRAY_SIZE*sizeof(float));
        pre_step_map = (float*)malloc(ARRAY_SIZE*sizeof(float));
        step_map = (float*)malloc(ARRAY_SIZE*sizeof(float));
        std::fill(pre_occ_grid, pre_occ_grid + ARRAY_SIZE, 50.0f);
        std::fill(pre_hei_grid, pre_hei_grid + ARRAY_SIZE, 0.0f);
        std::fill(hei_grid, hei_grid + ARRAY_SIZE, 0.0f);
        std::fill(pre_hei_diff_grid, pre_hei_diff_grid + ARRAY_SIZE, 0.0f);
        std::fill(hei_diff_grid, hei_diff_grid + ARRAY_SIZE, 0.0f);
        std::fill(pre_unocc_grid, pre_unocc_grid + ARRAY_SIZE, 0.0f);
        std::fill(unocc_grid, unocc_grid + ARRAY_SIZE, 0.0f);
        std::fill(pre_mean_xy, pre_mean_xy + MAP_SIZE*MAP_SIZE, std::pair<float,float>{0,0});
        std::fill(mean_xy, mean_xy + MAP_SIZE*MAP_SIZE, std::pair<float,float>{0,0});
        std::fill(pre_mse_cover, pre_mse_cover + ARRAY_SIZE, 0.0f);
        std::fill(mse_cover, mse_cover + ARRAY_SIZE, 0.0f);
        std::fill(pre_step_map, pre_step_map + ARRAY_SIZE, 0.0f);
        std::fill(step_map, step_map + ARRAY_SIZE, 1.0f);
        std::fill(pre_slope_map, pre_slope_map + ARRAY_SIZE, 0.0f);
        std::fill(slope_map, slope_map + ARRAY_SIZE, 1.0f);
        std::fill(pre_rough_map, pre_rough_map + ARRAY_SIZE, 0.0f);
        std::fill(rough_map, rough_map + ARRAY_SIZE, 1.0f);
        drivable_value_grid = (float*)malloc(ARRAY_SIZE*sizeof(float));
        pre_drivable_value_grid = (float*)malloc(ARRAY_SIZE*sizeof(float));
        obstacle_stamp_grid = (double*)calloc(ARRAY_SIZE, sizeof(double));
        pre_obstacle_stamp_grid = (double*)calloc(ARRAY_SIZE, sizeof(double));
        obstacle_value_grid = (float*)calloc(ARRAY_SIZE, sizeof(float));
        pre_obstacle_value_grid = (float*)calloc(ARRAY_SIZE, sizeof(float));
        std::fill(drivable_value_grid, drivable_value_grid + ARRAY_SIZE, 0.5f);   // 0.5 = 未知
        std::fill(pre_drivable_value_grid, pre_drivable_value_grid + ARRAY_SIZE, 0.5f);
        pre_utm_loc.setZero();
        pre_utmx = 0;
        pre_utmy = 0;
        map_history_initialized = false;
        near_ground_height = 0.0f;
        pre_near_ground_height = 0.0f;
        min_ground_height = 0.0f;
        pre_min_ground_height = 0.0f;
        // grid_map::Position center(ARRAY_NX /2 , ARRAY_NY /2);
        multi_map.setGeometry(grid_map::Length(MAP_SIZE*GRID_LEN, MAP_SIZE*GRID_LEN), GRID_LEN); // Size (10x10m), resolution (0.1m/cell)
        multi_map.setPosition(grid_map::Position(0.5 * GRID_LEN, 0.5 * GRID_LEN));
        multi_map.setFrameId("camera_init");
        // Pre_state.setGeometry(grid_map::Length(MAP_SIZE*GRID_LEN, MAP_SIZE*GRID_LEN), GRID_LEN); // Size (10x10m), resolution (0.1m/cell)
        // Pre_state.setFrameId("camera_init");
        // Initialize all layers with zeros
        for (const auto& layer : multi_map.getLayers()) {
            multi_map[layer].setZero();
        }
        // for(int i = 0; i < ARRAY_SIZE; i++){
        //     int grid_i = (ARRAY_NY - 1 - (i / ARRAY_NX)) * ARRAY_NX + (i % ARRAY_NX);
        //     // multi_map.get("unocc").data()[grid_i] = 0;
        //     // multi_map.get("mean_x").data()[grid_i] = 0;
        //     // multi_map.get("mean_y").data()[grid_i] = 0;
        //     // multi_map.get("mse_cover").data()[grid_i] = 0;
        //     if(i >= o_ARRAY_SIZE){
        //         grid_array.push_back( new GRID_INFO());
        //     }
        // }
        for(int i = o_ARRAY_SIZE; i < ARRAY_SIZE; i++){
            grid_array.push_back( new GRID_INFO());
        }      
        
    }
    void set_lidar_offset(float offset_x, float offset_y){
        lidar_offset_x = offset_x;
        lidar_offset_y = offset_y;
    }
    void transform_translation(   PointType const *const pi, 
                                PointType *const po, 
                                float x_div, 
                                float y_div,
                                float z_div=0.0);

    void transform_rotation(PointType const *const pi, 
                            PointType *const po);
    void updateUnocclusion(int i,int tx, int ty, int cx, int cy,float d_neg_obs = 5);
    //publich variables
    pcl::PointCloud<PointType>::Ptr cloud_in;
    pcl::PointCloud<PointType>::Ptr cloud_prcs;
    pcl::PointCloud<PointType>::Ptr cloud_frames;
    pcl::PointCloud<PointType>::Ptr cloud_out;
    Eigen::Vector3d utm_loc;
    Eigen::Vector3d pre_utm_loc;
    std::set<int> available_grid;
    std::set<int> feasible_grid;
    std::set<int> non_flat_grid;
    std::set<int> non_ground_grid;
    int pre_utmx, pre_utmy;
    float GRID_LEN=1.0f;
    int ARRAY_NX = 3; // 必须是奇数
    int ARRAY_NY = 3; // 必须是奇数
    int ARRAY_SIZE = ARRAY_NX * ARRAY_NY;
    int frameCount = 0;
    std::vector<GRID_INFO *> grid_array;
    float heading;
    float lidar_offset_x = 0.0f;  // 雷达原点相对车辆中心：x 前，y 左（米）
    float lidar_offset_y = 0.0f;
    float near_ground_height, z_thred, pre_near_ground_height, min_ground_height, pre_min_ground_height;
    float* occ_grid;
    float* pre_occ_grid;
    float* hei_grid;
    float* pre_hei_grid;
    float* hei_diff_grid;
    float* pre_hei_diff_grid;
    float* pre_unocc_grid;
    float* unocc_grid;
    float* pre_slope_map;
    float* slope_map;
    float* pre_step_map;
    float* step_map;
    float* pre_rough_map;
    float* rough_map;
    float* drivable_value_grid;      // 可通行性连续值 [0,1]，1=最佳
    float* pre_drivable_value_grid;  // 上一帧缓存，用于多帧融合
    double* obstacle_stamp_grid;     // 障碍记忆：最近一次观测为障碍的时间戳（0=无）
    double* pre_obstacle_stamp_grid;
    float* obstacle_value_grid;      // 障碍记忆：对应时刻的可通行度（越低越不可通行）
    float* pre_obstacle_value_grid;
    double frame_time = 0.0;         // 当前帧时间戳（秒）
    double grid_anchor_x = 0.0;      // 当前栅格内容与 ini() 滚动使用的 UTM 锚点
    double grid_anchor_y = 0.0;
    bool map_history_initialized = false;
    std::pair<float,float>* pre_mean_xy;
    std::pair<float,float>* mean_xy;
    float* pre_mse_cover;
    float* mse_cover;
    std::vector<pcl::PointCloud<PointType>> laserCloudScans;

    bool start_desample = false;
    //filter method
    pcl::PassThrough<PointType> pass;
    pcl::VoxelGrid<PointType> pass_vox;
    pcl::UniformSampling<PointType> pass_uni;
    pcl::RadiusOutlierRemoval<PointType> pass_radius;
};
#endif
