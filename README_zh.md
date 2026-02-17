# 巴黎治安预警站

一张以巴黎互动地图为中心的中文治安预警网页，自动聚合法语/英语新闻源，翻译为中文，每天更新两次，部署在 GitHub Pages 上。

**在线地址:** https://weis49.github.io/paris-safety/

## 功能

- 聚合 4 个 RSS 新闻源（Actu17、20 Minutes Paris、France 3 IDF、France 24）
- 自动将标题和摘要翻译为中文（Google 翻译，免费）
- 从文章文本中提取巴黎地点（区号 + 地标名称）
- 生成 Folium/Leaflet 交互式地图，事件按类型颜色区分：
  - 红色：刑事犯罪
  - 橙色：罢工抗议
  - 蓝色：交通出行
  - 灰色：其他新闻
- 叠加巴黎 20 区行政边界（GeoJSON）
- 点击标记弹出中文摘要 + 原文链接

## 本地运行

```bash
# 安装依赖
uv sync

# 生成地图（含翻译）
uv run python src/main.py

# 生成地图（跳过翻译，用于快速测试）
uv run python src/main.py --no-translate

# 打开结果
open output/index.html
```

## 项目结构

```
src/
  fetcher.py          # RSS 抓取
  translator.py       # 法/英 → 中文翻译
  locator.py          # 地名提取 + 坐标映射
  map_generator.py    # Folium 地图生成
  main.py             # 流水线入口
data/
  paris_locations.json  # 巴黎 20 区 + 地标坐标字典
output/
  index.html          # 生成的地图（部署到 GitHub Pages）
```

## 覆盖范围

- 巴黎 20 区 (75001-75020)
- 拉德芳斯 / 皮托 (92)
- 主要地标和交通枢纽

## 费用

每月 $0。所有组件均免费：
- GitHub Pages（免费托管）
- GitHub Actions（每次运行约 2 分钟，远低于每月 2000 分钟免费额度）
- Google 翻译（通过 deep-translator，免费，无需 API key）
- OpenStreetMap 地图底图（免费）

## 许可证

MIT
