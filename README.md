# NyaManga
用 python 驱动最新的 nano-banana-2（兼容 ephone.chat / OpenAI 接口）的漫画嵌字小工具。这里只提供基础管线和接口，UI 交给其他模型或前端来做。

## 特性
- 统一封装 chat 和 image（edits/generations）端点，默认模型 nano-banana-2 + gpt-image-1
- 提供 `TypesettingPipeline`，一行完成：翻译/改写台词 -> 生成带字图片（返回 base64，方便 UI）
- 纯 Python，Win/Mac 都可直接跑；安卓可用 Termux/Chaquopy 集成
- 简单 CLI（重写/嵌字/一体化），便于调试或脚本化

## 安装（基于 uv）
```bash
# 安装依赖 & 创建虚拟环境
uv sync

# 激活虚拟环境（可选，也可直接用 uv run）
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
```
> 若未安装 uv，请参考 https://docs.astral.sh/uv/getting-started/ 或使用 `pip install uv`.

## 环境变量
- `NYAMANGA_API_KEY`（或 `EPHONE_API_KEY` / `OPENAI_API_KEY`）：ephone.chat 的 key
- 可选：`NYAMANGA_BASE_URL`（默认 `https://api.ephone.chat/v1`）、`NYAMANGA_CHAT_MODEL`、`NYAMANGA_IMAGE_MODEL`（默认 `nano-banana-2`）

## 命令行快速用（uv）
```bash
# 仅重写/翻译台词
uv run nyamanga rewrite "よろしくね!" --target-language zh

# 直接将文本嵌入图（需要 image、可选 mask/png）
uv run nyamanga embed panel.png "你好！" --bubble-hint "左上对话框" --output out.png

# 翻译 + 嵌字一体化
uv run nyamanga localize panel.png "よろしくね!" --target-language zh --output out.png
```

## 作为库使用
```python
from pathlib import Path
from nyamanga.config import ApiConfig
from nyamanga.pipeline import TypesettingPipeline

cfg = ApiConfig.from_env()
with TypesettingPipeline(cfg) as pipeline:
    result = pipeline.localize_panel(
        image_path=Path("panel.png"),
        source_text="よろしくね!",
        target_language="zh",
        bubble_hint="左上气泡",
    )
    # result.edited_image_b64 可交给 UI 渲染或自行写入文件
```

## Flet UI 运行
```bash
uv run app_ui.py
```

### UI 对接面向接口
- `MangaEmbedder.rewrite_dialogue(text, target_language, tone)`：仅返回改写后的文本
- `MangaEmbedder.embed_text(image_path, text, bubble_hint=None, mask_path=None)`：返回编辑后图片的 base64
- `TypesettingPipeline.localize_panel(...)`：组合调用，返回改写文本 + base64 图，便于前端直接展示

## 安卓/跨平台说明
- 代码无本地依赖，Termux + `pip install -r requirements.txt` 可用；或在原生 App 里用 Chaquopy/pyodide 载入
- 如需本地缓存或并发队列，可在 UI 层对 `TypesettingPipeline` 再封装
- 所有 API 调用都走 HTTPS，无文件系统特权需求，适合沙箱化
