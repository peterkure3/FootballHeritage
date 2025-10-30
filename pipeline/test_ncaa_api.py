"""
Test NCAA API connectivity and data availability.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent))

from etl.fetch_ncaa_data import NCAADataFetcher
from config import NCAA_SPORTS


def test_ncaa_api():
    """Test NCAA API endpoints."""
    print("=" * 60)
    print("NCAA API Test")
    print("=" * 60)
    print()
    
    fetcher = NCAADataFetcher()
    
    # Test each sport
    for sport_key, sport_config in NCAA_SPORTS.items():
        print(f"Testing {sport_config['name']}...")
        print("-" * 60)
        
        try:
            # Get today's scoreboard
            scoreboard = fetcher.fetch_scoreboard(
                sport_key,
                sport_config['division']
            )
            
            games = scoreboard.get('games', [])
            print(f"✓ API accessible")
            print(f"  Games today: {len(games)}")
            
            if games:
                sample_game = games[0]
                game_id = sample_game.get('game', {}).get('gameID')
                home = sample_game.get('game', {}).get('home', {}).get('names', {}).get('short', 'N/A')
                away = sample_game.get('game', {}).get('away', {}).get('names', {}).get('short', 'N/A')
                print(f"  Sample game: {away} @ {home} (ID: {game_id})")
            
            # Try fetching last week
            last_week = datetime.now() - timedelta(days=7)
            date_str = last_week.strftime("%Y/%m/%d")
            
            scoreboard_past = fetcher.fetch_scoreboard(
                sport_key,
                sport_config['division'],
                date_str
            )
            
            past_games = scoreboard_past.get('games', [])
            print(f"  Games on {date_str}: {past_games and len(past_games) or 0}")
            
            print(f"✓ {sport_config['name']} API working")
            
        except Exception as e:
            print(f"✗ Error testing {sport_config['name']}: {str(e)}")
        
        print()
    
    # Test game details endpoint
    print("Testing game details endpoint...")
    print("-" * 60)
    
    try:
        # Try a sample game ID (may not exist)
        game_details = fetcher.fetch_game_details("6459218")
        
        if game_details:
            print("✓ Game details endpoint accessible")
        else:
            print("⚠ Game details endpoint returned empty (game may not exist)")
    except Exception as e:
        print(f"⚠ Game details test: {str(e)}")
    
    print()
    print("=" * 60)
    print("NCAA API Test Complete")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Fetch NCAA data: python -m etl.fetch_ncaa_data")
    print("2. Transform data: python -m etl.transform_ncaa")
    print("3. See NCAA_BASKETBALL_GUIDE.md for full instructions")
    print()


if __name__ == "__main__":
    test_ncaa_api()
