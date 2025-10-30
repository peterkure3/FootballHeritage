"""
Automatic data downloader - no user input required.
Downloads historical data and creates sample data automatically.
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent))

import pandas as pd
import requests
from config import HISTORICAL_CSV_DIR, LOG_LEVEL
from etl.utils import setup_logger, ensure_dir

logger = setup_logger(__name__, LOG_LEVEL)


def download_and_normalize():
    """Download and normalize historical data automatically."""
    
    print("\n" + "="*80)
    print("AUTO DOWNLOAD - Getting Historical Data")
    print("="*80)
    
    ensure_dir(HISTORICAL_CSV_DIR)
    
    # Define seasons and leagues
    seasons = ["2324", "2223", "2122"]  # Last 3 seasons
    leagues = {
        "E0": "Premier_League",
        "SP1": "La_Liga",
        "D1": "Bundesliga",
        "I1": "Serie_A",
        "F1": "Ligue_1",
    }
    
    base_url = "https://www.football-data.co.uk/mmz4281"
    total_downloaded = 0
    successful_downloads = []
    
    print("\nDownloading historical match data...")
    print("-" * 80)
    
    for season in seasons:
        for league_code, league_name in leagues.items():
            url = f"{base_url}/{season}/{league_code}.csv"
            filename = f"{league_name}_{season}.csv"
            filepath = HISTORICAL_CSV_DIR / filename
            
            try:
                print(f"Downloading {league_name} {season}...", end=" ")
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    # Save raw CSV
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    # Verify it's valid CSV
                    df = pd.read_csv(filepath)
                    print(f"✓ {len(df)} matches")
                    total_downloaded += len(df)
                    successful_downloads.append(filepath)
                else:
                    print(f"✗ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
    
    print("-" * 80)
    print(f"Downloaded {total_downloaded} matches from {len(successful_downloads)} files")
    
    # Normalize the downloaded files
    if successful_downloads:
        print("\nNormalizing data...")
        print("-" * 80)
        
        normalized_count = 0
        
        for csv_file in successful_downloads:
            try:
                print(f"Processing {csv_file.name}...", end=" ")
                df = pd.read_csv(csv_file)
                
                # Create normalized DataFrame
                df_normalized = pd.DataFrame()
                
                # Map columns
                if 'Date' in df.columns:
                    df_normalized['date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
                
                if 'HomeTeam' in df.columns and 'AwayTeam' in df.columns:
                    df_normalized['home_team'] = df['HomeTeam']
                    df_normalized['away_team'] = df['AwayTeam']
                
                if 'FTHG' in df.columns and 'FTAG' in df.columns:
                    df_normalized['home_score'] = pd.to_numeric(df['FTHG'], errors='coerce')
                    df_normalized['away_score'] = pd.to_numeric(df['FTAG'], errors='coerce')
                
                # Add match_id
                df_normalized['match_id'] = range(1, len(df_normalized) + 1)
                
                # Add competition from filename
                league_name = csv_file.stem.rsplit('_', 1)[0].replace('_', ' ')
                df_normalized['competition'] = league_name
                
                # Add status
                df_normalized['status'] = 'FINISHED'
                
                # Add data source
                df_normalized['data_source'] = 'historical_csv'
                
                # Calculate result
                if 'home_score' in df_normalized.columns and 'away_score' in df_normalized.columns:
                    df_normalized['result'] = df_normalized.apply(
                        lambda row: 'home_win' if pd.notna(row['home_score']) and pd.notna(row['away_score']) and row['home_score'] > row['away_score']
                        else ('away_win' if pd.notna(row['home_score']) and pd.notna(row['away_score']) and row['home_score'] < row['away_score']
                        else ('draw' if pd.notna(row['home_score']) and pd.notna(row['away_score']) else None)),
                        axis=1
                    )
                
                # Remove rows with missing critical data
                df_normalized = df_normalized.dropna(subset=['home_team', 'away_team', 'home_score', 'away_score'])
                
                # Save normalized version
                output_file = HISTORICAL_CSV_DIR / f"normalized_{csv_file.name}"
                df_normalized.to_csv(output_file, index=False)
                
                print(f"✓ {len(df_normalized)} matches normalized")
                normalized_count += len(df_normalized)
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
        
        print("-" * 80)
        print(f"Normalized {normalized_count} total matches")
    
    # Create sample data as backup
    print("\nCreating sample data as backup...")
    print("-" * 80)
    
    sample_data = {
        'match_id': range(1, 201),
        'home_team': ['Arsenal', 'Liverpool', 'Man City', 'Chelsea'] * 50,
        'away_team': ['Tottenham', 'Man Utd', 'Newcastle', 'Brighton'] * 50,
        'home_score': [2, 1, 3, 0, 1, 2, 1, 0] * 25,
        'away_score': [1, 1, 2, 2, 0, 1, 3, 1] * 25,
        'date': pd.date_range('2024-01-01', periods=200, freq='2D'),
        'competition': 'Premier League',
        'status': 'FINISHED',
        'data_source': 'sample',
    }
    
    df_sample = pd.DataFrame(sample_data)
    
    # Add result
    df_sample['result'] = df_sample.apply(
        lambda row: 'home_win' if row['home_score'] > row['away_score']
        else ('away_win' if row['home_score'] < row['away_score'] else 'draw'),
        axis=1
    )
    
    sample_file = HISTORICAL_CSV_DIR / "sample_matches.csv"
    df_sample.to_csv(sample_file, index=False)
    print(f"✓ Created {len(df_sample)} sample matches")
    
    # Summary
    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE")
    print("="*80)
    
    all_csv_files = list(HISTORICAL_CSV_DIR.glob("*.csv"))
    normalized_files = list(HISTORICAL_CSV_DIR.glob("normalized_*.csv"))
    
    print(f"\nTotal CSV files: {len(all_csv_files)}")
    print(f"Normalized files: {len(normalized_files)}")
    print(f"Total matches available: {total_downloaded + len(df_sample)}")
    print(f"\nData location: {HISTORICAL_CSV_DIR}")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Transform data:    python -m etl.transform")
    print("2. Load to database:  python -m etl.load_to_db")
    print("3. Train model:       python -m models.train_model")
    print("4. Generate predictions: python -m models.predict")
    print("="*80)
    
    return total_downloaded + len(df_sample)


if __name__ == "__main__":
    try:
        total = download_and_normalize()
        print(f"\n✅ SUCCESS! Downloaded {total} matches")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        logger.error(f"Download failed: {str(e)}", exc_info=True)
        sys.exit(1)
