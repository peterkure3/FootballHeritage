"""
Test script to verify API keys and check available data.
Run this before the full pipeline to ensure APIs are working.
"""

import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.append(str(Path(__file__).parent))

import requests
from config import (
    FOOTBALL_DATA_ORG_API_KEY,
    FOOTBALL_DATA_ORG_BASE_URL,
    THE_ODDS_API_KEY,
    THE_ODDS_API_BASE_URL,
    ODDS_API_SPORTS,
)


def test_football_data_org():
    """Test football-data.org API."""
    print("\n" + "="*60)
    print("Testing football-data.org API")
    print("="*60)
    
    headers = {
        "X-Auth-Token": FOOTBALL_DATA_ORG_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Test 1: Get competitions
    print("\n1. Testing /competitions endpoint...")
    try:
        response = requests.get(
            f"{FOOTBALL_DATA_ORG_BASE_URL}/competitions",
            headers=headers,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            competitions = data.get("competitions", [])
            print(f"   ✓ Success! Found {len(competitions)} competitions")
            
            # Show first few competitions
            print("\n   Available competitions:")
            for comp in competitions[:5]:
                print(f"   - {comp.get('name')} (ID: {comp.get('id')}, Code: {comp.get('code')})")
        else:
            print(f"   ✗ Error: {response.text}")
            
    except Exception as e:
        print(f"   ✗ Exception: {str(e)}")
    
    # Test 2: Get matches for Premier League
    print("\n2. Testing /competitions/PL/matches endpoint...")
    try:
        response = requests.get(
            f"{FOOTBALL_DATA_ORG_BASE_URL}/competitions/PL/matches",
            headers=headers,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            print(f"   ✓ Success! Found {len(matches)} matches")
            
            if matches:
                match = matches[0]
                print(f"\n   Sample match:")
                print(f"   - {match.get('homeTeam', {}).get('name')} vs {match.get('awayTeam', {}).get('name')}")
                print(f"   - Date: {match.get('utcDate')}")
                print(f"   - Status: {match.get('status')}")
        elif response.status_code == 403:
            print(f"   ⚠ Forbidden - This competition may not be available on your API tier")
            print(f"   Response: {response.text}")
        else:
            print(f"   ✗ Error: {response.text}")
            
    except Exception as e:
        print(f"   ✗ Exception: {str(e)}")
    
    # Test 3: Try with competition ID instead
    print("\n3. Testing /competitions/2021/matches endpoint (using ID)...")
    try:
        response = requests.get(
            f"{FOOTBALL_DATA_ORG_BASE_URL}/competitions/2021/matches",
            headers=headers,
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            print(f"   ✓ Success! Found {len(matches)} matches")
        elif response.status_code == 403:
            print(f"   ⚠ Forbidden - Competition 2021 (Premier League) not available on your tier")
        else:
            print(f"   ✗ Error: {response.text}")
            
    except Exception as e:
        print(f"   ✗ Exception: {str(e)}")


def test_the_odds_api():
    """Test The Odds API."""
    print("\n" + "="*60)
    print("Testing The Odds API")
    print("="*60)
    
    # Test 1: Get available sports
    print("\n1. Testing /sports endpoint...")
    try:
        response = requests.get(
            f"{THE_ODDS_API_BASE_URL}/sports",
            params={"apiKey": THE_ODDS_API_KEY},
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Remaining requests: {response.headers.get('x-requests-remaining', 'unknown')}")
        
        if response.status_code == 200:
            sports = response.json()
            print(f"   ✓ Success! Found {len(sports)} sports")
            
            # Show soccer sports
            print("\n   Available soccer sports:")
            for sport in sports:
                if 'soccer' in sport.get('key', ''):
                    print(f"   - {sport.get('title')} (key: {sport.get('key')})")
                    print(f"     Active: {sport.get('active')}, Has outrights: {sport.get('has_outrights')}")
        else:
            print(f"   ✗ Error: {response.text}")
            
    except Exception as e:
        print(f"   ✗ Exception: {str(e)}")
    
    # Test 2: Get odds for a specific sport
    for sport_key in ODDS_API_SPORTS[:2]:  # Test first 2 sports
        print(f"\n2. Testing /sports/{sport_key}/odds endpoint...")
        try:
            response = requests.get(
                f"{THE_ODDS_API_BASE_URL}/sports/{sport_key}/odds",
                params={
                    "apiKey": THE_ODDS_API_KEY,
                    "regions": "uk",
                    "markets": "h2h",
                    "oddsFormat": "decimal"
                },
                timeout=10
            )
            print(f"   Status: {response.status_code}")
            print(f"   Remaining requests: {response.headers.get('x-requests-remaining', 'unknown')}")
            
            if response.status_code == 200:
                events = response.json()
                print(f"   ✓ Success! Found {len(events)} upcoming events")
                
                if events:
                    event = events[0]
                    print(f"\n   Sample event:")
                    print(f"   - {event.get('home_team')} vs {event.get('away_team')}")
                    print(f"   - Commence time: {event.get('commence_time')}")
                    print(f"   - Bookmakers: {len(event.get('bookmakers', []))}")
            else:
                print(f"   ✗ Error: {response.text}")
                
        except Exception as e:
            print(f"   ✗ Exception: {str(e)}")


def main():
    """Run all API tests."""
    print("\n" + "="*60)
    print("API Key Validation and Data Availability Test")
    print("="*60)
    
    print(f"\nFootball-data.org API Key: {FOOTBALL_DATA_ORG_API_KEY[:10]}...")
    print(f"The Odds API Key: {THE_ODDS_API_KEY[:10]}...")
    
    test_football_data_org()
    test_the_odds_api()
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    print("\nNotes:")
    print("- If you see 403 errors, your API tier may not have access to those competitions")
    print("- Free tier for football-data.org has limited competitions")
    print("- The Odds API shows remaining requests in headers")
    print("- Check the API documentation for your specific tier limits")
    print("\nNext steps:")
    print("1. If tests pass, you can run: python run_pipeline.py")
    print("2. If you see errors, check your API keys in .env file")
    print("3. Update TRACKED_COMPETITIONS in config.py based on available data")


if __name__ == "__main__":
    main()
