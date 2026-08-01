#!/usr/bin/env python3
"""read-image: 把图片 base64 编码后调用纯视觉模型，识别结果输出到 stdout 供主模型使用。

配置（按优先级从高到低）：
  1. 命令行参数（--api-key / --base-url / --model / --thinking）
  2. 环境变量 READ_IMAGE_API_KEY / READ_IMAGE_BASE_URL / READ_IMAGE_MODEL / READ_IMAGE_THINKING
  3. 插件根目录的 .env 文件（插件自带配置，随插件卸载一起删除，推荐）
  4. ~/.config/read-image/.env（可选备用位置，插件升级不会覆盖）
  5. 内置默认值：base_url 为 https://api.openai.com/v1，model 为 gpt-4o-mini

thinking 参数：glm 系列模型默认自动开启思考模式，其他模型自动关闭；
可用环境变量 READ_IMAGE_THINKING=on/off/auto 覆盖。
单张图片超过 10MB 会提示先压缩。

用法：
  python3 read_image.py 图片1.png 图片2.jpg --prompt "描述这两张图"
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request

from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PLUGIN_ROOT / ".env"
USER_ENV_FILE = Path.home() / ".config" / "read-image" / ".env"


def load_dotenv(path: Path) -> dict[str, str]:
    """读取简单的 KEY=VALUE 格式文件，跳过注释和空行。"""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            result[key] = value
    return result


# 插件目录内的配置优先于用户级备用配置，真实环境变量再覆盖两者
_DOTENV = {**load_dotenv(USER_ENV_FILE), **load_dotenv(ENV_FILE)}
_CONFIG = {**_DOTENV, **os.environ}
DEFAULT_BASE_URL = _CONFIG.get("READ_IMAGE_BASE_URL", "https://api.openai.com/v1")
DEFAULT_MODEL = _CONFIG.get("READ_IMAGE_MODEL", "gpt-4o-mini")
DEFAULT_THINKING = _CONFIG.get("READ_IMAGE_THINKING", "auto").strip().lower()
if DEFAULT_THINKING not in ("auto", "on", "off"):
    DEFAULT_THINKING = "auto"
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def guess_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    if mime and mime.startswith("image/"):
        return mime
    ext = os.path.splitext(path)[1].lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }.get(ext, "image/png")


def encode_image(path: str) -> tuple[str, str]:
    mime = guess_mime(path)
    with open(path, "rb") as handle:
        data = handle.read()
    if not data:
        raise ValueError(f"图片文件为空：{path}")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"图片过大（{len(data) / 1024 / 1024:.1f}MB），超过 10MB 上限，"
            "请先用 `sips -Z 1024 原图 --out 缩小图.png` 缩小后再试。"
        )
    return mime, base64.b64encode(data).decode("ascii")


def call_vision_model(
    *,
    mime: str,
    b64: str,
    prompt: str,
    base_url: str,
    api_key: str,
    model: str,
    max_tokens: int,
    temperature: float,
    thinking: str,
) -> str:
    if not api_key:
        raise RuntimeError(
            "未配置视觉模型 API 密钥。请编辑 "
            f"{ENV_FILE}（或备用位置 {USER_ENV_FILE}）中的 READ_IMAGE_API_KEY，"
            "或设置环境变量 READ_IMAGE_API_KEY，或使用 --api-key 参数。"
        )
    base = base_url.rstrip("/")
    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    if thinking == "on" or (thinking == "auto" and "glm" in model.lower()):
        payload["thinking"] = {"type": "enabled"}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    retry_codes = {429, 500, 502, 503, 504}
    max_retries = 4
    last_error = ""
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            last_error = f"接口返回错误 {error.code}: {detail}"
            retryable = error.code in retry_codes
        except urllib.error.URLError as error:
            last_error = f"网络连接失败: {error.reason}"
            retryable = True
        else:
            if isinstance(result, dict) and result.get("error"):
                last_error = "接口返回业务错误: " + json.dumps(
                    result["error"], ensure_ascii=False
                )[:500]
                retryable = True
            else:
                break
        if attempt < max_retries - 1 and retryable:
            wait = 3 * (attempt + 1)
            sys.stderr.write(f"{last_error}，{wait} 秒后重试（第 {attempt + 1} 次）\n")
            time.sleep(wait)
            continue
        raise RuntimeError(last_error)
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            f"视觉模型返回了无法解析的结果：{json.dumps(result, ensure_ascii=False)[:500]}"
        )
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        content = "".join(parts)
    return content or ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="图片转 base64 并调用纯视觉模型识别，结果输出到 stdout。"
    )
    parser.add_argument("images", nargs="+", help="图片路径，可传多张")
    parser.add_argument("--prompt", default="请详细描述这张图片的内容。", help="要问视觉模型的问题")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="视觉模型名称")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI 兼容接口地址")
    parser.add_argument("--api-key", default=_CONFIG.get("READ_IMAGE_API_KEY", ""), help="API 密钥")
    parser.add_argument("--max-tokens", type=int, default=1024, help="最多输出 token 数")
    parser.add_argument("--temperature", type=float, default=0.2, help="采样温度")
    parser.add_argument(
        "--thinking",
        choices=["auto", "on", "off"],
        default=DEFAULT_THINKING,
        help="思考模式：auto 按模型自动判断（glm 系列开启）/ on 开启 / off 关闭",
    )
    args = parser.parse_args()

    exit_code = 0
    for index, image in enumerate(args.images, start=1):
        label = image if len(args.images) == 1 else f"[{index}/{len(args.images)}] {image}"
        try:
            mime, b64 = encode_image(image)
            text = call_vision_model(
                mime=mime,
                b64=b64,
                prompt=args.prompt,
                base_url=args.base_url,
                api_key=args.api_key,
                model=args.model,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                thinking=args.thinking,
            )
        except (OSError, ValueError, RuntimeError) as error:
            print(f"读取失败 {label}: {error}", file=sys.stderr)
            exit_code = 1
            continue
        print(f"===== {label} =====")
        print((text or "").strip())
        print()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
