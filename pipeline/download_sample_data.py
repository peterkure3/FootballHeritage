"""
Download sample historical football data from public sources.
This provides additional training data when API limits are reached.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import pandas as pd
import requests
from config import HISTORICAL_CSV_DIR, LOG_LEVEL
from etl.utils import setup_logger, ensure_dir

logger = setup_logger(__name__, LOG_LEVEL)


def download_football_data_uk():
    """
    Download historical data from football-data.co.uk
    Free historical football results and betting odds data.
    """
    logger.info("Downloading data from football-data.co.uk...")
    
    ensure_dir(HISTORICAL_CSV_DIR)
    
    # Define seasons and leagues
    seasons = ["2324", "2223", "2122", "2021", "1920"]
    leagues = {
        "E0": "Premier League",
        "SP1": "La Liga",
        "D1": "Bundesliga",
        "I1": "Serie A",
        "F1": "Ligue 1",
    }
    
    base_url = "https://www.football-data.co.uk/mmz4281"
    total_downloaded = 0
    
    for season in seasons:
        for league_code, league_name in leagues.items():
            url = f"{base_url}/{season}/{league_code}.csv"
            filename = f"{league_name.replace(' ', '_')}_{season}.csv"
            filepath = HISTORICAL_CSV_DIR / filename
            
            try:
                logger.info(f"Downloading {league_name} {season}...")
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    # Save raw CSV
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    # Verify it's valid CSV
                    df = pd.read_csv(filepath)
                    logger.info(f"✓ {league_name} {season}: {len(df)} matches")
                    total_downloaded += len(df)
                else:
                    logger.warning(f"⚠ {league_name} {season}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"✗ Error downloading {league_name} {season}: {str(e)}")
    
    logger.info(f"Total matches downloaded: {total_downloaded}")
    return total_downloaded


def create_sample_data():
    """Create sample data if downloads fail."""
    logger.info("Creating sample data...")
    
    ensure_dir(HISTORICAL_CSV_DIR)
    
    # Create sample matches
    sample_data = {
        'match_id': range(1, 101),
        'home_team': ['Team A', 'Team B'] * 50,
        'away_team': ['Team C', 'Team D'] * 50,
        'home_score': [2, 1, 3, 0, 1] * 20,
        'away_score': [1, 1, 2, 2, 0] * 20,
        'date': pd.date_range('2024-01-01', periods=100, freq='3D'),
        'competition': ['Premier League'] * 100,
        'status': ['FINISHED'] * 100,
    }
    
    df = pd.DataFrame(sample_data)
    
    # Add result column
    df['result'] = df.apply(
        lambda row: 'home_win' if row['home_score'] > row['away_score']
        else ('away_win' if row['home_score'] < row['away_score'] else 'draw'),
        axis=1
    )
    
    # Save sample data
    filepath = HISTORICAL_CSV_DIR / "sample_matches.csv"
    df.to_csv(filepath, index=False)
    
    logger.info(f"✓ Created sample data: {len(df)} matches")
    logger.info(f"  Saved to: {filepath}")
    
    return len(df)


def normalize_downloaded_data():
    """Normalize downloaded CSV files to standard format."""
    logger.info("Normalizing downloaded data...")
    
    csv_files = list(HISTORICAL_CSV_DIR.glob("*.csv"))
    
    if not csv_files:
        logger.warning("No CSV files found to normalize")
        return
    
    for csv_file in csv_files:
        if "normalized" in csv_file.name:
            continue
            
        try:
            logger.info(f"Processing {csv_file.name}...")
            df = pd.read_csv(csv_file)
            
            # Map football-data.co.uk columns to our schema
            column_mapping = {
                'Date': 'date',
                'HomeTeam': 'home_team',
                'AwayTeam': 'away_team',
                'FTHG': 'home_score',  # Full Time Home Goals
                'FTAG': 'away_score',  # Full Time Away Goals
                'FTR': 'result_code',  # Full Time Result (H/D/A)
                'Div': 'competition',
            }
            
            # Rename columns if they exist
            df_normalized = df.rename(columns=column_mapping)
            
            # Add required columns
            if 'match_id' not in df_normalized.columns:
                df_normalized['match_id'] = range(1, len(df_normalized) + 1)
            
            if 'status' not in df_normalized.columns:
                df_normalized['status'] = 'FINISHED'
            
            # Convert result code to our format
            if 'result_code' in df_normalized.columns:
                df_normalized['result'] = df_normalized['result_code'].map({
                    'H': 'home_win',
                    'D': 'draw',
                    'A': 'away_win'
                })
            
            # Select only columns we need
            required_cols = ['match_id', 'home_team', 'away_team', 'home_score', 
                           'away_score', 'date', 'competition', 'status', 'result']
            
            available_cols = [col for col in required_cols if col in df_normalized.columns]
            df_final = df_normalized[available_cols]
            
            # Save normalized version
            output_file = HISTORICAL_CSV_DIR / f"normalized_{csv_file.name}"
            df_final.to_csv(output_file, index=False)
            
            logger.info(f"✓ Normalized {csv_file.name}: {len(df_final)} matches")
            
        except Exception as e:
            logger.error(f"✗ Error normalizing {csv_file.name}: {str(e)}")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("DOWNLOAD SAMPLE HISTORICAL DATA")
    print("="*80)
    
    print("\nThis script will:")
    print("1. Download historical match data from football-data.co.uk (free)")
    print("2. Normalize the data to match our schema")
    print("3. Create sample data if downloads fail")
    print(f"\nData will be saved to: {HISTORICAL_CSV_DIR}")
    
    choice = input("\nChoose option:\n1. Download real data\n2. Create sample data\n3. Both\n> ")
    
    total_matches = 0
    
    if choice in ["1", "3"]:
        print("\n" + "="*80)
        print("Downloading real historical data...")
        print("="*80)
        total_matches += download_football_data_uk()
        normalize_downloaded_data()
    
    if choice in ["2", "3"]:
        print("\n" + "="*80)
        print("Creating sample data...")
        print("="*80)
        total_matches += create_sample_data()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total matches available: {total_matches}")
    print(f"Data location: {HISTORICAL_CSV_DIR}")
    
    csv_files = list(HISTORICAL_CSV_DIR.glob("*.csv"))
    print(f"\nFiles created: {len(csv_files)}")
    for f in csv_files[:10]:  # Show first 10
        print(f"  - {f.name}")
    if len(csv_files) > 10:
        print(f"  ... and {len(csv_files) - 10} more")
    
    print("\nNext steps:")
    print("1. Run: python -m etl.transform")
    print("2. Run: python -m etl.load_to_db")
    print("3. Run: python -m models.train_model")
    print("="*80)


if __name__ == "__main__":
    main()
