import os
import sys
import psycopg2
import socket
from urllib.parse import urlparse 
import random

def main():
    print("DEBUG: Starting IPv4 Forced Script...")
    
    url = os.environ.get('DATABASE_URL')
    if not url:
        print("Error: No Secret")
        sys.exit(1)
        
    # Parse URL
    result = urlparse(url)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port
    
    # Force IPv4 Resolution
    print(f"DEBUG: Resolving {hostname}...")
    try:
        ipv4_ip = socket.gethostbyname(hostname)
        print(f"DEBUG: Resolved to {ipv4_ip} (IPv4)")
    except Exception as e:
        print(f"DEBUG: DNS Resolution Failed: {e}")
        sys.exit(1)
    
    try:
        # Pass BOTH host (for SSL) and hostaddr (for network path)
        print("DEBUG: Connecting with forced IPv4...")
        conn = psycopg2.connect(
            host=hostname,
            hostaddr=ipv4_ip,
            user=username,
            password=password,
            dbname=database,
            port=port,
            sslmode='require'
        )
        print("DEBUG: CONNECTION SUCCESSFUL!")
        
        # INSERT DATA (50 Records)
        cursor = conn.cursor()
        print("DEBUG: Inserting 50 test records...")
        
        counts = 0
        for i in range(50):
            try:
                # Randomize slightly so dashboards look real
                status = random.choice(['Salaried', 'Self-Employed'])
                income = random.randint(300000, 2000000)
                
                cursor.execute("""
                    INSERT INTO Applicants (FirstName, LastName, Age, Email, Address, PhoneNumber, EmploymentStatus, JobTitle, YearsExperience) 
                    VALUES (%s, 'CloudUser', 30, 'cloud@test.com', 'Supabase Cloud', '1234567890', %s, 'Tester', 5)
                    RETURNING ApplicantID
                """, (f"GenUser_{i}", status))
                app_id = cursor.fetchone()[0]
                
                cursor.execute("""
                    INSERT INTO FinancialProfile (ApplicantID, AnnualIncome, CreditScore, ExistingDebt, DebtToIncomeRatio, CollateralValue, CollateralType, AccountAgeDays, AvgTransactionCount, LastBranchVisited) 
                    VALUES (%s, %s, 750, 0, 0, 0, 'None', 100, 10, 'Online')
                """, (app_id, income))
                
                cursor.execute("""
                    INSERT INTO LoanApplications (ApplicantID, RequestAmount, Status) 
                    VALUES (%s, 100000, 'Pending')
                """, (app_id,))
                counts += 1
            except Exception as e:
                print(f"Row Error: {e}")
                
        conn.commit()
        conn.close()
        print(f"DEBUG: SUCCESS! Inserted {counts} records.")
        
    except Exception as e:
        print(f"DEBUG: ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
