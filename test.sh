#!/bin/bash

# Test-skript for lokal utvikling og feilsøking

echo "🔍 Tester politiske møter scraper..."

# Sjekk at Python-avhengigheter er installert
echo "📦 Installerer avhengigheter..."
pip install -r requirements.txt

echo ""
echo "🧪 Kjører scraper i debug-modus..."
python scraper.py --debug

echo ""
echo "✅ Test fullført!"
echo ""
echo "For å sende til Slack:"
echo "export SLACK_WEBHOOK_URL='your_webhook_here'"
echo "python scraper.py"
