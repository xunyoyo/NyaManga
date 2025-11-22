# NyaManga
用 python 驱动最新的 nano-banana-2（兼容 ephone.chat / OpenAI 接口）的漫画嵌字小工具。这里只提供基础管线和接口，UI 交给其他模型或前端来做。

## 使用
- 安装依赖：`uv sync`（或用已有发行包直接运行）。
- 运行 UI：`uv run app_ui.py`，界面中输入 API Key，点击“选择图片/选择文件夹”或“手动输入路径”，设置目标语言/风格提示，点击“开始嵌字”。
- 自动模式：无需输入原文，模型会识别气泡文字、翻译并嵌字；可选气泡位置提示与附加提示词优化排版。
- 命令行：`uv run nyamanga localize panel.png "よろしくね!" --target-language zh --output out.png`（或用发行包内附带的可执行文件运行同样命令）。

## 桌面打包 (macOS/Windows)
```bash
# 打包，生成可执行/应用在 dist/
uv run flet pack app_ui.py --name NyaManga          # macOS 不支持 --onedir
uv run flet pack app_ui.py --name NyaManga --onedir # Windows / Linux 推荐
```
> 如需自定义图标，追加 `--icon assets/icon.png`（自行准备 PNG/ICO）。  
> 若提示缺少 PyInstaller，先 `uv sync`（已在依赖里）。

### CI/CD 自动打包发布
- 已提供 GitHub Actions 工作流 `.github/workflows/release.yml`：
  - 自动：推送 `v*` 标签时在 macOS/Windows/Linux 上用 `uv sync` + `flet pack --onedir` 构建，并上传到对应 release。
  - 手动：在 GitHub Actions 页面手动触发 `build-release`（可选 ref），默认仅产出 artifacts；如勾选 `create_release=true` 则会发布一个 draft release 并附上三平台包。
- 自动发布：本地打 tag 并推送：`git tag v0.1.0 && git push origin v0.1.0`，等待 Actions 完成后在 Releases 页面下载。
- 手动构建/发布：
  1) Actions -> `build-release` -> “Run workflow”，ref 留空或选分支/commit。
  2) 只要 artifacts：保持 `create_release=false`，在 workflow run 页面下载。
  3) 想要发布 draft release：把 `create_release` 设为 `true`，等待完成后在 Releases 页面找到 draft，确认后可编辑/发布。
