#!/bin/bash

# Installer Playwright og nødvendige browsere

echo "🎭 Installerer Playwright for politiske møter scraper..."

# Installer Python-pakker
echo "📦 Installerer Python-avhengigheter..."
pip install -r requirements.txt

# Installer Playwright browsere
echo "🌐 Installerer Playwright browsere..."
python -m playwright install chromium

echo "✅ Playwright installasjon fullført!"
echo ""
echo "Nå kan du teste Playwright-scraperen:"
echo "python playwright_scraper.py"
echo ""
echo "Eller kjøre hovedscraperen med Playwright-støtte:"
echo "python scraper.py --debug"
