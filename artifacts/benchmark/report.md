# 平台探针批量运行报告

此报告由实际运行生成。内置探针不具有完整寻迹能力；失败样本全部保留。

实际耗时：540.7 s；每回合最多 400 步；仿真步长 0.05 s。

| 算法 | 场景族 | 样本量 | 成功 | 平均有效进度 | 失败/结束原因 |
|---|---|---:|---:|---:|---|
| stop | 直线 | 2 | 0 | 0.0% | {'episode_timeout': 2} |
| stop | 单弯 | 2 | 0 | 0.0% | {'episode_timeout': 2} |
| stop | S 形连续弯 | 2 | 0 | 0.0% | {'episode_timeout': 2} |
| stop | 大角度转弯 | 2 | 0 | 0.0% | {'episode_timeout': 2} |
| stop | 可通行回头弯 | 2 | 0 | 0.0% | {'episode_timeout': 2} |
| stop | 平行干扰线 | 2 | 0 | 0.0% | {'episode_timeout': 2} |
| stop | 近距离断开线 | 2 | 0 | 0.0% | {'episode_timeout': 2} |
| stop | 同线多段可见 | 2 | 0 | 0.0% | {'episode_timeout': 2} |
| constant | 直线 | 2 | 0 | 38.7% | {'deviation': 2} |
| constant | 单弯 | 2 | 0 | 31.9% | {'deviation': 2} |
| constant | S 形连续弯 | 2 | 0 | 26.7% | {'deviation': 2} |
| constant | 大角度转弯 | 2 | 0 | 31.0% | {'deviation': 2} |
| constant | 可通行回头弯 | 2 | 0 | 30.5% | {'deviation': 2} |
| constant | 平行干扰线 | 2 | 0 | 38.7% | {'deviation': 2} |
| constant | 近距离断开线 | 2 | 0 | 31.7% | {'illegal_switch': 1, 'deviation': 1} |
| constant | 同线多段可见 | 2 | 0 | 20.5% | {'deviation': 2} |

场景、种子与阈值在运行前固定；详见 plan.json。原始每帧记录见 artifacts/runs/<run_id>/。

典型限制：停车探针始终不接入；固定动作探针不读取图像，初始航向有偏差或出现弯道时会偏离；分割探针没有驾驶输出。
