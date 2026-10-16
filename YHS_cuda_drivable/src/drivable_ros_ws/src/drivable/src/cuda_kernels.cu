#include <cuda_runtime.h>
#include <device_launch_parameters.h>
#include "CVaRcal_cuda.h"
#include <cmath>

// CUDA kernel for row-wise prefix sum
__global__ void row_scan_kernel(const float *input, float *output, int rows, int cols)
{
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < rows && col < cols)
    {
        int idx = row * cols + col;
        if (col == 0)
        {
            output[idx] = std::isfinite(input[idx]) ? input[idx] : 0.0f;
        }
        else
        {
            float prev_val = output[row * cols + col - 1];
            float curr_val = std::isfinite(input[idx]) ? input[idx] : 0.0f;
            output[idx] = prev_val + curr_val;
        }
    }
}

// CUDA kernel for column-wise prefix sum
__global__ void column_scan_kernel(const float *row_sum, float *integral, int rows, int cols)
{
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < rows && col < cols)
    {
        int idx = row * cols + col;
        if (row == 0)
        {
            integral[idx] = row_sum[idx];
        }
        else
        {
            integral[idx] = row_sum[idx] + integral[(row - 1) * cols + col];
        }
    }
}

// CUDA kernel for computing integral images (sum, squared sum, count)
__global__ void compute_integral_images_kernel(
    const float *input,
    float *sum_integral,
    float *sq_integral,
    float *count_integral,
    int rows, int cols)
{

    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    if (row < rows && col < cols)
    {
        int idx = row * cols + col;
        float val = input[idx];
        bool valid = std::isfinite(val);

        float sum_val = valid ? val : 0.0f;
        float sq_val = valid ? val * val : 0.0f;
        float count_val = valid ? 1.0f : 0.0f;

        // Compute row-wise prefix sums
        if (col > 0)
        {
            sum_val += sum_integral[idx - 1];
            sq_val += sq_integral[idx - 1];
            count_val += count_integral[idx - 1];
        }

        sum_integral[idx] = sum_val;
        sq_integral[idx] = sq_val;
        count_integral[idx] = count_val;

        __syncthreads();

        // Compute column-wise prefix sums
        if (row > 0)
        {
            sum_integral[idx] += sum_integral[(row - 1) * cols + col];
            sq_integral[idx] += sq_integral[(row - 1) * cols + col];
            count_integral[idx] += count_integral[(row - 1) * cols + col];
        }
    }
}

// CUDA kernel for window sum using integral images
__device__ float get_window_sum_device(
    const float *integral, int x, int y, int r, int rows, int cols)
{

    int x1 = max(0, x - r);
    int y1 = max(0, y - r);
    int x2 = min(cols - 1, x + r);
    int y2 = min(rows - 1, y + r);

    float A = integral[y2 * cols + x2];
    float B = (y1 > 0) ? integral[(y1 - 1) * cols + x2] : 0.0f;
    float C = (x1 > 0) ? integral[y2 * cols + (x1 - 1)] : 0.0f;
    float D = (x1 > 0 && y1 > 0) ? integral[(y1 - 1) * cols + (x1 - 1)] : 0.0f;

    return A - B - C + D;
}

// CUDA kernel for computing local variance
__global__ void compute_local_variance_kernel(
    const float *sum_integral,
    const float *sq_integral,
    const float *count_integral,
    float *variance_output,
    int rows, int cols, int window_radius)
{

    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    if (x < cols && y < rows)
    {
        float S = get_window_sum_device(sum_integral, x, y, window_radius, rows, cols);
        float SS = get_window_sum_device(sq_integral, x, y, window_radius, rows, cols);
        float n = get_window_sum_device(count_integral, x, y, window_radius, rows, cols);

        if (n <= 2.0f)
        {
            variance_output[y * cols + x] = 0.0f;
        }
        else
        {
            variance_output[y * cols + x] = (SS - (S * S) / n) / (n - 1.0f);
        }
    }
}

// CUDA kernel for computing CVaR for all cells
__global__ void compute_cvar_kernel(
    const float **layer_data,
    const float **layer_variance,
    const float *weights,
    int num_layers,
    float cvar_factor,
    float *cvar_result,
    int rows, int cols)
{

    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;

    if (x < cols && y < rows)
    {
        int idx = y * cols + x;
        float mu = 0.0f;
        float sigma2 = 0.0f;

        for (int i = 0; i < num_layers; i++)
        {
            float value = layer_data[i][idx];
            if (std::isfinite(value))
            {
                float var = layer_variance[i][idx];
                mu += weights[i] * value;
                sigma2 += weights[i] * weights[i] * var;
            }
        }

        sigma2 = max(sigma2, 0.0f);
        cvar_result[idx] = mu + sqrt(sigma2) * cvar_factor;
    }
}

void computeIntegralImageCUDAWarpper(const Matrix &input, Matrix &sum, Matrix &sqsum, Matrix &count)
{
    int rows = input.rows();
    int cols = input.cols();
    int size = rows * cols * sizeof(float);

    // 分配 GPU 内存
    float *d_input, *d_sum, *d_sqsum, *d_count;
    cudaMalloc(&d_input, size);
    cudaMalloc(&d_sum, size);
    cudaMalloc(&d_sqsum, size);
    cudaMalloc(&d_count, size);

    cudaMemcpy(d_input, input.data(), size, cudaMemcpyHostToDevice);

    // 配置 grid & block
    dim3 blockSize(16, 16);
    dim3 gridSize((cols + 15) / 16, (rows + 15) / 16);

    // 启动 kernel
    compute_integral_images_kernel<<<gridSize, blockSize>>>(
        d_input, d_sum, d_sqsum, d_count, rows, cols);
    cudaDeviceSynchronize();

    // 拷回结果
    cudaMemcpy(sum.data(), d_sum, size, cudaMemcpyDeviceToHost);
    cudaMemcpy(sqsum.data(), d_sqsum, size, cudaMemcpyDeviceToHost);
    cudaMemcpy(count.data(), d_count, size, cudaMemcpyDeviceToHost);

    cudaFree(d_input);
    cudaFree(d_sum);
    cudaFree(d_sqsum);
    cudaFree(d_count);
}
#define TILE_SIZE 16

#define CUDA_CHECK(call)                                                  \
    do                                                                    \
    {                                                                     \
        cudaError_t err = (call);                                         \
        if (err != cudaSuccess)                                           \
        {                                                                 \
            fprintf(stderr, "CUDA error %s:%d: %s\n", __FILE__, __LINE__, \
                    cudaGetErrorString(err));                             \
            exit(EXIT_FAILURE);                                           \
        }                                                                 \
    } while (0)

// Kernel：每层计算局部 mean 和 sq-mean，然后按权重累加到 CVar（在 d_CVar 上做 +=）
__global__ void conv3x3cov_accumulate(const float *input, float *dCVar,
                                      float cvarFactor, float weight,
                                      int width, int height)
{
    // shared tile size = TILE_SIZE + 2 halo
    __shared__ float tile[TILE_SIZE + 2][TILE_SIZE + 2];

    int tx = threadIdx.x;
    int ty = threadIdx.y;
    int col = blockIdx.x * TILE_SIZE + tx; // x
    int row = blockIdx.y * TILE_SIZE + ty; // y

    // 全局索引
    int idx = row * width + col;

    // 初始化 shared memory 为 0 防止未赋值位置被读
    // 每个线程清理自己负责的 shared cell(s)
    // 为简单起见，令每线程初始化一个或多个 cells; 这里只初始化主体元素 (ty+1, tx+1)
    float v = 0.0f;
    if (row < height && col < width)
    {
        v = input[idx];
        // 如果 input 是 NaN/infinite，把它当作 0
        if (!isfinite(v))
            v = 0.0f;
        tile[ty + 1][tx + 1] = v;
    }
    else
    {
        tile[ty + 1][tx + 1] = 0.0f;
    }

    // 边界线程加载 halo（注意检查边界）
    if (tx == 0)
    {
        int c = col - 1;
        if (row < height && c >= 0)
        {
            float vv = input[row * width + c];
            tile[ty + 1][0] = isfinite(vv) ? vv : 0.0f;
        }
        else
            tile[ty + 1][0] = 0.0f;
    }
    if (tx == TILE_SIZE - 1)
    {
        int c = col + 1;
        if (row < height && c < width)
        {
            float vv = input[row * width + c];
            tile[ty + 1][TILE_SIZE + 1] = isfinite(vv) ? vv : 0.0f;
        }
        else
            tile[ty + 1][TILE_SIZE + 1] = 0.0f;
    }
    if (ty == 0)
    {
        int r = row - 1;
        if (r >= 0 && col < width)
        {
            float vv = input[r * width + col];
            tile[0][tx + 1] = isfinite(vv) ? vv : 0.0f;
        }
        else
            tile[0][tx + 1] = 0.0f;
    }
    if (ty == TILE_SIZE - 1)
    {
        int r = row + 1;
        if (r < height && col < width)
        {
            float vv = input[r * width + col];
            tile[TILE_SIZE + 1][tx + 1] = isfinite(vv) ? vv : 0.0f;
        }
        else
            tile[TILE_SIZE + 1][tx + 1] = 0.0f;
    }

    // 四个角的 halo 也要在对应线程初始化（简化：在 tx==0 && ty==0 等情况）
    if (tx == 0 && ty == 0)
    {
        int r = row - 1, c = col - 1;
        tile[0][0] = (r >= 0 && c >= 0) ? (isfinite(input[r * width + c]) ? input[r * width + c] : 0.0f) : 0.0f;
    }
    if (tx == TILE_SIZE - 1 && ty == 0)
    {
        int r = row - 1, c = col + 1;
        tile[0][TILE_SIZE + 1] = (r >= 0 && c < width) ? (isfinite(input[r * width + c]) ? input[r * width + c] : 0.0f) : 0.0f;
    }
    if (tx == 0 && ty == TILE_SIZE - 1)
    {
        int r = row + 1, c = col - 1;
        tile[TILE_SIZE + 1][0] = (r < height && c >= 0) ? (isfinite(input[r * width + c]) ? input[r * width + c] : 0.0f) : 0.0f;
    }
    if (tx == TILE_SIZE - 1 && ty == TILE_SIZE - 1)
    {
        int r = row + 1, c = col + 1;
        tile[TILE_SIZE + 1][TILE_SIZE + 1] = (r < height && c < width) ? (isfinite(input[r * width + c]) ? input[r * width + c] : 0.0f) : 0.0f;
    }

    __syncthreads();

    // 只在有效内部点计算（或你也可以对边界做处理）
    if (row >= 0 && row < height && col >= 0 && col < width)
    {
        // 计算 3x3 sum 和 sq_sum
        float sum = 0.0f;
        float sq_sum = 0.0f;
#pragma unroll
        for (int dy = -1; dy <= 1; ++dy)
        {
#pragma unroll
            for (int dx = -1; dx <= 1; ++dx)
            {
                float vv = tile[ty + 1 + dy][tx + 1 + dx];
                sum += vv;
                sq_sum += vv * vv;
            }
        }
        // mean 和 var estimate (注意 denom: 使用 count=9 或实际有效点数)
        float mean = sum / 9.0f;
        float mean_sq = sq_sum / 9.0f;
        float var = mean_sq - mean * mean; // population var approx
        var = fmaxf(var, 0.0f);

        // 累加到 dCVar（每层贡献）
        // 这里我们直接在全局上做累加。因为 kernel 是按层顺序串行 launch，
        // 同一时刻只有一个 kernel 在写 dCVar，所以不用 atomicAdd。
        float contrib = weight * mean + (weight * weight) * var * cvarFactor;
        // 注意：如果你担心并发写（多流并行），需要用 atomicAdd
        dCVar[idx] += contrib;
    }
}

__global__ void conv3x3cov_step_cal(const float *input, float *d_output,
                                    int width, int height)
{
    // shared tile size = TILE_SIZE + 2 halo
    __shared__ float tile[TILE_SIZE + 2][TILE_SIZE + 2];

    int tx = threadIdx.x;
    int ty = threadIdx.y;
    int col = blockIdx.x * TILE_SIZE + tx; // x
    int row = blockIdx.y * TILE_SIZE + ty; // y

    // 全局索引
    int idx = row * width + col;

    // 初始化 shared memory 为 0 防止未赋值位置被读
    // 每个线程清理自己负责的 shared cell(s)
    // 为简单起见，令每线程初始化一个或多个 cells; 这里只初始化主体元素 (ty+1, tx+1)
    float v = 0.0f;
    if (row < height && col < width)
    {
        v = input[idx];
        // 如果 input 是 NaN/infinite，把它当作 0
        if (!isfinite(v))
            v = 0.0f;
        tile[ty + 1][tx + 1] = v;
    }
    else
    {
        tile[ty + 1][tx + 1] = 0.0f;
    }

    // 边界线程加载 halo（注意检查边界）
    if (tx == 0)
    {
        int c = col - 1;
        if (row < height && c >= 0)
        {
            float vv = input[row * width + c];
            tile[ty + 1][0] = isfinite(vv) ? vv : 0.0f;
        }
        else
            tile[ty + 1][0] = 0.0f;
    }
    if (tx == TILE_SIZE - 1)
    {
        int c = col + 1;
        if (row < height && c < width)
        {
            float vv = input[row * width + c];
            tile[ty + 1][TILE_SIZE + 1] = isfinite(vv) ? vv : 0.0f;
        }
        else
            tile[ty + 1][TILE_SIZE + 1] = 0.0f;
    }
    if (ty == 0)
    {
        int r = row - 1;
        if (r >= 0 && col < width)
        {
            float vv = input[r * width + col];
            tile[0][tx + 1] = isfinite(vv) ? vv : 0.0f;
        }
        else
            tile[0][tx + 1] = 0.0f;
    }
    if (ty == TILE_SIZE - 1)
    {
        int r = row + 1;
        if (r < height && col < width)
        {
            float vv = input[r * width + col];
            tile[TILE_SIZE + 1][tx + 1] = isfinite(vv) ? vv : 0.0f;
        }
        else
            tile[TILE_SIZE + 1][tx + 1] = 0.0f;
    }

    // 四个角的 halo 也要在对应线程初始化（简化：在 tx==0 && ty==0 等情况）
    if (tx == 0 && ty == 0)
    {
        int r = row - 1, c = col - 1;
        tile[0][0] = (r >= 0 && c >= 0) ? (isfinite(input[r * width + c]) ? input[r * width + c] : 0.0f) : 0.0f;
    }
    if (tx == TILE_SIZE - 1 && ty == 0)
    {
        int r = row - 1, c = col + 1;
        tile[0][TILE_SIZE + 1] = (r >= 0 && c < width) ? (isfinite(input[r * width + c]) ? input[r * width + c] : 0.0f) : 0.0f;
    }
    if (tx == 0 && ty == TILE_SIZE - 1)
    {
        int r = row + 1, c = col - 1;
        tile[TILE_SIZE + 1][0] = (r < height && c >= 0) ? (isfinite(input[r * width + c]) ? input[r * width + c] : 0.0f) : 0.0f;
    }
    if (tx == TILE_SIZE - 1 && ty == TILE_SIZE - 1)
    {
        int r = row + 1, c = col + 1;
        tile[TILE_SIZE + 1][TILE_SIZE + 1] = (r < height && c < width) ? (isfinite(input[r * width + c]) ? input[r * width + c] : 0.0f) : 0.0f;
    }

    __syncthreads();

    // 只在有效内部点计算（或你也可以对边界做处理）
    if (row >= 0 && row < height && col >= 0 && col < width)
    {
        // 计算 3x3 sum 和 sq_sum
        float sum = 0.0f;
        float sq_sum = 0.0f;
        float center = tile[ty + 1][tx + 1];
        if (center == 0.0)
        {
            d_output[idx] = 1;
            return;
        }
#pragma unroll
        for (int dy = -1; dy <= 1; ++dy)
        {
#pragma unroll
            for (int dx = -1; dx <= 1; ++dx)
            {
                float vv = tile[ty + 1 + dy][tx + 1 + dx];
                if (vv == 0)
                {
                    vv = 2.0; // treat the void as 3.0
                }
                sum += vv;
                sq_sum += vv * vv;
            }
        }
        // mean 和 var estimate (注意 denom: 使用 count=9 或实际有效点数)
        float mean = sum / 9.0f;
        float mean_sq = sq_sum / 9.0f;
        float var = mean_sq - mean * mean; // population var approx
        var = fmaxf(var, 0.0f);
        d_output[idx] = var;
    }
}

// Wrapper（Host）
// 说明：weights 和 layers 传 const & 更高效；这里假设 map["CVaR"] 已经存在并已初始化
void computeCVaRCUDAWrapper(grid_map::GridMap &map,
                            const std::vector<float> &weights,
                            const std::vector<std::string> &layers,
                            float cvarFactor)
{
    // 参数合法性
    int numLayers = (int)layers.size();
    if (numLayers == 0)
        return;
    const Matrix &ref = map[layers[0]];
    int rows = ref.rows();
    int cols = ref.cols();
    size_t N = (size_t)rows * (size_t)cols;
    size_t sizeBytes = N * sizeof(float);

    // 在 GPU 上为 CVaR 分配并初始化（一次）
    float *d_output = nullptr;
    CUDA_CHECK(cudaMalloc(&d_output, sizeBytes));

    // 每层处理：分配 d_input（可以重用同一指针）
    float *d_input = nullptr;
    CUDA_CHECK(cudaMalloc(&d_input, sizeBytes));

    dim3 block(TILE_SIZE, TILE_SIZE);
    dim3 grid((cols + TILE_SIZE - 1) / TILE_SIZE, (rows + TILE_SIZE - 1) / TILE_SIZE);
    // compute step with variance
    CUDA_CHECK(cudaMemcpy(d_input, map["elevation"].data(), sizeBytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_output, map["step"].data(), sizeBytes, cudaMemcpyHostToDevice));
    conv3x3cov_step_cal<<<grid, block>>>(d_input, d_output, cols, rows);
    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess)
    {
        fprintf(stderr, "Kernel launch failed: %s\n", cudaGetErrorString(err));
    }
    CUDA_CHECK(cudaDeviceSynchronize());
    CUDA_CHECK(cudaMemcpy(map["step"].data(), d_output, sizeBytes, cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(d_output, map["CVaR"].data(), sizeBytes, cudaMemcpyHostToDevice));

    for (int i = 0; i < numLayers; ++i)
    {
        const Matrix &input = map[layers[i]];
        // 先打包或确保 input.data() 是 row-major & 连续，如果是 Eigen col-major, 需转换为行主序数组
        // 这里假设 map Matrix 已是与 kernel 访问方式一致
        CUDA_CHECK(cudaMemcpy(d_input, input.data(), sizeBytes, cudaMemcpyHostToDevice));

        // launch kernel: 参数注意 width=cols, height=rows
        conv3x3cov_accumulate<<<grid, block>>>(d_input, d_output, cvarFactor, weights[i], cols, rows);
        cudaError_t err = cudaGetLastError();
        if (err != cudaSuccess)
        {
            fprintf(stderr, "Kernel launch failed: %s\n", cudaGetErrorString(err));
            break;
        }
        CUDA_CHECK(cudaDeviceSynchronize());
    }

    // 拷回最终结果
    CUDA_CHECK(cudaMemcpy(map["CVaR"].data(), d_output, sizeBytes, cudaMemcpyDeviceToHost));

    CUDA_CHECK(cudaFree(d_input));
    CUDA_CHECK(cudaFree(d_output));
}
