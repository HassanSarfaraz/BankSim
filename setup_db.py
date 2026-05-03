#!/usr/bin/env python3
"""
SecureBank — One-click database setup.
Creates the database (if needed), loads schema, stored procedures,
triggers, views, indexes, then seeds sample data.

Usage:  python setup_db.py
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'securebank')

SQL_FILES = [
    'db/schema.sql',
    'db/stored_procedures.sql',
    'db/triggers.sql',
    'db/views.sql',
    'db/indexes.sql',
]


def get_conn(dbname='postgres'):
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        dbname=dbname
    )


def create_database():
    """Create the securebank database if it doesn't exist."""
    conn = get_conn('postgres')
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone():
        print(f"  ✓ Database '{DB_NAME}' already exists")
    else:
        cur.execute(f'CREATE DATABASE {DB_NAME}')
        print(f"  ✓ Database '{DB_NAME}' created")
    cur.close()
    conn.close()


def run_sql_file(filepath):
    """Execute a .sql file against the securebank database."""
    if not os.path.exists(filepath):
        print(f"  ⚠ Skipping {filepath} (file not found)")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()

    conn = get_conn(DB_NAME)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(sql)
        print(f"  ✓ {filepath}")
    except Exception as e:
        print(f"  ✗ {filepath}: {e}")
    finally:
        cur.close()
        conn.close()


def main():
    print("=" * 50)
    print("  SecureBank — Database Setup")
    print("=" * 50)
    print(f"  Host: {DB_HOST}:{DB_PORT}  User: {DB_USER}")
    print()

    # Step 1: Create database
    print("[1/3] Creating database...")
    try:
        create_database()
    except Exception as e:
        print(f"  ✗ Cannot connect to PostgreSQL: {e}")
        print()
        print("  Make sure PostgreSQL is running and your .env credentials are correct.")
        sys.exit(1)

    # Step 2: Run SQL files
    print()
    print("[2/3] Loading SQL scripts...")
    for filepath in SQL_FILES:
        run_sql_file(filepath)

    # Step 3: Seed data
    print()
    print("[3/3] Seeding sample data...")
    try:
        from seed_db import run as seed_run
        seed_run()
    except Exception as e:
        print(f"  ✗ Seeding failed: {e}")
        sys.exit(1)

    print()
    print("=" * 50)
    print("  ✅ Database setup complete!")
    print()
    print("  Next steps:")
    print("    1. python -m backend.app     (start API)")
    print("    2. python -m frontend.main   (start GUI)")
    print("=" * 50)


if __name__ == '__main__':
    main()
