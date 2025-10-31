"""
Test automation setup - runs a quick pipeline test.
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(str(Path(__file__).parent))

print("=" * 60)
print("TESTING AUTOMATION SETUP")
print("=" * 60)
print()

# Test imports
print("[1/5] Testing imports...")
try:
    from etl.fetch_raw_data import main as fetch_data
    from etl.transform import main as transform_data
    from etl.load_to_db import main as load_data
    from models.predict import main as predict_matches
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print()

# Test database connection
print("[2/5] Testing database connection...")
try:
    import psycopg2
    conn = psycopg2.connect('postgresql://postgres:jumpman13@localhost:5432/football_betting')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM matches')
    count = cur.fetchone()[0]
    print(f"✓ Database connected ({count} matches)")
    conn.close()
except Exception as e:
    print(f"✗ Database connection failed: {e}")
    sys.exit(1)

print()

# Test API keys
print("[3/5] Testing API keys...")
try:
    from config import FOOTBALL_DATA_ORG_API_KEY, THE_ODDS_API_KEY
    
    if FOOTBALL_DATA_ORG_API_KEY and FOOTBALL_DATA_ORG_API_KEY != "YOUR_FOOTBALL_DATA_ORG_API_KEY":
        print("✓ Football-data.org API key configured")
    else:
        print("⚠ Football-data.org API key not configured")
    
    if THE_ODDS_API_KEY and THE_ODDS_API_KEY != "YOUR_THE_ODDS_API_KEY":
        print("✓ The Odds API key configured")
    else:
        print("⚠ The Odds API key not configured")
        
except Exception as e:
    print(f"✗ API key check failed: {e}")

print()

# Test schedule package (for Python scheduler)
print("[4/5] Testing schedule package...")
try:
    import schedule
    print("✓ Schedule package installed")
except ImportError:
    print("⚠ Schedule package not installed (run: pip install schedule)")

print()

# Test batch files exist
print("[5/5] Testing batch files...")
batch_files = [
    Path("run_daily_fetch.bat"),
    Path("run_weekly_retrain.bat")
]

for batch_file in batch_files:
    if batch_file.exists():
        print(f"✓ {batch_file.name} exists")
    else:
        print(f"✗ {batch_file.name} not found")

print()
print("=" * 60)
print("AUTOMATION TEST COMPLETE")
print("=" * 60)
print()
print("Next steps:")
print("1. Review AUTOMATION_SETUP.md for setup instructions")
print("2. Choose your automation method:")
print("   - Windows Task Scheduler (recommended)")
print("   - Python Scheduler (cross-platform)")
print("   - Apache Airflow (production)")
print()
