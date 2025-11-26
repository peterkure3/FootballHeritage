#!/usr/bin/env python3
"""Performance comparison test for different scraper implementations."""

import sys
import os
import time
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etl.fetch_basketball_reference import BasketballReferenceScraper
from etl.fetch_basketball_reference_async import AsyncBasketballReferenceScraper

def test_sync_scraper():
    """Test the original synchronous scraper."""
    print("\n🐌 Testing Synchronous Scraper...")
    scraper = None
    try:
        start_time = time.time()
        scraper = BasketballReferenceScraper()
        games = scraper.get_season_schedule(2024)
        elapsed_time = time.time() - start_time
        print(f"✅ Sync: {len(games)} games in {elapsed_time:.1f}s")
        return elapsed_time, len(games)
    except Exception as e:
        print(f"❌ Sync error: {e}")
        return None, None
    finally:
        if scraper:
            scraper.close()

async def test_async_scraper():
    """Test the new asynchronous scraper."""
    print("\n🚀 Testing Asynchronous Scraper...")
    try:
        start_time = time.time()
        async with AsyncBasketballReferenceScraper() as scraper:
            games = await scraper.get_season_schedule(2024)
            elapsed_time = time.time() - start_time
            print(f"✅ Async: {len(games)} games in {elapsed_time:.1f}s")
            return elapsed_time, len(games)
    except Exception as e:
        print(f"❌ Async error: {e}")
        return None, None

def main():
    """Run performance comparison."""
    print("🏁 Performance Comparison Test")
    print("=" * 50)
    
    # Test synchronous version
    sync_time, sync_games = test_sync_scraper()
    
    # Test asynchronous version
    async_time, async_games = asyncio.run(test_async_scraper())
    
    # Compare results
    print("\n📊 Performance Comparison")
    print("=" * 50)
    
    if sync_time and async_time:
        speedup = sync_time / async_time
        print(f"Synchronous:  {sync_time:.1f}s ({sync_games} games)")
        print(f"Asynchronous: {async_time:.1f}s ({async_games} games)")
        print(f"Speedup:       {speedup:.1f}x faster")
        
        if speedup > 1:
            print(f"🎉 Async is {speedup:.1f}x faster!")
        else:
            print(f"⚠️  Async is {1/speedup:.1f}x slower")
    else:
        print("❌ Could not complete comparison")

if __name__ == "__main__":
    main()
