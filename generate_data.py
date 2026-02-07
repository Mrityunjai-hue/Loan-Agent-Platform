import db_config
from faker import Faker
import random
import time
import sys

# Configuration
BATCH_SIZE = 10  # Generate 10 at a time
DELAY_SECONDS = 5 # Wait 5 seconds between batches for demo purposes
INITIAL_POPULATION = 200

# Initialize Faker with Indian Locale
fake = Faker('en_IN')

def generate_applicant():
    return {
        'FirstName': fake.first_name(),
        'LastName': fake.last_name(),
        'Age': random.randint(21, 65),
        'Email': fake.email(),
        'Address': fake.address().replace('\n', ', '),
        'PhoneNumber': fake.phone_number(),
        'MaidenName': fake.last_name() if random.random() < 0.3 else None,
        'SocialMediaHandle': '@' + fake.user_name() if random.random() < 0.6 else None,
        'LastLoginIP': fake.ipv4(),
        'LoyaltyPoints': random.randint(0, 5000),
        'EmploymentStatus': random.choice(['Salaried', 'Self-Employed', 'Unemployed', 'Retired']),
        'JobTitle': fake.job(),
        'YearsExperience': random.randint(0, 40)
    }

def generate_financials(employment_status):
    # Income in INR (Annual)
    if employment_status == 'Unemployed':
        income = random.uniform(0, 100000) # 0 to 1 Lakh
        credit_score = random.randint(300, 650)
    else:
        income = random.uniform(300000, 3000000) # 3 Lakhs to 30 Lakhs
        credit_score = random.randint(550, 850) # CIBIL typically 300-900, scaled here
    
    existing_debt = random.uniform(0, income * 0.4)
    dti = (existing_debt / income) if income > 0 else 0
    
    return {
        'AnnualIncome': round(income, 2),
        'CreditScore': credit_score,
        'ExistingDebt': round(existing_debt, 2),
        'DebtToIncomeRatio': round(dti, 2),
        'CollateralValue': round(random.uniform(0, 5000000), 2), # Up to 50 Lakhs
        'CollateralType': random.choice(['Residential Property', 'Vehicle', 'Fixed Deposits', 'Gold', 'None']),
        'AccountAgeDays': random.randint(100, 5000),
        'AvgTransactionCount': random.randint(5, 100),
        'LastBranchVisited': fake.city() + " Branch"
    }

def generate_loan_request(income, collateral):
    # Loan Request in INR
    max_reasonable = (income * 4) + (collateral * 0.7)
    request_amount = random.uniform(50000, max(100000, max_reasonable)) # Min 50k
    purpose = random.choice(['Home Purchase', 'Business Expansion', 'Higher Education', 'Medical Emergency', 'Personal Loan'])
    
    total_asset_value = request_amount + collateral
    ltc = request_amount / total_asset_value if total_asset_value > 0 else 1.0

    return {
        'RequestAmount': round(request_amount, 2),
        'LoanPurpose': purpose,
        'LoanToCostRatio': round(ltc, 2),
        'ApplicationSource': random.choice(['Mobile App', 'Website', 'Branch Referral', 'Partner']),
        'ReferralCode': fake.bothify(text='REF-####-????') if random.random() < 0.2 else None,
        'ProcessingPriority': random.randint(1, 10)
    }

def update_existing_applicant(cursor):
    """
    Randomly selects an existing applicant and updates their financial profile
    to simulate a change in circumstances (Raise, New Debt, etc.),
    and flags them for Re-evaluation.
    """
    try:
        # Pick a random applicant (Postgres syntax for Random Sort)
        cursor.execute("SELECT ApplicantID, EmploymentStatus FROM Applicants ORDER BY RANDOM() LIMIT 1")
        row = cursor.fetchone()
        
        if not row:
            return None # No applicants yet
            
        app_id, emp_status = row
        
        # Generate varied financial data (simulating change)
        if random.random() < 0.1: # 10% chance to change employment status
            emp_status = random.choice(['Salaried', 'Self-Employed', 'Unemployed', 'Retired'])
            cursor.execute("UPDATE Applicants SET EmploymentStatus = %s WHERE ApplicantID = %s", (emp_status, app_id))
            
        fin_data = generate_financials(emp_status)
        
        # Update Financial Table
        cursor.execute("""
            UPDATE FinancialProfile 
            SET AnnualIncome = %s, CreditScore = %s, ExistingDebt = %s, DebtToIncomeRatio = %s, CollateralValue = %s, CollateralType = %s,
                AccountAgeDays = %s, AvgTransactionCount = %s, LastBranchVisited = %s
            WHERE ApplicantID = %s
        """, (fin_data['AnnualIncome'], fin_data['CreditScore'], fin_data['ExistingDebt'], 
             fin_data['DebtToIncomeRatio'], fin_data['CollateralValue'], fin_data['CollateralType'],
             fin_data['AccountAgeDays'], fin_data['AvgTransactionCount'], fin_data['LastBranchVisited'], app_id))
             
        # CRITICAL: Reset Status to 'Pending' so the Prediction Agent re-evaluates
        # UPDATE: Also update Request Amount to make it dynamic as per User Request
        new_loan_data = generate_loan_request(fin_data['AnnualIncome'], fin_data['CollateralValue'])
        
        cursor.execute("""
            UPDATE LoanApplications 
            SET Status = 'Pending', RequestAmount = %s, LoanToCostRatio = %s 
            WHERE ApplicantID = %s
        """, (new_loan_data['RequestAmount'], new_loan_data['LoanToCostRatio'], app_id))
        
        return app_id
    except Exception as e:
        print(f"Error updating applicant: {e}")
        return None

def main():
    print("Starting Continuous Data Generation Agent (Simulating Days)...")
    print("This agent will generate new applicants AND update old ones to trigger re-evaluation.")
    print("Press Ctrl+C to stop.")
    
    day_count = 1
    
    while True:
        conn = db_config.get_connection()
        if not conn:
            print("Waiting for Database Config...")
            time.sleep(10)
            continue
            
        cursor = conn.cursor()
        
        try:
            print(f"\n--- Day {day_count} ---")
            
            # 1. Generate NEW Applicants (Morning Batch)
            print(f"Generating batch of {BATCH_SIZE} NEW applicants...")
            for _ in range(BATCH_SIZE):
                # Applicant
                app_data = generate_applicant()
                cursor.execute("""
                    INSERT INTO Applicants (FirstName, LastName, Age, Email, Address, PhoneNumber, MaidenName, SocialMediaHandle, LastLoginIP, LoyaltyPoints, EmploymentStatus, JobTitle, YearsExperience) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING ApplicantID
                """, (app_data['FirstName'], app_data['LastName'], app_data['Age'], app_data['Email'], app_data['Address'], app_data['PhoneNumber'],
                     app_data['MaidenName'], app_data['SocialMediaHandle'], app_data['LastLoginIP'], app_data['LoyaltyPoints'],
                     app_data['EmploymentStatus'], app_data['JobTitle'], app_data['YearsExperience']))
                
                applicant_id = cursor.fetchone()[0]

                # Financials
                fin_data = generate_financials(app_data['EmploymentStatus'])
                cursor.execute("""
                    INSERT INTO FinancialProfile (ApplicantID, AnnualIncome, CreditScore, ExistingDebt, DebtToIncomeRatio, CollateralValue, CollateralType, AccountAgeDays, AvgTransactionCount, LastBranchVisited)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (applicant_id, fin_data['AnnualIncome'], fin_data['CreditScore'], fin_data['ExistingDebt'], 
                     fin_data['DebtToIncomeRatio'], fin_data['CollateralValue'], fin_data['CollateralType'],
                     fin_data['AccountAgeDays'], fin_data['AvgTransactionCount'], fin_data['LastBranchVisited']))

                # Loan Request
                loan_data = generate_loan_request(fin_data['AnnualIncome'], fin_data['CollateralValue'])
                cursor.execute("""
                    INSERT INTO LoanApplications (ApplicantID, RequestAmount, LoanPurpose, LoanToCostRatio, ApplicationSource, ReferralCode, ProcessingPriority)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (applicant_id, loan_data['RequestAmount'], loan_data['LoanPurpose'], loan_data['LoanToCostRatio'],
                     loan_data['ApplicationSource'], loan_data['ReferralCode'], loan_data['ProcessingPriority']))

            # 2. Update EXISTING Applicants (Afternoon Events)
            update_count = random.randint(2, 5)
            print(f"Updating {update_count} existing applicants (Re-evaluation triggers)...")
            updated_ids = []
            for _ in range(update_count):
                uid = update_existing_applicant(cursor)
                if uid: updated_ids.append(uid)
                
            conn.commit()
            print(f"Day {day_count} Complete. New: {BATCH_SIZE}, Updated: {len(updated_ids)} (IDs: {updated_ids})")
            print(f"Sleeping for {DELAY_SECONDS} seconds to simulate night...")
            
            day_count += 1
            cursor.close()
            conn.close()
            time.sleep(DELAY_SECONDS)
            
        except Exception as e:
            print(f"Error in generation loop: {e}")
            if conn: conn.close()
            time.sleep(5)

def generate_bulk_data(conn):
    cursor = conn.cursor()
    print(f"--- INITIALIZING WORLD WITH {INITIAL_POPULATION} POPULATION ---")
    print("This may take a minute...")
    
    batch_size = 1000
    total_generated = 0
    
    while total_generated < INITIAL_POPULATION:
        # Generate in chunks
        current_batch = min(batch_size, INITIAL_POPULATION - total_generated)
        
        for _ in range(current_batch):
            # Same logic as daily generation
            app_data = generate_applicant()
            cursor.execute("""
                INSERT INTO Applicants (FirstName, LastName, Age, Email, Address, PhoneNumber, MaidenName, SocialMediaHandle, LastLoginIP, LoyaltyPoints, EmploymentStatus, JobTitle, YearsExperience) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING ApplicantID
            """, (app_data['FirstName'], app_data['LastName'], app_data['Age'], app_data['Email'], app_data['Address'], app_data['PhoneNumber'],
                     app_data['MaidenName'], app_data['SocialMediaHandle'], app_data['LastLoginIP'], app_data['LoyaltyPoints'],
                     app_data['EmploymentStatus'], app_data['JobTitle'], app_data['YearsExperience']))
            
            applicant_id = cursor.fetchone()[0]

            fin_data = generate_financials(app_data['EmploymentStatus'])
            cursor.execute("""
                INSERT INTO FinancialProfile (ApplicantID, AnnualIncome, CreditScore, ExistingDebt, DebtToIncomeRatio, CollateralValue, CollateralType, AccountAgeDays, AvgTransactionCount, LastBranchVisited)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (applicant_id, fin_data['AnnualIncome'], fin_data['CreditScore'], fin_data['ExistingDebt'], 
                    fin_data['DebtToIncomeRatio'], fin_data['CollateralValue'], fin_data['CollateralType'],
                     fin_data['AccountAgeDays'], fin_data['AvgTransactionCount'], fin_data['LastBranchVisited']))

            loan_data = generate_loan_request(fin_data['AnnualIncome'], fin_data['CollateralValue'])
            cursor.execute("""
                INSERT INTO LoanApplications (ApplicantID, RequestAmount, LoanPurpose, LoanToCostRatio, ApplicationSource, ReferralCode, ProcessingPriority)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (applicant_id, loan_data['RequestAmount'], loan_data['LoanPurpose'], loan_data['LoanToCostRatio'],
                     loan_data['ApplicationSource'], loan_data['ReferralCode'], loan_data['ProcessingPriority']))
        
        conn.commit()
        total_generated += current_batch
        print(f"Generated {total_generated}/{INITIAL_POPULATION}...")

    print("--- WORLD GENERATION COMPLETE ---")

if __name__ == '__main__':
    # Cloud Optimization: Limit endless loop or run once for GitHub Actions
    if len(sys.argv) > 1 and sys.argv[1] == '--bulk-only':
         conn = db_config.get_connection()
         if conn:
             generate_bulk_data(conn)
             conn.close()
    else:
        main()

