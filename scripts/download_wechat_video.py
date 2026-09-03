#!/usr/bin/env python3
"""Download a public WeChat Channels share link as an MP4.

The resolver returns a short-lived signed Tencent CDN URL. This helper keeps
that URL out of normal output, downloads it atomically, and performs a small
MP4 container sanity check without requiring third-party Python packages.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_PARSER = "https://v.mtotech.com/api/resolve"
SHARE_URL_RE = re.compile(r"^https://weixin\.qq\.com/sph/([A-Za-z0-9_-]+)/?$")
ALLOWED_MEDIA_HOST = "finder.video.qq.com"


def https_context() -> ssl.SSLContext:
    """Use certifi when the system Python lacks a usable CA bundle."""
    try:
        import certifi  # type: ignore
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


class DownloadError(RuntimeError):
    """A user-actionable resolver or download failure."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a public WeChat Channels share link as MP4."
    )
    parser.add_argument("--url", required=True, help="https://weixin.qq.com/sph/<id>")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output MP4 path (default: outputs/wechat_video_<id>.mp4)",
    )
    parser.add_argument(
        "--quality",
        choices=("h264", "h265"),
        default="h264",
        help="Preferred stream; falls back to the other stream if unavailable.",
    )
    parser.add_argument(
        "--parser",
        default=DEFAULT_PARSER,
        help="Resolver endpoint (default: the public resolver used by this skill).",
    )
    parser.add_argument("--timeout", type=int, default=120, help="HTTP timeout in seconds.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve only; print metadata and the signed URL, without downloading.",
    )
    return parser.parse_args()


def validate_share_url(raw_url: str) -> str:
    match = SHARE_URL_RE.fullmatch(raw_url.strip())
    if not match:
        raise DownloadError(
            "只支持标准公开链接：https://weixin.qq.com/sph/<分享标识>"
        )
    return match.group(1)


def resolve_share_url(share_url: str, parser_url: str, timeout: int) -> dict:
    payload = json.dumps({"url": share_url}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        parser_url,
        data=payload,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "wechat-video-downloader/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=https_context()) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read(400).decode("utf-8", "replace").strip()
        raise DownloadError(f"解析服务返回 HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise DownloadError(f"无法连接解析服务: {exc.reason}") from exc

    try:
        result = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DownloadError("解析服务返回了无法识别的响应") from exc

    if not isinstance(result, dict) or result.get("ok") is not True:
        raise DownloadError(str(result.get("error") or result.get("message") or "解析失败"))
    data = result.get("data")
    if not isinstance(data, dict):
        raise DownloadError("解析服务没有返回视频信息")
    return data


def choose_media_url(data: dict, quality: str) -> tuple[str, str]:
    candidates = [quality, "h265" if quality == "h264" else "h264"]
    for name in candidates:
        value = data.get(f"{name}_url")
        if not isinstance(value, str) or not value.startswith("https://"):
            continue
        parsed = urllib.parse.urlparse(value)
        if parsed.hostname != ALLOWED_MEDIA_HOST:
            raise DownloadError(
                f"解析服务返回了非腾讯视频 CDN 地址，已停止：{parsed.hostname or '未知主机'}"
            )
        return value, name
    raise DownloadError("解析结果中没有可用的 H.264/H.265 视频地址")


def download_media(media_url: str, output: Path, timeout: int) -> int:
    output = output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    part_path = output.with_name(output.name + ".part")
    curl = shutil.which("curl")
    if not curl:
        raise DownloadError("下载视频需要系统中的 curl 命令")
    command = [
        curl,
        "--location",
        "--fail",
        "--silent",
        "--show-error",
        "--retry",
        "2",
        "--max-time",
        str(timeout),
        "--user-agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36",
        "--referer",
        "https://channels.weixin.qq.com/",
        "--header",
        "Accept: */*",
        "--output",
        str(part_path),
        media_url,
    ]
    try:
        subprocess.run(command, check=True, timeout=timeout + 10, capture_output=True, text=True)
    except subprocess.TimeoutExpired as exc:
        part_path.unlink(missing_ok=True)
        raise DownloadError("下载视频超时") from exc
    except subprocess.CalledProcessError as exc:
        part_path.unlink(missing_ok=True)
        # curl's exit 22 covers HTTP 4xx/5xx, including expired signed URLs.
        if exc.returncode == 22:
            raise DownloadError("签名视频地址已失效，请重新解析后再试") from exc
        raise DownloadError("下载视频失败，请检查网络连接或重新解析") from exc
    except OSError as exc:
        part_path.unlink(missing_ok=True)
        raise DownloadError(f"下载视频失败：{exc}") from exc

    try:
        header = part_path.read_bytes()[:64]
        if b"ftyp" not in header:
            raise DownloadError("下载结果不是有效的 MP4 文件")
        part_path.replace(output)
        return output.stat().st_size
    except (DownloadError, OSError) as exc:
        part_path.unlink(missing_ok=True)
        if isinstance(exc, DownloadError):
            raise
        raise DownloadError(f"保存视频失败：{exc}") from exc


def main() -> int:
    args = parse_args()
    try:
        share_id = validate_share_url(args.url)
        share_url = f"https://weixin.qq.com/sph/{share_id}"
        data = resolve_share_url(share_url, args.parser, args.timeout)
        media_url, selected_quality = choose_media_url(data, args.quality)

        if args.dry_run:
            print(
                json.dumps(
                    {
                        "quality": selected_quality,
                        "author": data.get("author", ""),
                        "description": data.get("description", ""),
                        "media_url": media_url,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        output = args.output or Path("outputs") / f"wechat_video_{share_id}.mp4"
        output = output.expanduser()
        if output.exists() and not args.force:
            raise DownloadError(f"文件已存在，使用 --force 覆盖：{output}")
        size = download_media(media_url, output, args.timeout)
        print(f"已保存：{output} ({size} bytes, {selected_quality})")
        return 0
    except DownloadError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
