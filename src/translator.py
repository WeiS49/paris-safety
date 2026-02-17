"""
翻译模块 — 使用 deep_translator 将文本翻译成中文
依赖 Google Translate 免费接口（无需 API Key）
"""

import logging
from typing import Optional

from deep_translator import GoogleTranslator

# 配置日志
logger = logging.getLogger(__name__)

# Google Translate 每次请求的最大字符数限制
_MAX_CHARS = 4999


def translate_text(
    text: str,
    source: str = "auto",
    target: str = "zh-CN",
) -> str:
    """
    翻译单条文本。

    Args:
        text: 待翻译的原文
        source: 源语言代码，'auto' 表示自动检测
        target: 目标语言代码，默认简体中文

    Returns:
        翻译后的文本；若翻译失败则返回原文（不崩溃）
    """
    # 空字符串直接返回，避免无意义的网络请求
    if not text or not text.strip():
        return text

    # 超长文本截断，防止超出 API 限制
    truncated = text[:_MAX_CHARS] if len(text) > _MAX_CHARS else text

    try:
        translator = GoogleTranslator(source=source, target=target)
        result: str = translator.translate(truncated)
        # deep_translator 在某些边界情况下可能返回 None
        return result if result is not None else text
    except Exception as exc:
        logger.warning(f"翻译失败，返回原文: {exc}")
        return text


def translate_batch(
    texts: list[str],
    source: str = "auto",
    target: str = "zh-CN",
) -> list[str]:
    """
    批量翻译文本列表。
    逐条翻译（deep_translator 的 translate_batch 对超长文本不够稳健）。

    Args:
        texts: 待翻译文本列表
        source: 源语言代码
        target: 目标语言代码

    Returns:
        与输入等长的翻译结果列表；单条失败时保留原文
    """
    results: list[str] = []

    for i, text in enumerate(texts):
        translated = translate_text(text, source=source, target=target)
        results.append(translated)

        # 简单进度提示，便于 GitHub Actions 日志追踪
        if (i + 1) % 10 == 0:
            logger.info(f"  已翻译 {i + 1}/{len(texts)} 条")

    return results


def translate_articles(
    articles: list[dict],
    source: str = "auto",
    target: str = "zh-CN",
) -> list[dict]:
    """
    批量翻译文章列表中的标题和摘要字段。
    在原字典基础上添加 title_zh / summary_zh 字段，保留原文。

    Args:
        articles: fetch_all() 返回的文章列表
        source: 源语言
        target: 目标语言

    Returns:
        每条文章增加了 title_zh 和 summary_zh 字段的新列表
    """
    if not articles:
        return articles

    logger.info(f"开始翻译 {len(articles)} 篇文章的标题和摘要...")

    # 先收集所有标题 + 摘要，减少循环中的重复对象创建
    titles = [a.get("title", "") for a in articles]
    summaries = [a.get("summary", "") for a in articles]

    logger.info("  翻译标题中...")
    titles_zh = translate_batch(titles, source=source, target=target)

    logger.info("  翻译摘要中...")
    summaries_zh = translate_batch(summaries, source=source, target=target)

    # 将翻译结果合并回文章字典（复制一份，不修改原始数据）
    enriched: list[dict] = []
    for article, t_zh, s_zh in zip(articles, titles_zh, summaries_zh):
        enriched.append(
            {
                **article,
                "title_zh": t_zh,
                "summary_zh": s_zh,
            }
        )

    logger.info("翻译完成。")
    return enriched
