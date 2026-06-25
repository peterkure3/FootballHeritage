# What-If Matchup Prediction

## 🎯 Choose Any Two Teams and Get Predictions!

The new `/predict-matchup` endpoint allows you to get predictions for **any two teams**, even if they haven't played each other recently or at all!

## 🚀 Quick Start

### API Endpoint

```
GET /api/v1/predict-matchup?home_team={team1}&away_team={team2}
```

### Example

```bash
curl "http://localhost:8000/api/v1/predict-matchup?home_team=Arsenal&away_team=Chelsea"
```

### Response

```json
{
  "home_team": "Arsenal",
  "away_team": "Chelsea",
  "winner": "home_win",
  "home_prob": 0.52,
  "draw_prob": 0.28,
  "away_prob": 0.20,
  "model_version": "1.0.0",
  "confidence": "Medium",
  "recommendation": "Arsenal is favored to win at home. Arsenal is in excellent form."
}
```

## 📊 How It Works

The prediction is based on:

1. **Recent Form** - Last 5 matches for each team
   - Wins, draws, losses
   - Goal difference

2. **Historical Odds** - Average betting odds from database

3. **Machine Learning Model** - Trained XGBoost classifier

4. **Confidence Scoring**:
   - **High**: Probability > 60%
   - **Medium**: Probability 45-60%
   - **Low**: Probability < 45%

## 💻 Usage Examples

### Python

```python
import requests

def predict_matchup(home_team, away_team):
    response = requests.get(
        "http://localhost:8000/api/v1/predict-matchup",
        params={
            "home_team": home_team,
            "away_team": away_team
        }
    )
    return response.json()

# Example
prediction = predict_matchup("Arsenal", "Chelsea")
print(f"Winner: {prediction['winner']}")
print(f"Home: {prediction['home_prob']*100:.1f}%")
print(f"Draw: {prediction['draw_prob']*100:.1f}%")
print(f"Away: {prediction['away_prob']*100:.1f}%")
print(f"Confidence: {prediction['confidence']}")
print(f"Recommendation: {prediction['recommendation']}")
```

### JavaScript

```javascript
async function predictMatchup(homeTeam, awayTeam) {
    const params = new URLSearchParams({
        home_team: homeTeam,
        away_team: awayTeam
    });
    
    const response = await fetch(
        `http://localhost:8000/api/v1/predict-matchup?${params}`
    );
    return await response.json();
}

// Example
predictMatchup('Arsenal', 'Chelsea').then(prediction => {
    console.log(`Winner: ${prediction.winner}`);
    console.log(`Home: ${(prediction.home_prob * 100).toFixed(1)}%`);
    console.log(`Confidence: ${prediction.confidence}`);
});
```

### React Component

```jsx
import React, { useState } from 'react';

function MatchupPredictor() {
    const [homeTeam, setHomeTeam] = useState('');
    const [awayTeam, setAwayTeam] = useState('');
    const [prediction, setPrediction] = useState(null);
    const [loading, setLoading] = useState(false);

    const predictMatchup = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                home_team: homeTeam,
                away_team: awayTeam
            });
            
            const response = await fetch(
                `http://localhost:8000/api/v1/predict-matchup?${params}`
            );
            const data = await response.json();
            setPrediction(data);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h2>What-If Matchup Predictor</h2>
            
            <input
                type="text"
                placeholder="Home Team"
                value={homeTeam}
                onChange={(e) => setHomeTeam(e.target.value)}
            />
            
            <input
                type="text"
                placeholder="Away Team"
                value={awayTeam}
                onChange={(e) => setAwayTeam(e.target.value)}
            />
            
            <button onClick={predictMatchup} disabled={loading}>
                {loading ? 'Predicting...' : 'Predict'}
            </button>
            
            {prediction && (
                <div className="prediction-result">
                    <h3>{prediction.home_team} vs {prediction.away_team}</h3>
                    <p><strong>Predicted Winner:</strong> {prediction.winner}</p>
                    <p><strong>Confidence:</strong> {prediction.confidence}</p>
                    
                    <div className="probabilities">
                        <div>Home: {(prediction.home_prob * 100).toFixed(1)}%</div>
                        <div>Draw: {(prediction.draw_prob * 100).toFixed(1)}%</div>
                        <div>Away: {(prediction.away_prob * 100).toFixed(1)}%</div>
                    </div>
                    
                    <p><em>{prediction.recommendation}</em></p>
                </div>
            )}
        </div>
    );
}
```

### cURL Examples

```bash
# Arsenal vs Chelsea
curl "http://localhost:8000/api/v1/predict-matchup?home_team=Arsenal&away_team=Chelsea"

# Liverpool vs Manchester City
curl "http://localhost:8000/api/v1/predict-matchup?home_team=Liverpool&away_team=Manchester%20City"

# Barcelona vs Real Madrid
curl "http://localhost:8000/api/v1/predict-matchup?home_team=Barcelona&away_team=Real%20Madrid"
```

## 🎮 Interactive Testing

Run the test script:

```bash
python test_matchup_prediction.py
```

This will:
1. Test several example matchups
2. Show predictions with probabilities
3. Allow you to enter your own matchups
4. Display code examples

## 🔍 Team Name Matching

The endpoint uses **fuzzy matching** (case-insensitive, partial match):

- ✅ "Arsenal" matches "Arsenal FC"
- ✅ "Man City" matches "Manchester City"
- ✅ "barcelona" matches "FC Barcelona"
- ✅ "liverpool" matches "Liverpool FC"

## 📈 Understanding the Results

### Winner Field
- `home_win` - Home team is predicted to win
- `away_win` - Away team is predicted to win
- `draw` - Match is predicted to end in a draw

### Probabilities
- Sum of all probabilities = 1.0 (100%)
- Higher probability = more confident prediction

### Confidence Levels
- **High** (>60%): Strong prediction, model is very confident
- **Medium** (45-60%): Moderate prediction, reasonable confidence
- **Low** (<45%): Weak prediction, outcome is uncertain

### Recommendation
Human-readable summary including:
- Predicted outcome
- Team form analysis
- Contextual insights

## 🎯 Use Cases

### 1. Fantasy Football
```python
# Compare potential matchups
teams = ["Arsenal", "Liverpool", "Man City", "Chelsea"]
for home in teams:
    for away in teams:
        if home != away:
            pred = predict_matchup(home, away)
            print(f"{home} vs {away}: {pred['winner']}")
```

### 2. Betting Analysis
```python
# Find favorable matchups
prediction = predict_matchup("Arsenal", "Chelsea")
if prediction['confidence'] == 'High' and prediction['home_prob'] > 0.6:
    print(f"Strong bet: {prediction['home_team']} to win")
```

### 3. Tournament Simulation
```python
# Simulate knockout rounds
def simulate_match(team1, team2):
    pred = predict_matchup(team1, team2)
    if pred['winner'] == 'home_win':
        return team1
    elif pred['winner'] == 'away_win':
        return team2
    else:
        # Simulate penalty shootout
        return random.choice([team1, team2])
```

### 4. Mobile App Integration
Perfect for:
- Match prediction apps
- Fantasy football tools
- Betting calculators
- Sports analytics dashboards

## ⚠️ Limitations

1. **Data Dependency**: Predictions are based on teams in the database
   - Teams must have recent match history
   - New teams may have limited data

2. **Form-Based**: Uses last 5 matches
   - Doesn't account for injuries
   - Doesn't consider head-to-head history
   - Doesn't factor in home/away specific performance

3. **Model Accuracy**: ~44% overall accuracy
   - Better than random (33%)
   - Not perfect - use as guidance, not certainty

## 🔧 Advanced Features

### Get Available Teams

```python
# Get list of teams from database
response = requests.get("http://localhost:8000/api/v1/matches?limit=1000")
matches = response.json()

teams = set()
for match in matches:
    teams.add(match['home_team'])
    teams.add(match['away_team'])

print(f"Available teams: {sorted(teams)}")
```

### Batch Predictions

```python
matchups = [
    ("Arsenal", "Chelsea"),
    ("Liverpool", "Man City"),
    ("Barcelona", "Real Madrid"),
]

predictions = []
for home, away in matchups:
    pred = predict_matchup(home, away)
    predictions.append(pred)

# Analyze results
for pred in predictions:
    print(f"{pred['home_team']} vs {pred['away_team']}: "
          f"{pred['winner']} ({pred['confidence']} confidence)")
```

## 📚 API Documentation

Visit the interactive docs:
```
http://localhost:8000/docs
```

Look for the `/predict-matchup` endpoint to:
- Try it out directly in the browser
- See full request/response schemas
- Generate code samples

## 🎉 Summary

The What-If Matchup Prediction feature allows you to:

✅ Predict **any matchup** between two teams  
✅ Get **probabilities** for all outcomes  
✅ Receive **confidence scores** and recommendations  
✅ Use **fuzzy team name matching**  
✅ Integrate with **any application**  

Perfect for fantasy football, betting analysis, and sports apps! 🏆
