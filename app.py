import streamlit as st
import pandas as pd
import time
import db_config
import os

# Configuration
st.set_page_config(page_title="Agentic Loan Platform", layout="wide")

def get_data():
    conn = db_config.get_connection()
    if not conn:
        return pd.DataFrame()
        
    try:
        # Postgres Syntax: LIMIT instead of TOP
        # CRITICAL: Postgres returns lowercase columns by default. 
        # We must Alias them with quotes to keep them Capitalized for the DF code.
        query = """
        SELECT 
            A.ApplicantID AS "ApplicantID",
            A.FirstName || ' ' || A.LastName AS "Name",
            A.Age AS "Age",
            A.EmploymentStatus AS "EmploymentStatus",
            FP.AnnualIncome AS "AnnualIncome",
            FP.CreditScore AS "CreditScore",
            LA.RequestAmount AS "RequestAmount",
            LA.Status AS "Status",
            P.RecommendedLoanAmount AS "RecommendedLoanAmount",
            P.Reasoning AS "Reasoning"
        FROM LoanApplications LA
        JOIN Applicants A ON LA.ApplicantID = A.ApplicantID
        JOIN FinancialProfile FP ON A.ApplicantID = FP.ApplicantID
        LEFT JOIN Predictions P ON LA.ApplicationID = P.ApplicationID
        ORDER BY LA.ApplicationID DESC
        LIMIT 1000
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Live Dashboard", "Apply for Loan", "Check Status"])

if page == "Live Dashboard":
    st.title("🏦 Agentic Loan Eligibility Platform (Cloud Version)")
    st.markdown("### AI-Powered Underwriting System (24/7 Simulation)")

    # Metrics
    df = get_data()
    if not df.empty:
        total_apps = len(df)
        approved = len(df[df['Status'] == 'Approved'])
        rejected = len(df[df['Status'] == 'Rejected'])
        pending = len(df[df['Status'] == 'Pending'])
        rate = (approved / total_apps * 100) if total_apps > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Applications", total_apps)
        col2.metric("Approval Rate", f"{rate:.1f}%")
        col3.metric("Pending (Queue)", pending)
        col4.metric("rejected", rejected)
        
        st.subheader("Latest Decisions")
        st.dataframe(df)
    else:
        st.warning("No data found or Database Connection Failed. Please check your Secret Keys.")

    if st.button("Refresh Data"):
        st.rerun()

elif page == "Apply for Loan":
    st.title("📝 New Loan Application")
    st.markdown("Submit your details manually. Our AI Agent will review it shortly.")
    
    with st.form("application_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            age = st.number_input("Age", 18, 100, 30)
            email = st.text_input("Email")
            address = st.text_input("Address")
            phone = st.text_input("Phone Number")
        
        with col2:
            employment = st.selectbox("Employment Status", ["Salaried", "Self-Employed", "Unemployed", "Retired"])
            job_title = st.text_input("Job Title")
            exp = st.number_input("Years Experience", 0, 50, 5)
            income = st.number_input("Annual Income (INR)", 0.0, 100000000.0, 500000.0)
            credit_score = st.number_input("Credit Score", 300, 900, 750)
            debt = st.number_input("Existing Debt", 0.0, 100000000.0, 0.0)
            
        st.subheader("Loan Details")
        req_amount = st.number_input("Requested Amount", 10000.0, 100000000.0, 100000.0)
        collateral_val = st.number_input("Collateral Value", 0.0, 100000000.0, 0.0)
        
        submitted = st.form_submit_button("Submit Application")
        
        if submitted:
            if not first_name or not last_name:
                st.error("Please fill in your name.")
            else:
                conn = db_config.get_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        # Calculate derived fields
                        dti = (debt / income) if income > 0 else 0
                        total_asset = req_amount + collateral_val
                        lc = req_amount / total_asset if total_asset > 0 else 1.0
                        
                        # Generic noise for manual entry
                        maiden_noise = None
                        handle_noise = None
                        ip = "127.0.0.1"
                        loyalty = 0
                        collateral_type = "None" if collateral_val == 0 else "Other"
                        
                        # INSERT Applicant
                        cursor.execute("""
                            INSERT INTO Applicants (FirstName, LastName, Age, Email, Address, PhoneNumber, MaidenName, SocialMediaHandle, LastLoginIP, LoyaltyPoints, EmploymentStatus, JobTitle, YearsExperience) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING ApplicantID
                        """, (first_name, last_name, age, email, address, phone, maiden_noise, handle_noise, ip, loyalty, employment, job_title, exp))
                        
                        app_id = cursor.fetchone()[0]
                        
                        # INSERT Financials
                        cursor.execute("""
                            INSERT INTO FinancialProfile (ApplicantID, AnnualIncome, CreditScore, ExistingDebt, DebtToIncomeRatio, CollateralValue, CollateralType, AccountAgeDays, AvgTransactionCount, LastBranchVisited)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (app_id, income, credit_score, debt, dti, collateral_val, collateral_type, 365, 10, 'Online'))
                        
                        # INSERT LoanRequest
                        cursor.execute("""
                            INSERT INTO LoanApplications (ApplicantID, RequestAmount, LoanPurpose, LoanToCostRatio, ApplicationSource, ReferralCode, ProcessingPriority)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (app_id, req_amount, 'Personal', lc, 'Web Form', None, 5))
                        
                        conn.commit()
                        conn.close()
                        st.success(f"Application Submitted! Reference ID: {app_id}. Status: Pending.")
                        st.info("The AI Agent will evaluate this shortly. Check the Dashboard.")
                        
                    except Exception as e:
                        st.error(f"Database Error: {e}")
                else:
                    st.error("Could not connect to database.")

elif page == "Check Status":
    st.title("🔍 Check Application Status")
    
    app_id_input = st.number_input("Enter Application ID", min_value=1, value=1, step=1)
    
    if st.button("Check Status"):
        conn = db_config.get_connection()
        if conn:
            try:
                # Aliasing for DataFrame compatibility (though we just use fetchone here)
                query = """
                SELECT 
                    LA.ApplicationID,
                    LA.Status,
                    LA.RequestAmount,
                    P.PredictedEligibilityScore,
                    P.ModelRiskLevel,
                    P.Reasoning,
                    P.RecommendedLoanAmount
                FROM LoanApplications LA
                LEFT JOIN Predictions P ON LA.ApplicationID = P.ApplicationID
                WHERE LA.ApplicationID = %s
                """
                cursor = conn.cursor()
                cursor.execute(query, (app_id_input,))
                row = cursor.fetchone()
                
                if row:
                    # Unpack (Postgres returns tuple)
                    status = row[1]
                    req_amount = row[2]
                    score = row[3] if row[3] is not None else 0.0
                    risk = row[4] if row[4] is not None else "Unknown"
                    reasoning = row[5] if row[5] is not None else "Pending AI Analysis..."
                    rec_amount = row[6]
                    
                    st.divider()
                    st.subheader(f"Application #{row[0]}")
                    
                    if status == "Approved":
                        st.success(f"Status: {status}")
                    elif status == "Rejected":
                        st.error(f"Status: {status}")
                    else:
                        st.warning(f"Status: {status}")
                        
                    col1, col2 = st.columns(2)
                    col1.metric("Requested Amount", f"₹{req_amount:,.2f}")
                    if rec_amount:
                        col2.metric("Approved Amount", f"₹{rec_amount:,.2f}")
                    
                    st.markdown("### 🤖 AI Analysis")
                    st.write(f"**Risk Level:** {risk}")
                    st.write(f"**Eligibility Score:** {score:.2f}")
                    st.info(f"**Reasoning:** {reasoning}")
                    
                else:
                    st.error("Application ID not found.")
                
                conn.close()
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Database connection failed.")
