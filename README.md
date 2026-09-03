# 微信视频号下载器 · WeChat Video Downloader Skill

一个用于 Codex 的 skill：下载公开的微信视频号分享链接并保存为 MP4。

## 功能

- 支持 `https://weixin.qq.com/sph/<分享标识>` 形式的公开短链
- 优先下载 H.264，必要时可选择 H.265
- 使用临时文件和 MP4 容器校验，避免留下不完整文件
- 不登录微信、不读取 Cookie、不处理私密链接

## 使用

将此目录放入 Codex 的 skills 目录后，可使用 `$wechat-video-downloader` 调用。也可以直接运行脚本：

```bash
python3 scripts/download_wechat_video.py \
  --url "https://weixin.qq.com/sph/分享标识" \
  --output "outputs/video.mp4"
```

运行环境需要 Python 3.10+ 和系统 `curl`。

## 工作方式

脚本把公开分享链接提交给一个第三方解析服务，取得短时有效的腾讯视频 CDN 地址，再下载并校验 MP4。解析服务并非微信官方 API；不要对私密或敏感链接使用此功能。

## 许可

本项目采用 MIT License，详见 [LICENSE](LICENSE)。
