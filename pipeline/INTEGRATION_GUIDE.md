# API Integration Guide

## 🔗 How to Connect Other Applications

Your API is running at: **http://localhost:8000**

## Quick Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/predictions/{match_id}` | GET | Get prediction for a specific match |
| `/api/v1/matches` | GET | List matches with filters |
| `/api/v1/health` | GET | Check API health |
| `/docs` | GET | Interactive API documentation |

### Base URL

```
Local:    http://localhost:8000
Network:  http://YOUR_IP:8000
```

## 📱 Integration Examples

### 1. Python Application

```python
import requests

class FootballBettingAPI:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def get_prediction(self, match_id):
        """Get prediction for a match."""
        response = requests.get(f"{self.base_url}/api/v1/predictions/{match_id}")
        response.raise_for_status()
        return response.json()
    
    def get_matches(self, competition=None, date=None, limit=10):
        """Get list of matches."""
        params = {"limit": limit}
        if competition:
            params["competition"] = competition
        if date:
            params["date"] = date
        
        response = requests.get(f"{self.base_url}/api/v1/matches", params=params)
        response.raise_for_status()
        return response.json()
    
    def health_check(self):
        """Check API health."""
        response = requests.get(f"{self.base_url}/api/v1/health")
        return response.json()

# Usage
api = FootballBettingAPI()

# Get prediction
prediction = api.get_prediction(537863)
print(f"Winner: {prediction['winner']}")
print(f"Probabilities: H:{prediction['home_prob']:.2%} D:{prediction['draw_prob']:.2%} A:{prediction['away_prob']:.2%}")

# Get matches
matches = api.get_matches(competition="Premier League", limit=5)
for match in matches:
    print(f"{match['home_team']} vs {match['away_team']} - {match['date']}")
```

### 2. JavaScript/TypeScript

```javascript
class FootballBettingAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async getPrediction(matchId) {
        const response = await fetch(`${this.baseUrl}/api/v1/predictions/${matchId}`);
        if (!response.ok) throw new Error('Failed to fetch prediction');
        return await response.json();
    }
    
    async getMatches(filters = {}) {
        const params = new URLSearchParams({
            limit: filters.limit || 10,
            ...(filters.competition && { competition: filters.competition }),
            ...(filters.date && { date: filters.date })
        });
        
        const response = await fetch(`${this.baseUrl}/api/v1/matches?${params}`);
        if (!response.ok) throw new Error('Failed to fetch matches');
        return await response.json();
    }
    
    async healthCheck() {
        const response = await fetch(`${this.baseUrl}/api/v1/health`);
        return await response.json();
    }
}

// Usage
const api = new FootballBettingAPI();

// Get prediction
api.getPrediction(537863).then(prediction => {
    console.log(`Winner: ${prediction.winner}`);
    console.log(`Home: ${(prediction.home_prob * 100).toFixed(1)}%`);
});

// Get matches
api.getMatches({ competition: 'Premier League', limit: 5 }).then(matches => {
    matches.forEach(match => {
        console.log(`${match.home_team} vs ${match.away_team}`);
    });
});
```

### 3. React Component

```jsx
import React, { useState, useEffect } from 'react';

const API_BASE_URL = 'http://localhost:8000';

function MatchPredictions() {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchMatchesWithPredictions();
    }, []);

    const fetchMatchesWithPredictions = async () => {
        try {
            // Fetch matches
            const matchesRes = await fetch(`${API_BASE_URL}/api/v1/matches?limit=10`);
            const matchesData = await matchesRes.json();
            
            // Fetch predictions for each match
            const matchesWithPredictions = await Promise.all(
                matchesData.map(async (match) => {
                    try {
                        const predRes = await fetch(
                            `${API_BASE_URL}/api/v1/predictions/${match.match_id}`
                        );
                        const prediction = await predRes.json();
                        return { ...match, prediction };
                    } catch {
                        return { ...match, prediction: null };
                    }
                })
            );
            
            setMatches(matchesWithPredictions);
            setLoading(false);
        } catch (error) {
            console.error('Error fetching data:', error);
            setLoading(false);
        }
    };

    if (loading) return <div>Loading...</div>;

    return (
        <div className="predictions-container">
            <h1>Football Match Predictions</h1>
            {matches.map(match => (
                <div key={match.match_id} className="match-card">
                    <h3>{match.home_team} vs {match.away_team}</h3>
                    <p>Date: {new Date(match.date).toLocaleDateString()}</p>
                    
                    {match.prediction && (
                        <div className="prediction">
                            <h4>Prediction: {match.prediction.winner.replace('_', ' ')}</h4>
                            <div className="probabilities">
                                <span>Home: {(match.prediction.home_prob * 100).toFixed(1)}%</span>
                                <span>Draw: {(match.prediction.draw_prob * 100).toFixed(1)}%</span>
                                <span>Away: {(match.prediction.away_prob * 100).toFixed(1)}%</span>
                            </div>
                        </div>
                    )}
                    
                    {match.home_win_odds && (
                        <div className="odds">
                            <span>Odds - H: {match.home_win_odds?.toFixed(2)}</span>
                            <span>D: {match.draw_odds?.toFixed(2)}</span>
                            <span>A: {match.away_win_odds?.toFixed(2)}</span>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

export default MatchPredictions;
```

### 4. Mobile App (React Native)

```javascript
import React, { useState, useEffect } from 'react';
import { View, Text, FlatList, ActivityIndicator } from 'react-native';

const API_BASE_URL = 'http://YOUR_IP:8000'; // Replace with your computer's IP

const MatchPredictionsScreen = () => {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/matches?limit=20`);
            const data = await response.json();
            
            // Fetch predictions
            const withPredictions = await Promise.all(
                data.map(async (match) => {
                    try {
                        const predRes = await fetch(
                            `${API_BASE_URL}/api/v1/predictions/${match.match_id}`
                        );
                        const prediction = await predRes.json();
                        return { ...match, prediction };
                    } catch {
                        return match;
                    }
                })
            );
            
            setMatches(withPredictions);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const renderMatch = ({ item }) => (
        <View style={styles.matchCard}>
            <Text style={styles.teams}>
                {item.home_team} vs {item.away_team}
            </Text>
            {item.prediction && (
                <View>
                    <Text>Predicted: {item.prediction.winner}</Text>
                    <Text>
                        H: {(item.prediction.home_prob * 100).toFixed(0)}% | 
                        D: {(item.prediction.draw_prob * 100).toFixed(0)}% | 
                        A: {(item.prediction.away_prob * 100).toFixed(0)}%
                    </Text>
                </View>
            )}
        </View>
    );

    if (loading) return <ActivityIndicator />;

    return (
        <FlatList
            data={matches}
            renderItem={renderMatch}
            keyExtractor={item => item.match_id.toString()}
        />
    );
};
```

### 5. Excel/Power Query

```m
let
    // API Configuration
    BaseUrl = "http://localhost:8000",
    
    // Fetch matches
    MatchesUrl = BaseUrl & "/api/v1/matches?limit=100",
    MatchesSource = Json.Document(Web.Contents(MatchesUrl)),
    MatchesTable = Table.FromList(MatchesSource, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    MatchesExpanded = Table.ExpandRecordColumn(MatchesTable, "Column1", 
        {"match_id", "home_team", "away_team", "date", "competition"}),
    
    // Add predictions
    AddPredictions = Table.AddColumn(MatchesExpanded, "Prediction", each 
        try Json.Document(Web.Contents(BaseUrl & "/api/v1/predictions/" & Text.From([match_id])))
        otherwise null
    ),
    
    // Expand prediction data
    ExpandPredictions = Table.ExpandRecordColumn(AddPredictions, "Prediction",
        {"winner", "home_prob", "draw_prob", "away_prob"})
in
    ExpandPredictions
```

## 🌐 Network Access

### Find Your IP Address

**Windows:**
```bash
ipconfig
# Look for "IPv4 Address"
```

**Mac/Linux:**
```bash
ifconfig
# or
ip addr show
```

### Access from Other Devices

Replace `localhost` with your computer's IP:
```
http://192.168.1.100:8000  # Example
```

### Firewall Settings

**Windows:**
```powershell
# Allow port 8000
netsh advfirewall firewall add rule name="FastAPI" dir=in action=allow protocol=TCP localport=8000
```

**Linux:**
```bash
sudo ufw allow 8000
```

## 🔒 Security Considerations

### 1. Add Authentication (Optional)

```python
# api/routes.py
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "your-secret-key":
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

@router.get("/predictions/{match_id}", dependencies=[Depends(verify_api_key)])
async def get_prediction(match_id: int):
    # ... your code
```

### 2. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/predictions/{match_id}")
@limiter.limit("10/minute")
async def get_prediction(match_id: int):
    # ... your code
```

### 3. HTTPS (Production)

Use a reverse proxy like nginx with SSL certificate.

## 📊 Response Examples

### Prediction Response
```json
{
  "match_id": 537863,
  "winner": "home_win",
  "home_prob": 0.65,
  "draw_prob": 0.20,
  "away_prob": 0.15,
  "model_version": "1.0.0",
  "created_at": "2025-10-26T12:00:00"
}
```

### Matches Response
```json
[
  {
    "match_id": 537863,
    "competition": "Premier League",
    "date": "2025-10-27T15:00:00",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "home_score": null,
    "away_score": null,
    "status": "SCHEDULED",
    "home_win_odds": 2.10,
    "draw_odds": 3.40,
    "away_win_odds": 3.50
  }
]
```

### Health Response
```json
{
  "status": "healthy",
  "last_pipeline_run": "2025-10-26T10:00:00",
  "database_connected": true
}
```

## 🚀 Production Deployment

### Using Docker

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t football-api .
docker run -p 8000:8000 football-api
```

### Using nginx (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📱 Testing

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get matches
curl "http://localhost:8000/api/v1/matches?limit=5"

# Get prediction
curl http://localhost:8000/api/v1/predictions/537863
```

## 🔗 Interactive Documentation

Visit: **http://localhost:8000/docs**

This provides:
- ✅ Try out endpoints directly
- ✅ See request/response schemas
- ✅ Generate code samples
- ✅ Test authentication

## 💡 Best Practices

1. **Use environment variables** for API URL
2. **Handle errors gracefully** (network failures, 404s, etc.)
3. **Cache responses** when appropriate
4. **Implement retry logic** for failed requests
5. **Monitor API health** before making requests
6. **Use async/await** for better performance
7. **Validate responses** before using data

## 📞 Support

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health
- Project README: See README.md

Your API is ready to integrate with any application! 🎉
