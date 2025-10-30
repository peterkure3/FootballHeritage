"""Fix missing match_ids in processed data."""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from pathlib import Path

processed_dir = Path("data/processed")
matches_file = processed_dir / "matches_2025-10-26.parquet"

# Load data
df = pd.read_parquet(matches_file)

print(f"Total matches: {len(df)}")
print(f"Null match_ids: {df['match_id'].isna().sum()}")
print(f"Null home_team: {df['home_team'].isna().sum()}")
print(f"Null away_team: {df['away_team'].isna().sum()}")

# Generate match_ids for rows that don't have them
if df['match_id'].isna().any():
    print("\nFixing null match_ids...")
    
    # Get max existing match_id
    max_id = df['match_id'].max()
    if pd.isna(max_id):
        max_id = 0
    
    # Assign new IDs to null rows
    null_mask = df['match_id'].isna()
    num_nulls = null_mask.sum()
    
    new_ids = range(int(max_id) + 1, int(max_id) + 1 + num_nulls)
    df.loc[null_mask, 'match_id'] = list(new_ids)
    
    # Convert to int
    df['match_id'] = df['match_id'].astype(int)
    
    # Save fixed data
    df.to_parquet(matches_file, index=False)
    
    print(f"✓ Fixed {num_nulls} null match_ids")
    print(f"✓ New match_id range: {df['match_id'].min()} to {df['match_id'].max()}")
else:
    print("✓ No null match_ids found")

# Remove rows with null critical fields
print("\nCleaning data...")
initial_count = len(df)
df = df.dropna(subset=['home_team', 'away_team', 'home_score', 'away_score'])
removed_count = initial_count - len(df)

if removed_count > 0:
    print(f"✓ Removed {removed_count} rows with missing critical data")
    df.to_parquet(matches_file, index=False)
    print(f"✓ Saved cleaned data: {len(df)} matches")

print(f"\nSample data:")
print(df[['match_id', 'home_team', 'away_team', 'home_score', 'away_score', 'result']].head(10))
