"""
RSS 抓取模块 — 从多个新闻源获取巴黎安全相关新闻
"""

import logging
from datetime import datetime
from typing import Optional

import feedparser

# 配置日志
logger = logging.getLogger(__name__)

# 默认 RSS 新闻源列表
# 每个条目包含: name(显示名称), url(RSS地址), language(原文语言)
RSS_SOURCES: list[dict] = [
    {
        "name": "Actu17",
        "url": "https://actu17.fr/feed/",
        "language": "fr",
    },
    {
        "name": "20 Minutes Paris",
        "url": "https://www.20minutes.fr/feeds/rss-paris.xml",
        "language": "fr",
    },
    {
        "name": "France 3 Paris IDF",
        "url": "https://france3-regions.francetvinfo.fr/paris-ile-de-france/rss",
        "language": "fr",
    },
    {
        "name": "France 24",
        "url": "https://www.france24.com/en/france/rss",
        "language": "en",
    },
]


def fetch_articles(source: dict, limit: int = 20) -> list[dict]:
    """
    从单个 RSS 源抓取文章列表。

    Args:
        source: 包含 name/url/language 的新闻源字典
        limit: 最多返回的文章数量

    Returns:
        文章字典列表，每条包含 title/url/summary/published/source_name
    """
    url = source["url"]
    source_name = source["name"]

    try:
        logger.info(f"正在抓取: {source_name} ({url})")
        feed = feedparser.parse(url)

        # feedparser 不抛出异常，通过 bozo 字段标识解析错误
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"RSS 解析警告 [{source_name}]: {feed.bozo_exception}")

        articles: list[dict] = []

        for entry in feed.entries[:limit]:
            # 提取文章链接
            article_url = entry.get("link", "")

            # 提取摘要：优先使用 summary，其次 description
            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "description"):
                summary = entry.description

            # 去除 HTML 标签（简单清理，保留纯文本）
            summary = _strip_html(summary)

            # 提取发布时间
            published: Optional[str] = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6]).isoformat()
                except (ValueError, TypeError) as e:
                    logger.debug(f"时间解析失败: {e}")

            articles.append(
                {
                    "title": entry.get("title", "（无标题）"),
                    "url": article_url,
                    "summary": summary,
                    "published": published,
                    "source_name": source_name,
                    "language": source.get("language", "en"),
                }
            )

        logger.info(f"  成功获取 {len(articles)} 篇文章")
        return articles

    except Exception as exc:
        logger.warning(f"抓取失败 [{source_name}]: {exc}")
        return []


def fetch_all(sources: Optional[list[dict]] = None, limit: int = 20) -> list[dict]:
    """
    从所有 RSS 源抓取文章。

    Args:
        sources: 新闻源列表，默认使用 RSS_SOURCES
        limit: 每个源最多抓取的文章数

    Returns:
        所有来源的文章合并列表
    """
    if sources is None:
        sources = RSS_SOURCES

    all_articles: list[dict] = []

    for source in sources:
        articles = fetch_articles(source, limit=limit)
        all_articles.extend(articles)

    logger.info(f"共抓取 {len(all_articles)} 篇文章（来自 {len(sources)} 个源）")
    return all_articles


def _strip_html(text: str) -> str:
    """
    简单去除 HTML 标签，保留纯文本内容。
    使用正则而非 BeautifulSoup，避免额外依赖。
    """
    import re

    # 去除 HTML 标签
    text = re.sub(r"<[^>]+>", " ", text)
    # 合并多余空白
    text = re.sub(r"\s+", " ", text).strip()
    return text
