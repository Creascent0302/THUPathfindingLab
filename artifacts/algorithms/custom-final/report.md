# 复杂地图闭环评测摘要

详解见 [修复报告](../../../docs/custom-map-results.md)。完整指标与实际计划在同目录 report.json；同目录 report.csv 可用于表格分析。

| 集合 | 方法 | 成功 / 回合 |
|---|---|---:|
| user | temporal_pursuit | 2/2 |
| user | temporal_mpc | 2/2 |
| user | scanline_pid | 2/2 |
| user | cnn_gru | 2/2 |
| core | temporal_pursuit | 8/8 |
| core | temporal_mpc | 8/8 |
| complex | temporal_pursuit | 8/8 |
| complex | temporal_mpc | 8/8 |
| core | scanline_pid | 8/8 |
| core | cnn_gru | 8/8 |
| complex | scanline_pid | 8/8 |
| complex | cnn_gru | 7/8 |
| legacy_core | cnn_gru | 8/8 |
| legacy_complex | cnn_gru | 6/8 |
| validation | scanline_pid | 20/20 |
| validation | cnn_gru | 20/20 |
| before_scanline | scanline_pid | 0/2 |

当前四方法的独立保留集分别是 core + complex；用户案例和 validation 单独统计。旧权重列在 legacy_*。失败全部保留。

独立进程用户地图：scanline_pid success, cnn_gru success。
