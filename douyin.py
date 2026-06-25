"""抖音/TikTok 链接解析模块"""

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("WxPowerBot.douyin")

# 默认本地抖音解析 API
DEFAULT_API_URL = "http://192.168.10.233:851/api/hybrid/video_data"

# 抖音/TikTok 链接正则
DOUYIN_PATTERNS = [
    r"(?:https?://)?(?:www\.)?douyin\.com/video/\d+",
    r"(?:https?://)?(?:www\.)?douyin\.com/\S+",
    r"(?:https?://)?v\.douyin\.com/\S+",
    r"(?:https?://)?(?:www\.)?iesdouyin\.com/\S+",
    r"(?:https?://)?(?:www\.)?tiktok\.com/@\w+/video/\d+",
    r"(?:https?://)?(?:www\.)?tiktok\.com/\S+",
    r"(?:https?://)?vm\.tiktok\.com/\S+",
]


def extract_douyin_url(text: str) -> Optional[str]:
    """从文本中提取抖音链接"""
    if not text:
        return None
    for pattern in DOUYIN_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            url = m.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            return url
    return None


def parse_video(share_url: str, api_url: str = DEFAULT_API_URL) -> Optional[Dict[str, Any]]:
    """调用本地抖音解析 API 解析视频，返回视频信息"""
    if not api_url:
        api_url = DEFAULT_API_URL
    try:
        encoded_url = urllib.parse.quote(share_url, safe="")
        url = f"{api_url}?url={encoded_url}&minimal=true"
        req = urllib.request.Request(url, headers={"User-Agent": "WxPowerBot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        # 检查是否返回了错误
        if isinstance(data, dict) and "detail" in data:
            logger.warning("抖音解析API错误: %s", data["detail"].get("message", ""))
            return None
        return data
    except Exception as e:
        logger.exception("抖音解析失败: %s", e)
        return None


def format_video_info(data: Optional[Dict[str, Any]]) -> Optional[str]:
    """将解析结果格式化为可读文本"""
    if not data:
        return None
    info = data.get("data") or data
    if not isinstance(info, dict):
        return None

    title = info.get("title") or info.get("desc") or ""
    author = info.get("author") or info.get("nickname") or ""
    duration = info.get("duration") or info.get("duration_text") or ""
    play_url = info.get("play_url") or info.get("video_url") or ""
    cover = info.get("cover") or info.get("cover_url") or ""

    lines = [f"🎵 抖音视频"]
    if title:
        lines.append(f"📌 {title}")
    if author:
        lines.append(f"👤 {author}")
    if duration:
        lines.append(f"⏱ {duration}")
    if play_url:
        lines.append(f"📎 播放地址: {play_url}")
    if cover:
        lines.append(f"🖼 {cover}")

    return "\n".join(lines) if len(lines) > 1 else None
