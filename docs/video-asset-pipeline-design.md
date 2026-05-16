# Video Asset Pipeline 设计草案

_最后更新：2026-05-07_
_状态：详细设计，暂不实现_

本文设计 browser-bridge 面向 B 站、抖音等视频站点的下一阶段基础设施能力。

核心原则：

- 视频不是“更长的文本”，而是多模态知识对象。
- 站点 adapter 只负责页面语义和资源入口，不直接承担视频理解。
- 模型负责理解和判断，确定性工具负责下载、切片、截图、落盘和格式转换。
- 先生成可检查的中间产物，再生成面向业务的报告、图文或指标。

## 背景

当前 B 站和抖音第一版支持只读取：

- 视频页标题、作者、描述、封面。
- 公开互动指标。
- 搜索结果链接。
- 作者主页公开指标。

这已经足够支撑 media-suite 的基础发现、追踪和对标。但视频内容本身仍未被解析：

- 不识别口播。
- 不读取字幕。
- 不理解画面、PPT、代码、商品、UI 或演示流程。
- 不抽取关键帧。
- 不生成视频内容摘要或图文稿。

后续应把视频处理做成独立异步管线，而不是把复杂逻辑塞进每个站点 adapter。

## 项目边界

browser-bridge 负责：

- 从真实浏览器页面读取视频页语义信息。
- 获取可用的视频资产入口或保存页面上下文。
- 触发视频资产采集与分析 workflow。
- 产生结构化中间产物和文件资产。
- 向 media-suite 返回可追踪的任务结果。

browser-bridge 不负责：

- 账号、作品、选题、发布任务、竞品实体的业务建模。
- 长期保存业务快照。
- 决定内容策略。
- 直接替 media-suite 发布最终报告。

media-suite 负责：

- 调度什么时候分析哪个视频。
- 保存分析任务、资产引用、指标快照和报告结果。
- 把分析结果转成业务状态、看板或内容生产任务。

## 分层架构

```text
Site Page
  -> extension adapter
    -> read_post / read_profile_metrics / search
      -> video asset workflow
        -> acquisition
        -> inspection
        -> segmentation
        -> multimodal analysis
        -> keyframe extraction
        -> material synthesis
          -> media-suite
```

建议新增模块：

```text
bridge/app/video/
  assets.py
  inspect.py
  segment.py
  keyframes.py
  schemas.py
  workflows.py
```

建议本地缓存目录：

```text
temp/video-assets/
  <asset_id>/
    source.json
    manifest.json
    original.*
    normalized.mp4
    segments/
      0001.mp4
      0002.mp4
    frames/
      0001.jpg
      0002.jpg
    analysis/
      inspection.json
      segments.json
      multimodal.json
      keyframes.json
      material.json
```

## 核心数据模型

### VideoAssetSource

```json
{
  "site": "bilibili",
  "url": "https://www.bilibili.com/video/...",
  "externalPostId": "BV...",
  "author": {
    "name": "...",
    "profileUrl": "..."
  },
  "title": "...",
  "description": "...",
  "cover": "...",
  "metrics": {},
  "capturedAt": "2026-05-07T10:14:30+08:00"
}
```

### VideoAssetManifest

```json
{
  "assetId": "bilibili_BVxxx_20260507T101430",
  "source": {},
  "files": {
    "original": null,
    "normalized": null,
    "cover": null
  },
  "media": {
    "type": "video",
    "durationSec": null,
    "width": null,
    "height": null,
    "fps": null,
    "hasAudio": null,
    "hasSubtitles": null
  },
  "status": "created"
}
```

### VideoSegment

```json
{
  "index": 1,
  "startSec": 0,
  "endSec": 600,
  "file": "segments/0001.mp4",
  "status": "ready"
}
```

### MultimodalSegmentAnalysis

```json
{
  "segmentIndex": 1,
  "startSec": 0,
  "endSec": 600,
  "summary": "...",
  "topics": [],
  "entities": [],
  "visualEvidence": [
    {
      "timestampSec": 123.4,
      "description": "画面中出现架构图",
      "reason": "支撑关于系统分层的论点"
    }
  ],
  "audioEvidence": [
    {
      "startSec": 120.0,
      "endSec": 135.0,
      "summary": "讲者解释关键限制"
    }
  ],
  "uncertainties": []
}
```

### KeyframeCandidate

```json
{
  "timestampSec": 123.4,
  "file": "frames/0003.jpg",
  "caption": "...",
  "reason": "这张图支撑文章第二节的核心论点",
  "linkedSectionId": "section-2"
}
```

### ArticleMaterial

```json
{
  "title": "...",
  "outline": [
    {
      "id": "section-1",
      "heading": "...",
      "claims": [],
      "evidence": []
    }
  ],
  "terms": [],
  "quotes": [],
  "keyframes": [],
  "uncertainties": [],
  "recommendedUse": "draft_article"
}
```

## Workflow 设计

### `prepare_video_asset`

输入：

```json
{
  "site": "bilibili",
  "url": "https://www.bilibili.com/video/..."
}
```

职责：

- 调用站点 `read_post` 获取页面语义。
- 创建 `assetId` 和本地目录。
- 保存 `source.json` 和初始 `manifest.json`。
- 不下载视频，不调用模型。

输出：

```json
{
  "ok": true,
  "assetId": "...",
  "manifestPath": "temp/video-assets/.../manifest.json",
  "source": {}
}
```

### `inspect_video_asset`

职责：

- 检查是否已有本地视频文件。
- 使用 `ffprobe` 读取时长、分辨率、fps、音轨。
- 更新 `manifest.media`。

边界：

- 如果只拿到页面元信息，没有视频文件，则返回 `needsAcquisition: true`。
- 不绕过平台限制，不做未授权下载。

### `segment_video_asset`

职责：

- 根据时长、大小和分辨率决定是否切片。
- 默认目标：
  - 单片不超过 20 分钟。
  - 必要时降采样到 720p。
  - 保留音频和画面，不退化成纯文本。

输出：

```json
{
  "segments": [
    {
      "index": 1,
      "startSec": 0,
      "endSec": 600,
      "file": "segments/0001.mp4"
    }
  ]
}
```

### `analyze_video_segments`

职责：

- 对每个 segment 做多模态理解。
- 输出结构化 JSON，而不是直接写最终文章。
- 支持并发，但合并时必须按全局时间线排序。

模型输入应尽量保留：

- 视频画面。
- 音频。
- 屏幕文字。
- 页面元信息。
- 业务提示词。

输出字段：

- `summary`
- `topics`
- `entities`
- `visualEvidence`
- `audioEvidence`
- `uncertainties`

### `select_keyframes`

职责：

- 基于文章材料和视频理解结果挑选关键帧候选。
- 每个候选必须包含 `reason`。
- 时间戳统一使用原视频全局时间。

注意：

- 模型给出的时间戳不要求帧级精准。
- 后续可以在目标时间前后各取几张候选帧二次筛选。

### `extract_keyframes`

职责：

- 使用 `ffmpeg` 按时间戳截图。
- 文件命名稳定。
- 更新 `keyframes.json`。

这一步不需要模型参与。

### `generate_article_material`

职责：

- 根据多模态分析和关键帧生成可供 media-suite 使用的素材包。
- 输出结构化材料，不直接假设最终发布渠道。

可服务的上层场景：

- 视频转图文草稿。
- 竞品视频拆解。
- 直播复盘。
- 课程视频笔记。
- 产品演示分析。

## 状态机

```text
created
  -> inspected
  -> acquired
  -> segmented
  -> analyzed
  -> keyframes_selected
  -> keyframes_extracted
  -> material_ready
  -> failed
```

失败处理：

- 每一步保存局部结果。
- 每一步可独立重试。
- 模型输出解析失败只重试当前 segment。
- ffmpeg 失败保留 stderr 摘要。
- 永远不要删除已有成功产物，除非显式清理缓存。

## 与 media-suite 的合同

media-suite 可以先只依赖以下字段：

```json
{
  "assetId": "...",
  "source": {},
  "media": {},
  "status": "material_ready",
  "material": {
    "outline": [],
    "keyframes": [],
    "uncertainties": []
  }
}
```

media-suite 不应依赖：

- 本地 ffmpeg 命令细节。
- 模型供应商。
- segment 文件名之外的内部临时路径结构。
- 浏览器 DOM selector。

## 实现顺序建议

1. 只实现 `prepare_video_asset`，保存页面语义和 manifest。
2. 增加本地文件输入版 `inspect_video_asset`，先不做平台下载。
3. 增加 `segment_video_asset` 和 `extract_keyframes`，验证 ffmpeg 链路。
4. 增加可插拔 multimodal provider 接口，但先支持 mock/provider-less dry run。
5. 增加真实多模态分析 provider。
6. 最后接入 media-suite 的异步任务调度。

## 不做事项

第一阶段不做：

- 自动绕过平台下载限制。
- 实时直播分析。
- 自动发布最终图文。
- 自动点击视频平台状态变更动作。
- 把长视频直接一次性塞给模型。
- 把视频先完整压扁成 ASR 文本再做全部理解。

## 质量门

实现时至少验证：

- `prepare_video_asset` 不依赖视频文件也能产出 manifest。
- `inspect_video_asset` 对无视频文件返回 `needsAcquisition`。
- ffmpeg/ffprobe 不存在时错误清晰。
- segment 合并后时间戳是原视频全局时间。
- keyframe 文件路径真实存在。
- 模型 JSON 解析失败可定位到 segment。
- media-suite 可只读 `assetId/status/material` 完成业务落库。
