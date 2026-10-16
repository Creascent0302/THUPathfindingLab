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
#include <pcl/PolygonMesh.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/io/pcd_io.h>
#include <pcl/filters/extract_indices.h>
// mls is used to do triangle mesh in the future.
// but currently, we need to distinguish obstacle and edge of the
// road first to avoid meshing them with road together, especially
// for the road edge
#include <pcl/search/organized.h>
#include <pcl/search/kdtree.h>
#include <pcl/features/normal_3d_omp.h>
#include <pcl/features/don.h>
#include <pcl/filters/conditional_removal.h>
// #include <pcl/filters/farthest_point_sampling.h>
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
#include <pcl/surface/poisson.h>
#include <pcl/surface/organized_fast_mesh.h>
#include <pcl/surface/reconstruction.h>
#include <pcl/surface/mls.h>
#include <pcl/surface/simplification_remove_unused_vertices.h>
#include <pcl/features/normal_3d.h>
#include <grid_map_ros/grid_map_ros.hpp>
#include <grid_map_msgs/GridMap.h>
#include <ros/ros.h>
#include <sensor_msgs/Imu.h>
#include <sensor_msgs/PointCloud2.h>
#include <tf/transform_datatypes.h>
#include <tf/transform_broadcaster.h>

// #include <mesh_msgs_conversions/conversions.h>
// #include <mesh_msgs/MeshTexture.h>
#include <sensor_msgs/point_cloud_conversion.h>
#include <nav_msgs/Odometry.h>
#include <nav_msgs/OccupancyGrid.h>
#include "tic_toc.h"
#include "common.h"


class Mesh{
public:
    // EIGEN_MAKE_ALIGNED_OPERATOR_NEW
    float score;
    int f_num;
    int pt_num;
    Eigen::VectorXd maxCoeff;
    Eigen::Matrix<double, 3, Eigen::Dynamic> points; // Each column represents a point (3 rows for x, y, z)
    Eigen::Matrix<int, Eigen::Dynamic, 3> faces;
    Mesh():score(0.0),f_num(0),pt_num(0){}
    Mesh(pcl::PolygonMesh::Ptr polygon):score(0.0){
        pcl::PointCloud<pcl::PointXYZ>::Ptr vertice(new pcl::PointCloud<pcl::PointXYZ>);
        pcl::fromPCLPointCloud2(polygon->cloud, *vertice);
        pt_num = vertice->size();
        f_num = polygon->polygons.size();
        points.resize(3,pt_num);
        faces.resize(f_num,3);
        
        int index = 0;
        for(const auto& face : polygon->polygons){
            setface(index,face.vertices[0], face.vertices[1], face.vertices[2]);
            index++;
        }
        // index = 0;
        
        for(int i = 0; i < vertice->size(); i++){
            pcl::PointXYZ pt = vertice->points[i];
            setPoint(i, pt.x, pt.y, pt.z);
        }
    }
    Mesh(int pt_size, int f_size):score(0.0),f_num(f_size),pt_num(pt_size){
        points.resize(3,pt_num);
        faces.resize(f_num,3);
    }
    void clean(){
        score = 0.0;
        f_num = 0;
        pt_num = 0;
        points.resize(0,0);
        faces.resize(0,0);
    }
    bool self_check(){
        if(f_num != faces.rows() || pt_num != points.cols()){
            return true;
        }
        else{
            return false;
        }
    }
    void setPoint(const int& index,const float& x ,const float& y ,const float& z){
        points.col(index) << x , y , z ;
    }
    void setface(const int& index,const int& v1 ,const int& v2 ,const int& v3){
        faces.row(index) << v1 , v2 , v3;
    }
    Mesh & operator+= (const Mesh mesh_add){
        score = std::min(mesh_add.score,score);
        points.conservativeResize(Eigen::NoChange, pt_num + mesh_add.pt_num);
        points.block(0, pt_num, 3, mesh_add.pt_num) = mesh_add.points;
        faces.conservativeResize(faces.rows() + mesh_add.f_num, 3);
        faces.bottomRows(mesh_add.f_num) = mesh_add.faces.array() + pt_num;
        // Eigen::MatrixXd conca_pts(points.rows() , points.cols()+mesh_add.points.cols());
        // conca_pts<< points , mesh_add.points;
        // Eigen::MatrixXi conca_fcs(faces.rows() + mesh_add.faces.rows() , faces.cols());
        // Eigen::MatrixXi addition(mesh_add.faces.rows() , mesh_add.faces.cols());
        // addition.setConstant(pt_num);
        // conca_fcs << faces , mesh_add.faces+ addition;
        f_num += mesh_add.f_num;
        pt_num += mesh_add.pt_num;
        return *this;
    }
    void transform_to_cur(  Eigen::Quaterniond Mv_q_odom, 
                            Eigen::Quaterniond pre_Mv_q_odom,
                            Eigen::Vector3d Mv_t_odom, 
                            Eigen::Vector3d pre_Mv_t_odom
                            ){
        
        for(int i = 0; i < pt_num; i++){
            Eigen::Vector3d point =points.col(i);
            Eigen::Vector3d ori_point = point;
            point = Mv_q_odom.inverse() * ((pre_Mv_q_odom * point) - Mv_t_odom + pre_Mv_t_odom);
            points.col(i) = point;
        }
        maxCoeff = points.rowwise().maxCoeff();
    }
    void output_pc(pcl::PointCloud<PointType>::Ptr &target_pc){
        for(int i = 0; i < pt_num; i++){
            // Eigen::Vector3d points = points.col(i);
            PointType pt;
            pt.x = points(0,i);
            pt.y = points(1,i);
            pt.z = points(2,i);
            pt.intensity = INTENSITY_OBSTACLE;
            target_pc->points.push_back(pt);
        }
    }
    void output_xyzpc(pcl::PointCloud<pcl::PointXYZ>::Ptr &target_pc){
        for(int i = 0; i < pt_num; i++){
            // Eigen::Vector3d points = points.col(i);
            
            pcl::PointXYZ pt;
            pt.x = points(0,i);
            pt.y = points(1,i);
            pt.z = points(2,i);
            std::cout<< pt.x << " " << pt.y <<" " << pt.z << "; ";
            target_pc->points.push_back(pt);
        }
    }
    void copy(Mesh* mesh_cpy){
        f_num = mesh_cpy->f_num;
        pt_num = mesh_cpy->pt_num;
        score = mesh_cpy->score;
        points = mesh_cpy->points;
        faces = mesh_cpy->faces;
    }
    bool improve(pcl::PolygonMesh::Ptr &triangular_mesh){
        pcl::MovingLeastSquares<pcl::PointXYZ,pcl::PointNormal> mls;
        pcl::PointCloud<pcl::PointXYZ>::Ptr cloud_xyz (new pcl::PointCloud<pcl::PointXYZ>);
        // pcl::MeshProcessing Mp; 
        // pcl::SurfaceReconstruction<> SR; 
        std::vector<int> indices;
        // this->output_xyzpc(cloud_xyz);
        ROS_INFO("ori_pc num: %d", pt_num);
        for( int i = 0; i < pt_num; i++){
            pcl::PointXYZ pt;
            pt.x = points(0,i);
            pt.y = points(1,i);
            pt.z = points(2,i);
            // std::cout<< std::setprecision(10) <<pt.x << " " << std::setprecision(10) << pt.y <<" " << std::setprecision(10) << pt.z << "; ";
            if(pcl::isFinite(pt)){
                cloud_xyz->push_back(pt);
            }
            else{
                ROS_WARN("Invalid point coordinates!");
                continue;
            }
        }
        pcl::removeNaNFromPointCloud(*cloud_xyz, *cloud_xyz, indices);
        if(cloud_xyz->size() != pt_num){
            ROS_WARN("Someting wrong with output_pc"); 
        }
        if(cloud_xyz->size() == 0){
            return false;
        }
        pcl::search::KdTree<pcl::PointXYZ>::Ptr tree (new pcl::search::KdTree<pcl::PointXYZ>);
        pcl::search::KdTree<pcl::PointNormal>::Ptr tree2 (new pcl::search::KdTree<pcl::PointNormal>);
        pcl::PointCloud<pcl::PointNormal>::Ptr cloud_with_normals (new pcl::PointCloud<pcl::PointNormal>);
        pcl::GreedyProjectionTriangulation<pcl::PointNormal> gp3;
        // tree->setInputCloud(cloud_xyz);
        ROS_WARN("Tree 1");
        mls.setSearchRadius(1);
        mls.setPolynomialFit(true);
        mls.setComputeNormals(true);
        mls.setPolynomialOrder(2);
        mls.setUpsamplingMethod(pcl::MovingLeastSquares<pcl::PointXYZ, pcl::PointNormal>::RANDOM_UNIFORM_DENSITY);
        
        // mls.setUpsamplingMethod(pcl::MovingLeastSquares<pcl::PointXYZ, pcl::PointNormal>::VOXEL_GRID_DILATION);
        // mls.setDilationVoxelSize(0.1);
        // mls.setDilationIterations(1s);
        // mls.setPointDensity(50);
        mls.setUpsamplingRadius(0.1);
        mls.setUpsamplingStepSize(0.05);
        mls.setInputCloud(cloud_xyz);
        mls.setSearchMethod(tree);
        mls.process(*cloud_with_normals);
        pcl::removeNaNFromPointCloud(*cloud_with_normals, *cloud_with_normals, indices);
        ROS_INFO("Normal_pc num: %d", cloud_with_normals->size());
        indices.clear();
        for(int i = 0; i < cloud_with_normals->size(); i++){
            pcl::PointNormal pt = cloud_with_normals->points[i];
            if(std::isnan(pt.x) || std::isnan(pt.y) || std::isnan(pt.z) ){
                indices.push_back(i);
            }    
            // ROS_INFO("pt x: %05f, y: %05f, z: %05f", pt.x , pt.y , pt.z);
        }
        if(cloud_with_normals->size() == 0){
            return false;
        }
        pcl::PointIndices::Ptr nan_indices(new pcl::PointIndices());
        nan_indices->indices = indices;
        pcl::ExtractIndices<pcl::PointNormal> extract;
        extract.setInputCloud(cloud_with_normals);
        extract.setIndices(nan_indices);
        extract.setNegative(true);
        extract.filter(*cloud_with_normals);

        gp3.setSearchRadius(1);
        gp3.setMu(2.5);
        gp3.setMaximumSurfaceAngle(M_PI*2/3);//M_PI/2 someone said 45deg is a good option
        gp3.setMinimumAngle(M_PI/18);
        gp3.setMaximumAngle(M_PI*2/3);//M_PI*2/3
        gp3.setMaximumNearestNeighbors(150);
        gp3.setNormalConsistency(false);
        indices.clear();
        
        ROS_WARN("Tree 2");
        // tree2->setInputCloud(cloud_with_normals);
        gp3.setSearchMethod(tree2);
        gp3.setInputCloud(cloud_with_normals);
        ROS_WARN("RECONSTRUCTION");        
        gp3.reconstruct(*triangular_mesh);
        return true;
    }
};

// class MeshMap
// {
//     //This will be handled as always 
// public:
//     int vertex_num;
//     int glb_obs_triangle_num;
//     mesh_msgs::MeshGeometryStamped tmp_mesh;
//     std::set<std::pair<int, int>> uniqueEdge;
//     std::unordered_set<int> all_id;
//     std::unordered_map<int,float> mesh_score_table;
//     MeshMap():vertex_num(0),glb_obs_triangle_num(0){
//         tmp_mesh.header.frame_id = "camera_init";
//         // tmp_mesh.header.stamp = ros::Time::now();
//         uniqueEdge.clear();
//     }
//     void init(){
//         mesh_msgs::MeshGeometryStamped new_mesh;
//         new_mesh.header.frame_id = "camera_init";
//         new_mesh.header.stamp = ros::Time::now();
//         tmp_mesh = new_mesh;
//         glb_obs_triangle_num = 0;
//         vertex_num = 0;
//         uniqueEdge.clear();
//     }
//     void Inputground(GRID_INFO* grid_array[], const std::set<int> &available_grid, const int &ARRAY_NY);
//     void InputIntersection(GRID_INFO* grid_array[], const std::set<int> &intersection_grid,const std::set<int> & available_grid, const int &ARRAY_NY);
//     void Inputobstacle(const std::unordered_map<int, pcl::PointCloud<PointType>::Ptr >& obs_map,
//                             std::unordered_map<int, Mesh*>& completed_obstacle,
//                             std::unordered_set<int>& id_set);
    
//     void InputAllAtOnce(pcl::PointCloud<PointType>::Ptr cloud_out);
//     void g_triangulation();
//     void Evaluation();
//     bool Obs_mesh_Evaluation(   const int & obs_id, 
//                                 const int & tri_num,
//                                 const int & edge_num, 
//                                 const int & used_vertex, 
//                                 const int & total_vertex);

//     void PrepareDisplay(pcl::PolygonMesh::Ptr upload_mesh ,Mesh *best_mesh_record);
//     void refine(Mesh* coarse_Mesh);
// };

// class OCC_Labeler{
//     public:
//         OCC_Labeler();
//         ~OCC_Labeler(){};
//         void Static_Scene_Reconstruct(){}
//         void Movable_Obj(){}
// };