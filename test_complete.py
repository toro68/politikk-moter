#!/usr/bin/env python3
"""
Test Playwright-funksjonalitet uten å sende til Slack.
"""

import os
import sys
import asyncio
import pytest

# Sett test-modus
os.environ['TESTING'] = 'true'

def test_standard_scraping():
    """Test standard scraping uten Playwright."""
    print("🧪 Tester standard scraping...")
    
    from scraper import MoteParser, KOMMUNE_URLS
    
    parser = MoteParser()
    
    # Test kun ACOS og custom sider (ikke JavaScript-tunge)
    standard_sites = [config for config in KOMMUNE_URLS if config['type'] in ['acos', 'custom']]
    
    total_meetings = 0
    for kommune_config in standard_sites[:3]:  # Test bare første 3
        print(f"  📄 Tester {kommune_config['name']}...")
        
        try:
            if kommune_config['type'] == 'acos':
                meetings = parser.parse_acos_site(kommune_config['url'], kommune_config['name'])
            elif kommune_config['type'] == 'custom':
                meetings = parser.parse_custom_site(kommune_config['url'], kommune_config['name'])
            
            print(f"    ✅ {len(meetings)} møter funnet")
            total_meetings += len(meetings)
            
            # Vis første møte som eksempel
            if meetings:
                first = meetings[0]
                print(f"    📅 Eksempel: {first['title']} - {first['date']} {first['time'] or 'ukjent tid'}")
        
        except Exception as e:
            print(f"    ❌ Feil: {e}")
    
    print(f"\n📊 Standard scraping totalt: {total_meetings} møter")
    return total_meetings

@pytest.mark.asyncio
async def test_playwright_scraping():
    """Test Playwright scraping."""
    print("\n🎭 Tester Playwright scraping...")
    
    try:
        from playwright_scraper import scrape_with_playwright
        
        # Test JavaScript-tunge sider
        js_sites = [
            {
                "name": "Elements Cloud",
                "url": "https://prod01.elementscloud.no/publikum/971045698/Dmb",
                "type": "elements"
            }
        ]
        
        meetings = await scrape_with_playwright(js_sites)
        
        print(f"📊 Playwright totalt: {len(meetings)} møter")
        
        # Vis eksempler
        for meeting in meetings[:3]:
            print(f"  📅 {meeting['date']} {meeting['time'] or 'ukjent tid'} - {meeting['title']} ({meeting['kommune']})")
        
        return len(meetings)
        
    except ImportError:
        print("❌ Playwright ikke installert")
        return 0
    except Exception as e:
        print(f"❌ Playwright feil: {e}")
        return 0

def test_slack_formatting():
    """Test Slack-formatering med mock data."""
    print("\n💬 Tester Slack-formatering...")
    
    from scraper import format_slack_message, filter_meetings_by_date_range
    from mock_data import get_mock_meetings
    
    # Hent mock data
    mock_meetings = get_mock_meetings()
    
    # Filtrer for neste 10 dager
    filtered = filter_meetings_by_date_range(mock_meetings, days_ahead=9)
    
    # Formater melding
    slack_message = format_slack_message(filtered)
    
    print(f"📝 Slack-melding generert ({len(filtered)} møter)")
    print("═" * 50)
    print(slack_message[:300] + "..." if len(slack_message) > 300 else slack_message)
    print("═" * 50)

def test_complete_pipeline():
    """Test hele pipelinen."""
    print("\n🔄 Tester komplett pipeline...")
    
    from scraper import scrape_all_meetings, filter_meetings_by_date_range, format_slack_message
    
    # Scrape alle møter (vil bruke mock hvis scraping feiler)
    all_meetings = scrape_all_meetings()
    print(f"📊 Total møter: {len(all_meetings)}")
    
    # Filtrer
    filtered = filter_meetings_by_date_range(all_meetings, days_ahead=9)
    print(f"📅 Filtrert møter: {len(filtered)}")
    
    # Formater
    slack_message = format_slack_message(filtered)
    print(f"💬 Slack-melding: {len(slack_message)} tegn")
    
    return len(filtered)

async def main():
    """Hovedtest-funksjon."""
    print("🧪 TESTING SUITE: Politiske møter scraper")
    print("=" * 60)
    
    # Test 1: Standard scraping
    standard_count = test_standard_scraping()
    
    # Test 2: Playwright scraping
    playwright_count = await test_playwright_scraping()
    
    # Test 3: Slack formatering
    test_slack_formatting()
    
    # Test 4: Komplett pipeline
    pipeline_count = test_complete_pipeline()
    
    # Sammendrag
    print("\n" + "=" * 60)
    print("📊 TESTRESULTATER:")
    print(f"  📄 Standard scraping: {standard_count} møter")
    print(f"  🎭 Playwright scraping: {playwright_count} møter")
    print(f"  🔄 Pipeline total: {pipeline_count} møter")
    
    if pipeline_count > 0:
        print("\n✅ Testing vellykket! Systemet er klart.")
        print("\nNeste steg:")
        print("  1. For å teste ekte Slack-sending: python scraper.py --force")
        print("  2. For produksjon: fjern TESTING env var og kjør: python scraper.py")
    else:
        print("\n❌ Testing feilet. Sjekk konfigurasjon.")

if __name__ == '__main__':
    asyncio.run(main())
