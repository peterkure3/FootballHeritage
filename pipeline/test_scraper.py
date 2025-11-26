#!/usr/bin/env python3
"""Test script for the Basketball Reference scraper."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.fetch_basketball_reference import BasketballReferenceScraper

def test_scraper():
    """Test the scraper with a single season."""
    scraper = None
    try:
        print("Initializing scraper...")
        scraper = BasketballReferenceScraper()
        
        # Test with just the 2024 season
        print("Testing with 2024-25 season...")
        games = scraper.get_season_schedule(2024)
        
        if games:
            print(f"Successfully fetched {len(games)} games!")
            print("\nSample game:")
            print(games[0])
            
            # Save the test data
            output_file = scraper.save_games_to_json(games, 2024)
            if output_file:
                print(f"\nSaved test data to: {output_file}")
        else:
            print("No games found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if scraper:
            scraper.close()
        print("Test completed!")

if __name__ == "__main__":
    test_scraper()
