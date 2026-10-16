#include "CVaRcal.h"
TicToc t_CVAR;
// 正态分布的 PDF
inline float normalPDF(float x) {
    return std::exp(-0.5f * x * x) / std::sqrt(2.0f * M_PI);
}

// 简单近似 inverse erf
inline float approx_erfinv(float x) {
    float a = 0.147;
    float ln = std::log(1 - x * x);
    float t1 = 2 / (M_PI * a) + ln / 2.0;
    float t2 = ln / a;
    return std::copysign(std::sqrt(std::sqrt(t1 * t1 - t2) - t1), x);
}

// 构造函数
CVaRCalculator::CVaRCalculator(float alpha, const std::vector<RiskFactorSetting>& riskFactors)
    : alpha_(alpha), riskFactors_(riskFactors) {
    z_ = approx_erfinv(alpha_);
    phi_ = normalPDF(z_);
    cvarFactor_ = phi_ / (1.0f - alpha_);
}

// 构建积分图
// 修改后的积分图计算（无填充）
void CVaRCalculator::computeIntegralImage(const Matrix& input, Matrix& sum, Matrix& sqsum, Matrix& count) {
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

// 修改后的窗口求和（自动处理边界）
static float getWindowSum(const Matrix& integral, int x, int y, int r, int rows, int cols) {
    int x1 = std::max(0, x - r);
    int y1 = std::max(0, y - r);
    int x2 = std::min(cols - 1, x + r);
    int y2 = std::min(rows - 1, y + r);
    
    return integral(x2 + 1, y2 + 1) 
         - integral(x1, y2 + 1) 
         - integral(x2 + 1, y1) 
         + integral(x1, y1);
}

// 预处理所有 layer 的积分图
void CVaRCalculator::prepare(const GridMap& map) {
    meanIntegrals_.clear();
    sqIntegrals_.clear();
    layerRefs_.clear();

    for (const auto& rf : riskFactors_) {
        if (!map.exists(rf.layer)) continue;

        const Matrix& data = map[rf.layer];
        layerRefs_[rf.layer] = &data;

        Matrix sum, sqsum, count;
        computeIntegralImage(data, sum, sqsum, count);  // 无填充版本
        
        meanIntegrals_[rf.layer] = std::move(sum);
        sqIntegrals_[rf.layer] = std::move(sqsum);
        countIntegrals_[rf.layer] = std::move(count);  // 存储计数图
    }
}


// 使用积分图计算某个 cell 的局部方差
float CVaRCalculator::computeLocalVariance(const std::string& layer, int x, int y) const {
    const Matrix& data = *layerRefs_.at(layer);
    int rows = data.rows();
    int cols = data.cols();
    
    float S = getWindowSum(meanIntegrals_.at(layer), x, y, 1, rows, cols);
    float SS = getWindowSum(sqIntegrals_.at(layer), x, y, 1, rows, cols);
    float n = getWindowSum(countIntegrals_.at(layer), x, y, 1, rows, cols);
    
    if (n <= 2.0f) return 0.0f;  // 不足2个点无法计算方差
    
    // 稳定公式: Var = (SS - S^2/n) / (n - 1)
    return (SS - (S * S) / n) / (n - 1);
}
// 最终 CVaR 计算接口
float CVaRCalculator::computeCellCVaR(const Index& index) const {
    float mu = 0.0f;
    float sigma2 = 0.0f;

    int x = index(0), y = index(1);

    for (const auto& rf : riskFactors_) {
        const Matrix* layer = layerRefs_.at(rf.layer);
        float value = (*layer)(x, y);
        if (!std::isfinite(value)) continue;

        float var = computeLocalVariance(rf.layer, x, y);
        mu += rf.weight * value;
        sigma2 += rf.weight * rf.weight * var;
    }
    sigma2 = std::max(sigma2, 0.0f);
//  mu + std::sqrt(sigma2) * cvarFactor_
    return mu + std::sqrt(sigma2) * cvarFactor_;
}
