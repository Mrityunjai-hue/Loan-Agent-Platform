import os
import psycopg2
import sys

# Default to a placeholder if env var not set (User must set this in Cloud)
# Example Supabase URL: postgres://postgres:password@db.supabase.co:5432/postgres
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        print("Please set it in your .env file or Cloud Environment Secrets.")
        return None
    
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return None
