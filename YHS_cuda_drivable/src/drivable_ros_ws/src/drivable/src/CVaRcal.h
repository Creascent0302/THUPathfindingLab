#pragma once
#include <grid_map_core/grid_map_core.hpp>
#include <unordered_map>
#include <vector>
#include <string>
#include <cmath>
#include <iostream>
#include "tic_toc.h"
using namespace grid_map;

struct RiskFactorSetting {
    std::string layer;
    float weight;
};

class CVaRCalculator {
public:
    CVaRCalculator(float alpha, const std::vector<RiskFactorSetting>& riskFactors);

    void prepare(const GridMap& map); // 预处理所有积分图
    float computeCellCVaR(const Index& index) const;

private:
    float computeLocalVariance(const std::string& layer, int x, int y) const;
    void computeIntegralImage(const Matrix& input, Matrix& sum, Matrix& sqsum, Matrix& count);

    float alpha_, z_, phi_, cvarFactor_;
    std::vector<RiskFactorSetting> riskFactors_;
    std::unordered_map<std::string, Matrix> countIntegrals_;
    std::unordered_map<std::string, Matrix> meanIntegrals_;
    std::unordered_map<std::string, Matrix> sqIntegrals_;
    std::unordered_map<std::string, const Matrix*> layerRefs_;
};
