#include <grid_map_core/grid_map_core.hpp>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <iostream>
#include "tic_toc.h"
#include "common.h"
using namespace grid_map;
struct RiskFactorSetting {
    std::string layer;
    float weight;
};

class CVaRCalculator {
public:
    CVaRCalculator(float alpha, const std::vector<RiskFactorSetting>& riskFactors)
        : alpha_(alpha), riskFactors_(riskFactors) {
        z_ = approx_erfinv(alpha_);
        phi_ = normalPDF(z_);
        cvarFactor_ = phi_ / (1.0 - alpha_);
    }

    // 计算某个 cell 的 CVaR
    float computeCellCVaR(const GridMap& map, const Index& index) {
        float mu = 0.0f;
        float sigma2 = 0.0f;

        // Cache layer data references
        std::vector<std::pair<const Matrix*, float>> layerData;
        for (const auto& rf : riskFactors_) {
            if (map.exists(rf.layer)) {
                layerData.emplace_back(&map[rf.layer], rf.weight);
            }
        }
        // #pragma omp parallel for
        for (const auto& [data, weight] : layerData) {
            float value = (*data)(index(0), index(1));
            if (!std::isfinite(value)) continue;

            float var = computeLocalVariance(map, data, index);
            mu += weight * value;
            sigma2 += weight * weight * var;
        }

        return mu + std::sqrt(sigma2) * cvarFactor_;
    }

private:
    float alpha_;
    float z_;
    float phi_;
    float cvarFactor_;
    std::vector<RiskFactorSetting> riskFactors_;
    /**
     * Computes variance of values in a 3x3 window around the given grid cell
     * 
     * @param map The grid map containing the data
     * @param layer The layer name to compute variance for
     * @param index The center cell index (x,y)
     * @return Variance of the 3x3 neighborhood (returns 0 if <2 valid neighbors)
     * 
     * Implementation details:
     * - Uses direct matrix access for performance
     * - Checks all 8 neighbors + center cell
     * - Uses Welford's algorithm for numerical stability
     * - Skips invalid/NaN values
     */
    float computeLocalVariance(const GridMap& map, const Matrix* data, const Index& index) {
        const Size size = map.getSize();
        
        static const std::vector<std::pair<int,int>> offsets = {
            {-1,-1}, {-1,0}, {-1,1},
            {0,-1},  {0,0},  {0,1},
            {1,-1},  {1,0},  {1,1}
            // {-1,0}, {0,0},  {1,0}
        };

        float sum = 0.0f;
        float sum_sq = 0.0f;
        int count = 0;
        float hei_diff = 0.0f;
        #pragma omp parallel for
        for (const auto& offset : offsets) {
            int x = index(0) + offset.first;
            int y = index(1) + offset.second;
            
            if (x >= 0 && x < size(0) && y >= 0 && y < size(1)) {
                float value = (*data)(x, y);
                if (std::isfinite(value)) {
                    sum += value;
                    sum_sq += value * value;
                    count++;
                }
            }
        }

        if (count < 2) return 0.0f;
        
        float mean = sum / count;
        return (sum_sq - sum * mean) / count;
    }

    float computeLocalVariance(const GridMap& map, const std::string& layer, const Index& index) {
        return computeLocalVariance(map, &map[layer], index);
    }
};
