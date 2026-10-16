#include "CVaRcal_cuda.h"
#include <cuda_runtime.h>
#include <iostream>
#include <stdexcept>
// 正态分布的 PDF
float CVaRCalculatorCUDA::normalPDF(float x) {
    return std::exp(-0.5f * x * x) / std::sqrt(2.0f * M_PI);
}

// 简单近似 inverse erf
float CVaRCalculatorCUDA::approx_erfinv(float x) {
    float a = 0.147;
    float ln = std::log(1 - x * x);
    float t1 = 2 / (M_PI * a) + ln / 2.0;
    float t2 = ln / a;
    return std::copysign(std::sqrt(std::sqrt(t1 * t1 - t2) - t1), x);
}

// 构造函数
CVaRCalculatorCUDA::CVaRCalculatorCUDA(float alpha, const std::vector<RiskFactorSettingCUDA>& riskFactors)
    : alpha_(alpha), riskFactors_(riskFactors) {
    z_ = approx_erfinv(alpha_);
    phi_ = normalPDF(z_);
    cvarFactor_ = phi_ / (1.0f - alpha_);
}

// 析构函数
CVaRCalculatorCUDA::~CVaRCalculatorCUDA() {
    freeGPUMemory();
}
extern void computeIntegralImageCUDAWarpper(
    const Matrix &input, 
    Matrix &sum, 
    Matrix &sqsum, 
    Matrix &count);
void compute_cvar_kernel(
    const float **layer_data,
    const float **layer_variance,
    const float *weights,
    int num_layers,
    float cvar_factor,
    float *cvar_result,
    int rows, int cols);
void compute_local_variance_kernel(
    const float *sum_integral,
    const float *sq_integral,
    const float *count_integral,
    float *variance_output,
    int rows, int cols, int window_radius);
void column_scan_kernel(const float *row_sum, float *integral, int rows, int cols);
void row_scan_kernel(const float *input, float *output, int rows, int cols);
// GPU内存分配
void CVaRCalculatorCUDA::allocateGPUMemory() {
    freeGPUMemory(); // 先释放已有内存
    
    for (const auto& [layerName, layerData] : layerRefs_) {
        int rows = layerData->rows();
        int cols = layerData->cols();
        size_t size = rows * cols * sizeof(float);
        
        GPULayerData gpuData;
        gpuData.rows = rows;
        gpuData.cols = cols;
        
        cudaMalloc(&gpuData.data, size);
        cudaMalloc(&gpuData.sumIntegral, (rows + 1) * (cols + 1) * sizeof(float));
        cudaMalloc(&gpuData.sqIntegral, (rows + 1) * (cols + 1) * sizeof(float));
        cudaMalloc(&gpuData.countIntegral, (rows + 1) * (cols + 1) * sizeof(float));
        
        gpuLayerData_[layerName] = gpuData;
    }
}

// GPU内存释放
void CVaRCalculatorCUDA::freeGPUMemory() {
    for (auto& [layerName, gpuData] : gpuLayerData_) {
        if (gpuData.data) cudaFree(gpuData.data);
        if (gpuData.sumIntegral) cudaFree(gpuData.sumIntegral);
        if (gpuData.sqIntegral) cudaFree(gpuData.sqIntegral);
        if (gpuData.countIntegral) cudaFree(gpuData.countIntegral);
        
        gpuData.data = nullptr;
        gpuData.sumIntegral = nullptr;
        gpuData.sqIntegral = nullptr;
        gpuData.countIntegral = nullptr;
    }
    gpuLayerData_.clear();
}

// 数据拷贝到GPU
void CVaRCalculatorCUDA::copyDataToGPU(const GridMap& map) {
    for (const auto& rf : riskFactors_) {
        if (!map.exists(rf.layer)) continue;
        
        const Matrix& data = map[rf.layer];
        auto it = gpuLayerData_.find(rf.layer);
        if (it != gpuLayerData_.end()) {
            size_t size = data.rows() * data.cols() * sizeof(float);
            cudaMemcpy(it->second.data, data.data(), size, cudaMemcpyHostToDevice);
        }
    }
}

// 从GPU拷贝数据
void CVaRCalculatorCUDA::copyDataFromGPU() {
    // 如果需要从GPU读取结果数据，可以在这里实现
}

// CPU版本的积分图计算（保持原有实现）
void CVaRCalculatorCUDA::computeIntegralImage(const Matrix& input, Matrix& sum, Matrix& sqsum, Matrix& count) {
    int rows = input.rows();
    int cols = input.cols();
    
    sum = Matrix::Zero(rows + 1, cols + 1);
    sqsum = Matrix::Zero(rows + 1, cols + 1);
    count = Matrix::Zero(rows + 1, cols + 1);

    for (int i = 0; i < rows; ++i) {
        float row_sum = 0.0f, row_sqsum = 0.0f, row_count = 0.0f;
        for (int j = 0; j < cols; ++j) {
            float val = input(i, j);
            if (std::isfinite(val)) {
                row_sum += val;
                row_sqsum += val * val;
                row_count += 1.0f;
            }
            sum(i + 1, j + 1) = sum(i, j + 1) + row_sum;
            sqsum(i + 1, j + 1) = sqsum(i, j + 1) + row_sqsum;
            count(i + 1, j + 1) = count(i, j + 1) + row_count;
        }
    }
}


// CPU版本的局部方差计算
float CVaRCalculatorCUDA::computeLocalVariance(const std::string& layer, int x, int y) const {
    const Matrix& data = *layerRefs_.at(layer);
    int rows = data.rows();
    int cols = data.cols();
    
    float S = 0.0f, SS = 0.0f, n = 0.0f;
    int r = 1; // 窗口半径
    
    for (int i = std::max(0, y - r); i <= std::min(rows - 1, y + r); ++i) {
        for (int j = std::max(0, x - r); j <= std::min(cols - 1, x + r); ++j) {
            float val = data(i, j);
            if (std::isfinite(val)) {
                S += val;
                SS += val * val;
                n += 1.0f;
            }
        }
    }
    
    if (n <= 2.0f) return 0.0f;
    return (SS - (S * S) / n) / (n - 1.0f);
}

// 预处理
void CVaRCalculatorCUDA::prepare(const GridMap& map) {
    useCUDA_= true;
    if (useCUDA_) {
        prepareCUDA(map);
    } else {
        meanIntegrals_.clear();
        sqIntegrals_.clear();
        layerRefs_.clear();

        for (const auto& rf : riskFactors_) {
            if (!map.exists(rf.layer)) continue;

            const Matrix& data = map[rf.layer];
            layerRefs_[rf.layer] = &data;

            Matrix sum, sqsum, count;
            computeIntegralImage(data, sum, sqsum, count);
            
            meanIntegrals_[rf.layer] = std::move(sum);
            sqIntegrals_[rf.layer] = std::move(sqsum);
            countIntegrals_[rf.layer] = std::move(count);
        }
    }
}

// CUDA版本的预处理
void CVaRCalculatorCUDA::prepareCUDA(const GridMap& map) {
    meanIntegrals_.clear();
    sqIntegrals_.clear();
    layerRefs_.clear();

    for (const auto& rf : riskFactors_) {
        if (!map.exists(rf.layer)) continue;

        const Matrix& data = map[rf.layer];
        layerRefs_[rf.layer] = &data;

        Matrix sum, sqsum, count;
        computeIntegralImageCUDAWarpper(data, sum, sqsum, count);
        
        meanIntegrals_[rf.layer] = std::move(sum);
        sqIntegrals_[rf.layer] = std::move(sqsum);
        countIntegrals_[rf.layer] = std::move(count);
    }
}


void CVaRCalculatorCUDA::compute(GridMap& map) {
    // if (useCUDA_) {
    //     Matrix& data = map["CVaR"];   // 提取出 CVaR 层
    //     computeCUDA(data);            // 直接在 matrix 上做 CUDA 计算
    // } else {
    for (grid_map::GridMapIterator it(map); !it.isPastEnd(); ++it) {
        const Index index(*it);
        if (map.isValid(index, riskFactors_[0].layer)) {
            map.at("CVaR", index) = computeCellCVaR(index);
        } else {
            map.at("CVaR", index) = 1.0f;  // 无效格子设为默认值
        }
    }
    // }
}

// void CVaRCalculatorCUDA::computeCUDA(const GridMap& map){
//     for (grid_map::GridMapIterator it(map); !it.isPastEnd(); ++it) {
//         const Index index(*it);
//         if (map.isValid(index, riskFactors_[0].layer)) {
//             map.at("CVaR", index) = computeCellCVaR(index);
//         } else {
//             map.at("CVaR", index) = 1.0f;  // 无效格子设为默认值
//         }
//     }
// }
// 计算单个cell的CVaR
float CVaRCalculatorCUDA::computeCellCVaR(const Index& index) const {
    float mu = 0.0f;
    float sigma2 = 0.0f;

    int x = index(0), y = index(1);
    for (const auto& rf : riskFactors_) {
        const Matrix* layer = layerRefs_.at(rf.layer);
        float value = (*layer)(x, y);
        if (!std::isfinite(value)) continue;
        float var = 0;
        var = computeLocalVariance(rf.layer, x, y);
        
        mu += rf.weight * value;
        sigma2 += rf.weight * rf.weight * var;
    }
    sigma2 = std::max(sigma2, 0.0f);
    return mu + std::sqrt(sigma2) * cvarFactor_;
}

