"""
地图生成模块 — 使用 Folium 创建巴黎安全事件交互式地图
输出为单文件 HTML，可直接在浏览器打开或部署到 GitHub Pages
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import folium

# 配置日志
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 常量配置
# ─────────────────────────────────────────────

# 巴黎市中心坐标（地图初始中心）
PARIS_CENTER = [48.8566, 2.3522]
PARIS_ZOOM = 12

# 巴黎行政区 GeoJSON（来自 gregoiredavid/france-geojson，MIT 开源）
ARRONDISSEMENTS_GEOJSON_URL = (
    "https://raw.githubusercontent.com/gregoiredavid/france-geojson"
    "/master/departements/75-paris/arrondissements-75-paris.geojson"
)

# ─────────────────────────────────────────────
# 事件类别颜色配置
# ─────────────────────────────────────────────

# 关键词 → 类别映射（按优先级顺序排列）
_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "crime",  # 红色：刑事犯罪类
        [
            "vol", "agression", "meurtre", "crime", "cambriolage",
            "theft", "robbery", "murder", "attack", "stabbing",
            "shooting", "assault", "burglary", "pickpocket", "scam",
            "fraud", "violence", "drug", "drugs", "prostitution",
        ],
    ),
    (
        "strike",  # 橙色：罢工抗议类
        [
            "grève", "greve", "manifestation", "strike", "protest",
            "demonstration", "mouvement social", "blocage",
        ],
    ),
    (
        "transport",  # 蓝色：交通出行类
        [
            "ratp", "sncf", "métro", "metro", "rer", "tram", "bus",
            "traffic", "accident", "collision", "perturbation",
            "disruption", "transport",
        ],
    ),
]

# 类别 → 颜色（Hex）映射
_CATEGORY_COLORS: dict[str, str] = {
    "crime": "#e74c3c",      # 红色
    "strike": "#e67e22",     # 橙色
    "transport": "#3498db",  # 蓝色
    "other": "#95a5a6",      # 灰色（默认）
}

# 类别 → 中文标签
_CATEGORY_LABELS: dict[str, str] = {
    "crime": "刑事犯罪",
    "strike": "罢工抗议",
    "transport": "交通出行",
    "other": "其他新闻",
}


def _classify_article(article: dict) -> str:
    """
    根据文章标题和摘要中的关键词判断新闻类别。

    Args:
        article: 包含 title/summary（原文）和 title_zh/summary_zh（中文）的字典

    Returns:
        类别字符串: 'crime' | 'strike' | 'transport' | 'other'
    """
    # 合并标题 + 摘要，转小写，提升命中率
    text = " ".join(
        filter(
            None,
            [
                article.get("title", ""),
                article.get("summary", ""),
                article.get("title_zh", ""),
                article.get("summary_zh", ""),
            ],
        )
    ).lower()

    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            return category

    return "other"


def _build_popup_html(article: dict) -> str:
    """
    构建 Folium 弹窗 HTML 内容。
    显示中文标题、摘要片段、来源、时间和原文链接。
    """
    title_zh = article.get("title_zh") or article.get("title", "（无标题）")
    summary_zh = article.get("summary_zh") or article.get("summary", "")
    # 摘要最多显示 150 个字符，避免弹窗过大
    if len(summary_zh) > 150:
        summary_zh = summary_zh[:150] + "..."

    source = article.get("source_name", "未知来源")
    published = article.get("published") or "时间未知"
    # 只取 ISO 时间的日期+时间部分（去掉微秒）
    if "T" in str(published):
        published = published.replace("T", " ")[:16]

    url = article.get("url", "#")
    location_name = article.get("location_name", "巴黎")

    html = f"""
<div style="
    font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-size: 13px;
    max-width: 280px;
    line-height: 1.5;
">
  <div style="
      font-weight: bold;
      font-size: 14px;
      color: #2c3e50;
      margin-bottom: 6px;
      border-bottom: 1px solid #ecf0f1;
      padding-bottom: 6px;
  ">{title_zh}</div>
  <div style="color: #555; margin-bottom: 8px;">{summary_zh}</div>
  <div style="color: #888; font-size: 11px; margin-bottom: 4px;">
    📍 {location_name} &nbsp;|&nbsp; 📰 {source}
  </div>
  <div style="color: #888; font-size: 11px; margin-bottom: 8px;">
    🕐 {published}
  </div>
  <a href="{url}" target="_blank" style="
      color: #3498db;
      text-decoration: none;
      font-size: 12px;
  ">阅读原文 →</a>
</div>
"""
    return html


def _build_title_html(article_count: int, update_time: str) -> str:
    """
    构建顶部标题横幅 HTML（使用 Folium FloatImage 或 branca Macro 注入）。
    """
    return f"""
<div style="
    position: fixed;
    top: 10px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    background: rgba(44, 62, 80, 0.90);
    color: white;
    padding: 8px 20px;
    border-radius: 24px;
    font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 1px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    pointer-events: none;
">
  🗼 巴黎治安预警站
  <span style="font-size:11px; font-weight:normal; margin-left:10px; opacity:0.8;">
    {article_count} 条新闻 &nbsp;|&nbsp; 更新于 {update_time}
  </span>
</div>
"""


def _build_legend_html() -> str:
    """
    构建图例 HTML，说明各颜色代表的事件类型。
    """
    items = []
    for cat, color in _CATEGORY_COLORS.items():
        label = _CATEGORY_LABELS[cat]
        items.append(
            f'<div style="display:flex;align-items:center;margin-bottom:4px;">'
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'border-radius:50%;background:{color};margin-right:8px;'
            f'flex-shrink:0;"></span>'
            f'<span>{label}</span></div>'
        )

    items_html = "\n".join(items)
    return f"""
<div style="
    position: fixed;
    bottom: 30px;
    right: 10px;
    z-index: 9999;
    background: rgba(255,255,255,0.92);
    color: #2c3e50;
    padding: 10px 14px;
    border-radius: 8px;
    font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
    font-size: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    min-width: 110px;
">
  <div style="font-weight:bold;margin-bottom:6px;font-size:13px;">图例</div>
  {items_html}
</div>
"""


def generate_map(articles: list[dict], output_path: Path) -> None:
    """
    生成巴黎安全事件交互式地图并保存为 HTML 文件。

    Args:
        articles: 经过翻译和位置提取的文章列表
        output_path: 输出 HTML 文件路径
    """
    logger.info("正在生成 Folium 地图...")

    # 获取当前 UTC 时间（GitHub Actions 在 UTC 时区运行）
    now_utc = datetime.now(tz=timezone.utc)
    update_time = now_utc.strftime("%Y-%m-%d %H:%M UTC")

    # ── 1. 创建底图 ──────────────────────────────
    m = folium.Map(
        location=PARIS_CENTER,
        zoom_start=PARIS_ZOOM,
        tiles="CartoDB positron",  # 浅色底图，适合覆盖彩色标记
        attr="© OpenStreetMap contributors, © CartoDB",
    )

    # ── 2. 加载行政区边界 GeoJSON ─────────────────
    logger.info("  加载巴黎行政区 GeoJSON 边界...")
    try:
        folium.GeoJson(
            ARRONDISSEMENTS_GEOJSON_URL,
            name="行政区边界",
            style_function=lambda _: {
                "fillColor": "#3498db",
                "color": "#2980b9",
                "weight": 1.5,
                "fillOpacity": 0.05,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["nom"],
                aliases=["区名:"],
                localize=True,
            ),
        ).add_to(m)
        logger.info("  GeoJSON 边界加载成功")
    except Exception as exc:
        logger.warning(f"  GeoJSON 加载失败（将跳过边界显示）: {exc}")

    # ── 3. 添加新闻标记 ──────────────────────────
    if articles:
        logger.info(f"  添加 {len(articles)} 个新闻标记...")

        # 按类别分组，方便图层控制
        category_groups: dict[str, folium.FeatureGroup] = {
            cat: folium.FeatureGroup(name=_CATEGORY_LABELS[cat], show=True)
            for cat in _CATEGORY_COLORS
        }

        for article in articles:
            lat = article.get("lat", PARIS_CENTER[0])
            lng = article.get("lng", PARIS_CENTER[1])
            category = _classify_article(article)
            color = _CATEGORY_COLORS[category]

            popup_html = _build_popup_html(article)
            title_zh = article.get("title_zh") or article.get("title", "")

            marker = folium.CircleMarker(
                location=[lat, lng],
                radius=8,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
                weight=2,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=title_zh[:60] + ("..." if len(title_zh) > 60 else ""),
            )
            marker.add_to(category_groups[category])

        # 将所有分组图层加入地图
        for group in category_groups.values():
            group.add_to(m)

    else:
        # 无新闻时显示提示信息标记
        logger.info("  无新闻文章，显示空地图提示")
        folium.Marker(
            location=PARIS_CENTER,
            popup=folium.Popup("<b>暂无新闻</b>", max_width=200),
            tooltip="暂无新闻",
            icon=folium.Icon(color="gray", icon="info-sign"),
        ).add_to(m)

    # ── 4. 图层控制（右上角） ─────────────────────
    folium.LayerControl(collapsed=False).add_to(m)

    # ── 5. 注入标题横幅和图例（Raw HTML 注入） ────
    title_html = _build_title_html(len(articles), update_time)
    legend_html = _build_legend_html()

    # 使用 branca MacroElement 将自定义 HTML 注入地图
    from branca.element import MacroElement
    from jinja2 import Template

    class RawHtmlElement(MacroElement):
        """将任意 HTML 字符串注入 Folium 地图的辅助类。"""

        def __init__(self, html: str):
            super().__init__()
            self._template = Template(
                "{% macro header(this, kwargs) %}" + html + "{% endmacro %}"
            )

    m.get_root().html.add_child(RawHtmlElement(title_html))
    m.get_root().html.add_child(RawHtmlElement(legend_html))

    # ── 6. 保存输出 ──────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    logger.info(f"地图已保存: {output_path}")
