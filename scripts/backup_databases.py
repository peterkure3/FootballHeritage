"""
Database Backup Script for Football Heritage
Backs up both pipeline (football_betting) and backend (football_heritage) databases.

Usage:
    python backup_databases.py
    python backup_databases.py --output-dir /path/to/backups
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# Default backup directory
DEFAULT_BACKUP_DIR = Path(__file__).parent.parent / "backups"

# Database configurations
DATABASES = [
    {
        "name": "football_betting",
        "description": "Pipeline database (matches, odds, predictions)",
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    },
    {
        "name": "football_heritage",
        "description": "Backend database (users, wallets, bets, events)",
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    },
]


def find_pg_dump():
    """Find pg_dump executable."""
    # Common PostgreSQL installation paths on Windows
    possible_paths = [
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\13\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\12\bin\pg_dump.exe",
    ]
    
    # Check if pg_dump is in PATH
    try:
        result = subprocess.run(["pg_dump", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "pg_dump"
    except FileNotFoundError:
        pass
    
    # Check common installation paths
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def backup_database(db_config: dict, output_dir: Path, timestamp: str) -> bool:
    """
    Backup a single database using pg_dump.
    
    Args:
        db_config: Database configuration dictionary
        output_dir: Directory to save backup files
        timestamp: Timestamp string for filename
        
    Returns:
        True if backup succeeded, False otherwise
    """
    pg_dump = find_pg_dump()
    if not pg_dump:
        print("ERROR: pg_dump not found. Please install PostgreSQL or add it to PATH.")
        print("Download from: https://www.postgresql.org/download/")
        return False
    
    db_name = db_config["name"]
    output_file = output_dir / f"{db_name}_{timestamp}.sql"
    
    print(f"\n{'='*60}")
    print(f"Backing up: {db_name}")
    print(f"Description: {db_config['description']}")
    print(f"Output: {output_file}")
    print(f"{'='*60}")
    
    # Set password in environment
    env = os.environ.copy()
    if db_config["password"]:
        env["PGPASSWORD"] = db_config["password"]
    
    # Build pg_dump command
    cmd = [
        pg_dump,
        "-h", db_config["host"],
        "-p", db_config["port"],
        "-U", db_config["user"],
        "-d", db_name,
        "-F", "p",  # Plain text format
        "--no-owner",  # Don't include ownership commands
        "--no-acl",  # Don't include access privileges
        "-f", str(output_file),
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            file_size = output_file.stat().st_size / 1024  # KB
            print(f"✅ SUCCESS: Backup completed ({file_size:.1f} KB)")
            return True
        else:
            print(f"❌ FAILED: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def create_manifest(output_dir: Path, timestamp: str, results: dict):
    """Create a manifest file with backup details."""
    manifest_file = output_dir / f"backup_manifest_{timestamp}.txt"
    
    with open(manifest_file, "w") as f:
        f.write("Football Heritage Database Backup Manifest\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Backup Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Timestamp: {timestamp}\n\n")
        
        f.write("Databases Backed Up:\n")
        f.write("-" * 30 + "\n")
        
        for db_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            f.write(f"  {db_name}: {status}\n")
        
        f.write("\n\nRestore Instructions:\n")
        f.write("-" * 30 + "\n")
        f.write("1. Ensure PostgreSQL is installed and running\n")
        f.write("2. Run: python scripts/restore_databases.py --backup-dir <this_folder>\n")
        f.write("   Or manually:\n")
        f.write("   psql -U postgres -c \"CREATE DATABASE football_betting;\"\n")
        f.write("   psql -U postgres -d football_betting -f football_betting_<timestamp>.sql\n")
        f.write("   psql -U postgres -c \"CREATE DATABASE football_heritage;\"\n")
        f.write("   psql -U postgres -d football_heritage -f football_heritage_<timestamp>.sql\n")
    
    print(f"\n📄 Manifest created: {manifest_file}")


def main():
    parser = argparse.ArgumentParser(description="Backup Football Heritage databases")
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"Output directory for backups (default: {DEFAULT_BACKUP_DIR})"
    )
    parser.add_argument(
        "--db-password", "-p",
        type=str,
        default=os.getenv("DB_PASSWORD", ""),
        help="Database password (or set DB_PASSWORD env var)"
    )
    args = parser.parse_args()
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = args.output_dir / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 60)
    print("  Football Heritage Database Backup")
    print("=" * 60)
    print(f"Backup directory: {backup_dir}")
    
    # Update password in configs if provided
    if args.db_password:
        for db in DATABASES:
            db["password"] = args.db_password
    
    # Backup each database
    results = {}
    for db_config in DATABASES:
        success = backup_database(db_config, backup_dir, timestamp)
        results[db_config["name"]] = success
    
    # Create manifest
    create_manifest(backup_dir, timestamp, results)
    
    # Summary
    print("\n" + "=" * 60)
    print("  Backup Summary")
    print("=" * 60)
    
    success_count = sum(1 for s in results.values() if s)
    total_count = len(results)
    
    for db_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {db_name}")
    
    print(f"\nTotal: {success_count}/{total_count} databases backed up successfully")
    print(f"Backup location: {backup_dir}")
    
    if success_count < total_count:
        print("\n⚠️  Some backups failed. Check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ All backups completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
