# Filmcut Collage B-roll

把初剪口播视频和逐字稿，做成可以自行插入剪辑的半调纸拼贴动画。

一个为 Codex 等具备内置图片生成与本地执行能力的助手设计的 skill：**四列表格确认脚本 → 在同一张表确认最终结果图 → 本地分层动画 → 独立片段与连续预览**。

图片使用宿主内置生图，动画使用 Canvas、浏览器与 FFmpeg。无需配置 Gemini 或其他外部生成 API Key。内置生图的可用性、额度和费用由宿主产品决定；本仓库本身不提供图片生成服务。

## 实际效果

| 三步学习路径 | 资料摊开 | 整理与阶段输出 |
|---|---|---|
| ![三步学习路径](examples/learning-workflow/01-three-steps.png) | ![资料摊开](examples/learning-workflow/02-information-sprawl.png) | ![分阶段输出](examples/learning-workflow/03-stage-plan.png) |

[查看或下载 22 秒连续样片](examples/learning-workflow/preview-22s.mp4) · [示例四列表格](examples/learning-workflow/README.md)

该样片为 720×1280、24fps、无声。它是本地分层动画的实际输出；未对齐真实口播。原 GitHub 的四条参考 GIF 另存于 `assets/original-reference/`，与本项目样片明确区分。

## 使用流程

1. 提供初剪口播视频和逐字稿。只有逐字稿也可以先做画面，但时间标为待对齐。
2. 助手通读全文，决定哪些内容保留本人出镜、哪些适合动画，用一张四列表格供你确认。
3. 脚本确认后生成每镜的最终结果图，直接填回表格最后一列。默认只确认完成图，不额外审阅中间静帧。
4. 结果图确认后，按已描述的开始、变化、结果制作动画，保持完成构图一致。
5. 交付独立无声 MP4、连续效果预览、插入说明和可编辑项目。最终与本人出镜视频拼接由你完成。

审阅格式始终为：

| 文案 | 时间/时长 | 预期画面呈现 | 最终结果图 |
|---|---|---|---|
| 对应的原句或连续片段 | 核验后的原片入点–出点、动画长度；无视频时写待对齐 | 简短写清开始 → 变化 → 结果 | 脚本阶段待生成；随后直接嵌入完成静帧 |

参考可直接借用原版的构图、物件组合与动作结构，不必为原创而回避有效设计。保留来源，并按文稿语义适配。每个物件要有作用，动作应产生可见结果，不用增加装饰掩盖内容单薄。

## 安装 skill

仓库根目录就是 skill。克隆到宿主的 skills 目录；已有同名目录时先检查版本，不直接覆盖个人修改。

Windows PowerShell：

```powershell
git clone https://github.com/hysNote/filmcut-collage-broll.git "$env:USERPROFILE\.codex\skills\filmcut-collage-broll"
```

macOS / Linux：

```bash
git clone https://github.com/hysNote/filmcut-collage-broll.git ~/.codex/skills/filmcut-collage-broll
```

如配置了自定义 `CODEX_HOME`，将目标换成其 `skills/filmcut-collage-broll` 子目录。也可让宿主的 skill 安装器从本仓库根路径安装。安装后在新一轮对话调用：

```text
使用 $filmcut-collage-broll，处理我的初剪口播视频和逐字稿。
先给我四列脚本表，确认后把最终结果图填进去；结果图通过后再做动画。
```

## 本地依赖

- Python 3.10+。
- Python Playwright 包，见 `requirements.txt`。
- 可启动的 Chrome / Edge / Chromium。
- FFmpeg 和 ffprobe，需具备 H.264 编码能力。
- 正确显示所需语言的字体；中文排版需检查实际渲染结果。
- 宿主提供内置图片生成。没有该工具时不能仅靠本仓库凭空生成栅格素材。

在本仓库目录创建隔离环境并安装 Python 依赖：

```bash
python -m venv .venv
# Windows: .venv\Scripts\python.exe -m pip install -r requirements.txt
# macOS/Linux: .venv/bin/python -m pip install -r requirements.txt
```

后续命令中的 `python` 指这个环境的解释器。浏览器优先使用已安装版本；没有时可执行 `python -m playwright install chromium`。FFmpeg/ffprobe 放入 PATH，或配置 `FILMCUT_FFMPEG`、`FILMCUT_FFPROBE` 的可执行文件绝对路径；浏览器可用 `FILMCUT_CHROME` 指定。

```bash
python scripts/local_tools.py
```

完整流程已在 Windows、Chrome、Python 3.12、Playwright 1.64 和 FFmpeg 9.0.2 上验证。macOS/Linux 具有工具发现支持，尚未做完整平台验证；字体和浏览器可影响跨平台像素结果。

## 工具与项目

工作项目应放在独立目录，保留自己的原片。下面是供助手执行的工具，不是绕过人工确认的一键生视频接口。

```bash
python scripts/init_project.py --project /path/to/project --transcript /path/to/script.txt --video /path/to/rough-cut.mp4
python scripts/review.py --project /path/to/project
# 真实确认画面脚本并生成分层素材后：
python scripts/render.py --project /path/to/project --stills
python scripts/review.py --project /path/to/project
# 真实确认结果图、实现动画并核对完成态后：
python scripts/render.py --project /path/to/project
python scripts/deliver.py --project /path/to/project
python scripts/assemble.py --project /path/to/project
```

初始化时 `--video` 可省略。源片规格与指纹可解析；语音转写/时间对齐需要宿主听审能力或另行安装的本地离线工具，本 skill 不自带 ASR 模型，也不会伪造时间码。完整 manifest、确认记录和命令说明见 [制作说明](references/production.md)。

项目典型产物：

```text
manifest.json              输入、分镜、图层、真实确认记录
review.html / storyboard.md 四列审阅表
assets/                    本项目生成素材与提示词
stills/                    最终结果图
clips/                     独立 MP4 和 combined-preview.mp4
watch.html                 连续预览播放页
preview-chapters.json      预览内部章节（不是口播时间码）
insertion-guide.md / .csv   原句、实际/待核验时间、片长、插入提示
qa/ 与 qa-review.md         技术检查和人工检查
```

普通 MP4 是不透明、无声的全屏素材；透明叠加需另行约定格式或蒙版。质量检查覆盖语义、动作因果、完成构图、边缘、准确文字、尺寸帧率和完整解码。

## 开发验证

```bash
python -m unittest discover -s tests -v
```

可选本地端到端测试使用合成测试确认记录，验证拒绝未批准片段、部分批准、真实导出和拼接；需要浏览器、FFmpeg 与 Python 依赖：

```powershell
# PowerShell
$env:FILMCUT_RUN_RENDER_TESTS = '1'
python -m unittest discover -s tests -v
```

```bash
# macOS/Linux
FILMCUT_RUN_RENDER_TESTS=1 python -m unittest discover -s tests -v
```

## 来源与许可

改编自狗哥笔记的 [gbro-collage-broll](https://github.com/pyang5166/gbro-collage-broll)，保留拼贴视觉、原版参考与确认方法；四列审阅、最终静帧流程和本地工具由本项目适配实现。

采用 [MIT License](LICENSE)，素材来源见 [NOTICE.md](NOTICE.md)。不包含原项目的外部生成服务脚本，也不包含个人原片、录音、账号信息或本地运行环境。
