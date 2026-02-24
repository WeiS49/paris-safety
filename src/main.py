"""
巴黎治安预警站 — 主入口
完整流水线: 抓取 RSS → 翻译中文 → 提取地点 → 生成 Folium 地图
运行方式: uv run python src/main.py [--output-dir output/]
"""

import argparse
import logging
import sys
from pathlib import Path

# ── 确保 src/ 目录在 Python 路径中（直接运行时生效）──
# 当以 `uv run python src/main.py` 从项目根运行时，
# Python 自动将 src/ 加入 sys.path，但为防万一也手动补充。
_SRC_DIR = Path(__file__).parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# 导入流水线各模块（与 main.py 同在 src/ 目录，使用绝对导入）
from fetcher import fetch_all
from locator import enrich_articles_with_location
from map_generator import generate_map
from translator import translate_articles


def _setup_logging(verbose: bool = False) -> None:
    """
    配置控制台日志格式和级别。
    verbose=True 时显示 DEBUG 级别日志（包含匹配细节）。
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="巴黎治安预警站 — 生成交互式安全事件地图"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        metavar="DIR",
        help="HTML 输出目录（默认: output/）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        metavar="N",
        help="每个 RSS 源最多抓取的文章数（默认: 50）",
    )
    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="跳过翻译步骤（用于调试/离线测试）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志（DEBUG 级别）",
    )
    return parser.parse_args()


def main() -> None:
    """
    流水线主函数，按以下顺序执行:
    1. 抓取 RSS 新闻
    2. 翻译标题和摘要为中文
    3. 提取地点坐标
    4. 生成 Folium 交互式地图
    5. 保存到 output/index.html
    """
    args = _parse_args()
    _setup_logging(verbose=args.verbose)
    logger = logging.getLogger("main")

    # 确定输出路径（相对于当前工作目录，即项目根）
    output_dir = Path(args.output_dir)
    output_file = output_dir / "index.html"

    logger.info("=" * 50)
    logger.info("巴黎治安预警站 — 开始运行")
    logger.info("=" * 50)

    # ── 步骤 1: 抓取 RSS ──────────────────────────
    logger.info("【步骤 1/4】抓取 RSS 新闻...")
    articles = fetch_all(limit=args.limit)

    if not articles:
        logger.warning("未抓取到任何文章，将生成空地图（显示「暂无新闻」）")
    else:
        logger.info(f"共抓取 {len(articles)} 篇文章")

    # ── 步骤 2: 翻译 ──────────────────────────────
    if args.no_translate:
        logger.info("【步骤 2/4】跳过翻译（--no-translate 模式）")
        # 未翻译时用原文填充 _zh 字段，保证后续步骤不报错
        for a in articles:
            a.setdefault("title_zh", a.get("title", ""))
            a.setdefault("summary_zh", a.get("summary", ""))
    else:
        logger.info("【步骤 2/4】翻译标题和摘要为中文...")
        articles = translate_articles(articles)

    # ── 步骤 3: 提取地点 ──────────────────────────
    logger.info("【步骤 3/4】提取新闻地点坐标...")
    articles = enrich_articles_with_location(articles)

    # 统计位置分布
    fallback_count = sum(
        1 for a in articles if a.get("location_name") == "Paris"
    )
    logger.info(
        f"  位置识别: {len(articles) - fallback_count}/{len(articles)} 条"
        f"找到具体位置，{fallback_count} 条回退到市中心"
    )

    # ── 步骤 4: 生成地图 ──────────────────────────
    logger.info("【步骤 4/4】生成 Folium 交互式地图...")
    generate_map(articles, output_file)

    logger.info("=" * 50)
    logger.info(f"完成！输出文件: {output_file.resolve()}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
