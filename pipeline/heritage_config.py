"""
Configuration for football_heritage database.
Use this to connect to the heritage database instead of the main one.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
_dotenv_path = Path(__file__).resolve().parent / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path)
else:
    load_dotenv()

# Database Configuration for Heritage DB
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = "football_heritage"  # Different database name

# Build database URI
DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Display connection info (without password)
def get_connection_info():
    """Get connection info for display."""
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "database": DB_NAME,
        "uri": f"postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    }


if __name__ == "__main__":
    print("Football Heritage Database Configuration")
    print("=" * 50)
    info = get_connection_info()
    for key, value in info.items():
        print(f"{key:12}: {value}")
