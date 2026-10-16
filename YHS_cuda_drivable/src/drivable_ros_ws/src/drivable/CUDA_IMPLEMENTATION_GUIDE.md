# CVaRcal CUDA 并行化改造指南

## 概述

本项目已将CVaRcal程序从drivable_detect.cpp中的compute_cvar函数开始进行CUDA并行化改造，主要针对积分图计算部分进行GPU加速。

## 主要改动

### 1. 新增文件
- `CVaRcal_cuda.h` - CUDA版本的CVaRCalculator类头文件
- `CVaRcal_cuda.cpp` - CUDA版本的CVaRCalculator类实现
- `cuda_kernels.cu` - CUDA核函数实现
- `test_cuda.cpp` - CUDA环境测试程序

### 2. 修改文件
- `CMakeLists.txt` - 添加CUDA支持和编译选项
- `drivable_detect.cpp` - 使用CUDA版本的CVaRCalculator

## 编译说明

### 环境要求
- CUDA Toolkit 12.3或更高版本
- 支持CUDA的NVIDIA GPU
- CMake 3.16.3或更高版本

### 编译步骤
1. 确保CUDA环境变量正确设置
2. 在项目根目录执行：
   ```bash
   catkin build drivable_area_detection
   ```
   或
   ```bash
   cd src/drivable_ros_ws
   catkin_make
   ```

### 测试CUDA环境
编译测试程序：
```bash
g++ -o test_cuda test_cuda.cpp -lcudart -L/usr/local/cuda/lib64 -I/usr/local/cuda/include
./test_cuda
```

## 功能特性

### 1. 积分图计算CUDA化
- 使用并行前缀和算法加速积分图计算
- 支持sum、squared sum、count三种积分图同时计算
- 自动处理边界条件和无效值

### 2. 内存管理
- 自动GPU内存分配和释放
- 批量数据传输优化
- 支持多layer并行处理

### 3. 兼容性设计
- 保持原有API接口不变
- 支持CPU/GPU模式切换（通过`useCUDA_`标志）
- 优雅降级：CUDA不可用时自动使用CPU版本

## 性能预期

### 理论加速比
- **积分图计算**: 从O(n²)降到O(log n)并行时间
- **CVaR计算**: 从串行循环变为完全并行
- **整体性能**: 预计10-100倍加速（取决于GPU和网格大小）

### 实际测试建议
1. 在不同网格大小下测试性能
2. 比较CPU和GPU版本的运行时间
3. 监控GPU利用率

## 使用示例

```cpp
// 创建CUDA计算器
std::vector<RiskFactorSetting> riskFactors = {
    {"slope", 0.5f},
    {"step", 0.5f}
};
CVaRCalculatorCUDA tool(0.3f, riskFactors);

// 预处理数据
tool.prepare(multi_map);

// 计算单个cell的CVaR
float cvar = tool.computeCellCVaR(index);

// 或者批量计算所有cell
Matrix cvarResult;
tool.computeAllCVaRCUDA(cvarResult);
```

## 故障排除

### 常见问题
1. **CUDA头文件找不到**: 检查CUDA安装路径和环境变量
2. **编译错误**: 确保CMake正确配置CUDA支持
3. **运行时错误**: 检查GPU驱动和CUDA版本兼容性

### 调试建议
1. 使用`test_cuda`程序验证CUDA环境
2. 检查GPU内存使用情况
3. 使用CUDA profiler分析性能瓶颈

## 后续优化方向

1. **进一步并行化**: 将局部方差计算和CVaR计算完全GPU化
2. **内存优化**: 使用CUDA流进行异步计算
3. **算法优化**: 实现更高效的并行前缀和算法
4. **多GPU支持**: 支持大规模网格的多GPU计算

## 注意事项

1. 当前版本在有CUDA环境时会自动使用GPU加速
2. 在没有GPU的环境中会自动回退到CPU版本
3. 建议在实际部署前进行充分的性能测试和验证
