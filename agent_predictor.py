import torch
import loan_model
import os
import db_config
import time
import sys
from decimal import Decimal

# Configuration
POLL_INTERVAL = 10 
MODEL_PATH = "loan_model.pth"


def evaluate_application(app):
    # App Structure: 0:AppID, 1:ReqAmount, 2:Income, 3:Score, 4:Debt, 5:DTI, 6:Collateral, 7:AcctAge, 8:AvgTrans, 9:Priority, 10:Loyalty
    # We slice to get what we need for the Ground Truth Rules
    app_id = app[0]
    req_amount = run_float(app[1])
    income = run_float(app[2])
    score = int(app[3]) if app[3] else 0
    # idx 4 is Debt (unused here)
    dti = run_float(app[5])
    collateral = run_float(app[6])
    
    # Noise columns (6,7,8,9) are ignored by the expert rules
    # This ensures the "Ground Truth" label is based only on signal.

    # 1. Indian Context Eligibility Logic (CIBIL-like)
    reasons = []
    
    # CIBIL Score check (Standard > 700 is good, > 650 okay)
    if score < 600:
        reasons.append(f"CIBIL Score {score} is below minimum 600")
        
    # DTI Check
    if dti > 0.50:
        reasons.append(f"Debt Burden Ratio {dti*100:.1f}% exceeds 50%")
        
    # Income Check (Minimum 2.5 LPA for Personal Loan often)
    if income < 250000:
        reasons.append("Annual Income below 2.5 Lakhs")

    if reasons:
        return {
            'Status': 'Rejected',
            'Score': 0.0,
            'Amount': 0.0,
            'Risk': 'High',
            'Reason': "; ".join(reasons)
        }

    # 2. Loan Amount Calculation
    # Max Eligibility = 50% of Income multiplier + Collateral LTV
    # In India, Housing Loan LTV up to 80-90%, LAP ~60%
    # Rough logic: 
    loan_capacity = (income * 5) # 5x annual income (Housing)
    if collateral > 0:
        loan_capacity += (collateral * 0.7) # 70% LTV
        
    risk = "Low"
    if score < 700:
        loan_capacity *= 0.8
        risk = "Medium"
    
    approved_amount = min(req_amount, loan_capacity)
    
    # Normalize score
    eligibility = (score / 900) * (1 - dti)
    
    return {
        'Status': 'Approved',
        'Score': round(eligibility, 2),
        'Amount': round(approved_amount, 2),
        'Risk': risk,
        'Reason': "Eligible based on CIBIL and Income norms"
    }

def run_float(val):
    if isinstance(val, Decimal):
        return float(val)
    if val is None:
        return 0.0
    return float(val)

def bootstrap_training(conn, model_path):
    print("Checking for existing model...")
    if os.path.exists(model_path):
        print(f"Loading existing model from {model_path}")
        model = loan_model.LoanNet()
        model.load_state_dict(torch.load(model_path))
        return model
    
    print("No model found. Checking if we can bootstrap from pending data...")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM LoanApplications WHERE Status='Pending'")
    pending_count = cursor.fetchone()[0]
    
    if pending_count < 100: # Lowered threshold for cloud demo
        print("Not enough data to bootstrap model (Need > 100). running in Fallback Rule-Based Mode.")
        return None

    print(f"Bootstrapping Model with {pending_count} pending applications...")
    print("Step 1: labeling using Rule-Based Teacher...")
    
    # Select data: (AppID, ReqAmount, Income, Score, Debt, DTI, Collateral, AccountAge, AvgTrans, Priority, Loyalty)
    # FIXED: Added FP.ExistingDebt at index 4
    cursor.execute("""
        SELECT LA.ApplicationID, LA.RequestAmount, 
               FP.AnnualIncome, FP.CreditScore, FP.ExistingDebt, FP.DebtToIncomeRatio, FP.CollateralValue,
               FP.AccountAgeDays, FP.AvgTransactionCount, LA.ProcessingPriority, A.LoyaltyPoints
        FROM LoanApplications LA
        JOIN Applicants A ON LA.ApplicantID = A.ApplicantID
        JOIN FinancialProfile FP ON A.ApplicantID = FP.ApplicantID
        WHERE LA.Status = 'Pending'
    """)
    rows = cursor.fetchall()
    
    features = []
    labels = []
    
    for row in rows:
        app_id = row[0]
        # Label with Rule-Based Logic - RULES DO NOT CHANGE (They generate "Ground Truth" Signal)
        # The Rules ignore the noise, so the Label is clean.
        # The Model receives Signal + Noise as input, and tries to predict the Clean Label.
        # This effectively forces the Model to learn that Noise is irrelevant.
        result = evaluate_application(row) 
        
        # Determine Label (1 for Approved, 0 for Rejected)
        label = 1.0 if result['Status'] == 'Approved' else 0.0
        
        # Prepare Features (Includes Noise)
        # row[1] is ReqAmount (skipped for simple eligibility model, used for logic)
        # Features start from row[2] (Income) to end
        # Now this includes ExistingDebt at index 4 (relative to query) / index 2 (relative to slice)
        # Slice from row[2] gives: [Income, Score, Debt, DTI, Collateral, AcctAge, AvgTrans, Priority, Loyalty] -> 9 items. Correct.
        feat = loan_model.prepare_features(row[2:]) 
        features.append(feat)
        labels.append(label)
        
        # Write "Ground Truth" to DB so we don't re-process them as pending forever
        # Warning: This "uses up" the pending data to create history
        cursor.execute("UPDATE LoanApplications SET Status = %s WHERE ApplicationID = %s", (result['Status'], app_id))
        
        # FIXED: Use actual reasoning instead of static string
        reasoning_text = f"{result['Reason']} (Bootstrapped Label)"
        
        cursor.execute("""
            INSERT INTO Predictions (ApplicationID, PredictedEligibilityScore, RecommendedLoanAmount, ModelRiskLevel, Reasoning)
            VALUES (%s, %s, %s, %s, %s)
        """, (app_id, result['Score'], result['Amount'], 'Bootstrap-Truth', reasoning_text))
    
    conn.commit()
    print("Step 2: Training Neural Network on Bootstrapped Data...")
    
    # Train
    model = loan_model.train_model(features, labels, epochs=5)
    
    # Save
    torch.save(model.state_dict(), model_path)
    print(f"Model saved to {model_path}")
    
    return model
    
def main():
    print("Starting AI Prediction Agent (Deep Neural Network Powered)...")
    
    single_run = '--single-run' in sys.argv
    if single_run:
        print("Mode: Single Batch Run (GitHub Actions)")

    # Startup Phase: Load or Train Model
    conn = db_config.get_connection()
    if not conn:
        print("DB Connection failed on startup.")
        return
        
    model = bootstrap_training(conn, MODEL_PATH)
    conn.close()
    
    while True:
        conn = db_config.get_connection()
        if not conn:
            time.sleep(5); continue
            
        cursor = conn.cursor()
        
        try:
            # Fetch Pending
            # FIXED QUERY HERE TOO
            cursor.execute("""
                SELECT LA.ApplicationID, LA.RequestAmount, 
                       FP.AnnualIncome, FP.CreditScore, FP.ExistingDebt, FP.DebtToIncomeRatio, FP.CollateralValue,
                       FP.AccountAgeDays, FP.AvgTransactionCount, LA.ProcessingPriority, A.LoyaltyPoints
                FROM LoanApplications LA
                JOIN Applicants A ON LA.ApplicantID = A.ApplicantID
                JOIN FinancialProfile FP ON A.ApplicantID = FP.ApplicantID
                WHERE LA.Status = 'Pending'
            """)
            rows = cursor.fetchall() 
            
            if rows:
                print(f"Processing {len(rows)} applications...")
                
                # If we still don't have a model (e.g. initial count < 1000), use rule based
                use_model = (model is not None)
                
                features_batch = []
                ids_batch = []
                rows_batch = []

                for row in rows:
                    if not use_model:
                        # Fallback Mode
                        result = evaluate_application(row)
                        cursor.execute("UPDATE LoanApplications SET Status = %s WHERE ApplicationID = %s", (result['Status'], row[0]))
                        cursor.execute("INSERT INTO Predictions (ApplicationID, PredictedEligibilityScore, RecommendedLoanAmount, ModelRiskLevel, Reasoning) VALUES (%s, %s, %s, %s, %s)", 
                            (row[0], result['Score'], result['Amount'], result['Risk'], result['Reason']))
                    else:
                        # Collect for Model Prediction
                        # Features match training preparation: row[2:]
                        feat = loan_model.prepare_features(row[2:])
                        features_batch.append(feat)
                        ids_batch.append(row[0])
                        rows_batch.append(row)

                if use_model and features_batch:
                    # Sequential Prediction
                    for i, feat in enumerate(features_batch):
                        app_id = ids_batch[i]
                        orig_row = rows_batch[i]
                        
                        # AI Prediction
                        prob = loan_model.predict_single(model, feat)
                        
                        # Interpretation
                        status = 'Approved' if prob > 0.5 else 'Rejected'
                        risk = 'Low' if prob > 0.8 else 'Medium' if prob > 0.5 else 'High'
                        
                        # We still need Amount logic (Model predicts eligibility, not amount yet - hybrid approach)
                        # Re-use rule logic strictly for Amount, but use Model for Status
                        rule_result = evaluate_application(orig_row)
                        amount = rule_result['Amount'] if status == 'Approved' else 0.0
                        
                        # Update: Use status-based logic AND probability for reasoning
                        # Calculate what the rule reasoning was (e.g. Low CIBIL)
                        # And display it alongside AI Confidence
                        
                        reason_prefix = "AI Logic"
                        if status == 'Rejected':
                            # If rejected, why? Use rule checker to hint at why
                            fail_reasons = rule_result['Reason']
                            if "Eligible" in fail_reasons: 
                                fail_reasons = "Model Rejection (Risk Factors High)" # Model disagreed with simple rules
                            reasoning_text = f"{fail_reasons} (AI Confidence: {100-int(prob*100)}%)"
                        else:
                            reasoning_text = f"Meets Eligibility Criteria (AI Confidence: {int(prob*100)}%)"

                        cursor.execute("UPDATE LoanApplications SET Status = %s WHERE ApplicationID = %s", (status, app_id))
                        cursor.execute("""
                            INSERT INTO Predictions (ApplicationID, PredictedEligibilityScore, RecommendedLoanAmount, ModelRiskLevel, Reasoning)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (app_id, float(prob), amount, risk, reasoning_text))

                conn.commit()
                print("Batch processed.")
            else:
                if single_run:
                    print("No pending applications. Existing.")
                    break
                print("No pending applications. Existing.")
            
        except Exception as e:
            print(f"Error: {e}")
            
        conn.close()
        
        if single_run:
            break
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
