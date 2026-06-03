# 当前真实教室 3D 模型说明

本文档记录当前已经完成并验收较满意的 Blender 教室模型，供后续开发者或后续 agent 继续制作智能节能灯光控制演示视频、研究图表和数据分析时参考。

当前阶段不要再根据旧需求从零重建教室。后续工作应基于现有模型继续扩展。

## 核心文件

```text
blender/create_realistic_classroom_preview.py
outputs/blender/showcase_classroom_scene.blend
outputs/videos/classroom_model_rear_to_front.png
outputs/videos/classroom_model_lighting_low.png
outputs/videos/classroom_model_lighting_compare.png
true_classroom_images/
天津大学北洋园校区教学楼总图20180529.pdf
```

`create_realistic_classroom_preview.py` 是当前模型的源代码。`.blend` 和预览图都由该脚本生成。

## 当前模型定位

这是基于实拍照片和天津大学北洋园校区教学楼资料迭代得到的“小教室版本”阶梯教室模型，用于后续智能照明控制演示。它不是工程测绘模型，但空间比例、座位密度、灯具数量、门窗方向、讲台黑板关系、阶梯逻辑和主相机视角已经按当前需求校准。

当前模型重点服务于：

- 真实教室空间展示；
- 20 秒智能节能灯光控制演示视频；
- 逐灯具调光逻辑；
- 自习模式“有人处亮、无人处暗”的局部照明展示；
- 配套研究图表和能耗对比。

## 坐标与视角约定

模型使用 Blender 局部坐标，单位为米：

```text
x：教室横向
y：教室前后方向，前方讲台/黑板靠近 y = 0
z：高度
```

需要特别注意：后往前主相机看到的画面左右，和世界坐标中的左右容易混淆。后续判断门窗、黑板、显示屏位置时，一律以主渲染画面为验收基准：

```text
后往前画面左侧：窗户、窗帘、移动显示屏一侧
后往前画面右侧：长白墙、侧门一侧
前方：讲台、黑板系统、投影/屏幕区域
后方：主相机所在方向
```

脚本中没有对最终图像做镜像、翻转或负缩放处理。

## 关键尺寸参数

当前主要参数位于 `create_realistic_classroom_preview.py` 顶部的 `P` 字典：

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
center_aisle_width = 1.00m
left_aisle_width = 0.72m
right_aisle_width = 0.86m
seat_modules_per_block = 7
window_count = 4
window_width = 1.95m
window_height = 1.95m
window_sill_z = 1.05m
ceiling_light_rows = 5
ceiling_lights_per_row = 4
```

这些参数是根据实拍图、地砖比例和视觉验收结果确定的，不要轻易改动。若后续必须调整，应重新渲染并检查主预览图。

## 房间与前后空间

当前房间长 16.20m。这个长度是为了给 12 排、0.90m 排距座位、后半 6 级阶梯和后墙贴近主相机留出足够空间。

座位第一排与讲台之间已经拉开，比早期版本更符合实拍教室。后部也已加长，使主相机可以贴近后墙，画面能看到更多天花灯具行和更完整的教室纵深。

## 阶梯与座位

当前座位和阶梯逻辑：

- 共 12 排固定连排桌椅；
- 前 6 排所在区域为平地；
- 后 6 排逐级升高；
- 共 6 个等距阶梯；
- 每级踏面深度和座椅排距绑定，均为 0.90m；
- 每级高度为 0.105m；
- 后方最后一级延伸到后墙附近，避免后排平台突然掉回原始地面。

座椅为左右两个大座位块，中间保留 1.00m 中央过道，两侧保留侧过道。每个座位块含 7 个座位模块。座椅由浅木色桌面/座板、浅灰金属支架、靠背横杆、置物篮等简化几何组成。

早期模型中曾出现中间过道黑块和阶梯混乱，根因是地台顶面与原始地板共面导致 z-fighting。当前版本已通过 `floor_skin = 0.024` 的地台表面层解决，不再依赖单独覆盖补丁。

## 地面与砖缝

地砖尺寸按 0.60m 处理。当前模型使用几何砖缝，而不是贴图。

地面砖缝规则：

- 普通平地使用 0.60m × 0.60m 网格；
- 阶梯踏面深度为 0.90m；
- 每级阶梯踏面按“前方一整块 0.60m 砖，后方约 0.30m 半砖”处理；
- 阶梯区不再使用全局自动砖缝撞台阶边界，避免出现两条线紧挨着的混乱效果；
- 砖缝位于地台顶面略上方，避免 z-fighting。

## 门窗与侧墙

以后往前主视角为准：

- 画面左侧是窗户侧；
- 画面右侧是长白墙和侧门；
- 门不在黑板旁边，而在窗户对面的长墙靠前位置。

窗户当前采用简化黑框玻璃分格：

- 每组窗户一条横梁、一条竖梁；
- 横梁偏上，上部窗格少、下部窗格多；
- 后往前画面中，窗格左侧较大、右侧较小；
- 窗外不做透明绿化场景，以避免不可控亮度；
- 玻璃为深灰材质；
- 两侧有拉开的面状灰色窗帘，带少量褶皱。

## 前方教学区

前墙包含：

- 多块组合黑板/白板系统；
- 中央白色讲台；
- 窗户侧前方移动显示屏；
- 右侧长墙前部侧门；
- 前方两侧黑色音响；
- 告示/海报、电箱、垃圾桶等简化细节；
- 投影设备和前方两条线状灯。

当前前墙布局以后往前主画面为准，不能再按对象名字中的 left/right 直接判断视觉左右。

## 天花、灯具与设备

当前顶灯为：

```text
5 行 × 4 列 = 20 个独立顶灯
```

顶灯命名：

```text
ceiling_light_r01_c01 ... ceiling_light_r05_c04
```

前方还有两条独立线状灯：

```text
front_linear_light_left
front_linear_light_right
```

每盏顶灯都包含：

- 可见灯罩；
- 对应独立 Area Light；
- 后续可单独控制的能量值；
- 灯罩可见发光外观。

当前灯具位置已经按加长后的教室重新分布，使后往前主视角可以看到更多灯具行。天花还包含规则吊顶分块、横梁、纵梁、通风口、投影设备等简化细节。

后续智能调光演示必须逐灯具控制，不要只把前/中/后区域作为整块统一亮度。

## 灯光与渲染约定

当前静态预览使用真实 Area Light 照亮物体。不要通过以下方式伪造开灯：

```text
提高整体曝光
把世界环境光开很大
把墙面或桌面材质改白
后期整体调亮
添加大面积全局补光掩盖分区差异
```

低亮图保留暗场可读性，不追求全黑。全亮图也不要白到过曝，应参考实拍图中“全开灯但仍有天花暗面、桌下阴影和灰色墙面”的观感。

## 相机

主相机：

```text
rear_to_front_camera
位置约为 (5.05, room_length - 0.12, 2.46)
方向看向讲台/黑板区域
视角约 78 度
```

它几乎贴近后墙，用于主要预览和后续演示视频。该视角能看到讲台、黑板、座位、窗户、门、天花灯具和教室纵深。

脚本中仍保留一个备用 `front_to_back_camera`，但当前验收优先以后往前主相机为准。

## 当前输出

```text
outputs/blender/showcase_classroom_scene.blend
outputs/videos/classroom_model_rear_to_front.png
outputs/videos/classroom_model_lighting_low.png
outputs/videos/classroom_model_lighting_compare.png
```

其中：

- `classroom_model_rear_to_front.png` 是主验收图；
- `classroom_model_lighting_low.png` 是低亮对比图；
- `classroom_model_lighting_compare.png` 是低亮/全亮并排对比图；
- `.blend` 是当前可打开的 Blender 场景。

## 后续开发建议

后续任务是在当前模型基础上制作智能节能灯光控制演示，而不是继续大改模型。建议新增：

```text
blender/create_smart_lighting_demo.py
scripts/create_research_figures.py
```

后续演示应包含：

- 20 秒视频；
- 无人安全模式；
- 上课模式；
- 课间模式；
- 投影模式；
- 下课后自习模式；
- 逐灯具亮度控制；
- 灯光亮度矩阵 GIF 或视频；
- 能耗对比、人员密度热力图、模式时间线等研究图表。

更具体的后续 agent 任务说明见：

```text
agent.prompt.md
```

## 容器内运行方式

所有命令应在容器内部运行：

```bash
cd /workspaces/green
python3 -m py_compile blender/create_realistic_classroom_preview.py
blender --background --python blender/create_realistic_classroom_preview.py
```

该命令会重新生成 `.blend` 文件和当前三张预览图。

## 不要再做的事

- 不要把教室退回长方体加几排方块桌椅的粗糙模型；
- 不要改变门窗左右关系；
- 不要让阶梯数量超过 6 级；
- 不要把排距和台阶踏面解绑；
- 不要用曝光/环境光/材质变白冒充灯具开灯；
- 不要只做区域整体调光而忽略单灯控制；
- 不要删除当前脚本、参考图和 `.blend` 输出。
