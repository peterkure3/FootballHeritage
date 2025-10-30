"""
Test the What-If matchup prediction feature.
Choose any two teams and see what would happen if they played!
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from urllib.parse import urlencode

API_URL = "http://localhost:8000/api/v1"


def predict_matchup(home_team, away_team):
    """Get prediction for any two teams."""
    params = {
        'home_team': home_team,
        'away_team': away_team
    }
    
    url = f"{API_URL}/predict-matchup?{urlencode(params)}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def display_prediction(prediction):
    """Display prediction in a nice format."""
    print("\n" + "="*80)
    print(f"MATCHUP PREDICTION: {prediction['home_team']} vs {prediction['away_team']}")
    print("="*80)
    
    print(f"\n🏆 Predicted Winner: {prediction['winner'].replace('_', ' ').upper()}")
    print(f"📊 Confidence Level: {prediction['confidence']}")
    
    print(f"\n📈 Win Probabilities:")
    print(f"   Home ({prediction['home_team']}): {prediction['home_prob']*100:.1f}%")
    print(f"   Draw:                            {prediction['draw_prob']*100:.1f}%")
    print(f"   Away ({prediction['away_team']}): {prediction['away_prob']*100:.1f}%")
    
    print(f"\n💡 Recommendation:")
    print(f"   {prediction['recommendation']}")
    
    print(f"\n🤖 Model Version: {prediction['model_version']}")
    print("="*80)


def main():
    """Demo the matchup prediction feature."""
    print("="*80)
    print("WHAT-IF MATCHUP PREDICTOR")
    print("="*80)
    print("\nPredict the outcome of any matchup between two teams!")
    print("The model uses recent form, goal differences, and historical data.\n")
    
    # Example matchups
    matchups = [
        ("Arsenal", "Chelsea"),
        ("Liverpool", "Manchester City"),
        ("Barcelona", "Real Madrid"),
        ("Bayern Munich", "Borussia Dortmund"),
    ]
    
    print("Testing example matchups...\n")
    
    for home, away in matchups:
        try:
            prediction = predict_matchup(home, away)
            display_prediction(prediction)
            print()
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                print(f"\n⚠️  Team data not found for {home} or {away}")
            else:
                print(f"\n❌ Error: {e}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    # Interactive mode
    print("\n" + "="*80)
    print("INTERACTIVE MODE")
    print("="*80)
    print("\nEnter your own matchup (or press Enter to skip):")
    
    try:
        home_team = input("Home team: ").strip()
        if home_team:
            away_team = input("Away team: ").strip()
            if away_team:
                prediction = predict_matchup(home_team, away_team)
                display_prediction(prediction)
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "="*80)
    print("HOW TO USE IN YOUR APPLICATION")
    print("="*80)
    print(f"""
# Python Example:
import requests

response = requests.get(
    "{API_URL}/predict-matchup",
    params={{"home_team": "Arsenal", "away_team": "Chelsea"}}
)
prediction = response.json()
print(f"Winner: {{prediction['winner']}}")
print(f"Home probability: {{prediction['home_prob']*100:.1f}}%")

# JavaScript Example:
const response = await fetch(
    '{API_URL}/predict-matchup?home_team=Arsenal&away_team=Chelsea'
);
const prediction = await response.json();
console.log(`Winner: ${{prediction.winner}}`);

# Direct URL:
{API_URL}/predict-matchup?home_team=Arsenal&away_team=Chelsea
    """)
    
    print("\n✅ You can now predict any matchup through the API!")
    print("📚 See INTEGRATION_GUIDE.md for more examples")


if __name__ == "__main__":
    main()
