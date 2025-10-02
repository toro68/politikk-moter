#!/usr/bin/env python3
"""
Demo-versjon som viser hvordan Slack-meldingen ser ut uten å sende til Slack.
"""

from scraper import scrape_all_meetings, filter_meetings_by_date_range, format_slack_message
from mock_data import get_mock_meetings

def demo_slack_message():
    """Generer og vis demo Slack-melding."""
    print("🎭 Demo: Politiske møter Slack-melding")
    print("=" * 50)
    
    # Hent møter
    meetings = scrape_all_meetings()
    print(f"\nTotalt møter: {len(meetings)}")
    
    # Filtrer for neste 10 dager
    filtered_meetings = filter_meetings_by_date_range(meetings, days_ahead=9)
    print(f"Møter neste 10 dager: {len(filtered_meetings)}")
    
    # Bruk mock-data hvis ingen møter funnet
    if not filtered_meetings:
        print("\n⚠️  Ingen møter i neste 10-dagers periode. Bruker mock-data...")
        mock_meetings = get_mock_meetings()
        filtered_meetings = filter_meetings_by_date_range(mock_meetings, days_ahead=9)
        print(f"Lastet {len(filtered_meetings)} mock-møter for de neste 10 dagene")
    
    # Generer Slack-melding
    slack_message = format_slack_message(filtered_meetings)
    
    print("\n📱 SLACK-MELDING:")
    print("=" * 50)
    print(slack_message)
    print("=" * 50)
    
    print("\n✅ Demo fullført!")
    print("\nFor å sende til ekte Slack:")
    print("1. Sett opp Slack webhook")
    print("2. Kjør: export SLACK_WEBHOOK_URL='din_webhook_url'")
    print("3. Kjør: python scraper.py")

if __name__ == '__main__':
    demo_slack_message()
