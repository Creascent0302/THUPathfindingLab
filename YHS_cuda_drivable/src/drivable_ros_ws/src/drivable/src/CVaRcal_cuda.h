#pragma once
#include <grid_map_core/grid_map_core.hpp>
#include <unordered_map>
#include <vector>
#include <string>
#include <cmath>
#include <iostream>
#include "tic_toc.h"
#include <cuda_runtime.h>

using namespace grid_map;

struct RiskFactorSettingCUDA
{
    std::string layer;
    float weight;
};
void computeIntegralImageCUDA(const Matrix &input, Matrix &sum, Matrix &sqsum, Matrix &count);
void computeCVaRCUDAWrapper(grid_map::GridMap &map,
                            const std::vector<float> &weights,
                            const std::vector<std::string> &layers,
                            float cvarFactor);
class CVaRCalculatorCUDA
{
public:
    CVaRCalculatorCUDA(float alpha, const std::vector<RiskFactorSettingCUDA> &riskFactors);
    ~CVaRCalculatorCUDA();

    void prepare(const GridMap &map); // 预处理所有积分图
    void compute(GridMap& map); // 基于积分图进行运算
    float computeCellCVaR(const Index &index) const;

    // CUDA specific methods
    void prepareCUDA(const GridMap &map);
    void computeAllCVaRCUDA(Matrix &cvarResult) const;

private:
    // CPU methods
    float computeLocalVariance(const std::string &layer, int x, int y) const;
    void computeIntegralImage(const Matrix &input, Matrix &sum, Matrix &sqsum, Matrix &count);

    float computeLocalVarianceCUDA(const std::string &layer, int x, int y) const;

    // GPU memory management
    void allocateGPUMemory();
    void freeGPUMemory();
    void copyDataToGPU(const GridMap &map);
    void copyDataFromGPU();
    float approx_erfinv(float x);
    float normalPDF(float x);
    float alpha_, z_, phi_, cvarFactor_;
    std::vector<RiskFactorSettingCUDA> riskFactors_;
    std::unordered_map<std::string, Matrix> countIntegrals_;
    std::unordered_map<std::string, Matrix> meanIntegrals_;
    std::unordered_map<std::string, Matrix> sqIntegrals_;
    std::unordered_map<std::string, const Matrix *> layerRefs_;

    // GPU memory pointers
    struct GPULayerData
    {
        float *data = nullptr;
        float *sumIntegral = nullptr;
        float *sqIntegral = nullptr;
        float *countIntegral = nullptr;
        int rows = 0;
        int cols = 0;
    };

    std::unordered_map<std::string, GPULayerData> gpuLayerData_;
    bool useCUDA_ = true;
};
