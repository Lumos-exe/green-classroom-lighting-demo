# Agent 项目任务书：基于实际阶梯教室的多相机视觉感知与智能照明调控仿真系统

## 0. 任务概述

请从零实现一个完整可运行的课程项目，项目主题为：

**基于人工智能的教学楼人员活动感知和节能联动研究**

本项目用于“绿色低碳校园”选修课结课报告。我们没有真实可控的摄像头和灯具，因此需要用软件构建一个仿真系统，模拟：

```text
实际阶梯教室平面图
    ↓
参数化三维教室建模
    ↓
人员进入、入座、移动、离开
    ↓
虚拟多摄像头视觉感知
    ↓
多视角融合得到教室空间占用状态
    ↓
考虑阶梯高度和灯具高度的三维照明模型
    ↓
智能分区调光控制
    ↓
节能效果、照明满足率、过照明比例等指标评估
    ↓
Python 图表 + Blender 三维动画展示
```

本项目的目标不是做真实工程产品，而是做一个**结构完整、逻辑严谨、结果可视化明显、适合课程报告展示的仿真平台**。

---

## 1. 最重要的设计原则

### 1.1 不能写死教室尺寸和座位灯具参数

请不要在代码中写死这些内容：

```text
教室长宽高
座位排数
每排座位数
座位坐标
教室容量
门窗位置
讲台位置
黑板位置
过道位置
灯具数量
灯具坐标
灯具高度
灯具分组
摄像头位置
阶梯高度
天花板高度
自然光方向
```

所有上述参数都必须从 YAML 配置文件读取。

可以提供默认示例配置，但代码必须支持用户替换为实际教室配置。

### 1.2 必须支持阶梯教室

我们的实际教室是大型阶梯教室，不是平面教室。系统必须考虑：

```text
座位排高差
人员所在位置 z 坐标
桌面高度
灯具高度
灯具到座位的三维距离
摄像头高度和俯仰角
阶梯对摄像头可见性的影响
Blender 三维模型中的阶梯结构
```

不能假设所有人、座椅和桌面都在 z = 0 平面上。

### 1.3 平面图只能提供布局，不能自动得到真实尺寸

我们会提供实际教室平面图，例如 B201 / B202 阶梯教室平面图，图中能看出座位布局、门、讲台、过道等结构，但不能直接看出真实物理尺寸。

因此系统必须支持两种方式：

1. 用户在 YAML 中手动填写真实尺寸；
2. 用户通过平面图中的参考距离进行比例尺标定。

如果缺少真实尺寸，程序不能假装知道准确尺寸，而应使用默认示例尺寸并在日志中给出 warning。

---

## 2. 项目名称和目录结构

项目名称建议：

```text
classroom-tiered-lighting-sim
```

请生成如下目录结构：

```text
classroom-tiered-lighting-sim/
├── README.md
├── requirements.txt
├── run_demo.py
├── config/
│   ├── default_tiered_classroom.yaml
│   └── b201_b202_template.yaml
├── assets/
│   └── floorplan_placeholder.png
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config_loader.py
│   ├── geometry.py
│   ├── floorplan_calibration.py
│   ├── classroom_model.py
│   ├── agents.py
│   ├── scenario_generator.py
│   ├── virtual_cameras.py
│   ├── perception_fusion.py
│   ├── lighting_model.py
│   ├── lighting_controller.py
│   ├── metrics.py
│   ├── visualization_2d.py
│   ├── export_blender.py
│   └── utils.py
├── blender/
│   └── create_tiered_classroom_animation.py
├── docs/
│   ├── report_notes.md
│   └── model_assumptions.md
└── outputs/
    ├── data/
    ├── figures/
    ├── videos/
    └── blender/
```

程序运行时如果输出目录不存在，应自动创建。

---

## 3. 技术栈要求

### 3.1 Python

使用 Python 3.10+。

基础依赖：

```text
numpy
pandas
matplotlib
pyyaml
tqdm
```

可选依赖：

```text
scipy
opencv-python
imageio
pillow
```

不要强依赖深度学习框架。
不要强依赖 PyTorch / TensorFlow。
本项目中的“AI视觉感知”使用**虚拟摄像头检测 + 噪声 + 漏检 + 多视角融合**进行模拟。

### 3.2 Blender

使用 Blender Python API，即 `bpy`。

Blender 脚本需要能：

```text
读取 Python 导出的 animation_data.json
生成阶梯教室三维模型
生成座椅、人员、讲台、黑板、门窗、灯具、摄像头
按照时间序列插入人员位置关键帧
按照时间序列插入灯具亮度关键帧
保存 classroom_scene.blend
可选渲染动画视频
```

如果用户没有安装 Blender，Python 主流程也必须能正常运行，并输出 2D 图表和数据。

---

## 4. 坐标系统

统一采用教室局部坐标系，单位为米：

```text
x：教室左右方向
y：教室前后方向
z：高度方向
```

建议约定：

```text
黑板/讲台所在前方为 y = 0
后门方向为 y = room.length_m
左墙为 x = 0
右墙为 x = room.width_m
地面高度由 floor_z(x, y) 决定
```

所有对象都使用三维坐标：

```text
person:  (x, y, z)
seat:    (x, y, z)
desk:    (x, y, z + desk_height)
lamp:    (x, y, z)
camera:  (x, y, z, yaw, pitch)
```

---

## 5. YAML 配置文件设计

请提供两个配置文件：

```text
config/default_tiered_classroom.yaml
config/b201_b202_template.yaml
```

其中：

* `default_tiered_classroom.yaml` 用于无实际数据时直接跑通；
* `b201_b202_template.yaml` 用于根据实际平面图修改。

### 5.1 配置文件应包含以下模块

```yaml
project:
  name: "classroom-tiered-lighting-sim"
  description: "Tiered classroom lighting control simulation"

floorplan:
  image_path: "assets/floorplan_placeholder.png"
  use_image_background: true
  scale:
    mode: "manual"   # manual / reference_points / unknown
    meters_per_pixel: null
    reference_points_px: null
    reference_distance_m: null

room:
  name: "B201_B202_template"
  expected_capacity: 238
  length_m: 22.0
  width_m: 11.0
  front_wall_y: 0.0
  back_wall_y: 22.0
  left_wall_x: 0.0
  right_wall_x: 11.0

tiered_floor:
  enabled: true
  mode: "per_row"   # per_row / slope
  front_floor_z: 0.0
  row_riser_m: 0.16
  row_depth_m: 0.9
  back_floor_z: null

ceiling:
  mode: "flat"      # flat / slope
  height_m: 4.8
  front_height_m: null
  back_height_m: null

blackboard:
  x1: 1.0
  y1: 0.15
  x2: 10.0
  y2: 0.15
  z_bottom: 0.9
  z_top: 2.5

teacher_area:
  x1: 0.8
  y1: 0.4
  x2: 10.2
  y2: 2.0

doors:
  - id: "front_left_door"
    x: 0.3
    y: 1.0
    z: 0.0
    width_m: 1.0
  - id: "back_right_door"
    x: 10.5
    y: 21.0
    z: 0.0
    width_m: 1.0

windows:
  - id: "left_windows"
    wall: "left"
    x1: 0.0
    y1: 3.0
    x2: 0.0
    y2: 18.0
    z_bottom: 1.0
    z_top: 2.6

seat_blocks:
  - id: "left_block"
    rows: 14
    cols: 6
    start_x: 1.2
    start_y: 2.8
    dx: 0.72
    dy: 0.90
    row_direction: "backward"
    col_direction: "right"
  - id: "middle_block"
    rows: 14
    cols: 7
    start_x: 4.2
    start_y: 2.8
    dx: 0.72
    dy: 0.90
    row_direction: "backward"
    col_direction: "right"
  - id: "right_block"
    rows: 14
    cols: 6
    start_x: 7.8
    start_y: 2.8
    dx: 0.72
    dy: 0.90
    row_direction: "backward"
    col_direction: "right"

aisles:
  - id: "left_aisle"
    x1: 0.5
    y1: 2.0
    x2: 1.0
    y2: 21.0
  - id: "middle_aisle_1"
    x1: 3.6
    y1: 2.0
    x2: 4.0
    y2: 21.0
  - id: "middle_aisle_2"
    x1: 7.2
    y1: 2.0
    x2: 7.6
    y2: 21.0
  - id: "right_aisle"
    x1: 10.2
    y1: 2.0
    x2: 10.7
    y2: 21.0

lights:
  max_power_watt_per_group: 80
  model: "gaussian_3d"
  sigma_m: 3.2
  groups:
    - id: "L01"
      name: "front_left"
      x: 2.2
      y: 3.0
      z: 4.5
      direction: [0, 0, -1]
      beam_angle_deg: 120
      region_hint: "front_left"
    - id: "L02"
      name: "front_middle"
      x: 5.5
      y: 3.0
      z: 4.5
      direction: [0, 0, -1]
      beam_angle_deg: 120
      region_hint: "front_middle"
    - id: "L03"
      name: "front_right"
      x: 8.8
      y: 3.0
      z: 4.5
      direction: [0, 0, -1]
      beam_angle_deg: 120
      region_hint: "front_right"

cameras:
  - id: "cam_back_left"
    x: 1.0
    y: 21.5
    z: 4.2
    yaw_deg: 180
    pitch_deg: -25
    fov_deg: 100
    max_range_m: 25
    miss_rate: 0.12
    noise_std_m: 0.25
  - id: "cam_front_right"
    x: 10.2
    y: 0.8
    z: 3.2
    yaw_deg: 0
    pitch_deg: -15
    fov_deg: 100
    max_range_m: 25
    miss_rate: 0.16
    noise_std_m: 0.30
  - id: "cam_side"
    x: 0.3
    y: 11.0
    z: 3.8
    yaw_deg: 90
    pitch_deg: -20
    fov_deg: 90
    max_range_m: 18
    miss_rate: 0.14
    noise_std_m: 0.25

simulation:
  duration_seconds: 600
  time_step_seconds: 2
  random_seed: 42
  scenario: "self_study"
  num_students: 80
  num_teachers: 1

control:
  update_interval_seconds: 4
  min_brightness: 0.05
  max_brightness: 1.0
  smoothing_factor: 0.35
  occupied_target: 0.85
  walking_target: 0.55
  empty_target: 0.15
  teacher_target: 0.95
  blackboard_target: 0.90
  daylight_compensation: true

lighting_surfaces:
  desk_height_m: 0.75
  person_body_height_m: 1.2
  person_head_height_m: 1.65

output:
  save_animation_json: true
  save_2d_video: true
  save_figures: true
  save_csv: true
```

注意：上述数值只是默认模板，不得在代码中写死。

---

## 6. 几何与阶梯建模

请实现 `geometry.py`。

### 6.1 floor_z 函数

必须提供：

```python
floor_z(x: float, y: float) -> float
```

如果 `tiered_floor.enabled = false`：

```text
floor_z = 0
```

如果 `mode = per_row`：

```text
row_index = floor((y - first_seat_y) / row_depth_m)
floor_z = front_floor_z + row_index * row_riser_m
```

如果 `mode = slope`：

```text
floor_z = front_floor_z + (back_floor_z - front_floor_z) * y / room.length_m
```

### 6.2 座位 z 坐标

每个座位坐标应为：

```text
seat_z = floor_z(seat_x, seat_y)
desk_z = seat_z + desk_height_m
```

### 6.3 人员 z 坐标

人员站立或坐下时：

```text
person_floor_z = floor_z(person_x, person_y)
person_body_z = person_floor_z + 0.9
person_head_z = person_floor_z + 1.6
```

### 6.4 灯具到桌面的三维距离

灯具贡献不能只用二维距离。

必须使用：

```text
d3 = sqrt((x - lx)^2 + (y - ly)^2 + (z_surface - lz)^2)
```

其中 `z_surface` 是桌面高度或目标照明平面高度。

---

## 7. 平面图标定模块

请实现 `floorplan_calibration.py`。

### 7.1 基本功能

支持读取平面图：

```text
assets/floorplan.jpg
```

如果没有该图，使用默认占位图或跳过。

### 7.2 标定模式

支持三种模式：

#### manual

用户已经在 YAML 中填写真实坐标，程序无需标定。

#### reference_points

用户给定两个像素点和真实距离：

```yaml
floorplan:
  scale:
    mode: "reference_points"
    reference_points_px:
      - [100, 80]
      - [900, 80]
    reference_distance_m: 20.0
```

程序计算：

```text
meters_per_pixel = reference_distance_m / pixel_distance
```

#### unknown

如果没有比例尺，程序使用配置中的房间尺寸运行，并给出 warning。

### 7.3 可选交互标注

如果实现方便，可以提供：

```bash
python src/floorplan_calibration.py --image assets/floorplan.jpg --output config/calibrated.yaml
```

支持用户点击教室四角、门、讲台、座位块边界等关键点。

如果交互实现较复杂，可以先提供非交互模板和清晰文档。

---

## 8. 教室模型

请实现 `classroom_model.py`。

需要根据 YAML 生成：

```text
room
floor
tiered_floor
seat list
desk list
aisle list
door list
window list
blackboard
teacher area
light groups
camera list
regions
```

### 8.1 座位生成

支持两种方式：

1. `seat_blocks` 自动生成；
2. `seats_manual` 手动指定。

如果同时存在，优先使用 `seats_manual`。

每个座位应包含：

```text
seat_id
block_id
row
col
x
y
z
desk_z
occupied
```

### 8.2 容量检查

如果配置中有：

```yaml
room:
  expected_capacity: 238
```

则实际生成座位数与 expected_capacity 不一致时，必须打印 warning，例如：

```text
WARNING: generated 266 seats, but expected_capacity is 238.
Please adjust seat_blocks or use seats_manual.
```

不能直接报错终止。

### 8.3 区域划分

区域划分应支持：

```text
front_left
front_middle
front_right
middle_left
middle_middle
middle_right
back_left
back_middle
back_right
teacher_area
blackboard_area
aisle
door_area
```

区域可以根据 x/y 范围自动划分，也可以由 YAML 指定。

---

## 9. 人员活动仿真

请实现：

```text
agents.py
scenario_generator.py
```

### 9.1 Agent 类型

至少包括：

```text
student
teacher
```

每个 Agent 具有：

```text
id
role
x
y
z
target_x
target_y
target_z
state
speed_m_per_s
assigned_seat_id
activity
```

状态包括：

```text
entering
walking
sitting
studying
teaching
leaving
idle
```

### 9.2 场景类型

至少实现四种场景：

#### lecture

上课模式：

```text
学生陆续从门进入
学生入座
教师在讲台区域移动
讲台灯、黑板灯需求较高
学生区整体需求较高
```

#### self_study

自习模式：

```text
学生数量较少
学生随机分散入座
无人区域应降低照明
有人区域和邻近区域保持照明
```

#### break

课间模式：

```text
部分学生离开座位
部分人在过道走动
门口和后排区域活动增多
照明随人员流动变化
```

#### projection

投影模式：

```text
学生基本坐下
投影幕/黑板区域亮度需求降低
学生桌面区域保持中低亮度
讲台区域适中
```

### 9.3 路径规划

不需要复杂寻路，但应避免完全穿墙。

可采用简化路径：

```text
门口 → 过道 → 座位所在排 → 座位
座位 → 过道 → 门口
```

如果实现简单，可以用折线路径。

---

## 10. 虚拟多摄像头视觉感知

请实现 `virtual_cameras.py`。

本项目不需要真实 YOLO 检测，而是模拟“AI视觉检测结果”。

每个摄像头根据真实人员位置生成检测结果。

### 10.1 可见性判断

至少考虑：

```text
摄像头三维位置
人员头部三维位置
水平视场角 fov
最大检测距离 max_range
摄像头 yaw
摄像头 pitch
人员距离越远，置信度越低
人员越靠边缘，置信度越低
阶梯遮挡造成额外漏检概率
```

### 10.2 检测输出

每个检测结果包含：

```json
{
  "time": 120.0,
  "camera_id": "cam_back_left",
  "person_id": "student_003",
  "x_detected": 3.25,
  "y_detected": 12.40,
  "z_detected": 1.20,
  "confidence": 0.86
}
```

### 10.3 噪声模型

检测位置 = 真实位置 + 高斯噪声。

噪声大小受以下影响：

```text
基础 noise_std_m
距离
摄像头视角边缘程度
遮挡程度
```

---

## 11. 多视角融合与 BEV 占用图

请实现 `perception_fusion.py`。

### 11.1 融合逻辑

由于仿真中知道 person_id，可以先使用 person_id 做融合，降低实现难度。

对同一个人的多个检测结果进行置信度加权平均：

```text
x_fused = sum(conf_i * x_i) / sum(conf_i)
y_fused = sum(conf_i * y_i) / sum(conf_i)
z_fused = floor_z(x_fused, y_fused)
```

如果某人只被一个摄像头检测到，也保留。

### 11.2 输出内容

输出：

```text
fused_people
occupancy_by_region
occupancy_grid
activity_by_region
confidence_by_region
```

BEV 占用图应按教室平面网格统计。

网格大小从配置读取，例如：

```yaml
room:
  grid_size_m: 0.5
```

如果配置中没有，则默认 0.5m。

---

## 12. 三维照明模型

请实现 `lighting_model.py`。

### 12.1 亮度单位

本项目使用归一化亮度，不声称得到真实 lux。

```text
0.0 = 完全黑暗
1.0 = 满足较高照明需求
```

但模型必须用于不同策略之间的相对比较。

### 12.2 自然光模型

自然光由窗户贡献。

可采用简化模型：

```text
靠近窗户亮度更高
远离窗户亮度衰减
一天中自然光随时间变化
```

例如：

```text
daylight = daylight_strength(t) * exp(-distance_to_window / decay_m)
```

### 12.3 灯具贡献模型

必须支持至少两种模型：

#### gaussian_3d

```text
contribution = brightness * exp(-d3^2 / (2 * sigma_m^2))
```

#### inverse_square

```text
contribution = brightness * cos(theta)^k / (d3^2 + epsilon)
```

默认使用 `gaussian_3d`，因为它稳定、适合课程仿真。

### 12.4 照明评价点

照明评价不要只在空网格点上做，至少要支持：

```text
座位桌面点
过道地面点
讲台区域点
黑板区域点
```

有人区域优先以座位桌面亮度作为评价对象。

---

## 13. 智能照明控制策略

请实现 `lighting_controller.py`。

至少实现四种策略，用于对比实验。

### 13.1 all_on

所有灯一直 100%。

### 13.2 presence_all_on

只要教室有人，所有灯 100%；无人时所有灯降到最低亮度。

### 13.3 region_rule

哪个区域有人，哪个区域灯提高亮度；无人区域降低亮度。

### 13.4 ai_adaptive

本项目提出的方法。

输入：

```text
多摄像头融合后人员位置
区域占用状态
人员活动状态
当前自然光估计
上一时刻灯光状态
灯具到各区域/座位的三维贡献矩阵
```

输出：

```text
每组灯 brightness in [0, 1]
```

控制逻辑应体现：

```text
有人学习区域目标亮度高
有人走动区域目标亮度中等
无人区域目标亮度低
教师讲台活动时讲台灯增强
黑板使用时黑板区域增强
投影模式下降低黑板/幕布附近亮度
自然光充足区域降低人工照明
灯光变化需要平滑，避免频繁闪烁
```

### 13.5 优化控制

对于 `ai_adaptive`，请尽量实现一个简单优化版本，而不是纯规则。

目标：

```text
在满足照明需求的前提下，最小化灯具能耗和频繁调光。
```

可定义目标函数：

```text
loss = α * energy
     + β * under_lighting_penalty
     + γ * over_lighting_penalty
     + δ * flicker_penalty
```

如果 `scipy` 可用，可以用 `scipy.optimize` 求解。
如果没有 `scipy`，使用启发式迭代或贪心近似。

---

## 14. 评价指标

请实现 `metrics.py`。

至少输出以下指标。

### 14.1 total_energy_wh

```text
energy += sum(brightness_g * max_power_watt_per_group) * dt / 3600
```

### 14.2 energy_saving_rate

相对于 all_on：

```text
saving = 1 - energy_method / energy_all_on
```

### 14.3 lighting_satisfaction_rate

有人区域或有人座位的亮度达到目标需求的比例。

### 14.4 under_lighting_rate

有人区域亮度不足的比例。

### 14.5 over_lighting_rate

无人区域亮度过高的比例。

### 14.6 flicker_score

相邻时间步灯光亮度变化总量：

```text
sum(abs(brightness_t - brightness_t_minus_1))
```

### 14.7 perception_recall

虚拟摄像头融合结果中，真实人员被检测到的比例。

### 14.8 region_occupancy_accuracy

真实区域占用与融合感知区域占用的一致性。

---

## 15. 输出文件

运行后应生成：

```text
outputs/data/simulation_log.json
outputs/data/people_trajectories.csv
outputs/data/camera_detections.csv
outputs/data/fused_people.csv
outputs/data/occupancy_by_region.csv
outputs/data/light_states.csv
outputs/data/metrics.csv

outputs/figures/classroom_layout.png
outputs/figures/tiered_side_view.png
outputs/figures/seat_height_distribution.png
outputs/figures/camera_layout.png
outputs/figures/occupancy_heatmap.png
outputs/figures/lamp_to_seat_distance_heatmap.png
outputs/figures/lighting_3d_effect_heatmap.png
outputs/figures/energy_comparison.png
outputs/figures/satisfaction_comparison.png
outputs/figures/light_brightness_curves.png
outputs/figures/perception_recall_comparison.png

outputs/videos/topdown_simulation.mp4
outputs/blender/animation_data.json
outputs/blender/classroom_scene.blend
```

如果 mp4 无法生成，可以生成 gif 或 PNG 序列，但不能让程序崩溃。

---

## 16. 二维可视化

请实现 `visualization_2d.py`。

至少生成以下图。

### 16.1 classroom_layout.png

显示：

```text
教室边界
座位块
讲台
黑板
门
窗
过道
灯具
摄像头
```

如果有平面图背景，可以叠加在图下。

### 16.2 tiered_side_view.png

显示从侧面看的阶梯高度变化：

```text
x 轴为 y 方向
y 轴为 z 高度
标出每排座位高度
标出灯具高度
标出摄像头高度
```

### 16.3 seat_height_distribution.png

显示每个座位的 z 坐标分布。

### 16.4 lamp_to_seat_distance_heatmap.png

显示不同座位到最近灯具的三维距离。

### 16.5 lighting_3d_effect_heatmap.png

显示某一时刻在三维照明模型下的座位亮度分布。

### 16.6 energy_comparison.png

对比四种控制策略的总能耗。

### 16.7 satisfaction_comparison.png

对比四种控制策略的照明满足率。

### 16.8 light_brightness_curves.png

显示 `ai_adaptive` 策略下各灯组亮度随时间变化曲线。

### 16.9 topdown_simulation.mp4

顶视角动画，显示：

```text
人员移动
灯具亮度
区域占用
摄像头位置
当前策略
当前能耗
当前时间
```

---

## 17. Blender 三维动画

请实现：

```text
blender/create_tiered_classroom_animation.py
```

### 17.1 输入

读取：

```text
outputs/blender/animation_data.json
```

### 17.2 场景必须包含

```text
阶梯地面
墙体
门
窗户
讲台
黑板
座位
桌面
学生低模模型
教师低模模型
灯具
摄像头
俯视相机
侧视相机
文字标签，可选
```

### 17.3 阶梯建模

必须能从侧面看出阶梯结构。

可简化为：

```text
每排座位所在区域是一层平台
每往后一排，z 增加 row_riser_m
```

### 17.4 人员动画

人员模型可以是：

```text
圆柱体身体 + 球体头部
```

根据 JSON 中的每帧位置插入关键帧。

### 17.5 灯光动画

每个灯组使用 Area Light 或 Point Light。

根据 JSON 中的 brightness 插入关键帧：

```text
brightness = 0.0 → 近似关闭
brightness = 1.0 → 满亮
```

灯具颜色或材质也可以随亮度改变，便于观察。

### 17.6 输出

至少生成：

```text
outputs/blender/classroom_scene.blend
```

如果可行，支持渲染：

```text
outputs/videos/blender_animation.mp4
```

---

## 18. 命令行接口

README 中必须提供以下命令。

### 18.1 安装

```bash
pip install -r requirements.txt
```

### 18.2 运行默认阶梯教室仿真

```bash
python src/main.py --config config/default_tiered_classroom.yaml --scenario self_study
```

### 18.3 运行 B201/B202 模板

```bash
python src/main.py --config config/b201_b202_template.yaml --scenario self_study
```

### 18.4 运行不同场景

```bash
python src/main.py --config config/b201_b202_template.yaml --scenario lecture
python src/main.py --config config/b201_b202_template.yaml --scenario break
python src/main.py --config config/b201_b202_template.yaml --scenario projection
```

### 18.5 不运行 Blender，仅生成 Python 图表

```bash
python src/main.py --config config/b201_b202_template.yaml --scenario self_study --no-blender
```

### 18.6 生成 Blender 场景

```bash
blender --background --python blender/create_tiered_classroom_animation.py
```

---

## 19. README 要求

请生成完整 `README.md`，必须包含：

```text
项目简介
研究背景
为什么使用仿真
系统架构
目录结构
安装方法
运行方法
配置文件说明
如何使用自己的阶梯教室平面图
如何填写实际教室尺寸
如何设置座位块
如何设置阶梯高度
如何设置灯具和摄像头
仿真场景说明
虚拟多摄像头视觉感知说明
三维照明模型说明
控制策略说明
评价指标说明
输出图表说明
Blender 动画生成说明
局限性
后续扩展方向
```

README 中必须明确说明：

```text
本项目不使用真实摄像头；
本项目不控制真实灯具；
AI 视觉感知是通过虚拟摄像头检测和多视角融合模拟；
亮度为归一化亮度，不等于真实 lux；
本项目关注不同控制策略在同一仿真环境下的相对节能效果；
实际工程部署需要进一步进行真实照度标定和硬件接入。
```

---

## 20. docs/report_notes.md 要求

请生成中文报告说明文档，语言正式，可直接辅助结课报告撰写。

内容包括：

```text
1. 研究问题
2. 教室照明粗粒度控制的不足
3. 为什么采用多相机视觉感知
4. 为什么需要三维阶梯教室建模
5. 系统总体框架
6. 人员活动仿真方法
7. 虚拟多摄像头感知方法
8. 多视角融合与 BEV 占用图
9. 三维灯光贡献模型
10. 分区调光控制策略
11. 对比实验设计
12. 评价指标
13. 结果解读方式
14. 方法局限
15. 未来改进方向
```

特别强调：

```text
阶梯教室中，不同座位排存在高度差，人员位置、摄像头可见性和灯具照射距离都具有三维特征。因此，本文将座位排高度、人员头部高度、桌面高度、灯具安装高度纳入统一三维坐标系，并基于三维距离计算照明贡献，从而比二维平面控制模型更合理。
```

---

## 21. 代码质量要求

请保证：

```text
代码可以运行
默认配置可以直接跑通
路径自动创建
随机种子可复现
函数和类有注释
错误提示清晰
没有大量 TODO
没有硬编码实际教室尺寸
没有强依赖 Blender
没有强依赖深度学习框架
没有强依赖真实平面图
```

如果配置文件缺少某些非关键参数，应使用合理默认值并打印 warning。
如果缺少关键参数，应明确报错并告诉用户应修改哪个字段。

---

## 22. 实现优先级

### 第一优先级：必须完成

```text
参数化配置读取
阶梯教室几何建模
座位生成与容量检查
人员活动仿真
虚拟多摄像头检测
多视角融合
三维灯光贡献模型
四种控制策略对比
指标计算
二维图表输出
README
docs/report_notes.md
```

### 第二优先级：尽量完成

```text
Matplotlib 顶视角动画
Blender 阶梯教室建模
Blender 人员移动动画
Blender 灯光亮度动画
```

### 第三优先级：可以简化

```text
人物模型可以低模
座椅可以简化为方块
灯具可以用点光源或面光源
自然光可以用简化距离衰减模型
摄像头遮挡可以用概率模型
真实平面图标定可以先用手动配置方式
```

---

## 23. 验收标准

运行：

```bash
pip install -r requirements.txt
python src/main.py --config config/default_tiered_classroom.yaml --scenario self_study --no-blender
```

必须成功，并至少生成：

```text
outputs/data/metrics.csv
outputs/data/simulation_log.json
outputs/data/people_trajectories.csv
outputs/data/light_states.csv
outputs/figures/classroom_layout.png
outputs/figures/tiered_side_view.png
outputs/figures/seat_height_distribution.png
outputs/figures/lamp_to_seat_distance_heatmap.png
outputs/figures/energy_comparison.png
outputs/figures/satisfaction_comparison.png
outputs/blender/animation_data.json
```

运行：

```bash
python src/main.py --config config/b201_b202_template.yaml --scenario lecture --no-blender
python src/main.py --config config/b201_b202_template.yaml --scenario break --no-blender
python src/main.py --config config/b201_b202_template.yaml --scenario projection --no-blender
```

也必须成功。

如果本机安装 Blender，运行：

```bash
blender --background --python blender/create_tiered_classroom_animation.py
```

应生成：

```text
outputs/blender/classroom_scene.blend
```

该 Blender 场景应能明显看出：

```text
阶梯教室
座位区逐排升高
学生位于不同高度
灯具位于上方
灯光亮度随时间变化
```

---

## 24. 最终交付内容

请最终交付完整项目，包含：

```text
完整源码
配置文件
README
中文报告说明文档
默认示例数据
运行脚本
输出图表示例
Blender 生成脚本
```

项目应围绕以下核心主线展开：

```text
实际阶梯教室参数化建模
    ↓
多相机视觉感知模拟
    ↓
人员活动空间占用估计
    ↓
考虑三维高差的灯光贡献计算
    ↓
分区自适应调光控制
    ↓
节能与照明效果评估
```

不要把项目做成普通平面教室模拟。
不要把项目做成简单“有人开灯、没人关灯”。
不要把项目做成只画动画、没有指标评估的展示程序。

本项目必须同时具备：

```text
仿真逻辑
控制算法
指标评估
二维图表
三维展示
课程报告说明
```
