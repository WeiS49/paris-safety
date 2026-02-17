"""
位置提取模块 — 从新闻文本中识别巴黎地点并返回坐标
支持区号（arrondissement）和地标名称两种匹配模式
"""

import json
import logging
import re
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)

# 巴黎市中心坐标（无法识别具体位置时的默认回退点）
PARIS_CENTER = ("Paris", 48.8566, 2.3522)

# 数据文件路径：相对于本模块位置向上一级，再进入 data/
_DATA_FILE = Path(__file__).parent.parent / "data" / "paris_locations.json"

# 缓存已加载的位置数据，避免重复读取文件
_locations: dict | None = None


def _load_locations() -> dict:
    """
    懒加载并缓存 paris_locations.json 数据。
    """
    global _locations
    if _locations is None:
        try:
            with open(_DATA_FILE, encoding="utf-8") as f:
                _locations = json.load(f)
            logger.debug(f"已加载位置数据: {_DATA_FILE}")
        except FileNotFoundError:
            logger.error(f"位置数据文件不存在: {_DATA_FILE}")
            _locations = {"arrondissements": {}, "landmarks": {}}
        except json.JSONDecodeError as exc:
            logger.error(f"位置数据 JSON 解析失败: {exc}")
            _locations = {"arrondissements": {}, "landmarks": {}}
    return _locations


# ─────────────────────────────────────────────
# 区号匹配正则（法语 + 英语两套）
# ─────────────────────────────────────────────
# 法语格式示例: "1er arrondissement", "2e", "18ème"
_RE_ARROND_FR = re.compile(
    r"\b(\d{1,2})(er|e|ème|eme)\s*(?:arrondissement)?\b",
    re.IGNORECASE,
)

# 英语格式示例: "1st arrondissement", "18th"
_RE_ARROND_EN = re.compile(
    r"\b(\d{1,2})(st|nd|rd|th)\s*(?:arrondissement)?\b",
    re.IGNORECASE,
)


def _match_arrondissement(text: str) -> tuple[str, float, float] | None:
    """
    尝试从文本中提取巴黎区号并返回对应坐标。
    先匹配法语格式，再匹配英语格式。
    """
    locs = _load_locations()
    arronds = locs.get("arrondissements", {})

    for pattern in (_RE_ARROND_FR, _RE_ARROND_EN):
        match = pattern.search(text)
        if match:
            num = match.group(1)  # 数字部分，如 "18"
            # 确保区号在 1–20 范围内
            if num in arronds:
                info = arronds[num]
                return (info["name_zh"], info["lat"], info["lng"])

    return None


def _match_landmark(text: str) -> tuple[str, float, float] | None:
    """
    尝试从文本中匹配预定义地标名称（大小写不敏感）。
    按地标名称从长到短排序，优先匹配更具体的名称。
    """
    locs = _load_locations()
    landmarks = locs.get("landmarks", {})
    text_lower = text.lower()

    # 按名称长度降序，确保更长（更具体）的名称优先
    sorted_keys = sorted(landmarks.keys(), key=len, reverse=True)

    for key in sorted_keys:
        if key in text_lower:
            info = landmarks[key]
            return (info["name_zh"], info["lat"], info["lng"])

    return None


def extract_location(text: str) -> tuple[str, float, float]:
    """
    从文本中提取巴黎位置，返回 (中文地名, 纬度, 经度)。

    匹配优先级:
    1. 法语/英语区号格式（arrondissement）
    2. 预定义地标名称（车站、广场等）
    3. 回退到巴黎市中心

    Args:
        text: 新闻标题或摘要文本（支持中英法混合）

    Returns:
        (name_zh, lat, lng) 元组
    """
    if not text or not text.strip():
        return PARIS_CENTER

    # 优先匹配区号
    result = _match_arrondissement(text)
    if result:
        logger.debug(f"  区号匹配: {result[0]}")
        return result

    # 其次匹配地标
    result = _match_landmark(text)
    if result:
        logger.debug(f"  地标匹配: {result[0]}")
        return result

    # 无匹配，回退到巴黎中心
    logger.debug("  未匹配到具体地点，使用巴黎市中心坐标")
    return PARIS_CENTER


def enrich_articles_with_location(articles: list[dict]) -> list[dict]:
    """
    为文章列表添加位置信息字段。
    优先使用已翻译的中文标题+摘要搜索，其次使用英文原文。

    Args:
        articles: 文章字典列表（可含 title_zh/summary_zh 字段）

    Returns:
        每条文章增加了 location_name/lat/lng 字段的列表
    """
    enriched: list[dict] = []

    for article in articles:
        # 合并标题和摘要文本，扩大匹配范围
        # 优先用中英双语混合文本以提升命中率
        combined = " ".join(
            filter(
                None,
                [
                    article.get("title", ""),
                    article.get("title_zh", ""),
                    article.get("summary", ""),
                ],
            )
        )

        name, lat, lng = extract_location(combined)

        enriched.append(
            {
                **article,
                "location_name": name,
                "lat": lat,
                "lng": lng,
            }
        )

    return enriched
