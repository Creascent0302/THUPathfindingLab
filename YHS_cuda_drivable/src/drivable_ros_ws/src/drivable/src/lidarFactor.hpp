// Author:   Tong Qin               qintonguav@gmail.com
// 	         Shaozu Cao 		    saozu.cao@connect.ust.hk

#include <ceres/ceres.h>
#include <ceres/rotation.h>
#include <eigen3/Eigen/Dense>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/kdtree/kdtree_flann.h>
#include <pcl_conversions/pcl_conversions.h>



// 点到线的残差距离计算
struct LidarEdgeFactor
{
	LidarEdgeFactor(
        Eigen::Vector3d curr_point_, 
        Eigen::Vector3d last_point_a_,
        Eigen::Vector3d last_point_b_, 
        double s_) :     
            curr_point(curr_point_), 
            last_point_a(last_point_a_), 
            last_point_b(last_point_b_), 
            s(s_) {}

	template <typename T> //T is double, or array of double 
	bool operator()(const T *q, const T *t, T *residual) const
	{
		Eigen::Matrix<T, 3, 1> cp{T(curr_point.x()), T(curr_point.y()), T(curr_point.z())};
		Eigen::Matrix<T, 3, 1> lpa{T(last_point_a.x()), T(last_point_a.y()), T(last_point_a.z())};
		Eigen::Matrix<T, 3, 1> lpb{T(last_point_b.x()), T(last_point_b.y()), T(last_point_b.z())};

		//Eigen::Quaternion<T> q_last_curr{q[3], T(s) * q[0], T(s) * q[1], T(s) * q[2]};
		Eigen::Quaternion<T> q_last_curr{q[3], q[0], q[1], q[2]};
		Eigen::Quaternion<T> q_identity{T(1), T(0), T(0), T(0)};
		
        // 考虑运动补偿，ktti点云已经补偿过所以可以忽略下面的对四元数slerp插值以及对平移的线性插值
		// If I am thinking this correctly, s is the sample rate or slerp rate.
        q_last_curr = q_identity.slerp(T(s), q_last_curr);
		Eigen::Matrix<T, 3, 1> t_last_curr{T(s) * t[0], T(s) * t[1], T(s) * t[2]};

		Eigen::Matrix<T, 3, 1> lp;
		// Odometry线程时，下面是将当前帧Lidar坐标系下的cp点变换到上一帧的Lidar坐标系下，
        // 然后在上一帧的Lidar坐标系计算点到线的残差距离
        // Mapping线程时，下面是将当前帧Lidar坐标系下的cp点变换到world坐标系下，
        // 然后在world坐标系下计算点到线的残差距离
        lp = q_last_curr * cp + t_last_curr; //cp 转到相同坐标系下，变成lp

		// 点到线的计算如下图所示
        // 三角形面积， a*b = |a||b|sin(theta)n  n是垂直a和b的单位向量
		Eigen::Matrix<T, 3, 1> nu = (lp - lpa).cross(lp - lpb); 
		Eigen::Matrix<T, 3, 1> de = lpa - lpb; //底边长度

		// 最终的残差本来应该是residual[0] = nu.norm() / de.norm(); 为啥也分成3个，我也不知
        // 道，从我试验的效果来看，确实是下面的残差函数形式，最后输出的pose精度会好一点点，这里需要
        // 注意的是，所有的residual都不用加fabs，因为Ceres内部会对其求 平方 作为最终的残差项
		//距离分量，三个方向的分量

		//I have the difficulty in understanding this part. From my understanding, the cross product
		//is the vector with the magintude of the two vectors and normal to both vectors.
		//OK, a*b/c is residual. 
		//|A X B| / | C | WHY NOT JUST USE NORM OF NU INSTEAD OF NU.X()...
		residual[0] = nu.x() / de.norm(); 
		residual[1] = nu.y() / de.norm();
		residual[2] = nu.z() / de.norm();
		
		residual[0] = nu.norm() / de.norm(); 
		residual[1] = nu.norm() / de.norm();
		residual[2] = nu.norm() / de.norm();
		return true;
	}

	static ceres::CostFunction *Create(const Eigen::Vector3d curr_point_, const Eigen::Vector3d last_point_a_,
									   const Eigen::Vector3d last_point_b_, const double s_)
	{
		return (new ceres::AutoDiffCostFunction<
				LidarEdgeFactor, 3, 4, 3>(new LidarEdgeFactor(curr_point_, last_point_a_, last_point_b_, s_)));
                //3： 残差的维度
                //4： 优化变量q的维度
                //3： 优化变量t的维度
	}

	Eigen::Vector3d curr_point, last_point_a, last_point_b;
	double s;
};








// 计算Odometry线程中点到面的残差距离
struct LidarPlaneFactor
{
	LidarPlaneFactor(
        Eigen::Vector3d curr_point_, 
        Eigen::Vector3d last_point_j_,
        Eigen::Vector3d last_point_l_, 
        Eigen::Vector3d last_point_m_, 
        double s_) : 
            curr_point(curr_point_), 
            last_point_j(last_point_j_), 
            last_point_l(last_point_l_),
            last_point_m(last_point_m_), 
            s(s_)
	{
		// 点l、j、m就是搜索到的最近邻的3个点，下面就是计算出这三个点构成的平面ljlm的法向量
        // 叉乘就是法向量
		ljm_norm = (last_point_j - last_point_l).cross(last_point_j - last_point_m);
		
        // 归一化法向量
		ljm_norm.normalize();
	}

	template <typename T>
	bool operator()(const T *q, const T *t, T *residual) const
	{

		Eigen::Matrix<T, 3, 1> cp{T(curr_point.x()), T(curr_point.y()), T(curr_point.z())};
		Eigen::Matrix<T, 3, 1> lpj{T(last_point_j.x()), T(last_point_j.y()), T(last_point_j.z())};
		Eigen::Matrix<T, 3, 1> ljm{T(ljm_norm.x()), T(ljm_norm.y()), T(ljm_norm.z())};

		//Eigen::Quaternion<T> q_last_curr{q[3], T(s) * q[0], T(s) * q[1], T(s) * q[2]};
		Eigen::Quaternion<T> q_last_curr{q[3], q[0], q[1], q[2]};
		Eigen::Quaternion<T> q_identity{T(1), T(0), T(0), T(0)};
		q_last_curr = q_identity.slerp(T(s), q_last_curr);
		Eigen::Matrix<T, 3, 1> t_last_curr{T(s) * t[0], T(s) * t[1], T(s) * t[2]};

		Eigen::Matrix<T, 3, 1> lp;
		lp = q_last_curr * cp + t_last_curr;

		// 计算点到平面的残差距离，如下图所示
        // 点乘 ab=|a||b|*cos(theta)，即lp-lpj在法向量ljm上的投影
        // 讲解网页上的图错了
		residual[0] = (lp - lpj).dot(ljm);

		return true;
	}

	static ceres::CostFunction *Create(const Eigen::Vector3d curr_point_, const Eigen::Vector3d last_point_j_,
									   const Eigen::Vector3d last_point_l_, const Eigen::Vector3d last_point_m_,
									   const double s_)
	{
		return (new ceres::AutoDiffCostFunction<
				LidarPlaneFactor, 1, 4, 3>(new LidarPlaneFactor(curr_point_, last_point_j_, last_point_l_, last_point_m_, s_)));
                //1： 残差的维度
                //4： 优化变量q的维度
                //3： 优化变量t的维度
	}

	Eigen::Vector3d curr_point, last_point_j, last_point_l, last_point_m;
	Eigen::Vector3d ljm_norm;
	double s;
};







//计算Mapping线程中点到平面的残差距离
//因为输入了平面方程的参数（），所以直接使用点到面的距离公式进行计算：
struct LidarPlaneNormFactor
{

	LidarPlaneNormFactor(
        Eigen::Vector3d curr_point_, 
        Eigen::Vector3d plane_unit_norm_,
		double negative_OA_dot_norm_) : 
                curr_point(curr_point_), 
                plane_unit_norm(plane_unit_norm_),
                negative_OA_dot_norm(negative_OA_dot_norm_) {}

	template <typename T>
	bool operator()(const T *q, const T *t, T *residual) const
	{
		Eigen::Quaternion<T> q_w_curr{q[3], q[0], q[1], q[2]};
		Eigen::Matrix<T, 3, 1> t_w_curr{t[0], t[1], t[2]};
		Eigen::Matrix<T, 3, 1> cp{T(curr_point.x()), T(curr_point.y()), T(curr_point.z())};
		Eigen::Matrix<T, 3, 1> point_w;
		point_w = q_w_curr * cp + t_w_curr;

		Eigen::Matrix<T, 3, 1> norm(T(plane_unit_norm.x()), T(plane_unit_norm.y()), T(plane_unit_norm.z()));
		
        // 点(x0, y0, z0)到平面Ax + By + Cz + D = 0 的
        // 距离 = fabs(A*x0 + B*y0 + C*z0 + D) / sqrt(A^2 + B^2 + C^2)，
        // 因为法向量（A, B, C）已经归一化了，所以距离公式可以简写为：
        // 距离 = fabs(A*x0 + B*y0 + C*z0 + D) ，即：
        // negative_OA_dot_norm也就是D
        residual[0] = norm.dot(point_w) + T(negative_OA_dot_norm);
		return true;
	}

	static ceres::CostFunction *Create(const Eigen::Vector3d curr_point_, const Eigen::Vector3d plane_unit_norm_,
									   const double negative_OA_dot_norm_)
	{
		return (new ceres::AutoDiffCostFunction<
				LidarPlaneNormFactor, 1, 4, 3>(
			new LidarPlaneNormFactor(curr_point_, plane_unit_norm_, negative_OA_dot_norm_)));
	}

	Eigen::Vector3d curr_point;
	Eigen::Vector3d plane_unit_norm;
	double negative_OA_dot_norm;
};


struct LidarDistanceFactor
{

	LidarDistanceFactor(
        Eigen::Vector3d curr_point_, 
        Eigen::Vector3d closed_point_)  : 
            curr_point(curr_point_), 
            closed_point(closed_point_){}

	template <typename T>
	bool operator()(const T *q, const T *t, T *residual) const
	{
		Eigen::Quaternion<T> q_w_curr{q[3], q[0], q[1], q[2]};
		Eigen::Matrix<T, 3, 1> t_w_curr{t[0], t[1], t[2]};
		Eigen::Matrix<T, 3, 1> cp{T(curr_point.x()), T(curr_point.y()), T(curr_point.z())};
		Eigen::Matrix<T, 3, 1> point_w;
		point_w = q_w_curr * cp + t_w_curr;

		residual[0] = point_w.x() - T(closed_point.x());
		residual[1] = point_w.y() - T(closed_point.y());
		residual[2] = point_w.z() - T(closed_point.z());
		return true;
	}

	static ceres::CostFunction *Create(const Eigen::Vector3d curr_point_, const Eigen::Vector3d closed_point_)
	{
		return (new ceres::AutoDiffCostFunction<
				LidarDistanceFactor, 3, 4, 3>(
			new LidarDistanceFactor(curr_point_, closed_point_)));
	}

	Eigen::Vector3d curr_point;
	Eigen::Vector3d closed_point;
};