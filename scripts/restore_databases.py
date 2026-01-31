"""
Database Restore Script for Football Heritage
Restores both pipeline (football_betting) and backend (football_heritage) databases from backup.

Usage:
    python restore_databases.py --backup-dir /path/to/backups/20260131_170000
    python restore_databases.py --backup-dir /path/to/backups/20260131_170000 --db-password yourpassword
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def find_psql():
    """Find psql executable."""
    # Common PostgreSQL installation paths on Windows
    possible_paths = [
        r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
        r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
        r"C:\Program Files\PostgreSQL\14\bin\psql.exe",
        r"C:\Program Files\PostgreSQL\13\bin\psql.exe",
        r"C:\Program Files\PostgreSQL\12\bin\psql.exe",
    ]
    
    # Check if psql is in PATH
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "psql"
    except FileNotFoundError:
        pass
    
    # Check common installation paths
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def create_database_if_not_exists(psql: str, db_name: str, host: str, port: str, user: str, env: dict) -> bool:
    """Create database if it doesn't exist."""
    # Check if database exists
    check_cmd = [
        psql,
        "-h", host,
        "-p", port,
        "-U", user,
        "-d", "postgres",
        "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"
    ]
    
    result = subprocess.run(check_cmd, env=env, capture_output=True, text=True)
    
    if result.stdout.strip() == "1":
        print(f"  Database '{db_name}' already exists")
        return True
    
    # Create database
    create_cmd = [
        psql,
        "-h", host,
        "-p", port,
        "-U", user,
        "-d", "postgres",
        "-c", f"CREATE DATABASE {db_name};"
    ]
    
    result = subprocess.run(create_cmd, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  ✅ Created database '{db_name}'")
        return True
    else:
        print(f"  ❌ Failed to create database: {result.stderr}")
        return False


def drop_database_if_exists(psql: str, db_name: str, host: str, port: str, user: str, env: dict) -> bool:
    """Drop database if it exists (for clean restore)."""
    # Terminate connections
    terminate_cmd = [
        psql,
        "-h", host,
        "-p", port,
        "-U", user,
        "-d", "postgres",
        "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}' AND pid <> pg_backend_pid();"
    ]
    subprocess.run(terminate_cmd, env=env, capture_output=True, text=True)
    
    # Drop database
    drop_cmd = [
        psql,
        "-h", host,
        "-p", port,
        "-U", user,
        "-d", "postgres",
        "-c", f"DROP DATABASE IF EXISTS {db_name};"
    ]
    
    result = subprocess.run(drop_cmd, env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  ✅ Dropped existing database '{db_name}'")
        return True
    else:
        print(f"  ⚠️  Could not drop database: {result.stderr}")
        return False


def restore_database(backup_file: Path, db_name: str, host: str, port: str, user: str, password: str, clean: bool) -> bool:
    """
    Restore a database from a SQL dump file.
    
    Args:
        backup_file: Path to the SQL backup file
        db_name: Name of the database to restore
        host: Database host
        port: Database port
        user: Database user
        password: Database password
        clean: If True, drop and recreate the database
        
    Returns:
        True if restore succeeded, False otherwise
    """
    psql = find_psql()
    if not psql:
        print("ERROR: psql not found. Please install PostgreSQL or add it to PATH.")
        print("Download from: https://www.postgresql.org/download/")
        return False
    
    print(f"\n{'='*60}")
    print(f"Restoring: {db_name}")
    print(f"From: {backup_file}")
    print(f"{'='*60}")
    
    # Set password in environment
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    
    # Drop and recreate if clean restore
    if clean:
        print("  Performing clean restore (dropping existing database)...")
        drop_database_if_exists(psql, db_name, host, port, user, env)
    
    # Create database if it doesn't exist
    if not create_database_if_not_exists(psql, db_name, host, port, user, env):
        return False
    
    # Restore from backup
    print(f"  Restoring data from backup...")
    restore_cmd = [
        psql,
        "-h", host,
        "-p", port,
        "-U", user,
        "-d", db_name,
        "-f", str(backup_file),
    ]
    
    try:
        result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ SUCCESS: Database '{db_name}' restored successfully")
            return True
        else:
            # Check if it's just warnings (common with pg_dump restores)
            if "ERROR" in result.stderr:
                print(f"❌ FAILED: {result.stderr}")
                return False
            else:
                print(f"✅ SUCCESS: Database '{db_name}' restored (with warnings)")
                return True
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def find_backup_files(backup_dir: Path) -> dict:
    """Find backup files in the specified directory."""
    backup_files = {}
    
    for sql_file in backup_dir.glob("*.sql"):
        if sql_file.name.startswith("football_betting_"):
            backup_files["football_betting"] = sql_file
        elif sql_file.name.startswith("football_heritage_"):
            backup_files["football_heritage"] = sql_file
    
    return backup_files


def main():
    parser = argparse.ArgumentParser(description="Restore Football Heritage databases from backup")
    parser.add_argument(
        "--backup-dir", "-b",
        type=Path,
        required=True,
        help="Directory containing backup files"
    )
    parser.add_argument(
        "--db-host",
        type=str,
        default=os.getenv("DB_HOST", "localhost"),
        help="Database host (default: localhost)"
    )
    parser.add_argument(
        "--db-port",
        type=str,
        default=os.getenv("DB_PORT", "5432"),
        help="Database port (default: 5432)"
    )
    parser.add_argument(
        "--db-user",
        type=str,
        default=os.getenv("DB_USER", "postgres"),
        help="Database user (default: postgres)"
    )
    parser.add_argument(
        "--db-password", "-p",
        type=str,
        default=os.getenv("DB_PASSWORD", ""),
        help="Database password (or set DB_PASSWORD env var)"
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Drop existing databases before restore (clean restore)"
    )
    parser.add_argument(
        "--database", "-d",
        type=str,
        choices=["football_betting", "football_heritage", "all"],
        default="all",
        help="Which database to restore (default: all)"
    )
    args = parser.parse_args()
    
    # Validate backup directory
    if not args.backup_dir.exists():
        print(f"ERROR: Backup directory not found: {args.backup_dir}")
        sys.exit(1)
    
    # Find backup files
    backup_files = find_backup_files(args.backup_dir)
    
    if not backup_files:
        print(f"ERROR: No backup files found in {args.backup_dir}")
        print("Expected files: football_betting_*.sql, football_heritage_*.sql")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("  Football Heritage Database Restore")
    print("=" * 60)
    print(f"Backup directory: {args.backup_dir}")
    print(f"Clean restore: {'Yes' if args.clean else 'No'}")
    print(f"\nFound backup files:")
    for db_name, file_path in backup_files.items():
        print(f"  - {db_name}: {file_path.name}")
    
    if args.clean:
        print("\n⚠️  WARNING: Clean restore will DELETE existing data!")
        response = input("Continue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Restore cancelled.")
            sys.exit(0)
    
    # Restore databases
    results = {}
    
    databases_to_restore = (
        list(backup_files.keys()) if args.database == "all" 
        else [args.database] if args.database in backup_files 
        else []
    )
    
    if not databases_to_restore:
        print(f"ERROR: No backup file found for database '{args.database}'")
        sys.exit(1)
    
    for db_name in databases_to_restore:
        if db_name in backup_files:
            success = restore_database(
                backup_file=backup_files[db_name],
                db_name=db_name,
                host=args.db_host,
                port=args.db_port,
                user=args.db_user,
                password=args.db_password,
                clean=args.clean
            )
            results[db_name] = success
    
    # Summary
    print("\n" + "=" * 60)
    print("  Restore Summary")
    print("=" * 60)
    
    success_count = sum(1 for s in results.values() if s)
    total_count = len(results)
    
    for db_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {db_name}")
    
    print(f"\nTotal: {success_count}/{total_count} databases restored successfully")
    
    if success_count < total_count:
        print("\n⚠️  Some restores failed. Check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ All databases restored successfully!")
        print("\nNext steps:")
        print("  1. Start the backend: cd backend && cargo run")
        print("  2. Start the pipeline API: cd pipeline && python -m api.main")
        sys.exit(0)


if __name__ == "__main__":
    main()
