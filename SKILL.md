---
name: wechat-video-downloader
description: Download public WeChat Channels (微信视频号) share links such as https://weixin.qq.com/sph/... to a local MP4 file.
---

# WeChat Video Downloader

Use this skill when the user supplies a public WeChat Channels share link and asks to download or save the video.

Requires Python 3.10+ and the system `curl` program.

## Workflow

1. Validate that the input is a standard public share link: `https://weixin.qq.com/sph/<id>`.
2. Run `scripts/download_wechat_video.py` with an explicit output path under the current task's `outputs/` directory.
3. The script sends the public share URL to `https://v.mtotech.com/api/resolve`, which returns short-lived signed H.264/H.265 CDN URLs. It then downloads the selected URL directly from `finder.video.qq.com` and validates the result as an MP4.
4. Report the saved file path and size. Do not print or retain the signed CDN URL unless the user explicitly asks for a dry-run URL.

Example:

```bash
python3 scripts/download_wechat_video.py \
  --url "https://weixin.qq.com/sph/AYVHprUXDE" \
  --output "outputs/wechat_video_AYVHprUXDE.mp4"
```

Use `--quality h265` only when the user requests it or H.264 is unavailable. Use `--parser` only when the user supplies a compatible parser endpoint.

## Boundaries

- This workflow is for public share links and does not log in to WeChat, inspect cookies, automate WeChat Desktop, or bypass access controls.
- The parser is a third-party service, not an official WeChat API. Tell the user if this matters, and do not use it for private or sensitive URLs without explicit permission.
- Signed media URLs expire quickly; if download fails with an authorization or expiry error, rerun the parser once and stop if it still fails.
- If the parser cannot resolve the link, report the concrete error. Do not search for credentials or attempt browser-security workarounds.
- Only download content the user has permission to save and use.

## Helper script

Read or run [scripts/download_wechat_video.py](scripts/download_wechat_video.py) for the deterministic request, download, and MP4 validation logic.
