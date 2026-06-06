# 基于 VGGT-3DGS-BEV 的纯视觉教室精细照明调控方法研究

## 引言

在绿色低碳校园建设背景下，教学楼照明系统既关系到公共建筑能耗，也直接影响课堂学习、板书观看和投影使用等教学体验。传统教室照明控制通常以房间级开关、定时控制、区域开关或人体红外感应为主，控制对象多为整间教室或固定灯区，难以区分学生课桌面、黑板面、投影幕面、讲台区域和过道等不同教学工作表面的实际需求。当教室内只有局部区域有人、窗边自然光已经充足、或课堂处于投影模式时，粗粒度控制容易造成无人区域过度照明；当学生书写、教师板书或局部讨论发生时，固定控制又可能无法保证关键任务表面的照明需求。

国内外关于智能照明控制的研究主要围绕建筑节能、视觉舒适、人员占用感知和日光利用展开。早期与工程应用较成熟的方案多采用人体存在传感器、照度传感器、定时开关和固定分区策略，通过判断空间是否有人、自然光是否充足以及是否处于使用时段来控制灯具开关或连续调光。这类方法结构简单、成本较低，适合教学楼、办公楼等大面积场景的基础节能控制。例如，基于占用传感器的控制方法可以在无人区域关闭或降低照明，基于日光传感器的 daylight harvesting 方法则可以在窗边自然光充足时降低人工照明输出，从而减少人工照明能耗。部分研究进一步将传感器布设在灯具附近，形成 luminaire-based sensing 系统，使每个灯具能够根据局部占用和局部照度进行调节，提升分区控制的灵活性。

随着控制理论和智能优化方法的发展，国外研究开始从简单规则控制转向个性化照明、闭环调光和多目标优化控制。例如，有研究利用桌面照度传感器、窗帘控制和智能控制器，在满足用户个性化照明需求的同时利用自然光降低能耗；也有研究在学校建筑中比较不同 daylight dimming 控制系统的节能效果，说明教室照明控制不仅与灯具开关有关，还与窗边自然光、教室朝向、控制策略和使用时段密切相关。近年来，部分研究开始关注课堂场景中的视觉舒适和教学活动差异，例如利用高动态范围图像或监控摄像头估计教室亮度分布，并结合日光和人工照明控制改善课堂视觉环境；也有研究从座位区域、投影使用和学生主观感受等角度评价大学教室视觉舒适，说明课堂照明不仅是能耗问题，也与学习活动和视觉任务密切相关。

国内关于教学楼和教室智能照明的研究与工程实践多集中在物联网传感器、单片机控制、ZigBee 或无线通信、人体红外检测、光敏电阻、照度采集和分区控制等方向。典型方案通常在教室内布设人体红外传感器和光照传感器，根据是否有人、环境光强和预设区域规则控制灯具开关或亮度；也有方案通过灯具分组、座位压力检测或人数统计实现按区域开灯，避免无人区域长时间照明。这些方法能够降低传统"整间教室统一开灯"造成的能源浪费，也具有较好的工程可实施性。

总体来看，现有智能照明控制研究已经在占用感知、日光利用、分区调光和节能优化方面形成了较成熟的技术路线，但仍存在三个不足：第一，控制粒度多停留在房间级、灯组级或固定分区级，难以精确表达课桌面、黑板面、投影幕面等不同教学任务表面的照明需求；第二，人员感知多关注"是否有人"或"有多少人"，对听课、书写、板书、投影观看等课堂活动差异考虑不足；第三，现有系统通常将感知结果直接转化为开关灯或调光规则，缺少从人员活动、当前光照、环境光贡献到灯具控制量之间的统一建模。因此，面向绿色低碳校园的教室照明控制仍需要进一步从粗粒度分区控制走向面向教学任务和真实工作表面的精细化调控。

本文的目标是在输入仅有多相机图像的条件下，探索一种具有创新性、解释性和闭环控制能力的纯视觉教室精细照明调控方法。本文首先利用 VGGT 点图和语义掩码构建三维工作表面；随后使用 3DGS 作为静态外观和可见性辅助模块；在线阶段采用 Swin-Tiny-FPN 共享视觉 backbone 和占用、活动、光照三个任务 head 输出 $O_{t}(i)$、$A_{t}(i,k)$ 和 $L_{t}(i)$；最后结合灯具贡献矩阵 $M(i,g)$、环境光估计 $L_{day,t}(i)$ 和目标需求 $R_{t}(i)$，通过约束优化求解灯组亮度 $c_{t}$。此外，考虑到逐个 $cell_{i}$ 标注目标亮度成本较高，本文利用人工标注的最终灯光控制策略作为间接监督，通过可微展开控制层反向校准目标需求函数中的策略系数。

## 研究内容

本文研究内容围绕"多相机视觉感知如何转化为真实工作表面上的精细照明控制"展开，主要包括以下四个方面。

第一，建立三维工作表面单元统一索引。本文以空教室多相机图像为输入，通过 VGGT 获得相机参数和点图，再结合分割模型初分割与人工校正关键帧得到课桌、黑板、投影幕、讲台、过道和灯具等语义掩码。随后直接在 VGGT 点图上提取三维语义表面点，采用 RANSAC 剔除离群点与最小二乘精修拟合工作表面，并将不同教学表面离散为统一的 $cell_{i}$。这样，后续人员占用、教学活动、当前光照、环境光、目标需求和灯光贡献均在同一空间索引下表达。

第二，构建基于 Swin-Tiny-FPN 的多任务视觉感知模型。在线阶段，多相机图像经该共享视觉 backbone 提取多尺度特征，并通过相机投影关系采样融合到每个 $cell_{i}$ 上，形成 cell 级融合观测特征 $F_{i}(t)$。在此基础上，occupancy head 输出人员占用 $O_{t}(i)$，activity head 输出活动状态 $A_{t}(i,k)$，lighting head 输出当前归一化视觉光照 $L_{t}(i)$。三个任务 head 共享底层视觉特征，但输出语义不同。

第三，建立从视觉光照状态到目标需求的可解释控制逻辑。本文使用灯光切换实验标定灯具贡献矩阵 $M(i,g)$，用上一时刻灯光状态扣除人工光贡献，估计不可控环境光 $L_{day,t}(i)$。目标需求 $R_{t}(i)$ 由基础项、占用项和活动项组成，能够表达不同表面、不同活动和板书场景下的差异化照明需求。由于本文纯视觉不使用照度计，所有光照量和需求量均采用归一化视觉量表达。

第四，提出利用人工控制策略校准需求系数的方法。逐 cell 标注目标亮度成本较高，而人工给出典型课堂场景下的灯光控制向量成本相对可控，并且也能够了解学习人们个性化的舒适度要求和照明需求风格。本文将需求函数中的 $b_{\mathcal{l}}$、$\lambda_{\mathcal{l}}^{occ}$、$r_{\mathcal{l},k}$ 和 $r_{board}$ 作为可学习策略系数，使用人工标注控制向量 $c_{t}^{gt}$ 作为间接监督。训练阶段将控制优化展开为可微投影梯度过程，使控制策略误差能够反向传播到需求系数；在线阶段则固定校准后的需求系数，采用 L-BFGS-B 求解当前灯光控制向量。

## 研究方法

### 1. 总体技术路线

本文方法分为离线准备阶段和在线运行阶段。

离线准备阶段完成三项工作。第一，使用空教室多相机图像和 VGGT 点图构建三维工作表面，并将其离散为 $cell_{i}$。第二，训练空教室 3DGS 静态表示，用于空教室参考渲染、动态残差、基础反射外观和可见性辅助。第三，通过空教室灯光切换实验标定灯具贡献矩阵 $M(i,g)$，表示第 $g$ 组灯对第 $i$ 个工作表面单元的照明贡献。

在线运行阶段在每个控制时刻执行。实时多相机图像先经过 Swin-Tiny-FPN 共享视觉 backbone 提取多尺度特征，然后通过相机投影关系将多视角特征组织到每个 $cell_{i}$ 上，形成融合观测特征 $F_{i}(t)$。三个任务 head 分别输出人员占用 $O_{t}(i)$、活动状态 $A_{t}(i,k)$ 和当前光照 $L_{t}(i)$。随后，系统利用 $M(i,g)$ 和上一时刻控制量 $c_{t - 1}$ 估计当前环境光 $L_{day,t}(i)$，再根据占用和活动生成目标照明需求 $R_{t}(i)$，最后求解灯光控制向量 $c_{t}$。此外，需求函数中的策略系数不完全依赖人工设定，而是在离线训练阶段利用人工标注的灯光控制策略进行校准。

整条链路可以概括为：

$$I_{t}^{1},\ldots,I_{t}^{N} \rightarrow F_{i}(t) \rightarrow \{ O_{t}(i),A_{t}(i,k),L_{t}(i)\} \rightarrow \{ L_{day,t}(i),R_{t}(i)\} \rightarrow c_{t}.$$

其中，所有中间状态均定义在同一组工作表面单元 $cell_{i}$ 上，保证了空间索引的一致性。

### 2. 离线阶段：三维工作表面构建

#### 2.1 使用 VGGT 点图恢复空教室几何

离线建模阶段只使用空教室多相机图像。设多个固定相机拍摄的空教室图像为：

$$I^{1},I^{2},\ldots,I^{N}.$$

将这些图像输入 VGGT，得到每个相机的几何信息和点图：

$$\left( K_{j},R_{j},t_{j},P_{j} \right),\quad j = 1,\ldots,N.$$

其中，$K_{j}$ 表示第 $j$ 个相机的内参，$R_{j},t_{j}$ 表示第 $j$ 个相机的外参，$P_{j}(u)$ 表示第 $j$ 个相机图像中像素 $u$ 对应的三维点。这里最关键的是点图 $P_{j}$：它将二维图像像素与真实教室三维空间建立了对应关系。后续工作表面提取直接在 VGGT 输出的稠密点图上完成。

#### 2.2 语义掩码与三维语义点集生成

VGGT 点图只提供几何点，并不知道哪些点属于课桌、黑板或投影幕等对视觉产生主要影响的物体的表面。因此，本文采用"分割模型初分割 + 人工校正关键帧"的方式获得语义掩码。对第 $j$ 个相机图像，记类别 $c$ 的语义掩码为：

$$S_{j}^{c}(u).$$

语义类别固定为：

$$c \in \{ student\_ desk,teacher\_ desk,board,screen,aisle,podium,lamp\}.$$

若像素 $u$ 在第 $j$ 个图像中属于类别 $c$，即 $S_{j}^{c}(u) = 1$，则将 VGGT 点图中的三维点 $P_{j}(u)$ 加入该类别的三维点集：

$$\mathcal{P}_{c} = \{ P_{j}(u) \mid S_{j}^{c}(u) = 1,\ j = 1,\ldots,N\}.$$

由此得到课桌、讲台、黑板、投影幕、过道、教师讲授活动区域和灯具的三维语义点集。该步骤的本质是把二维语义分割结果通过 VGGT 点图提升到三维空间。

#### 2.3 RANSAC 与最小二乘拟合工作表面

三维语义点集仍然包含分割误差、深度噪声、边界漂移和离群点。对于黑板、投影幕、讲台面、过道地面等近似平面结构，本文采用 RANSAC 剔除离群点，再使用最小二乘精修平面的策略。

对于类别 $c$ 的三维点集 $\mathcal{P}_{c}$，RANSAC 首先随机采样三点生成候选平面，并以点到平面的距离阈值筛选内点。经过多轮采样后，选择内点数量最多的候选平面。设得到的内点集合为 $\mathcal{I}_{c}$，则在内点集合上求解最小二乘问题：

$$\min_{n_{c},b_{c}}\sum_{X \in \mathcal{I}_{c}}\left( n_{c}^{\top}X + b_{c} \right)^{2},$$

并得到最终平面：

$$\pi_{c}:\quad n_{c}^{\top}X + b_{c} = 0.$$

其中，$n_{c}$ 是表面法向，$b_{c}$ 是平面偏置，$X$ 是三维空间点。该方法同时利用了 RANSAC 的抗离群点能力和最小二乘在干净点集上的精确拟合能力。

对于学生课桌面，不能把所有桌面点拟合成一个整体平面，因为教室中存在多张桌子。本文固定采用高度阈值、DBSCAN 聚类和人工校核的流程。首先根据桌面高度范围筛选候选点；然后在三维空间中使用 DBSCAN 将相互分离的桌面点聚成不同实例；最后人工校核聚类结果，避免相邻桌子误合并或单张桌子被误分裂。每个桌面实例再分别拟合局部平面。

#### 2.4 工作表面离散化与 cell_i 属性表

连续工作表面不能直接用于控制优化，因此需要离散化。本文将所有工作表面离散为三维工作表面单元集合：

$$\mathcal{C} = \{ cell_{i}\}_{i = 1}^{S_{c}}.$$

每个 $cell_{i}$ 是真实物理表面上的一个小区域，既不是图像像素，也不是普通二维 BEV 网格。每个单元保存如下属性：

$$cell_{i} = \{ X_{i},n_{i},\mathcal{l}_{i},\mathcal{V}_{i},\rho_{i}\}.$$

其中，$X_{i}$ 表示单元中心的三维坐标，$n_{i}$ 表示表面法向，$\mathcal{l}_{i}$ 表示语义标签，$\mathcal{V}_{i}$ 表示可以看到该单元的相机集合，$\rho_{i}$ 表示基础反射外观。离散粒度按实际灯具控制粒度自适应设置：灯具控制越粗，cell 尺度可以越大；灯具控制越细，cell 可以相应变小。后续所有状态量都以 $cell_{i}$ 为统一索引，包括 $O_{t}(i)$、$A_{t}(i,k)$、$L_{t}(i)$、$L_{day,t}(i)$、$R_{t}(i)$ 和 $M(i,g)$。

### 3. 3DGS 的定位：静态外观和可见性辅助

3DGS 的原始表示是一组三维 Gaussian：

$$G_{k} = \{\mu_{k},\Sigma_{k},\alpha_{k},s_{k}\}.$$

其中，$\mu_{k}$ 是 Gaussian 中心，$\Sigma_{k}$ 是协方差，$\alpha_{k}$ 是不透明度，$s_{k}$ 是颜色或球谐系数。由于这些 Gaussian 图元和 VGGT 输出的点图相比不适合课桌面、黑板面等表面的提取和重建，因此本文不从 3DGS 中直接提取工作表面。

3DGS 作用主要包括三点。第一，提供静态背景参照：系统优先使用真实空教室背景图像，当视角缺失或需要补全时，利用 3DGS 渲染空教室参考图像，并与当前图像相减生成动态残差，用于突出人员、物体和局部光照变化。第二，辅助多视角可见性判断：3DGS 渲染过程中的 alpha 累积和渲染深度可用于判断 $cell_{i}$ 在某一相机视角下是否被遮挡，或其投影深度是否一致，从而调整多视角特征融合权重。第三，辅助估计基础反射外观：系统可在真实空教室图像或 3DGS 渲染图像中采样 $cell_{i}$ 的静态颜色和亮度，得到 $\rho_{i}$，用于后续光照估计中的表面外观校正。

### 4. 灯具贡献矩阵 M(i,g) 的标定

灯具贡献矩阵 $M(i,g)$ 表示第 $g$ 组灯在满亮状态下对第 $i$ 个工作表面单元的归一化光照贡献。它是从灯具控制空间到工作表面光照空间的映射。

本文采用空教室灯光切换实验标定 $M$。实验固定包括全关灯、单灯组逐个开启和若干随机灯光组合。设第 $k$ 次实验的灯光控制向量为：

$$c^{k} = \left\lbrack c^{k}(1),c^{k}(2),\ldots,c^{k}(G) \right\rbrack,$$

第 $i$ 个工作表面单元在该实验状态下的归一化视觉亮度为 $L^{k}(i)$，全关灯背景亮度为 $B(i)$，则观测模型为：

$$L^{k}(i) \approx B(i) + \sum_{g = 1}^{G}M(i,g)c^{k}(g).$$

学习 $M$ 时使用梯度下降优化完整损失：

$$\mathcal{L}_{M} = \mathcal{L}_{rec} + \lambda_{1}\mathcal{L}_{nonneg} + \lambda_{2}\mathcal{L}_{smooth} + \lambda_{3}\mathcal{L}_{sparse} + \lambda_{4}\mathcal{L}_{geo}.$$

其中，$\mathcal{L}_{rec}$ 约束由 $M$ 和 $c^{k}$ 预测的亮度接近观测亮度；$\mathcal{L}_{nonneg}$ 保证灯光贡献非负；$\mathcal{L}_{smooth}$ 约束同一灯组对相邻工作表面的影响连续变化；$\mathcal{L}_{sparse}$ 鼓励每组灯主要影响附近区域；$\mathcal{L}_{geo}$ 使学习结果与由灯具位置、距离衰减、入射角和遮挡关系得到的几何先验保持一致。

标定完成后，$M$ 作为系统参数固定下来。在线阶段不再重新学习 $M$，而是在环境光分离和控制优化中直接调用。

### 5. 在线视觉感知：Swin-Tiny-FPN 与三任务 head

#### 5.1 多相机图像特征提取

在线时刻 $t$，输入实时多相机图像：

$$I_{t}^{1},I_{t}^{2},\ldots,I_{t}^{N}.$$

每个图像经过共享视觉 backbone：

$$F_{t}^{j} = \Phi\left( I_{t}^{j} \right).$$

本文将 $\Phi$ 具体设置为 Swin-Tiny-FPN。Swin-Tiny 通过 shifted window 注意力提取层级视觉特征，FPN 对不同层级特征进行自顶向下融合，形成适合多尺度 cell 投影采样的特征图。该 backbone 使用预训练权重初始化，训练时使用教室数据调整占用、活动和光照三个任务分支。注意，这里的 backbone 负责提取通用视觉特征，最终状态不是由 backbone 直接输出，而是由后续三个任务 head 输出。

#### 5.2 多视角特征融合到 cell_i

对于每个 $cell_{i}$，已知其三维中心 $X_{i}$。通过第 $j$ 个相机的投影函数，计算：

$$u_{ij} = \Pi_{j}\left( X_{i} \right).$$

然后在第 $j$ 个相机的多尺度特征图中采样局部特征。由于 FPN 提供多个尺度，本文根据 $cell_{i}$ 投影区域的尺度选择对应层级，或对相邻层级进行加权融合：

$$f_{ij}(t) = Sample\left( \{ F_{t,l}^{j}\}_{l = 1}^{L},u_{ij} \right).$$

多个相机的观测加权融合为：

$${\bar{f}}_{i}(t) = \sum_{j = 1}^{N}w_{ij}(t)f_{ij}(t).$$

其中，$w_{ij}(t)$ 由可见性、视角质量和遮挡状态决定。再将动态视觉特征与静态空间先验融合：

$$s_{i} = E_{S}\left( X_{i},n_{i},\mathcal{l}_{i},\rho_{i},\mathcal{V}_{i} \right).$$

结合动态残差特征 $\Delta{\bar{f}}_{i}(t)$，得到：

$$F_{i}(t) = \phi_{fuse}\left( \left\lbrack {\bar{f}}_{i}(t),s_{i},\Delta{\bar{f}}_{i}(t) \right\rbrack \right).$$

注意，这里 $F_{i}(t)$ 是 $cell_{i}$ 的融合观测特征，不是最终状态。最终的人员占用、活动状态和当前光照分别由三个任务 head 输出。

#### 5.3 占用 head：人员占用 O_t(i)

occupancy head 直接接收 $F_{i}(t)$ 并输出人员占用概率：

$$O_{t}(i) = h_{occ}\left( F_{i}(t) \right),\quad O_{t}(i) \in \lbrack 0,1\rbrack.$$

$O_{t}(i)$ 表示与 $cell_{i}$ 相关联的人员活动邻域中是否有人。注意，该值不是"人是否站在 $cell_{i}$ 表面上"，而是：

$$O_{t}(i) = P\left( \mathcal{N}_{occ}\left( cell_{i} \right)\text{ 中存在人员} \right).$$

例如，学生课桌 cell 的占用标签由其对应座位区域是否有人决定；过道 cell 的占用标签由其上方通行区域是否有人决定；讲台 cell 的占用标签由教师活动区域是否有人决定。

#### 5.4 活动 head：活动状态 A_t(i,k)

activity head 输出每个 $cell_{i}$ 的活动状态概率：

$$A_{t}(i,k) = h_{act}\left( F_{i}(t),O_{t}(i),\mathcal{l}_{i},T_{i}(t) \right).$$

其中，$T_{i}(t)$ 表示 cell 级别的时序特征，可由过去若干帧的 $F_{i}(t)$、$O_{t}(i)$ 或隐藏状态构成。活动类别固定为：

$$k \in \{ empty,listening,writing,projection,blackboard\text{-}writing,discussion,walking\}.$$

输出满足：

$$\sum_{k}A_{t}(i,k) = 1.$$

活动状态不再依赖显式人体轨迹，而是依赖 cell 级观测特征、占用概率、语义标签和时序变化。例如，学生课桌 cell 占用高且局部特征呈现稳定低头和桌面动作时，$writing$ 概率升高；投影幕相关区域出现投影亮度和观看模式时，$projection$ 概率升高；讲台或黑板前区域出现板书动作线索时，$blackboard\text{-}writing$ 概率升高。

#### 5.5 光照 head：当前光照 L_t(i)

lighting head 输出当前归一化视觉照明量：

$$L_{t}(i) = h_{light}\left( F_{i}(t),\rho_{i},\mathcal{l}_{i} \right),\quad L_{t}(i) \in \lbrack 0,1\rbrack.$$

由于本文纯视觉不使用照度计，$L_{t}(i)$ 表示工作表面在视觉上的归一化亮度状态。光照 head 使用小型 MLP 实现，输入包括融合观测特征、基础反射外观和表面语义信息。

光照 head 的无标定训练损失为：

$$\mathcal{L}_{light} = \lambda_{p}\mathcal{L}_{photo} + \lambda_{m}\mathcal{L}_{mv} + \lambda_{s}\mathcal{L}_{smooth}.$$

其中，$\mathcal{L}_{photo}$ 是图像重投影损失，$\mathcal{L}_{mv}$ 是多视角一致性损失，$\mathcal{L}_{smooth}$ 是同一表面内的空间平滑损失。

### 6. 环境光分离

当前光照 $L_{t}(i)$ 包含不可控环境光和上一时刻人工灯光贡献。利用已标定的灯光贡献矩阵 $M(i,g)$ 和上一时刻控制量 $c_{t - 1}(g)$，可写为：

$$L_{t}(i) = L_{day,t}(i) + \sum_{g = 1}^{G}M(i,g)c_{t - 1}(g).$$

因此：

$$L_{day,t}(i) = \max\left( 0,L_{t}(i) - \sum_{g = 1}^{G}M(i,g)c_{t - 1}(g) \right).$$

这里的 $L_{day,t}(i)$ 表示除可控灯具贡献之外的不可控背景光，包括自然光、室外反射光和其他不可控光源。

### 7. 目标照明需求生成与可学习需求系数

目标照明需求 $R_{t}(i)$ 表示第 $i$ 个工作表面单元当前应达到的归一化视觉亮度。由于不使用照度计，本文使用的是归一化目标值，例如 0.3、0.6、0.8。

目标需求由基础项、占用项和活动项组成：

$$R_{t}(i) = R_{base}(i) + R_{occ}(i) + R_{act}(i).$$

基础项由表面语义决定：

$$R_{base}(i) = b_{\mathcal{l}_{i}}.$$

占用项由 occupancy head 输出决定：

$$R_{occ}(i) = \lambda_{\mathcal{l}_{i}}^{occ}O_{t}(i).$$

活动项为：

$$R_{act}(i) = O_{t}(i)\sum_{k}A_{t}(i,k)r_{\mathcal{l}_{i},k} + \mathbf{1}\left\lbrack i \in \Omega_{board} \right\rbrack s_{board,t}r_{board}.$$

其中：

$$s_{board,t} = \max_{q \in \Omega_{board\_ front}}A_{t}\left( q,blackboard\text{-}writing \right).$$

第一项表示当前 cell 附近有人并发生某种活动时产生的本地活动需求。第二项是黑板板书传播项：当黑板前区域检测到板书活动时，黑板面作为被观看和书写的任务表面，需要提高照明需求。该项只作用于 $\Omega_{board}$ 中的黑板 cell，不影响课桌、过道或投影幕等工作表面。

需求函数中的策略系数记为：

$$\theta_{R} = \{ b_{\mathcal{l}},\lambda_{\mathcal{l}}^{occ},r_{\mathcal{l},k},r_{board}\}.$$

这些系数不再完全由人工设定，而是通过人工标注的最终灯光控制策略进行离线校准。对于若干典型课堂场景，由人工给出期望灯光控制向量：

$$c_{t}^{gt} = \left\lbrack c_{t}^{gt}(1),c_{t}^{gt}(2),\ldots,c_{t}^{gt}(G) \right\rbrack.$$

需求系数首先生成 $R_{t}\left( i;\theta_{R} \right)$，目标需求进入控制代价函数并经过可微展开控制层输出预测控制向量 ${\widehat{c}}_{t}$。训练损失为：

$$\mathcal{L}_{R} = \lambda_{c} \parallel {\widehat{c}}_{t} - c_{t}^{gt} \parallel_{2}^{2} + \lambda_{l} \parallel L_{pred}\left( {\widehat{c}}_{t} \right) - L_{pred}\left( c_{t}^{gt} \right) \parallel_{2}^{2} + \lambda_{p} \parallel \theta_{R} - \theta_{R}^{0} \parallel_{2}^{2}.$$

第一项约束预测控制向量接近人工控制策略；第二项约束预测控制产生的工作表面亮度分布接近人工策略产生的亮度分布，以缓解灯光控制非唯一问题；第三项约束需求系数不偏离初始经验策略 $\theta_{R}^{0}$ 过远。

为了使梯度能够从人工控制策略误差传回需求系数，训练阶段将控制求解展开为 $K$ 步可微投影梯度迭代。设：

$${\widehat{c}}_{t}^{(0)} = c_{t - 1},$$

第 $r$ 步更新为：

$${\widehat{c}}_{t}^{(r + 1)} = \Pi_{\lbrack 0,1\rbrack}\left( {\widehat{c}}_{t}^{(r)} - \tau\nabla_{c}J\left( {\widehat{c}}_{t}^{(r)};R_{t}\left( \theta_{R} \right),L_{day,t},M \right) \right),\quad r = 0,\ldots,K - 1.$$

经过 $K$ 步后得到 ${\widehat{c}}_{t} = {\widehat{c}}_{t}^{(K)}$。由于 $R_{t}\left( i;\theta_{R} \right)$ 对需求系数可微，展开控制层中的每一步也可微，因此 $\mathcal{L}_{R}$ 可以通过反向传播更新 $\theta_{R}$。在线阶段则固定校准后的 $\theta_{R}$，不再更新需求系数。

### 8. 控制优化

控制器输入包括环境光 $L_{day,t}(i)$、目标需求 $R_{t}(i)$、亮度上限 $R_{high,t}(i)$、灯光贡献矩阵 $M(i,g)$ 和上一时刻灯光状态 $c_{t - 1}$。控制器要求解当前灯光控制向量：

$$c_{t} = \left\lbrack c_{t}(1),c_{t}(2),\ldots,c_{t}(G) \right\rbrack,\quad 0 \leq c_{t}(g) \leq 1.$$

给定候选控制向量 $c_{t}$，预测工作表面亮度为：

$$L_{pred}\left( i,c_{t} \right) = L_{day,t}(i) + \sum_{g = 1}^{G}M(i,g)c_{t}(g).$$

控制代价函数定义为：

$$J\left( c_{t} \right) = \alpha E\left( c_{t} \right) + \beta U\left( c_{t} \right) + \gamma O\left( c_{t} \right) + \delta S\left( c_{t} \right) + \eta F\left( c_{t} \right).$$

其中，$E\left( c_{t} \right)$ 为能耗项，$U\left( c_{t} \right)$ 为欠照惩罚，$O\left( c_{t} \right)$ 为过照惩罚，$S\left( c_{t} \right)$ 为调光平滑项，$F\left( c_{t} \right)$ 为局部均匀性项。欠照惩罚约束重要工作表面达到目标需求，过照惩罚限制投影幕等区域过亮，平滑项避免灯光突变，局部均匀性项减少活动区域内部亮度差异。

在线控制时，需求系数 $\theta_{R}$ 已在离线训练阶段校准完成，因此 $R_{t}(i)$ 被视为当前场景下的已知目标需求。求解时采用 L-BFGS-B。初始点取上一时刻灯光状态：

$$c_{t}^{(0)} = c_{t - 1}.$$

优化器根据 $J\left( c_{t} \right)$ 对 $c_{t}$ 的梯度迭代更新，并在边界约束下求得近似最优控制向量：

$$c_{t}^{*} = \arg\min_{0 \leq c_{t} \leq 1}J\left( c_{t} \right).$$

如果实际灯具只支持离散档位，则先求连续解，再将结果量化到最近档位。需要强调的是，控制优化不是训练神经网络，其优化对象是当前灯光控制向量 $c_{t}$，不是模型参数。

### 9. 训练、标定、需求系数校准与在线控制的区分

本文中存在四类不同的优化过程，它们的优化对象不同，在此特意强调。

第一类是视觉感知网络调整。Swin-Tiny-FPN 共享 backbone 使用预训练权重初始化，占用、活动和光照三个任务 head 使用教室数据进行调整。对应损失为：

$$\mathcal{L}_{vision} = \lambda_{occ}\mathcal{L}_{occ} + \lambda_{act}\mathcal{L}_{act} + \lambda_{light}\mathcal{L}_{light}.$$

这里更新的是视觉网络参数，包括任务 head 参数以及可选的小学习率 backbone 参数，目标是提高 $O_{t}(i)$、$A_{t}(i,k)$ 和 $L_{t}(i)$ 的估计质量。

第二类是离线系统参数标定，包括 3DGS 静态表示优化和灯具贡献矩阵 $M$ 的标定优化。3DGS 优化的是静态 Gaussian 场景参数，$M$ 的标定优化的是灯具到工作表面的贡献矩阵。这些参数在在线控制阶段固定使用。

第三类是需求系数校准。需求系数 $\theta_{R}$ 决定了感知状态如何转化为目标需求 $R_{t}(i)$。本文不直接标注逐 cell 目标亮度，而是利用人工控制策略 $c_{t}^{gt}$ 作为间接监督。校准时先固定视觉感知网络和 $M$，只更新 $\theta_{R}$，避免需求系数吸收视觉感知误差。校准完成后，$\theta_{R}$ 固定用于在线目标需求生成。

第四类是在线控制优化。在线阶段不再更新网络参数，也不再更新需求系数，而是使用当前感知状态、已标定的 $M$ 和已校准的 $\theta_{R}$，通过 L-BFGS-B 求解当前时刻的灯光控制向量 $c_{t}$。

### 10. 原型仿真验证设计

本文定位为方法设计与原型仿真验证。验证重点不是完整工程部署，而是检查方法链条是否闭合、各变量是否能够在统一 $cell_{i}$ 索引下工作，以及控制优化是否能够根据归一化目标需求给出合理灯光方案。

验证数据由空教室多相机图像、人工校正语义掩码、VGGT 点图、3DGS 静态参考、灯光切换实验以及少量人工标注灯光控制策略组成。在线部分使用多相机视频片段模拟不同课堂状态，例如听课、书写、板书、投影和讨论。人工控制策略用于校准需求系数 $\theta_{R}$，而不是直接标注每个 $cell_{i}$ 的目标亮度。评价指标采用归一化误差和任务满足率，不使用 lux 误差。归一化光照估计误差可写为：

$$E_{L} = \frac{1}{S_{c}}\sum_{i = 1}^{S_{c}}\left| L_{t}(i) - {\widehat{L}}_{t}(i) \right|.$$

控制效果主要观察两个方面：一是高需求 cell 的欠照惩罚是否降低；二是灯光控制向量的总能耗是否低于统一高亮策略下的能耗。由于本文不设置对比方法和消融实验，验证部分只用于说明所提流程的可执行性和变量闭环。

## 研究结论

本文提出了一种基于 VGGT 点图、3DGS 静态辅助和三维工作表面单元的纯视觉教室精细照明调控方法。方法的核心不是直接在二维图像上判断哪里开灯，而是先建立真实三维工作表面单元，再将占用、活动、光照、环境光、目标需求和灯具贡献统一定义在 $cell_{i}$ 上。离线阶段，VGGT 点图和语义掩码用于构建工作表面，3DGS 用于静态外观与可见性辅助，灯光切换实验用于学习贡献矩阵 $M$。在线阶段，Swin-Tiny-FPN 共享视觉 backbone 和三个任务 head 输出 $O_{t}(i)$、$A_{t}(i,k)$ 和 $L_{t}(i)$，随后通过环境光分离、目标需求生成和 L-BFGS-B 控制优化得到灯组亮度 $c_{t}$。

相比传统的房间级或固定分区照明控制，本文方法把控制对象从抽象区域推进到真实教学工作表面；相比单纯视觉检测方法，本文进一步将视觉状态与灯具贡献矩阵、环境光分离和控制优化联系起来；相比直接人工设定照明需求参数，本文利用人工标注的灯光控制策略，通过可微展开控制层对需求系数进行校准，避免逐 cell 标注目标亮度的高成本。该方案在研究逻辑上形成了从三维建模、视觉感知、需求生成到灯光优化的闭环，为绿色低碳校园中的教室精细化节能照明提供了一种可解释、可复现的技术路线。

需要说明的是，本文仍属于方法设计和原型仿真验证方案。实际部署时，仍需进一步处理相机遮挡、长期光照变化、学生隐私保护、不同教室布局迁移以及真实灯具调光接口等问题。后续研究可进一步引入更大规模教室数据、用户舒适度反馈和更严格的实际节能评估，以验证该方法在真实校园建筑中的稳定性和节能收益。

## 参考文献

\[1\] Haq M. A. U., Hassan M. Y., Abdullah H., Rahman H. A., Abdullah M. P., Hussin F., Said D. M. A review on lighting control technologies in commercial buildings, their performance and affecting factors. Renewable and Sustainable Energy Reviews, 2014, 33: 268-279.

\[2\] Pandharipande A., Caicedo D. Smart indoor lighting systems with luminaire-based sensing: A review of lighting control approaches. Energy and Buildings, 2015, 104: 369-377.

\[3\] Delvaeye R., Ryckaert W., Stroobant L., Hanselaer P. Analysis of energy savings of three daylight control systems in a school building by means of monitoring. Energy and Buildings, 2016, 127: 969-979.

\[4\] Budhiyanto A., Chiou Y.-S. Visual comfort and energy savings in classrooms using surveillance camera derived HDR images for lighting and daylighting control system. Journal of Building Engineering, 2024, 86: 108841.

\[5\] Chiou Y.-S., Saputro S., Sari D. P. Visual comfort in modern university classrooms. Sustainability, 2020, 12(9): 3930.

\[6\] Wang J., et al. VGGT: Visual Geometry Grounded Transformer. CVPR, 2025.

\[7\] Kerbl B., Kopanas G., Leimkuehler T., Drettakis G. 3D Gaussian Splatting for Real-Time Radiance Field Rendering. ACM Transactions on Graphics, 2023.

\[8\] Liu Z., Lin Y., Cao Y., et al. Swin Transformer: Hierarchical Vision Transformer using Shifted Windows. ICCV, 2021.

\[9\] Lin T.-Y., Dollar P., Girshick R., et al. Feature Pyramid Networks for Object Detection. CVPR, 2017.

\[10\] Amos B., Kolter J. Z. OptNet: Differentiable Optimization as a Layer in Neural Networks. ICML, 2017.

\[11\] He K., Gkioxari G., Dollar P., Girshick R. Mask R-CNN. ICCV, 2017.

\[12\] Kendall A., Gal Y., Cipolla R. Multi-Task Learning Using Uncertainty to Weigh Losses for Scene Geometry and Semantics. CVPR, 2018.

\[13\] Liang T., et al. Lift, Splat, Shoot: Encoding Images from Arbitrary Camera Rigs by Implicitly Unprojecting to 3D. ECCV, 2020.

\[14\] Li Z., Wang W., Li H., et al. BEVFormer: Learning Bird's-Eye-View Representation from Multi-Camera Images via Spatiotemporal Transformers. ECCV, 2022.

\[15\] Mildenhall B., Srinivasan P. P., Tancik M., et al. NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis. ECCV, 2020.
