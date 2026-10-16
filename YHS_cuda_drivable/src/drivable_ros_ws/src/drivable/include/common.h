
#pragma once

#include <cmath>
#include <boost/math/special_functions/erf.hpp>
#include <pcl/point_types.h>

typedef pcl::PointXYZI PointType;

#define ABS(x) (((x)>0)?(x):-1*(x))
//Drivable green 10, 
//Undrivable pink 30, 
//UNKNOWN bright blue 20, 
//OBSTACLE yellow 5,
//Dense deep blue 25?,
#define INTENSITY_DRIVABLE      (30)
#define INTENSITY_UNKNOWN       (20)
#define INTENSITY_NON_DRIVABLE  (30)
#define INTENSITY_GRASS         (10)
#define INTENSITY_CURB          (2)
#define INTENSITY_OBSTACLE      (25)
#define INTENSITY_OCCLUDE       (2)

inline double rad2deg(double radians)
{
  return radians * 180.0 / M_PI;
}

inline double deg2rad(double degrees)
{
  return degrees * M_PI / 180.0;
}
