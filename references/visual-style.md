# 半调纸拼贴设计规范

保留原版的视觉语言，物件、配色和时长随文稿语义选择。

原版四条参考片已收录，见 [original-examples.md](original-examples.md)。按语义挑选并实际查看图像或抽帧；可直接沿用适合文稿的构图、物件组合和动作结构，无需先建立自己的参考库。保留来源和许可，按需要适配。原片尺寸仅 240×427、10fps，不能据此降低新项目的交付规格。

## 视觉命题

先提炼观众应理解的一个意思，再选动作与物件。常用动作：打开、连接、归档、装订、筛选、压缩、分叉、点亮、组装。机器、轨道、地图、文件夹、棋子等可作为隐喻，不必每次引入人物。避免把口播全文堆进画面。

一镜通常约 3–6 个主要视觉组；多张资料可视作一个资料组。多镜保持材质与图形语言一致，并形成先后叙事。

脚本、静帧和成片均按 [narrative-quality.md](narrative-quality.md) 检查。主体、作用物和结果物的关系优先于装饰数量；裁切、筛选导致主体减少时，要设计可读的结果构图，避免最后只剩窄小纸条和大量无意义空白。

## 美术规则

- 强烈、平坦、均匀的纸面色场，细微未涂布纸纤维。
- 主体以黑白 photographic halftone cut-outs 为骨架，保留可见网点。
- 局部彩色卡纸服务信息层级：奶油白、芥末黄、珊瑚红、青绿等。
- 清晰裁切边、细奶油白描边、低透明度柔和投影。
- 主体与关键动作落在安全区域，保留干净留白；字幕安全区域按用户剪辑需求预留。
- 避免杂乱小碎片、光滑 3D、写实背景漂移、Logo、水印、假字或界面。
- 默认不烧录字幕和口播全文。确需关键词、数字或真实图表时，先列文字白名单，由本地代码准确排版，不让图像模型杜撰。

色彩建议：焦橙/红适合消耗与紧迫，芥末黄适合警示，墨绿适合认知，深紫适合沉淀，青绿适合判断和协作。这些是建议，整批不必同色。

## 内置图片生成提示词模板

```text
Use case: stylized-concept
Asset type: separate transparent cutout for a layered editorial B-roll animation
Primary request: [一个物件或一组不可分割的剪贴物件及其语义]
Style: premium editorial paper collage, black-and-white photographic halftone,
selective [点色] cardstock, crisp cut edge, fine warm-cream keyline,
subtle uncoated-paper fiber and restrained physical paper shadow.
Composition: isolated full silhouette with generous transparent margin;
[与其他纸片需要保持的方向或尺度关系].
Constraints: actual alpha transparency; no background rectangle;
no readable text, numbers, logos, watermark, UI, glossy 3D or clutter.
```

最终构图使用已有的物件素材在本地组成。生成素材、最终静帧和最终动画分别保存；提示词也保存到项目，不能只留下聊天中的临时图片。

图集可以作为一个动画素材资产使用，但需检查真实边界；各图块应有透明间隔。优先单独图层文件，避免素材跨格或相互粘连。

## 本人照片与手绘形象

用户提供的照片是编辑目标，先查看原图再用内置图片工具处理。保留可识别的面部特征、眼镜、发型和经用户确认的服装；只改变抠图、半调印刷与纸边等所需风格。手绘形象优先保留原造型与画风，不擅自改成摄影人像。生成后让用户确认身份与形象，再固定为可复用资产。

## 动作与审美检查

结构 → 物件/人物 → 连接 → 动作/结果；元素滑入、卡位，最后稳定停留。12fps 左右的构图更新可营造定格感，容器输出帧率仍继承项目设置。动画开始和结束要适合剪辑，不为风格生硬抢占口播节奏。

静帧：隐喻清晰、主体集中、可分层、有留白、无伪字、人物正确。动画：逐件入场、无镜头漂移、无意形变或多余物件，末帧与确认构图一致。检查实际导出的首尾帧，不把每秒抽帧里的第一张误认为精确首帧。
