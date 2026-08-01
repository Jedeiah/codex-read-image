---
name: read-image
description: 当用户要求查看、读取、描述或分析图片/截图时使用（当前主模型不支持图像输入）。把图片交给配置的纯视觉模型识别，并把识别结果转述给用户。支持截图、报错图、图表、扫描件、照片等。
---

# Read Image（图片读取）

## 何时使用

- 用户提供了图片路径或拖入图片，要求"看一下 / 读取 / 描述 / 分析 / 识别"；
- 需要把图片内容变成文字：截图里的报错、图表数据、设计稿、证件扫描件、照片等；
- 用户提问时附带了图片文件。

## 工作流程

1. **确认图片存在**：检查用户给的路径是否真实存在，支持 png / jpg / jpeg / webp / gif。
2. **运行脚本**（脚本会先 base64 编码图片，再调用视觉模型）。脚本位于本技能同级目录 `../scripts/read_image.py`（相对于本 SKILL.md 所在目录的上一级）：

   ```bash
   python3 <插件目录>/scripts/read_image.py <图片路径> [更多图片...] --prompt "<用户的具体问题>"
   ```

   查找脚本位置后运行，例如安装目录为 `~/.codex/.tmp/marketplaces/codex-read-image/plugins/read-image` 时：

   ```bash
   python3 ~/.codex/.tmp/marketplaces/codex-read-image/plugins/read-image/scripts/read_image.py /tmp/screenshot.png \
     --prompt "详细描述这张截图的内容，包括其中的报错信息"
   ```

3. **读取脚本输出**：脚本把视觉模型的识别结果打印在终端，作为后续回答的事实依据。
4. **回复用户**：把识别结果转述给用户（中文），如果用户在原问题上继续追问，基于识别文本继续处理（总结、翻译、找 bug、提取数据等）。

## 配置检查（首次使用必须）

**推荐方式**：编辑 `~/.config/read-image/.env`（用户级配置，插件升级时不会被覆盖）。
如果该文件不存在，先创建目录和文件；也可以直接编辑插件目录里的 `.env` 模板。
两者结构相同，填好即可，不需要动 shell 配置：

| 环境变量 | 必填 | 说明 |
| --- | --- | --- |
| `READ_IMAGE_API_KEY` | 是 | 视觉模型服务的 API 密钥 |
| `READ_IMAGE_BASE_URL` | 否 | OpenAI 兼容接口地址，默认 `https://api.openai.com/v1` |
| `READ_IMAGE_MODEL` | 否 | 视觉模型名，默认 `gpt-4o-mini` |

常见可用的视觉模型示例：`gpt-4o-mini` / `gpt-4o`（OpenAI）、`qwen-vl-max`（通义千问，DashScope 兼容模式）、`glm-4v-plus`（智谱）、SiliconFlow 上各家开源视觉模型。

`.env` 示例（复制到 `~/plugins/read-image/.env` 后填值）：

推荐路径：`~/.config/read-image/.env`

```bash
READ_IMAGE_API_KEY=你的密钥
READ_IMAGE_MODEL=qwen-vl-max
READ_IMAGE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

如果都没有 `READ_IMAGE_API_KEY`，脚本会明确报错。此时应告诉用户按上面示例补上，改完重启 Codex 再试。配置优先级：命令行参数 > 环境变量 > `~/.config/read-image/.env` > 插件目录 `.env` > 内置默认值。

> 当前 DeepSeek 接口不支持图片输入，需要另配一个支持视觉的模型服务，在 `.env` 里填写即可。

## 注意事项

- 大图片可能超过视觉模型限制：可先用 macOS 自带命令缩小（`sips -Z 1024 原图 --out 缩小图.png`）再识别。
- 一次可以传多张图，脚本会逐张识别并分别输出。
- 图片只会上传到配置的视觉模型服务；不要把 API 密钥写进 prompt 或输出。
- `.env` 里存有你的密钥，不要把这个文件或整个插件目录分享给别人。
- 识别结果来自第三方视觉模型，可能与原图存在细节差异，回答时注意这一点。
