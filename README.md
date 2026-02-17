# Paris Safety Alert Station

An interactive map showing real-time safety news in Paris, translated to Chinese. Automatically updated twice daily via GitHub Actions and deployed to GitHub Pages.

**Live site:** https://weis49.github.io/paris-safety/

## Features

- Aggregates news from 4 RSS sources (Actu17, 20 Minutes Paris, France 3 IDF, France 24)
- Translates headlines and summaries to Chinese (via Google Translate)
- Extracts Paris locations from article text (arrondissements + landmarks)
- Generates an interactive Folium/Leaflet map with color-coded markers:
  - Red: crime incidents
  - Orange: strikes and protests
  - Blue: transport disruptions
  - Gray: other news
- District boundaries overlay from official GeoJSON data
- Click any marker to see Chinese summary + link to original article

## Tech Stack

| Component | Technology |
|-----------|-----------|
| RSS fetching | feedparser |
| Translation | deep-translator (Google Translate, free) |
| Location extraction | regex + predefined coordinate dictionary |
| Map generation | Folium (generates static Leaflet.js HTML) |
| Deployment | GitHub Actions + GitHub Pages |
| Base map | OpenStreetMap / CartoDB Positron |

## Run Locally

```bash
# Install dependencies
uv sync

# Generate map (with translation)
uv run python src/main.py

# Generate map (skip translation, faster for testing)
uv run python src/main.py --no-translate

# Open the result
open output/index.html
```

## Project Structure

```
src/
  fetcher.py          # RSS feed fetching
  translator.py       # French/English → Chinese translation
  locator.py          # Location extraction + coordinate mapping
  map_generator.py    # Folium map generation
  main.py             # Pipeline entry point
data/
  paris_locations.json  # Paris arrondissement + landmark coordinates
output/
  index.html          # Generated map (deployed to GitHub Pages)
```

## Coverage

- Paris 20 arrondissements (75001-75020)
- La Défense / Puteaux (92)
- Major landmarks and transit stations

## Cost

$0/month. All components are free:
- GitHub Pages (free hosting)
- GitHub Actions (~2 min/run, well within 2000 min/month free tier)
- Google Translate via deep-translator (free, no API key)
- OpenStreetMap tiles (free)

## License

MIT
