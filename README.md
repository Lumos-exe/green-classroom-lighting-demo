# Green Classroom Smart Lighting Demo

本项目用于制作一个“真实阶梯教室中的人员活动感知与智能节能照明控制”展示成果。最终包包含真实教室 Blender 模型、20 秒主动画、同步分析视频、研究图表和可复现数据。

项目的核心思想是：将教室中的桌面、过道、黑板和投影幕布离散为物理工作表面 cell；根据人员位置和活动类别计算每个 cell 的需求；再由 cell 到灯具的影响关系生成 20 个顶灯和 2 条前方线灯的逐灯亮度。视频中的亮暗变化来自真实 Blender Area Light 能量变化，不靠整体曝光、环境光或后期调亮伪造。

## Final Outputs

推荐最终展示视频：

```text
outputs/videos/companion/lighting_dashboard_video.mp4
```

该视频包含主动画同步画面、工作表面活动场、逐灯亮度矩阵和实时节能曲线，适合论文汇报或课堂展示。

其他最终视频：

```text
outputs/videos/smart_lighting_demo.mp4
outputs/videos/companion/activity_heatmap_video.mp4
outputs/videos/companion/light_matrix_video.mp4
```

辅助输出：

```text
outputs/videos/keyframes/keyframe_01_empty_safety.png
outputs/videos/keyframes/keyframe_02_class_mode.png
outputs/videos/keyframes/keyframe_03_break_mode.png
outputs/videos/keyframes/keyframe_04_projection_mode.png
outputs/videos/keyframes/keyframe_05_self_study_mode.png
outputs/videos/light_control_matrix.gif
outputs/videos/activity_heatmap.gif
outputs/figures/*.png
outputs/data/*.csv
outputs/blender/*.blend
```

## Repository Layout

```text
README.md                                      项目唯一说明文档
blender/create_realistic_classroom_preview.py  真实教室静态模型生成脚本
blender/create_smart_lighting_demo.py          智能照明动画、灯光控制和 CSV 数据导出脚本
scripts/create_research_figures.py             研究图表、灯光矩阵 GIF 和活动热力图 GIF 生成脚本
scripts/create_companion_videos.py             三个同步分析视频生成脚本
outputs/blender/                               生成的 Blender 场景
outputs/data/                                  动画、cell、人员、灯光和能耗数据
outputs/figures/                               论文展示用静态图
outputs/videos/                                主动画、关键帧、GIF 和 companion 视频
true_classroom_images/                         实拍参考照片
天津大学北洋园校区教学楼总图20180529.pdf       建筑资料参考
```

所有生成和检查命令应在 Docker 容器 `brave_cerf` 内执行，仓库路径为：

```text
/workspaces/green
```

## Classroom Model

模型基于实拍照片和天津大学北洋园校区教学楼资料迭代得到，用于课程展示和论文风格说明。它不是精确工程测绘模型，但空间比例、座位密度、门窗方向、灯具数量、讲台黑板关系和主相机视角已经按展示需求校准。

核心尺寸：

```text
room_length = 16.20 m
room_width = 9.85 m
room_height = 3.72 m
tile_size = 0.60 m
desk_row_count = 12
flat_rows = 6
max_step_count = 6
row_depth = 0.90 m
step_height = 0.105 m
center_aisle_width = 1.00 m
left_aisle_width = 0.72 m
right_aisle_width = 0.86 m
ceiling_lights = 5 x 4 = 20
front_linear_lights = 2
```

坐标约定：

```text
x: 教室横向
y: 教室前后方向，讲台/黑板靠近 y = 0
z: 高度
```

后往前主相机是最终视觉验收基准。以后往前画面为准：

```text
画面左侧: 窗户、窗帘、移动显示屏一侧
画面右侧: 长白墙、侧门一侧
画面前方: 讲台、黑板、投影幕布区域
画面后方: 主相机所在方向
```

主相机：

```text
rear_to_front_camera
location ~= (5.05, room_length - 0.12, 2.46)
```

不要按对象名中的 left/right 直接判断画面左右；最终分析图已经按后往前主画面做了左右映射。

## Lighting and Activity Method

灯具定义：

```text
ceiling_light_r01_c01 ... ceiling_light_r05_c04
front_linear_light_left
front_linear_light_right
```

这里的 `lamp` 指一个独立可控灯具，一共 22 个：20 个顶灯和 2 条前方线灯。每个灯具都有独立 Area Light 能量、可见灯罩发光强度和时间序列列名。

人员活动类别固定为：

```text
empty
listening
writing
projection
blackboard-writing
discussion
walking
```

工作表面 cell 不是灯具，也不是图像像素。它表示真实物理表面上的小区域，包括桌面、过道地面、黑板和投影幕布。每个 cell 保存中心坐标、法向、语义标签、可见相机集合和基础反射外观。动画脚本在每个时间采样点计算 cell 的主导活动 `A_t(i,k)`，再将工作表面需求投射到灯具亮度。

灯光控制原则：

```text
有人写作/听课的桌面附近提高照度
walking/discussion 活动提高过道和门侧灯光
projection 阶段降低前区强光并点亮投影幕布
self study 阶段只保留人员附近较亮，无人区域降到安全低亮
空教室保持低亮但可读的安全照明
```

禁止用整体曝光、世界环境光、材质变白或后期调亮冒充灯光变化。

## Timeline

公开模式时间线：

```text
0.0s - 2.2s    empty safety
2.2s - 8.0s    class mode
8.0s - 10.8s   break mode
10.8s - 14.0s  projection mode
14.0s - 20.0s  self study
```

行为摘要：

```text
empty safety: 无人安全照明，低亮但可读
class mode: 学生从前门进入并坐下，整体照明随人员活动升高
break mode: 部分学生在三条过道和门口附近活动，过道照明响应
projection mode: 学生坐好观看投影，前区强光降低，投影幕布发光
self study: 大部分学生离开，少数学生分散自习，局部亮、空区暗
```

人物路径遵守：

```text
前门 -> 侧边过道 / 中间过道 -> 排入口 -> 座位
座位 -> 排入口 -> 过道 -> 前门
```

## Data Files

```text
outputs/data/demo_timeline.csv
```

公开模式时间线，字段为 `mode,start_s,end_s,description`。

```text
outputs/data/light_brightness_timeseries.csv
```

逐灯亮度时间序列。字段包含 `time_s,mode` 和 22 个独立灯具列。数值是相对可控亮度，视频和 companion 图中的百分比由该值归一化得到。

```text
outputs/data/occupancy_timeseries.csv
```

人员位置和活动时间序列。字段包含 `time_s,mode,person_id,x_m,y_m,z_m,state,activity`。

```text
outputs/data/work_surface_cells.csv
```

工作表面 cell 定义。字段包含 `cell_id,x_m,y_m,z_m,normal_x,normal_y,normal_z,semantic_label,visible_cameras,rho`。

```text
outputs/data/activity_cell_timeseries.csv
```

cell 活动状态时间序列。字段包含 `time_s,mode,cell_id,x_m,y_m,dominant_activity` 以及七类活动分数。

```text
outputs/data/energy_summary.csv
```

能耗估算摘要。只比较：

```text
full_on
smart_per_lamp_dimming
```

`full_on` 表示 22 个灯具全程按最大可控亮度开启。`smart_per_lamp_dimming` 表示当前逐灯智能控制结果。相对能耗由灯具亮度时间序列积分估算。

## Reproduction Commands

检查静态模型脚本：

```bash
docker exec brave_cerf bash -lc 'cd /workspaces/green && python3 -m py_compile blender/create_realistic_classroom_preview.py'
```

生成静态教室模型：

```bash
docker exec brave_cerf bash -lc 'cd /workspaces/green && blender --background --python blender/create_realistic_classroom_preview.py'
```

检查智能照明脚本：

```bash
docker exec brave_cerf bash -lc 'cd /workspaces/green && python3 -m py_compile blender/create_smart_lighting_demo.py'
```

快速重导关键帧、Blender 场景和 CSV 数据：

```bash
docker exec brave_cerf bash -lc 'cd /workspaces/green && blender --background --python blender/create_smart_lighting_demo.py -- --keyframes-only'
```

重新渲染正式主动画会耗时较长：

```bash
docker exec brave_cerf bash -lc 'cd /workspaces/green && blender --background --python blender/create_smart_lighting_demo.py'
```

生成研究图、灯光矩阵 GIF 和活动热力图 GIF：

```bash
docker exec brave_cerf bash -lc 'cd /workspaces/green && python3 scripts/create_research_figures.py'
```

生成同步分析视频：

```bash
docker exec brave_cerf bash -lc 'cd /workspaces/green && python3 scripts/create_companion_videos.py'
```

一次性语法检查：

```bash
docker exec brave_cerf bash -lc 'cd /workspaces/green && python3 -m py_compile blender/create_realistic_classroom_preview.py blender/create_smart_lighting_demo.py scripts/create_research_figures.py scripts/create_companion_videos.py'
```

## Validation Checklist

数据检查：

```text
公开 CSV 的 mode 只包含 empty_safety/class_mode/break_mode/projection_mode/self_study
light_brightness_timeseries.csv 有 22 个灯具列
work_surface_cells.csv 包含 desk_work_surface、aisle_floor、blackboard、projection_screen
energy_summary.csv 只包含 full_on 和 smart_per_lamp_dimming
```

视频检查：

```text
smart_lighting_demo.mp4 约 20 秒
三个 companion 视频约 20 秒、24 fps、高分辨率
activity_heatmap_video.mp4 的人物位置与活动 cell 同步
light_matrix_video.mp4 的两条线灯位于矩阵前方
lighting_dashboard_video.mp4 中节能百分比只表示智能逐灯相对全开节能
```

视觉检查：

```text
自习阶段能看出有人处亮、无人处暗
投影阶段投影幕布发光，前区强光降低但画面可读
课间阶段 walking/discussion 活动与过道灯光响应一致
人物不穿墙、不穿桌椅、不悬空，出入从前门完成
```

清洁度检查：

```text
无 __pycache__、.pytest_cache、.mypy_cache、.ruff_cache
无低清开发预览视频
无废弃 combined dashboard 或 cell-only companion 视频
README.md 是唯一说明性 Markdown 文档
```

## Known Limitations

本项目用于论文/课程展示，不是照明工程仿真软件。能耗通过灯具相对亮度积分估算，未引入真实灯具功率曲线、传感器噪声、日照测量或照度计校准。人物为低多边形简化模型，重点服务于路径合理性和活动驱动灯光逻辑。工作表面 cell 的粒度按展示和灯具控制可解释性设置，并非真实施工级网格。
