# 视觉寻迹闭环评测

集合：test / core；种子：[1001, 1002, 1003, 1004, 1005]；每回合上限：4000 帧。

算法只接收公开 SDK 观测；评分使用原有私有评分器，阈值未放宽。耗时为进程内 step（含图像解码），不含工作进程传输、渲染与初始化。

| 算法 | 成功 / 总数 | 成功率 | Wilson 95% 区间 | 非法换线 | 推理均值 ms | 结束原因 |
|---|---:|---:|---|---:|---:|---|
| temporal_pursuit | 40/40 | 100.0% | 91.2%–100.0% | 0 | 18.76 | {'success': 40} |
| temporal_mpc | 40/40 | 100.0% | 91.2%–100.0% | 0 | 19.57 | {'success': 40} |
| scanline_pid | 25/40 | 62.5% | 47.0%–75.8% | 0 | 19.82 | {'success': 25, 'episode_timeout': 15} |

区间按回合二项采样计算；同一生成器的样本有相关性，不能解释为真实道路泛化保证。

| 算法 | 场景族 | 成功 / 总数 | 平均进度 | 失败原因 |
|---|---|---:|---:|---|
| temporal_pursuit | straight | 5/5 | 98.4% | {} |
| temporal_pursuit | bend | 5/5 | 98.3% | {} |
| temporal_pursuit | s_curve | 5/5 | 98.2% | {} |
| temporal_pursuit | sharp | 5/5 | 98.3% | {} |
| temporal_pursuit | hairpin | 5/5 | 98.5% | {} |
| temporal_pursuit | parallel | 5/5 | 98.4% | {} |
| temporal_pursuit | close_lines | 5/5 | 98.4% | {} |
| temporal_pursuit | repeated | 5/5 | 99.6% | {} |
| temporal_mpc | straight | 5/5 | 98.4% | {} |
| temporal_mpc | bend | 5/5 | 98.2% | {} |
| temporal_mpc | s_curve | 5/5 | 98.3% | {} |
| temporal_mpc | sharp | 5/5 | 98.3% | {} |
| temporal_mpc | hairpin | 5/5 | 98.5% | {} |
| temporal_mpc | parallel | 5/5 | 98.4% | {} |
| temporal_mpc | close_lines | 5/5 | 98.4% | {} |
| temporal_mpc | repeated | 5/5 | 99.6% | {} |
| scanline_pid | straight | 5/5 | 98.4% | {} |
| scanline_pid | bend | 5/5 | 98.2% | {} |
| scanline_pid | s_curve | 5/5 | 98.3% | {} |
| scanline_pid | sharp | 5/5 | 98.3% | {} |
| scanline_pid | hairpin | 0/5 | 70.3% | {'episode_timeout': 5} |
| scanline_pid | parallel | 0/5 | 0.0% | {'episode_timeout': 5} |
| scanline_pid | close_lines | 5/5 | 98.4% | {} |
| scanline_pid | repeated | 0/5 | 20.3% | {'episode_timeout': 5} |

逐回合结果、失败详情及最后一帧见 report.json / episodes；完整计划、代码与权重摘要见 plan.json。所有失败均进入分母。
