# 视觉寻迹闭环评测

集合：test / occlusion；种子：[1005]；每回合上限：4000 帧。

算法只接收公开 SDK 观测；评分使用原有私有评分器，阈值未放宽。耗时为进程内 step（含图像解码），不含工作进程传输、渲染与初始化。

| 算法 | 成功 / 总数 | 成功率 | Wilson 95% 区间 | 非法换线 | 推理均值 ms | 结束原因 |
|---|---:|---:|---|---:|---:|---|
| temporal_pursuit | 3/3 | 100.0% | 43.8%–100.0% | 0 | 20.45 | {'success': 3} |
| temporal_mpc | 3/3 | 100.0% | 43.8%–100.0% | 0 | 21.08 | {'success': 3} |

区间按回合二项采样计算；同一生成器的样本有相关性，不能解释为真实道路泛化保证。

| 算法 | 场景族 | 成功 / 总数 | 平均进度 | 失败原因 |
|---|---|---:|---:|---|
| temporal_pursuit | parallel | 1/1 | 98.4% | {} |
| temporal_pursuit | hairpin | 1/1 | 98.5% | {} |
| temporal_pursuit | repeated | 1/1 | 99.6% | {} |
| temporal_mpc | parallel | 1/1 | 98.4% | {} |
| temporal_mpc | hairpin | 1/1 | 98.4% | {} |
| temporal_mpc | repeated | 1/1 | 99.6% | {} |

逐回合结果、失败详情及最后一帧见 report.json / episodes；完整计划、代码与权重摘要见 plan.json。所有失败均进入分母。
