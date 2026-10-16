#include "ray_tracing.h"
#include <cmath>
#include <algorithm>
#include <limits>

RayTracing::GridMap RayTracing::process(const PointCloud::ConstPtr& cloud,
                                      float angular_resolution,
                                      const Eigen::Vector2i& grid_size,
                                      float max_range) {
    // Initialize grid map (all cells initially marked as occluded)
    GridMap grid(grid_size.y(), std::vector<bool>(grid_size.x(), false));

    if (!cloud || cloud->empty()) {
        return grid;
    }

    // Calculate number of rays based on angular resolution
    int num_rays = std::ceil(2 * M_PI / angular_resolution);

    // Perform ray tracing for each angle
    for (int i = 0; i < num_rays; ++i) {
        float angle = i * angular_resolution;
        traceRay(angle, grid, cloud, angular_resolution, max_range);
    }

    return grid;
}

void RayTracing::traceRay(float angle, GridMap& grid,
                         const PointCloud::ConstPtr& cloud,
                         float angular_resolution,
                         float max_range) {
    // Calculate ray direction
    float dx = std::cos(angle);
    float dy = std::sin(angle);

    // Get grid dimensions
    int width = grid[0].size();
    int height = grid.size();

    // Start from center of grid
    float x = width / 2.0f;
    float y = height / 2.0f;

    // Find closest valid obstacle point along this ray
    float min_dist = max_range; // Default to max range
    for (const auto& point : *cloud) {
        // Filter ground points (adjust height threshold as needed)
        if (point.z < -0.5f || point.z > 0.5f) {
            continue;
        }

        float point_angle = std::atan2(point.y, point.x);
        float angle_diff = std::abs(point_angle - angle);
        angle_diff = std::min(angle_diff, 2*M_PI - angle_diff); // Handle wrap-around
        
        if (angle_diff < angular_resolution/2) {
            float dist = std::hypot(point.x, point.y);
            if (dist < min_dist && dist <= max_range) {
                min_dist = dist;
            }
        }
    }

    // Trace ray until hitting closest point or edge of grid
    float dist = 0;
    float step = 0.1f; // Step size for ray marching
    while (x >= 0 && x < width && y >= 0 && y < height && dist < min_dist) {
        int ix = static_cast<int>(x);
        int iy = static_cast<int>(y);

        // Mark cell as visible
        grid[iy][ix] = true;

        // Move along ray
        x += dx * step;
        y += dy * step;
        dist += step;
    }
}
