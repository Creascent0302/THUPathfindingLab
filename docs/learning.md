# 学习模型与训练

平台启动不需要训练。执行 `python scripts/setup_learning.py` 安装 CPU PyTorch 后，即可使用当前 `driver-complex.pt`。权重校验值、来源和适用范围见 [模型卡](../algorithms/learning/weights/MODEL_CARD.md)。

## 1. 先明确“端到端”的边界

部署入口是 [RecurrentPolicy](../algorithms/learning/algorithm.py)，网络定义在 [RecurrentDriver](../algorithms/learning/model.py)。它从图像直接预测动作，没有鸟瞰道路提取、显式路径规划或传统控制器回退。公开标记颜色预处理用于提供任务提示，不提供目标路线或专家动作。

默认模型有 401,259 个可训练参数。场景真值只允许进入离线采集器；部署不导入 `data.py`，也不接收地图、车辆真实姿态或真实速度。训练时有专家并不意味着运行时还能问专家。

## 2. 图像和公开上下文怎样进入网络

`image_input()` 使用面积插值将 RGB 缩至 160×96。第四通道的规则由权重中的 `input_version` 决定；当前发布权重为 `rgb_marker_v2`，逐帧标记默认绿色提示。像素送入网络前除以 255，形状为 `[batch, time, 4, 96, 160]`。

标记通道只回答“哪里像绿色提示”，没有给出线路顺序。它解决早期纯 RGB 网络起步时容易忽略小标记的问题。自定义兼容权重仍可使用 `rgb_hint_v1` 的首帧点 / 区域通道，但发布权重只验证默认绿色提示；颜色或提示类型不匹配时 `reset()` 明确拒绝，不能静默沿用一套不适用的输入语义。

`context_input()` 形成五维向量：

```python
[
    previous_steering / max_steering,
    previous_speed / min(1.0, max_speed),
    wheelbase / 0.32,
    max_steering / 0.52,
    dt * 10,
]
```

“上一动作”是策略历史请求，遇到低可见性门控时记为零指令；它不是车辆实际执行状态。上下文没有逐项编码所有惯性参数，模型对不同响应时间的适应主要来自训练分布，不能因为平台公开了某个参数就假定网络确实使用了它。

## 3. 卷积、时序记忆和输出头的完整形状

| 层 | 每帧输出形状 | 作用 |
|---|---|---|
| 输入 | 4×96×160 | RGB 与提示 |
| 5×5 卷积，步长 2，填充 2 + SiLU | 12×48×80 | 初级颜色与局部边缘 |
| 3×3 卷积，步长 2，填充 1 + SiLU | 20×24×40 | 更大感受野 |
| 同类卷积 | 32×12×20 | 道路布局特征 |
| 同类卷积 | 40×6×10 | 紧凑空间表示 |
| 展平、Linear、LayerNorm、SiLU | 128 | 图像特征 |
| 拼接公开上下文 | 133 | 联合图像与动作历史信息 |
| GRU | 96 | 递归时序状态 |
| Linear 96→64、SiLU、Linear 64→3 | 3 | 转角、速度、可见性 |

卷积在每帧上共享权重，GRU 才沿时间传播。`forward()` 先合并 batch 和 time 维做卷积，再恢复时间维送入 GRU：

```python
encoded = self.encoder(images.reshape(-1, 4, HEIGHT, WIDTH)).reshape(
    batch, time, 128
)
sequence, hidden = self.memory(torch.cat([encoded, context], dim=-1), hidden)
raw = self.head(sequence)
```

转角使用 `tanh` 得到 [-1, 1]，速度使用 `sigmoid` 得到 [0, 1]。部署再分别乘以最大转角和 `min(1.0, max_speed_mps)`。第三个输出是可见性 logit，用 sigmoid 变成数值；它不等同于路线身份正确率、碰撞风险或任务成功概率。

速度头没有负值，也没有倒车训练标签。因此这次平台增加倒车功能后，当前 CNN 仍是前进寻迹模型，不能通过把输出速度乘负号就变成可靠倒车策略。独立避障算法的恢复流程也没有接到 CNN 后面。

## 4. 部署的一帧为什么不总更新 GRU

[RecurrentPolicy.step()](../algorithms/learning/algorithm.py) 根据时间戳而不是调用次数运行。权重的控制周期为 0.1 s；平台常以 0.05 s 积分，因此通常每两张图像更新一次网络，中间保持上一动作，避免以两倍训练频率递推隐状态。

`reset()` 清空隐状态、上一动作和时间戳。时间倒退必须重新 reset，不能从回放中间直接复用未来状态。当前帧满足更新时间时才解码图像、构造上下文并在 `torch.inference_mode()` 中预测。

可见性至少 0.2 时返回 `TRACK`，否则返回 `LOST`。原始网络动作仍可记录在输出中供诊断，但 [execution_action](../pathlab/adapters.py) 会将 `LOST` 门控为零速度制动。网络 `confidence` 留空，避免把可见性冒充通用置信度。

## 5. 离线专家如何构造监督

[TrainingExpert.action](../algorithms/learning/data.py) 读取有序真值路线，按连续弧长窗口选择后续约 4 m 的路线，并用 Pure Pursuit 生成监督动作。它不是基于图像感知的专家；训练标签的优势来自特权路线信息，部署需要由图像学会近似这些动作。

`collect_scene()` 每 0.1 s 保存图像、公开上下文、归一化专家动作及可见性标签，再执行两次 0.05 s 车辆积分。外观、相机和部分惯性参数有随机化。人工遮挡帧速度标签设为零、可见性标签设为零；这是一种合成遮挡监督，没有给所有可能的真实视觉失败自动标注。

行为克隆数据默认由专家驾驶，另加相关转向扰动产生恢复状态。如果指定学生 checkpoint，则以概率 `beta` 执行专家动作，其余时间执行学生动作，但在所有访问到的状态上仍保存专家标签：

```text
当前学生 / 混合策略访问的图像 → 专家在该状态的动作标签
                                ↓
                 与旧数据聚合，继续监督训练
```

这就是代码中的 DAgger 数据聚合过程。纯离线行为克隆只看专家常访问的状态，学生犯小错之后可能进入完全没学过的状态；聚合学生实际访问的状态可以减轻这种闭环分布偏移，但不能保证学习到未采集的所有复杂路线。

## 6. 序列训练怎样与实际起步对应

[Sequences](../algorithms/learning/train.py) 默认使用 24 帧窗口，步长为窗口长度的一半。随机左右翻转时，图像、转角标签和上下文中的上一转角一起翻转；速度不改符号。

从一条长轨迹中途截取窗口时，前两帧只用于 GRU 预热，不计算损失，因为它们没有真实的前置隐状态。回合真正的首帧没有这种豁免，必须参与监督，否则可能出现“训练损失看起来正常，但每次 reset 后第一步就 LOST”的缺陷。

默认前 35 个采样时刻，也就是前 3.5 s，可通过 `--acquisition-weight` 加权。令 `w_t` 是阶段权重（预热帧为零），`u_t` 是专家归一化转角，损失对应代码：

```text
L_steer = Σ [w_t (1 + 3|u_t|) (u_pred − u_t)²] / N_valid
L_speed = Σ [w_t (v_pred − v_t)²] / N_valid
L_visible = Σ [w_t BCEWithLogits(z_pred, visible_t)] / N_valid
L = 5 L_steer + 2 L_speed + 0.15 L_visible
```

较大的转角样本权重更高，避免长直道占据大部分数据后模型只学会直行。起步权重作用于三个头，不能只提高转向监督却忽略会让车停住的速度和可见性。

`fit()` 使用 AdamW、权重衰减 0.0001、余弦学习率和梯度范数裁剪 5。默认保存验证损失最低的候选；`--save-every` 可保存过程快照。验证损失只是离线拟合指标，接下来仍必须闭环运行，让每次动作真正改变下一张图像。

## 7. 采集与训练命令

`data.py` 用特权专家生成离线监督，可由已有学习策略实际驾驶并聚合专家标签（DAgger）；这些代码不进入推理。`custom_data.py` 生成套圈、平行弯线和起步场景，也可增强用户提供的开发地图。

在项目根目录、激活 `.venv` 后执行：

```bash
# 新建基础数据，训练候选权重
python run.py learning collect --data artifacts/learning/base --episodes-per-family 8 --jobs 4
python run.py learning fit --data artifacts/learning/base --epochs 20 --output artifacts/learning/bc.pt

# 用自己的候选策略收集闭环状态，再继续训练
python run.py learning collect --data artifacts/learning/dagger --checkpoint artifacts/learning/bc.pt --beta 0.25 --jobs 4
python run.py learning fit --data artifacts/learning/base artifacts/learning/dagger --resume artifacts/learning/bc.pt --epochs 8 --lr 0.00015 --output artifacts/learning/driver.pt

# 加入复杂几何和用户开发地图
python -m algorithms.learning.custom_data --data artifacts/learning/complex --scene-files scenarios/challenges/user-original.json scenarios/challenges/user-actual.json --jobs 4
python run.py learning fit --data artifacts/learning/base artifacts/learning/complex --resume artifacts/learning/bc.pt --acquisition-weight 4 --output artifacts/learning/complex.pt
```

训练默认使用 `rgb_marker_v2`、24 帧窗口；默认输出为 `artifacts/learning/model.pt`，不会直接覆盖附带的发布权重。`--checkpoint auto` 在采集时使用当前发布模型；也可指定兼容权重路径。

完整参数见 `python run.py learning fit --help`。`--save-every` 可保存固定轮次快照；默认只保留验证损失最低的模型。`--acquisition-weight` 对前 3.5 秒的转向、速度和可见性统一加权。

同初始化微调候选可用 `python run.py learning average --checkpoints 路径1 路径2 --output artifacts/learning/mean.pt` 做参数平均；结果仍是单个网络，必须独立验证，不能假定优于原模型。

## 8. 验证和发布

- 开发种子 0–99，离线验证 201–204，保留测试种子不允许进入采集或训练。同一完整场景不能跨训练与验证集合。
- 已有采集 manifest 的目录拒绝覆盖；新实验使用新目录。
- 训练写出计划、验证损失、数据摘要和候选权重；实际驾驶还必须用闭环评测确认。
- 前端参数 `{"checkpoint":"artifacts/learning/complex.pt"}` 可测试新权重。参数平均、训练轮次和速度选择只能依据开发 / 验证结果。

附带模型的原始训练数据、早期权重和重复开发日志已清理；上述命令使用当前生成器创建新实验，不承诺逐位复现历史训练。模型出处保留在模型卡，当前策略的独立结果保留在 [评测摘要](algorithm-results.json)。
