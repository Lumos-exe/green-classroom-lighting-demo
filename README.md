# Green Classroom Smart Lighting Demo

本项目用于制作“真实阶梯教室中的人员活动感知与节能灯光联动”展示成果。

当前仓库已经清理为一个聚焦项目：保留已验收的真实教室 3D 模型、模型生成脚本、参考照片、当前预览图，以及后续智能调光演示任务提示词。旧的粗糙动画、旧仿真数据、旧图表和不匹配代码已移除。

## 当前阶段

当前已经完成：

- 基于实拍图迭代的真实教室 Blender 静态模型；
- 12 排固定连排桌椅；
- 前半平地、后半 6 级阶梯；
- 0.90m 排距/台阶踏面；
- 0.60m 地砖网格；
- 窗户、门、讲台、黑板、显示屏、吊顶、通风口、投影设备；
- 5 行 × 4 列共 20 个独立顶灯；
- 前方 2 条独立线状灯；
- 后往前贴近后墙的主相机；
- 全亮、低亮和并排灯光对比预览图。

当前接下来的目标不是重新建模，而是在此模型基础上制作：

- 20 秒智能节能灯光控制演示视频；
- 无人、上课、课间、投影、自习等模式切换；
- 逐灯具精细调光；
- 灯光亮度矩阵 GIF/视频或视频内嵌示意；
- 人员密度热力图、能耗对比、灯光曲线等研究图表。

## 目录

```text
README.md                                      项目总览
CURRENT_3D_MODEL.md                            当前 3D 模型事实说明
agent.prompt.md                                后续 agent 任务提示词
blender/create_realistic_classroom_preview.py  当前模型生成脚本
outputs/blender/showcase_classroom_scene.blend 当前生成的 Blender 场景
outputs/videos/classroom_model_rear_to_front.png
outputs/videos/classroom_model_lighting_low.png
outputs/videos/classroom_model_lighting_compare.png
true_classroom_images/                         实拍参考照片
天津大学北洋园校区教学楼总图20180529.pdf       建筑资料参考
```

## 关键文档

后续开发请先读：

1. [CURRENT_3D_MODEL.md](CURRENT_3D_MODEL.md)

   记录当前模型的真实参数、空间关系、灯具命名、相机、地砖、阶梯、门窗和注意事项。

2. [agent.prompt.md](agent.prompt.md)

   面向后续 agent 的任务书，说明如何基于当前模型制作 20 秒智能调光演示视频和研究图表。

## 当前模型运行方式

所有命令应在容器内部运行，不要使用宿主机 Blender 或宿主机 Python 路径。

```bash
cd /workspaces/green
python3 -m py_compile blender/create_realistic_classroom_preview.py
blender --background --python blender/create_realistic_classroom_preview.py
```

运行后会生成：

```text
outputs/blender/showcase_classroom_scene.blend
outputs/videos/classroom_model_rear_to_front.png
outputs/videos/classroom_model_lighting_low.png
outputs/videos/classroom_model_lighting_compare.png
```

## 当前模型核心参数

```text
room_length = 16.20m
room_width = 9.85m
room_height = 3.72m
tile_size = 0.60m
front_platform_depth = 2.95m
desk_row_count = 12
flat_rows = 6
max_step_count = 6
row_depth = 0.90m
step_height = 0.105m
ceiling_lights = 5 × 4 = 20
front_linear_lights = 2
```

主相机：

```text
rear_to_front_camera
location ≈ (5.05, room_length - 0.12, 2.46)
```

以后往前主预览图为验收基准：

```text
画面左侧：窗户、窗帘、移动显示屏一侧
画面右侧：长白墙、侧门一侧
画面前方：讲台、黑板、投影/屏幕区域
```

## 后续智能调光演示要求摘要

后续新增脚本应复用当前模型，不要重新建一个不一致的教室。推荐新增：

```text
blender/create_smart_lighting_demo.py
scripts/create_research_figures.py
```

演示视频建议：

```text
时长：约 20 秒
帧率：24 fps
分辨率：1280 × 720
主视角：rear_to_front_camera
模式：无人安全 -> 上课 -> 课间 -> 投影 -> 下课后自习
```

灯光控制必须逐灯具进行。20 个顶灯和 2 条线灯都应有独立亮度时间序列。区域划分只能用于计算参考，不能用粗糙整块区域亮度替代单灯控制。

## 重要限制

- 不要推倒当前模型重建；
- 不要改变门窗左右关系；
- 不要把 6 级阶梯改成更多级；
- 不要把排距和台阶踏面解绑；
- 不要用曝光、环境光或材质变白假装开灯；
- 不要只做区域整体调光；
- 不要删除当前模型脚本、`.blend`、预览图、实拍参考图和模型说明文档。

## 当前输出预览

主预览：

```text
outputs/videos/classroom_model_rear_to_front.png
```

低亮对比：

```text
outputs/videos/classroom_model_lighting_low.png
outputs/videos/classroom_model_lighting_compare.png
```
