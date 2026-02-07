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
    app_id = app[0]
    req_amount = run_float(app[1])
    income = run_float(app[2])
    score = int(app[3]) if app[3] else 0
    # idx 4 is Debt (unused in simple rules)
    dti = run_float(app[5])
    collateral = run_float(app[6])
    
    reasons = []
    
    if score < 600:
        reasons.append(f"CIBIL Score {score} is below minimum 600")
        
    if dti > 0.50:
        reasons.append(f"Debt Burden Ratio {dti*100:.1f}% exceeds 50%")
        
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

    loan_capacity = (income * 5)
    if collateral > 0:
        loan_capacity += (collateral * 0.7)
        
    risk = "Low"
    if score < 700:
        loan_capacity *= 0.8
        risk = "Medium"
    
    approved_amount = min(req_amount, loan_capacity)
    
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
    
    if pending_count < 100:
        print("Not enough data to bootstrap model (Need > 100). running in Fallback Rule-Based Mode.")
        return None

    print(f"Bootstrapping Model with {pending_count} pending applications...")
    print("Step 1: labeling using Rule-Based Teacher...")
    
    # FIXED QUERY: Added FP.ExistingDebt
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
        result = evaluate_application(row) 
        
        label = 1.0 if result['Status'] == 'Approved' else 0.0
        
        # Features start from row[2] (Income) to end
        # Now this includes ExistingDebt at index 4 (relative to query) / index 2 (relative to slice)
        feat = loan_model.prepare_features(row[2:]) 
        features.append(feat)
        labels.append(label)
        
        cursor.execute("UPDATE LoanApplications SET Status = %s WHERE ApplicationID = %s", (result['Status'], app_id))
        cursor.execute("""
            INSERT INTO Predictions (ApplicationID, PredictedEligibilityScore, RecommendedLoanAmount, ModelRiskLevel, Reasoning)
            VALUES (%s, %s, %s, %s, %s)
        """, (app_id, result['Score'], result['Amount'], 'Bootstrap-Truth', 'Initial Training Data'))
    
    conn.commit()
    print("Step 2: Training Neural Network on Bootstrapped Data...")
    
    model = loan_model.train_model(features, labels, epochs=5)
    
    torch.save(model.state_dict(), model_path)
    print(f"Model saved to {model_path}")
    
    return model

def main():
    print("Starting AI Prediction Agent (Deep Neural Network Powered)...")
    
    single_run = '--single-run' in sys.argv
    if single_run:
        print("Mode: Single Batch Run (GitHub Actions)")

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
            # FIXED QUERY: Added FP.ExistingDebt
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
                
                use_model = (model is not None)
                
                features_batch = []
                ids_batch = []
                rows_batch = []

                for row in rows:
                    if not use_model:
                        result = evaluate_application(row)
                        cursor.execute("UPDATE LoanApplications SET Status = %s WHERE ApplicationID = %s", (result['Status'], row[0]))
                        cursor.execute("INSERT INTO Predictions (ApplicationID, PredictedEligibilityScore, RecommendedLoanAmount, ModelRiskLevel, Reasoning) VALUES (%s, %s, %s, %s, %s)", 
                            (row[0], result['Score'], result['Amount'], result['Risk'], result['Reason']))
                    else:
                        feat = loan_model.prepare_features(row[2:])
                        features_batch.append(feat)
                        ids_batch.append(row[0])
                        rows_batch.append(row)

                if use_model and features_batch:
                    for i, feat in enumerate(features_batch):
                        app_id = ids_batch[i]
                        orig_row = rows_batch[i]
                        
                        prob = loan_model.predict_single(model, feat)
                        
                        status = 'Approved' if prob > 0.5 else 'Rejected'
                        risk = 'Low' if prob > 0.8 else 'Medium' if prob > 0.5 else 'High'
                        
                        rule_result = evaluate_application(orig_row)
                        amount = rule_result['Amount'] if status == 'Approved' else 0.0
                        
                        cursor.execute("UPDATE LoanApplications SET Status = %s WHERE ApplicationID = %s", (status, app_id))
                        cursor.execute("""
                            INSERT INTO Predictions (ApplicationID, PredictedEligibilityScore, RecommendedLoanAmount, ModelRiskLevel, Reasoning)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (app_id, float(prob), amount, risk, f"DNN Probability: {prob:.4f}"))

                conn.commit()
                print("Batch processed.")
            else:
                if single_run:
                    print("No pending applications. Existing.")
                    break
            
        except Exception as e:
            print(f"Error: {e}")
            
        conn.close()
        
        if single_run:
            break
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
