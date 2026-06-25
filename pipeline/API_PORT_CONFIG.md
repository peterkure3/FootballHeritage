# API Port Configuration

## Current Port: 8080

The API has been changed from port **8000** to port **8080**.

## How to Access

### New URLs

- **API Base**: http://localhost:8080
- **Interactive Docs**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/api/v1/health
- **Matches**: http://localhost:8080/api/v1/matches
- **Predictions**: http://localhost:8080/api/v1/predictions/{match_id}
- **What-If Matchup**: http://localhost:8080/api/v1/predict-matchup

### Network Access

If accessing from other devices on your network:
```
http://YOUR_IP:8080
```

## Starting the API

```bash
# Start on port 8080 (default)
python -m api.main

# Or use uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

## Changing the Port

### Method 1: Edit .env File (Recommended)

Add to your `.env` file:
```bash
API_PORT=8080
```

Then restart the API.

### Method 2: Edit config.py

Change the default in `config.py`:
```python
API_PORT = int(os.getenv("API_PORT", "8080"))  # Change 8080 to your port
```

### Method 3: Environment Variable

Set temporarily:
```bash
# Windows PowerShell
$env:API_PORT=8080
python -m api.main

# Windows CMD
set API_PORT=8080
python -m api.main

# Linux/Mac
export API_PORT=8080
python -m api.main
```

### Method 4: Command Line

```bash
uvicorn api.main:app --host 0.0.0.0 --port 9000
```

## Update Client Applications

If you have applications connecting to the API, update the base URL:

### Python
```python
# Old
API_URL = "http://localhost:8000/api/v1"

# New
API_URL = "http://localhost:8080/api/v1"
```

### JavaScript
```javascript
// Old
const API_BASE_URL = 'http://localhost:8000';

// New
const API_BASE_URL = 'http://localhost:8080';
```

### cURL
```bash
# Old
curl http://localhost:8000/api/v1/health

# New
curl http://localhost:8080/api/v1/health
```

## Common Ports

| Port | Use Case |
|------|----------|
| 8000 | Default FastAPI/Django |
| 8080 | **Current** - Alternative HTTP |
| 8888 | Jupyter Notebook |
| 5000 | Flask default |
| 3000 | React/Node.js default |

## Troubleshooting

### Port Already in Use

If you get "Address already in use" error:

**Windows:**
```powershell
# Find what's using the port
netstat -ano | findstr :8080

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
# Find what's using the port
lsof -i :8080

# Kill the process
kill -9 <PID>
```

### Firewall Blocking

**Windows:**
```powershell
# Allow port 8080
netsh advfirewall firewall add rule name="FastAPI 8080" dir=in action=allow protocol=TCP localport=8080
```

**Linux:**
```bash
sudo ufw allow 8080
```

### Can't Access from Other Devices

Make sure:
1. API is running with `host="0.0.0.0"` (already configured)
2. Firewall allows the port
3. You're using your computer's IP, not localhost

## Multiple API Instances

Run multiple instances on different ports:

```bash
# Instance 1 - Main database (port 8080)
python -m api.main

# Instance 2 - Heritage database (port 8081)
API_PORT=8081 DB_NAME=football_heritage python -m api.main

# Instance 3 - Testing (port 8082)
API_PORT=8082 python -m api.main
```

## Summary

✅ **Current Port**: 8080  
✅ **Access**: http://localhost:8080  
✅ **Docs**: http://localhost:8080/docs  
✅ **Configurable** via .env or environment variables  

The port change is complete! Update your client applications to use the new port. 🚀
