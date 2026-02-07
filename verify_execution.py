import os
import sys

def check_file_exists(filename):
    if os.path.exists(filename):
        print(f"[OK] Found {filename}")
        return True
    else:
        print(f"[FAIL] Missing {filename}")
        return False

def check_imports():
    print("\nChecking Imports...")
    try:
        import psycopg2
        print("[OK] psycopg2 module found (Postgres Driver)")
    except ImportError:
        print("[FAIL] psycopg2 not found. Run: pip install psycopg2-binary")
        
    try:
        import db_config
        print("[OK] db_config module found")
    except ImportError:
        print("[FAIL] db_config not found or has errors.")
        
    try:
        import generate_data
        print("[OK] generate_data module valid")
    except ImportError as e:
        print(f"[FAIL] generate_data import error: {e}")
        
    try:
        import loan_model
        print("[OK] loan_model module valid")
    except ImportError as e:
        print(f"[FAIL] loan_model import error: {e}")

    try:
        import agent_predictor
        print("[OK] agent_predictor module valid")
    except ImportError as e:
        print(f"[FAIL] agent_predictor import error: {e}")

def main():
    print("--- Verifying CLOUD Version Files ---")
    files = [
        "setup_postgres.sql",
        "generate_data.py", 
        "agent_predictor.py", 
        "loan_model.py", 
        "app.py",
        "requirements.txt",
        "db_config.py"
    ]
    
    all_exist = True
    for f in files:
        if not check_file_exists(f):
            all_exist = False
            
    if all_exist:
        check_imports()
        print("\n--- READY FOR CLOUD DEPLOYMENT ---")
        print("1. Push this folder to GitHub context or as a new repo.")
        print("2. Connect Supabase & Streamlit.")
    else:
        print("\n[ERROR] Some cloud files are missing.")

if __name__ == "__main__":
    main()
