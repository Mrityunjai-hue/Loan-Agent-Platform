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
        # String concatenation: || is standard SQL (Postgres), + is T-SQL (SQL Server)
        query = """
        SELECT 
            A.ApplicantID,
            A.FirstName || ' ' || A.LastName AS Name,
            A.Age,
            A.EmploymentStatus,
            FP.AnnualIncome,
            FP.CreditScore,
            LA.RequestAmount,
            LA.Status,
            P.RecommendedLoanAmount,
            P.Reasoning
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
page = st.sidebar.radio("Go to:", ["Live Dashboard", "Apply for Loan"])

if page == "Live Dashboard":
    st.title("🏦 Agentic Loan Eligibility Platform (Cloud Cloud)")
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
                        # Returning ID syntax for Postgres
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
