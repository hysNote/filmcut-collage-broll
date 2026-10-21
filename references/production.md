# 本地制作与交付

## 工具与项目

所需工具：Python 3.10+、Python `playwright` 包、可启动的本机 Chrome/Edge/Chromium、FFmpeg 与 ffprobe。脚本通过显式参数、`FILMCUT_FFMPEG` / `FILMCUT_FFPROBE` / `FILMCUT_CHROME` 环境变量、PATH 和工作目录祖先的 `.runtime` 发现工具，不硬编码用户机器路径。

先检查已有环境，复用可用 Python 与浏览器。缺少 Python 包时在项目隔离环境安装 `playwright`；只有确实没有可用浏览器时才考虑安装本地浏览器。以上不需要生成服务密钥。本地缺项应如实说明，不切到外部生成服务。

下文 `python` 指选定的可用解释器，`<skill>` 与 `<project>` 换成实际绝对路径；不要原样传占位符。优先复用当前工作目录里已有且依赖齐全的隔离 Python 环境。

```text
python <skill>/scripts/local_tools.py
python <skill>/scripts/init_project.py --project <project> --video <rough-cut.mp4> --transcript <transcript.txt>
```

聊天中的逐字稿先保存成 UTF-8 文本再传路径。只有文稿时省略 `--video`，先做未对齐规划。需要给本地听审/转写工具提取音频时加 `--extract-audio`，输出为单声道 16kHz WAV；不要把它当成转写结果。初始化不复制大视频，只记录其绝对路径和指纹；移动项目后需重新定位并核验原片。

## 画面脚本与时间核验

`manifest.json` 是逐镜头记录。`inputs` 由初始化工具填写；`output` 根据原片规格初始化，再按用户确认调整。VFR 原片需检查剪辑软件导出的实际时间基准，不能仅用帧号推断口播时间。时间点核验方式可以是本地听审、经核对的字幕或用户明确提供的时间段。

用户审阅表以源视频为参考，按文稿顺序统一使用四列：

```text
文案 | 时间/时长 | 预期画面呈现 | 最终结果图
```

时间列记录核验后的源片入点–出点和动画长度；未核验时明确标为待对齐与建议时长。画面列简述开始、变化、结果。图片列脚本阶段标待生成，静帧阶段直接嵌入实际完成帧；出镜行写保留原片。详细镜头编号、参考、物件、配色与动作参数仍在 manifest/制作记录保存，不要求用户逐项阅读，也不默认展示中间静帧。

初剪文件内容变化时重新对齐。脚本的源文件 SHA256 检查会阻止使用已改变的原片继续出片。长文稿先选少量有信息价值的视觉节点；不因每段都能画而把整条口播铺满动画。

## 单个镜头的数据格式

以下是结构示例，不是自动批准或固定创意模板。`shots` 的数量可变，`id` 用稳定的 ASCII 编号。

```json
{
  "id": "01-map",
  "quote": "因此，我们需要 AI 帮助我们拆解每一个阶段的学习目标和范围。",
  "meaning": "给每阶段设定明确目标和边界",
  "visual_idea": "散乱资料分装到三个边界清楚的纸框里",
  "objects": ["资料组", "任务框", "目标标记"],
  "motion_plan": "散乱资料进入 → 任务框落位 → 资料归组 → 目标点出现",
  "duration_s": 4,
  "timeline": {"in_s": null, "out_s": null, "verified": false, "method": ""},
  "presentation": "full-screen",
  "edit_notes": "覆盖对应口播，句末回到出镜。人物需要时使用用户确认的形象。",
  "background": "#087e73",
  "stop_motion_fps": 12,
  "approvals": {},
  "layers": [
    {"type": "rect", "x": 360, "y": 620, "width": 540, "height": 400,
     "fill": "#f0e3c4", "enter": {"start": 0.2, "duration": 0.6, "from_x": -700}},
    {"type": "image", "src": "assets/research-papers.png", "x": 360, "y": 620,
     "width": 350, "rotation": -4, "enter": {"start": 0.9, "duration": 0.7, "from_y": 900}},
    {"type": "circle", "x": 520, "y": 470, "radius": 25, "fill": "#e3b743",
     "enter": {"start": 2.3, "duration": 0.4, "from_y": -100}}
  ]
}
```

示例中的图片需要由内置图片工具实际生成并保存。不要用缺失图片或纯占位形状代替最终栅格素材。`duration_s` 取实际核验区间长度，渲染四舍五入到最近一帧；`output.fps` 支持整数或 `30000/1001` 之类有理数。

有可靠时间时填写 `in_s`、`out_s`、`verified: true` 和 `method`，且长度与动画时长相差不超过一帧。不可靠时保留 null/false，插入说明会留空，不输出伪精确时间。

`presentation` 默认 `full-screen`。用户要求局部叠加时，另行设计透明图层/蒙版交付；当前编码器输出普通不透明 MP4。

## 确认记录

```text
python <skill>/scripts/render.py --project <project> --fingerprints --shots 01-map
```

这只打印指纹，不授予确认。收到真实用户确认后，把对应镜头记录为：

```json
"approvals": {
  "script": {"hash": "打印的 script_hash", "user_message": "用户实际同意该画面脚本的原话"}
}
```

随后生成素材并执行：

```text
python <skill>/scripts/render.py --project <project> --stills --shots 01-map
```

用户看过 `stills/01-map.png` 并确认后，再打印指纹，将确认记录补充为：

```json
"still": {
  "scene_hash": "当前 scene_hash",
  "image_hash": "当前 image_hash",
  "user_message": "用户实际认可该静帧的原话"
}
```

不得把“开始做静帧”记录成“静帧已通过”。记录的镜头范围与用户确认范围一致。用户明确认可整组素材并授权继续时可沿用，不重复索取同一确认；需要时说明素材如何对应完成帧。

画面脚本的语义、时长、时间点改变会使脚本指纹过期；静帧对应的层、动画参数或图片改变会使静帧指纹过期。旧静帧按内容指纹保留一份，不直接覆盖历史版本。再次只渲染被修改的 ID。

对于用户已明确授权的“结果图确认后实现过程”：先保留批准时的 PNG、manifest、模板、真实确认语句与场景指纹；实现同一脚本所述动作后，重新执行 `--stills`，比较新旧 PNG 的 SHA256。只有完成帧相同、语义及已确认时长不变，才可基于原授权更新 `still.scene_hash`，同时记录旧场景指纹、比较证据和继承依据。这是已授权动作的落实，不是新批准。图像或语义不同时重新提交相关行，不篡改旧记录。后续动画 QA 仍要检查中间动作，不能由末帧一致推断过程正确。

## 四列审阅表

执行 `python <skill>/scripts/review.py --project <project>` 生成 `review.html` 与 `storyboard.md`。它从 shots 读取原句、时间和画面构想；已有静帧直接嵌入，没有图片时显示待生成。先生成表，再在确认后更新同一张表，不增加中间静帧审阅。

可选 `review_sequence` 按全文记录出镜与动画顺序，例如：

```json
"review_sequence": [
  {"quote": "我想分享最近的学习方法。", "presentation": "talking-head", "visual": "保留本人出镜"},
  {"shot_id": "01-map"}
]
```

镜头可用 `review_visual` 提供面向用户的简短开始→变化→结果描述；用 `suggested_duration` 写建议范围。未核验行始终标待对齐；不要在这些字段里伪造真实时间码。

## 模板接口与分层控制

初始化复制 `assets/canvas-template.html` 到项目。渲染器把 JSON 嵌入为 `preview.html`，可以双击离线预览。项目内模板可针对创意扩展；保留以下接口：

- `window.ready`：素材载入完成。
- `window.assetErrors`：缺失素材列表；有错误时禁止出片。
- `window.drawFrame(shotId, seconds)`：确定性绘制指定时刻，不能依赖随机数或真实播放时间。
- 一个 canvas，像素尺寸与 `output` 完全一致，渲染模式隐藏周围 UI。

模板中的 `layers` 按数组顺序从底到顶绘制：

- `image`：项目内图片，`src` 用相对路径，`width` 等比缩放；可配 `height`、源图 `crop: [x,y,w,h]` 与相对 crop 的 `polygon`。
- `rect` / `circle`：纸框和目标点，使用 `fill`、可选 `stroke`。
- `line`：`points: [[x,y], ...]`、`stroke`、`line_width`，按进入进度逐步画出；`reveal: false` 可关闭逐段绘制。
- `text`：用户确认过的准确关键词或数字，使用 `text`、`font`、`fill`，默认不添加。
- 位置 `x,y` 为中心坐标，`rotation` 是角度，`scale` 默认为 1。
- `enter` 是出现时间和位移入场，`from_x/from_y` 是相对于最终位置的偏移；默认不做透明度淡入。
- `keyframes` 可以指定 `time,x,y,rotation,scale,opacity`；按时间升序，第一帧之前不出现，用于散乱 → 归组等多阶段运动。不要与 `enter` 叠加矛盾的位移。
- `stop_motion_fps` 控制定格节拍；设 0 可关闭，输出容器帧率不变。

保留有意义的最终停留，最后一个动作通常在镜头结束前至少约 0.4 秒完成，具体按口播节奏决定。人物以独立图片路径接入，替换后走对应静帧确认。图集取样不得混入相邻物件。

## 渲染、检查与交付

```text
python <skill>/scripts/render.py --project <project> --shots 01-map
python <skill>/scripts/deliver.py --project <project> --shots 01-map
```

未通过的镜头不要放进 `--shots`。渲染默认每 32 帧使用一个新的本地浏览器进程，避免长时间连续截图时的通信中断；`--batch-size` 可调整。每批完成后记录场景指纹，中断后只复用指纹一致的已完成批次。渲染采用项目内临时逐帧 JPEG，再以 H.264、yuv420p、零音轨编码，限制解码、滤镜和编码线程。保留 `.render-frames/` 便于失败后排查，后续清理按项目范围处理。工具发现优先使用项目 `.runtime/media-tools/stable/` 中的稳定版；开发快照发生访问冲突时，更换稳定发行版并复用已有帧，不反复重跑同一崩溃命令。

`deliver.py` 验证原片指纹、确认状态、渲染记录、片段指纹、尺寸、帧率、帧数、时长、零音轨以及完整解码，输出：

- `clips/<id>.mp4` 与 `.render.json`
- `stills/<id>.png`
- `qa/<id>/first.png`、`last.png`、`contact-sheet.jpg`
- `qa/technical.json`
- `insertion-guide.md` 和 `insertion-guide.csv`

人工对照实际末帧与确认静帧，检查组装过程、语义、人物身份与素材边缘，把结论补入 `qa-review.md`。每秒抽帧图的第一格可能不是精确第 0 帧；空场检查用 `first.png`。

同时执行 [叙事与丰富度检查](narrative-quality.md)，将语义覆盖、关键状态变化、参考借用和完成构图判断写入人工 QA。每秒抽帧不足以判断接触、裁切和归组时，再检查动作前后帧或播放实际片段。技术检查不评判这些项目；缺失关键语义时返回对应脚本阶段，不用增加装饰或放慢动画来掩盖。

工具链报告成功不代表视觉质量通过。只有两者都通过才交付为完成片段。附带保存到项目中的素材与图片生成提示词；拼接预览可选，最终合成由用户完成。

用户需要连续效果时执行 `python <skill>/scripts/assemble.py --project <project>`。它仅接受已确认且渲染指纹有效的片段，输出 `clips/combined-preview.mp4`、`preview-chapters.json` 和 `watch.html`；独立片段保留。连续预览使用相同规格的本地 H.264 片段，逐个及整体校验，章节时间仅指预览内部位置。

Windows 受限环境若浏览器启动持续停滞，保留日志并按宿主授权机制运行本地浏览器；不要反复启动相同失败进程。不能运行浏览器时说明缺项，不宣称已完成静帧或动画。中文字体依赖当前机器；跨平台复现时安装可用中文字体并重新检查排版。
