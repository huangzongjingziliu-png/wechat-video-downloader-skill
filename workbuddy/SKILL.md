---
name: wechat-video-downloader
display_name: 微信视频号下载器
display_name_en: WeChat Video Downloader
description: Download public WeChat Channels share links and save them as MP4 files.
description_zh: 下载公开的微信视频号分享链接并保存为 MP4。
description_en: Download public WeChat Channels share links and save them as MP4 files.
version: 1.0.0
author: huangzongjingziliu-png
---

# 微信视频号下载器 · WeChat Video Downloader

当用户提供公开的微信视频号分享链接并要求下载或保存视频时使用此技能。

## 执行流程

1. 只接受标准公开链接：`https://weixin.qq.com/sph/<分享标识>`。
2. 调用 `scripts/download_wechat_video.py`，并把输出路径设为当前工作区的 `outputs/` 目录。
3. 脚本将公开短链提交给 `https://v.mtotech.com/api/resolve`，取得短时有效的腾讯视频 CDN 地址，然后下载并校验 MP4 文件。
4. 向用户报告保存路径和文件大小。除非用户明确要求试运行 URL，否则不要输出或保存签名 CDN 地址。

示例：

```bash
python3 scripts/download_wechat_video.py \
  --url "https://weixin.qq.com/sph/AYVHprUXDE" \
  --output "outputs/wechat_video_AYVHprUXDE.mp4"
```

仅在用户要求或 H.264 不可用时使用 `--quality h265`。只有用户提供兼容解析端点时才使用 `--parser`。

## 边界与注意事项

- 仅处理公开分享链接；不登录微信、不读取 Cookie、不自动化微信客户端，也不绕过访问控制。
- 解析器是第三方服务，并非微信官方 API。它会接收用户提供的公开链接；不要对私密或敏感链接使用。
- 签名视频地址有效期较短；如果出现授权或过期错误，重新解析一次，仍失败就停止并报告错误。
- 不搜索凭据、不绕过浏览器安全限制，只下载用户有权保存和使用的内容。

需要 Python 3.10+ 和系统 `curl` 程序。
