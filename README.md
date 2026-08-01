# codex-read-image

让 Codex 查看图片的插件：把图片 base64 编码后调用纯视觉模型（OpenAI 兼容接口），
把识别结果返回给主模型。适合主模型不支持图像输入时使用（例如接入 DeepSeek 的 Codex）。

## 安装（别人直接用，无需手动下载）

### 方式一：Codex CLI

```bash
# 1. 添加本仓库为插件市场（一次即可）
codex plugin marketplace add Jedeiah/codex-read-image

# 2. 安装插件
codex plugin install read-image@codex-read-image

# 3. 新开会话后即可使用
codex
```

### 方式二：ChatGPT 桌面端

1. 打开桌面端，产品选择器选 **Codex**；
2. 打开 **Plugins**（插件目录），添加市场，粘贴仓库地址 `https://github.com/Jedeiah/codex-read-image`；
3. 在市场里找到 **read-image**，点 **+** 安装；
4. 开一个新对话使用。

## 配置（每个人填自己的视觉模型密钥）

编辑**插件目录里的 `.env`**（卸载插件/移除市场时随插件一起删除）。首次使用若只有
`.env.example` 模板，先复制：`cp plugins/read-image/.env.example plugins/read-image/.env`，再填写：

```bash
READ_IMAGE_API_KEY=你的密钥
READ_IMAGE_MODEL=glm-4.6v-flash
READ_IMAGE_BASE_URL=https://open.bigmodel.cn/api/paas/v4
READ_IMAGE_THINKING=auto
```

上面是智谱免费模型示例（GLM-4.6V-Flash，`thinking=auto` 会自动开启思考模式）；
不填时默认使用 `gpt-4o-mini` + `https://api.openai.com/v1`。

`.env` 不在 Git 仓库里，插件升级不会覆盖你的配置；想额外留一份备份，可复制到
`~/.config/read-image/.env` 作为备用。

配置优先级：命令行参数 > 环境变量 > 插件目录 `.env` > `~/.config/read-image/.env` > 默认值。
默认模型 `gpt-4o-mini`、默认接口 `https://api.openai.com/v1`。

常见视觉模型：OpenAI `gpt-4o-mini` / `gpt-4o`、通义千问 `qwen-vl-max`（DashScope 兼容模式）、
智谱 `glm-4.6v-flash` / `glm-4v-flash`（免费）、硅基流动上的开源视觉模型。

卸载插件 / 移除市场时，插件目录连同其中的 `.env` 配置会一起被删除。

## 使用

新对话中直接说：

> 查看这张图片：/path/to/image.png

插件会调用视觉模型识别并返回内容。也可在终端自测：

```bash
python3 plugins/read-image/scripts/read_image.py /path/to/image.png --prompt "描述这张图"
```

## 说明

- 支持 png / jpg / jpeg / webp / gif，可一次传多张图；
- 图片只会发送到你配置的视觉模型服务，不经过其他服务器；
- `.env` 里的密钥请自行保管，不要把包含真实密钥的配置提交到仓库。

## License

MIT
