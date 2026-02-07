import os
import sys
import psycopg2
import time

def main():
    print("DEBUG: Starting Self-Contained Diagnosis...")
    
    # 1. Get Secret directly
    url = os.environ.get('DATABASE_URL')
    print(f"DEBUG: Reading DATABASE_URL from Env...")
    
    if not url:
        print("DEBUG: ERROR - DATABASE_URL is None/Empty!")
        sys.exit(1)
        
    print(f"DEBUG: URL found (Length: {len(url)})")
    print(f"DEBUG: Starts with: {url[:10]}...")
    
    # 2. Try Connect
    try:
        print("DEBUG: Attempting psycopg2.connect()...")
        conn = psycopg2.connect(url, sslmode='require')
        print("DEBUG: CONNECTION SUCCESSFUL!")
        
        # 3. Test Query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        v = cursor.fetchone()
        print(f"DEBUG: Success! DB Version: {v}")
        
    except Exception as e:
        print(f"DEBUG: CRITICAL CONNECTION ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
