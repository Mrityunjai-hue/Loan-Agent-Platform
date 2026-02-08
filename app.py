import streamlit as st
import pandas as pd
import time
import db_config
import os
import plotly.express as px
import plotly.graph_objects as go

# Configuration
st.set_page_config(page_title="Agentic Loan Platform", layout="wide", page_icon="🏦")

# --- Custom CSS Injection ---
def local_css():
    st.markdown("""
    <style>
        /* Modern Font Import */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Metric Cards */
        div[data-testid="stMetric"] {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            border: 1px solid #e0e0e0;
        }
        
        /* Dark Mode Adjustment for Metric Cards */
        @media (prefers-color-scheme: dark) {
            div[data-testid="stMetric"] {
                background-color: #262730;
                border: 1px solid #41424b;
            }
        }

        /* Buttons */
        div.stButton > button {
            width: 100%;
            border-radius: 8px;
            font-weight: 600;
            padding-top: 10px;
            padding-bottom: 10px;
        }

        /* Headers */
        h1, h2, h3 {
            font-weight: 800;
            color: #1E88E5; /* Brand Color */
        }
        
        /* Success/Error Callouts */
        .element-container .stAlert {
            border-radius: 8px;
        }
        
        /* Result Card - Custom HTML Class */
        .result-card {
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 2rem;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .approved {
            background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        }
        .rejected {
            background: linear-gradient(135deg, #ff5f6d 0%, #ffc371 100%);
        }
        .pending {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
    </style>
    """, unsafe_allow_html=True)

local_css()

def get_data():
    conn = db_config.get_connection()
    if not conn:
        return pd.DataFrame()
        
    try:
        # Postgres Syntax: LIMIT instead of TOP
        # String concatenation: || is standard SQL (Postgres), + is T-SQL (SQL Server)
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
            P.Reasoning AS "Reasoning",
            LA.ApplicationID AS "ApplicationID"
        FROM LoanApplications LA
        JOIN Applicants A ON LA.ApplicantID = A.ApplicantID
        JOIN FinancialProfile FP ON A.ApplicantID = FP.ApplicantID
        LEFT JOIN Predictions P ON LA.ApplicationID = P.ApplicationID
        ORDER BY LA.ApplicationID DESC
        LIMIT 100
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Sidebar Navigation
with st.sidebar:
    st.image("https://img.icons8.com/cloud/100/4a90e2/bank-building.png", width=80)
    st.title("Agentic Loans")
    st.markdown("---")
    page = st.radio("Navigate", ["Live Dashboard", "Apply for Loan", "Check Status"], index=0)
    st.markdown("---")
    st.info("System Status: **Online** 🟢")

if page == "Live Dashboard":
    st.title("🏦 Executive Dashboard")
    st.markdown("Real-time insights into loan processing and AI decisions.")

    # Metrics
    df = get_data()
    if not df.empty:
        total_apps = len(df)
        approved = len(df[df['Status'] == 'Approved'])
        rejected = len(df[df['Status'] == 'Rejected'])
        pending = len(df[df['Status'] == 'Pending'])
        approval_rate = (approved / total_apps * 100) if total_apps > 0 else 0
        
        # Top Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Applications", total_apps, "+2", delta_color="normal")
        col2.metric("Approval Rate", f"{approval_rate:.1f}%", f"{approval_rate-50:.1f}%")
        col3.metric("Pending Queue", pending, "Wait time < 5m", delta_color="off")
        col4.metric("Rejected", rejected, delta_color="inverse")
        
        st.markdown("### 📈 Analytics")
        
        # Charts Row 1
        c1, c2 = st.columns(2)
        
        with c1:
            # Status Distribution Pie Chart
            fig_pie = px.pie(df, names='Status', title='Application Status Distribution', 
                             color='Status',
                             color_discrete_map={'Approved':'#00cc96', 'Rejected':'#EF553B', 'Pending':'#FFA15A'},
                             hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c2:
            # Income vs Loan Amount Scatter
            fig_scatter = px.scatter(df, x="AnnualIncome", y="RequestAmount", color="Status",
                                     title="Income vs Requested Loan Amount",
                                     color_discrete_map={'Approved':'#00cc96', 'Rejected':'#EF553B', 'Pending':'#FFA15A'},
                                     log_x=True, log_y=True)
            st.plotly_chart(fig_scatter, use_container_width=True)

        # Recent Data Table
        st.markdown("### 📋 Recent Applications")
        st.dataframe(
            df[['ApplicationID', 'Name', 'RequestAmount', 'Status', 'CreditScore']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "RequestAmount": st.column_config.NumberColumn("Amount", format="₹%d"),
                "Status": st.column_config.TextColumn("Status"),
                "CreditScore": st.column_config.ProgressColumn("Credit Score", min_value=300, max_value=900, format="%d"),
            }
        )
        
    else:
        st.warning("No data found or Database Connection Failed. Please check your Secret Keys.")

    if st.button("🔄 Refresh Data"):
        st.rerun()

elif page == "Apply for Loan":
    st.title("📝 New Loan Application")
    st.markdown("Submit your details below for an instant AI assessment.")
    
    with st.form("application_form"):
        st.subheader("1. Personal Information")
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name", placeholder="e.g. Rahul")
            last_name = st.text_input("Last Name", placeholder="e.g. Sharma")
            email = st.text_input("Email", placeholder="rahul@example.com")
            phone = st.text_input("Phone Number", placeholder="+91 98765 43210")
        with col2:
            age = st.number_input("Age", 18, 100, 30)
            address = st.text_area("Address", placeholder="Full residential address", height=108)

        st.markdown("---")
        st.subheader("2. Financial Profile")
        col3, col4 = st.columns(2)
        with col3:
            employment = st.selectbox("Employment Status", ["Salaried", "Self-Employed", "Unemployed", "Retired"])
            job_title = st.text_input("Job Title", placeholder="e.g. Software Engineer")
            exp = st.number_input("Years Experience", 0, 50, 5)
        with col4:
            income = st.number_input("Annual Income (₹)", 0.0, 100000000.0, 500000.0, step=10000.0)
            credit_score = st.slider("Credit Score (CIBIL)", 300, 900, 750)
            debt = st.number_input("Existing Debt (₹)", 0.0, 100000000.0, 0.0, step=5000.0)

        st.markdown("---")
        st.subheader("3. Loan Details")
        col5, col6 = st.columns(2)
        with col5:
            req_amount = st.number_input("Requested Amount (₹)", 10000.0, 100000000.0, 500000.0, step=10000.0)
        with col6:
            collateral_val = st.number_input("Collateral Value (₹)", 0.0, 100000000.0, 0.0, step=10000.0)
        
        submitted = st.form_submit_button("🚀 Submit Application")
        
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
                        
                        st.balloons()
                        st.success(f"Application Submitted Successfully! Reference ID: {app_id}")
                        st.info("The AI Agent is evaluating your profile now. Check the 'Check Status' page in a few seconds.")
                        
                    except Exception as e:
                        st.error(f"Database Error: {e}")
                else:
                    st.error("Could not connect to database.")

elif page == "Check Status":
    st.title("🔍 Track Application")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        app_id_input = st.number_input("Enter Application ID", min_value=1, value=1, step=1)
        check_btn = st.button("Check Status")
    
    if check_btn:
        conn = db_config.get_connection()
        if conn:
            try:
                query = """
                SELECT 
                    LA.ApplicationID,
                    LA.Status,
                    LA.RequestAmount,
                    P.PredictedEligibilityScore,
                    P.ModelRiskLevel,
                    P.Reasoning,
                    P.RecommendedLoanAmount,
                    A.FirstName || ' ' || A.LastName AS Name,
                    A.EmploymentStatus,
                    FP.AnnualIncome,
                    FP.CreditScore,
                    FP.DebtToIncomeRatio
                FROM LoanApplications LA
                JOIN Applicants A ON LA.ApplicantID = A.ApplicantID
                JOIN FinancialProfile FP ON A.ApplicantID = FP.ApplicantID
                LEFT JOIN Predictions P ON LA.ApplicationID = P.ApplicationID
                WHERE LA.ApplicationID = %s
                """
                cursor = conn.cursor()
                cursor.execute(query, (app_id_input,))
                row = cursor.fetchone()
                
                if row:
                    status = row[1]
                    req_amount = row[2]
                    score = row[3] if row[3] is not None else 0.0
                    risk = row[4] if row[4] is not None else "Pending"
                    reasoning = row[5] if row[5] is not None else "AI Analysis in progress..."
                    rec_amount = row[6]
                    
                    name = row[7]
                    emp_status = row[8]
                    income = row[9]
                    cibil = row[10]
                    dti = row[11]
                    
                    # Determine styling class
                    card_class = "pending"
                    if status == "Approved": card_class = "approved"
                    elif status == "Rejected": card_class = "rejected"
                    
                    st.markdown(f"""
                    <div class="result-card {card_class}">
                        <h2>Application #{row[0]}</h2>
                        <h1>{status.upper()}</h1>
                        <p>Applicant: {name}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Columns for details
                    d1, d2 = st.columns(2)
                    
                    with d1:
                        st.markdown("### 📊 Financial Context")
                        st.write(f"**Credit Score:** {cibil}")
                        st.write(f"**Annual Income:** ₹{income:,.0f}")
                        st.write(f"**Debt-to-Income:** {dti*100:.1f}%")
                        
                    with d2:
                        st.markdown("### 💰 Offer Details")
                        st.write(f"**Requested:** ₹{req_amount:,.2f}")
                        if rec_amount:
                            st.write(f"**Approved:** ₹{rec_amount:,.2f}")
                        else:
                            st.write("**Approved:** ₹0.00")

                    st.markdown("---")
                    st.markdown("### 🤖 AI Agent Analysis")
                    
                    # Gauge chart for score
                    fig = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = score * 100,
                        domain = {'x': [0, 1], 'y': [0, 1]},
                        title = {'text': "Eligibility Score"},
                        gauge = {
                            'axis': {'range': [0, 100]},
                            'bar': {'color': "#1E88E5"},
                            'steps': [
                                {'range': [0, 50], 'color': "#ffe0e0"},
                                {'range': [50, 80], 'color': "#fff5cc"},
                                {'range': [80, 100], 'color': "#e0ffe0"}],
                        }
                    ))
                    fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("📝 View Detailed Agent Reasoning", expanded=True):
                        st.write(reasoning)
                        if status == "Rejected":
                            st.warning("Tip: Improve your credit score or reduce existing debt to increase approval chances.")

                else:
                    st.error("Application ID not found.")
                
                conn.close()
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Database connection failed.")
