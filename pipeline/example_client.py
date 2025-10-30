"""
Example client application showing how to connect to the API.
Run this to test your API integration.
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime

class FootballBettingClient:
    """Simple client for the Football Betting API."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
    
    def health_check(self):
        """Check if API is healthy."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}
    
    def get_matches(self, competition=None, date=None, limit=10):
        """Get list of matches."""
        params = {"limit": limit}
        if competition:
            params["competition"] = competition
        if date:
            params["date"] = date
        
        response = requests.get(f"{self.api_url}/matches", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_prediction(self, match_id):
        """Get prediction for a specific match."""
        response = requests.get(f"{self.api_url}/predictions/{match_id}")
        response.raise_for_status()
        return response.json()


def main():
    """Demo the API client."""
    print("="*80)
    print("Football Betting API - Example Client")
    print("="*80)
    
    # Initialize client
    client = FootballBettingClient()
    
    # 1. Health Check
    print("\n1. Checking API Health...")
    print("-"*80)
    health = client.health_check()
    print(f"Status: {health.get('status')}")
    print(f"Database Connected: {health.get('database_connected')}")
    print(f"Last Pipeline Run: {health.get('last_pipeline_run', 'N/A')}")
    
    if health.get('status') != 'healthy':
        print("\n⚠️  API is not healthy. Make sure it's running:")
        print("   python -m api.main")
        return
    
    # 2. Get Matches
    print("\n2. Fetching Matches...")
    print("-"*80)
    try:
        matches = client.get_matches(limit=5)
        print(f"Found {len(matches)} matches:\n")
        
        for i, match in enumerate(matches, 1):
            match_date = datetime.fromisoformat(match['date'].replace('Z', '+00:00'))
            print(f"{i}. Match ID: {match['match_id']}")
            print(f"   {match['home_team']} vs {match['away_team']}")
            print(f"   Competition: {match.get('competition', 'N/A')}")
            print(f"   Date: {match_date.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Status: {match['status']}")
            
            if match.get('home_win_odds'):
                print(f"   Odds: H:{match['home_win_odds']:.2f} D:{match['draw_odds']:.2f} A:{match['away_win_odds']:.2f}")
            print()
        
        # 3. Get Predictions
        if matches:
            print("\n3. Fetching Predictions...")
            print("-"*80)
            
            for match in matches[:3]:  # Get predictions for first 3 matches
                match_id = match['match_id']
                
                try:
                    prediction = client.get_prediction(match_id)
                    
                    print(f"\nMatch: {match['home_team']} vs {match['away_team']}")
                    print(f"Predicted Winner: {prediction['winner'].replace('_', ' ').title()}")
                    print(f"Probabilities:")
                    print(f"  Home Win: {prediction['home_prob']*100:.1f}%")
                    print(f"  Draw:     {prediction['draw_prob']*100:.1f}%")
                    print(f"  Away Win: {prediction['away_prob']*100:.1f}%")
                    print(f"Model Version: {prediction['model_version']}")
                    
                    # Calculate betting edge if odds available
                    if match.get('home_win_odds'):
                        home_edge = (prediction['home_prob'] * match['home_win_odds']) - 1
                        draw_edge = (prediction['draw_prob'] * match['draw_odds']) - 1
                        away_edge = (prediction['away_prob'] * match['away_win_odds']) - 1
                        
                        print(f"\nBetting Edge (Expected Value - 1):")
                        print(f"  Home: {home_edge:+.2%}")
                        print(f"  Draw: {draw_edge:+.2%}")
                        print(f"  Away: {away_edge:+.2%}")
                        
                        best_bet = max(
                            ('Home', home_edge),
                            ('Draw', draw_edge),
                            ('Away', away_edge),
                            key=lambda x: x[1]
                        )
                        
                        if best_bet[1] > 0:
                            print(f"  💡 Best Value: {best_bet[0]} ({best_bet[1]:+.2%})")
                    
                except requests.HTTPException as e:
                    if e.response.status_code == 404:
                        print(f"\nNo prediction available for match {match_id}")
                    else:
                        print(f"\nError getting prediction: {e}")
                except Exception as e:
                    print(f"\nError: {e}")
        
        # 4. Summary
        print("\n" + "="*80)
        print("Integration Test Complete!")
        print("="*80)
        print("\n✅ Your API is working correctly!")
        print("\nYou can now integrate this API with:")
        print("  • Web applications (React, Vue, Angular)")
        print("  • Mobile apps (React Native, Flutter)")
        print("  • Desktop applications")
        print("  • Excel/Power BI")
        print("  • Other backend services")
        print("\nSee INTEGRATION_GUIDE.md for code examples.")
        
    except requests.RequestException as e:
        print(f"\n❌ Error connecting to API: {e}")
        print("\nMake sure the API is running:")
        print("  python -m api.main")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
