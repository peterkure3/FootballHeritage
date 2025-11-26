#!/usr/bin/env python3
"""Test script for the parallel Basketball Reference scraper."""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.fetch_basketball_reference_parallel import ParallelBasketballReferenceScraper

def test_parallel_scraper():
    """Test the parallel scraper with a single season."""
    scraper = None
    try:
        print("🚀 Initializing parallel scraper...")
        start_time = time.time()
        scraper = ParallelBasketballReferenceScraper()
        
        # Test with just the 2024 season
        print("📊 Testing with 2024-25 season (parallel processing)...")
        games = scraper.get_season_schedule(2024)
        
        if games:
            elapsed_time = time.time() - start_time
            print(f"✅ Successfully fetched {len(games)} games in {elapsed_time:.1f}s!")
            print("\n📋 Sample game:")
            print(games[0])
            
            # Save the test data
            output_file = scraper.save_games_to_json(games, 2024)
            if output_file:
                print(f"\n💾 Saved test data to: {output_file}")
        else:
            print("❌ No games found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if scraper:
            scraper.close()
        print("🏁 Test completed!")

if __name__ == "__main__":
    test_parallel_scraper()
