import db_config
from faker import Faker
import random
import time
import sys
import psycopg2 

# Configuration
BATCH_SIZE = 10
DELAY_SECONDS = 5
INITIAL_POPULATION = 100 # Reduced for faster debug
fake = Faker('en_IN')

# Mock data generation
def generate_applicant():
    # Simplified for debug
    return {
        'FirstName': fake.first_name(), 'LastName': fake.last_name(), 'Age': random.randint(21, 65),
        'Email': fake.email(), 'Address': fake.address().replace('\n', ', '), 'PhoneNumber': fake.phone_number(),
        'MaidenName': None, 'SocialMediaHandle': None, 'LastLoginIP': fake.ipv4(), 'LoyaltyPoints': 0,
        'EmploymentStatus': 'Salaried', 'JobTitle': 'Engineer', 'YearsExperience': 5
    }

def generate_financials(estatus):
    return {
        'AnnualIncome': 500000.0, 'CreditScore': 750, 'ExistingDebt': 0.0, 'DebtToIncomeRatio': 0.0,
        'CollateralValue': 0.0, 'CollateralType': 'None', 'AccountAgeDays': 100,
        'AvgTransactionCount': 10, 'LastBranchVisited': 'Online'
    }

def generate_loan_request(income, col):
    return {
        'RequestAmount': 100000.0, 'LoanPurpose': 'Personal', 'LoanToCostRatio': 0.5,
        'ApplicationSource': 'App', 'ReferralCode': None, 'ProcessingPriority': 1
    }

def generate_bulk_data(conn):
    print("DEBUG: INSIDE generate_bulk_data")
    try:
        cursor = conn.cursor()
        print(f"DEBUG: Starting loop for {INITIAL_POPULATION} records...")
        
        for i in range(10): # Just 10 to test first
            try:
                # Direct SQL for debugging speed
                cursor.execute("""
                    INSERT INTO Applicants (FirstName, LastName, Age, Email, Address, PhoneNumber, EmploymentStatus, JobTitle, YearsExperience) 
                    VALUES (%s, 'TestUser', 25, 'test@example.com', '123 Test Lane', '9999999999', 'Salaried', 'Tester', 2)
                    RETURNING ApplicantID
                """, (f"User{i}",))
                app_id = cursor.fetchone()[0]
                
                cursor.execute("""
                    INSERT INTO FinancialProfile (ApplicantID, AnnualIncome, CreditScore, ExistingDebt) 
                    VALUES (%s, 500000, 750, 0)
                """, (app_id,))
                
                cursor.execute("""
                    INSERT INTO LoanApplications (ApplicantID, RequestAmount, Status) 
                    VALUES (%s, 100000, 'Pending')
                """, (app_id,))
                
                print(f"DEBUG: Inserted User {i} (ID: {app_id})")
                
            except Exception as e:
                print(f"DEBUG: ERROR inserting row {i}: {e}")
                
        conn.commit()
        print("DEBUG: Generation Complete! Data Committed.")
    except Exception as exc:
        print(f"DEBUG: Global Error: {exc}")

if __name__ == '__main__':
    print("DEBUG: Script Started")
    print(f"DEBUG: Arguments: {sys.argv}")
    
    # Force run regardless of args for now to debug
    print("DEBUG: Connecting to DB...")
    conn = db_config.get_connection()
    print(f"DEBUG: Connection Object: {conn}")
    
    if not conn:
        print("DEBUG: Connection failed. Exiting with Error 1.")
        sys.exit(1) # Force Red X
    
    print("DEBUG: Calling generate_bulk_data...")
    generate_bulk_data(conn)
    conn.close()
    print("DEBUG: Script Finished Successfully.")
