# Agentic Loan Platform: Technical Documentation 

## 1. Project Overview & Architecture 

This project implements an **Agentic AI System** for converting raw loan applications into approved/rejected decisions using a **Hybrid Teacher-Student Model**. It simulates a real-world financial environment where autonomous agents interact through a shared database.

### System Components (Micro-Agents)
The architecture consists of three independent processes (Agents) that run in parallel:

1.  **Values & Simulation Agent (`generate_data.py`)**:
    *   **Role**: functions as the "World Simulator". It generates synthetic applicants and simulates the passage of time.
    *   **Behavior**: Creates new applicants with realistic Indian-context data (Names, Addresses, Pan-like logic) and updates existing applicants' financial status (e.g., salary hikes, new debts) to trigger re-evaluation.
    
2.  **Intelligence & Decision Agent (`agent_predictor.py`)**:
    *   **Role**: The "Brain" of the bank. It is an infinite-loop background service.
    *   **Behavior**: Polls the database for `Pending` applications, runs them through a Deep Neural Network (DNN), assigns a Risk Score, and commits the decision back to the database.

3.  **Experience & Interface Agent (`app.py`)**:
    *   **Role**: The "Frontend". A Streamlit-based web application.
    *   **Behavior**: Allows users to interact with the system, submit applications, track status in real-time, and view executive dashboards.

---

## 2. Artificial Intelligence Model 

The decision engine is a **Feed-Forward Neural Network** built using **PyTorch**, designed to mimic an Expert Underwriter (Rule-Based Logic).

### A. Model Architecture (`loan_model.py`)
*   **Type**: Multi-Layer Perceptron (MLP) / Deep Feed-Forward Network.
*   **Input Layer**: 9 Neurons (corresponding to 9 normalized features).
*   **Hidden Layer 1**: 64 Neurons with **ReLU** (Rectified Linear Unit) activation.
*   **Hidden Layer 2**: 32 Neurons with **ReLU** activation.
*   **Output Layer**: 1 Neuron with **Sigmoid** activation (Outputs a probability $P \in [0, 1]$).
*   **Optimizer**: Adam (Adaptive Moment Estimation) with Learning Rate `0.001`.
*   **Loss Function**: Binary Cross Entropy (BCELoss).

### B. Feature Engineering & Normalization
The model receives a vector of 9 features. Crucially, this includes **Signal** (Valid predictors) and **Noise** (Irrelevant data) to robustly test the AI's ability to filter information.

**Signal Features (The factors that SHOULD matter):**
1.  **Annual Income**: normalized as $\min(\frac{\text{Income}}{30,00,000}, 1.0)$. Checks repayment capacity.
2.  **Credit Score**: normalized as $\frac{\text{Score}}{900}$. Checks creditworthiness (CIBIL equivalent).
3.  **Existing Debt**: normalized as $\min(\frac{\text{Debt}}{10,00,000}, 1.0)$. Checks current burden.
4.  **Debt-to-Income Ratio (DTI)**: normalized as $\min(\text{DTI}, 1.0)$. Checks leverage.
5.  **Collateral Value**: normalized as $\min(\frac{\text{Collateral}}{50,00,000}, 1.0)$. Checks security.

**Noise Features (The factors that SHOULD NOT matter):**
6.  **Account Age**: $\min(\frac{\text{Days}}{5000}, 1.0)$. Tenure length.
7.  **Avg Transaction Count**: $\min(\frac{\text{Count}}{100}, 1.0)$. Usage frequency.
8.  **Processing Priority**: $\min(\frac{\text{Priority}}{10}, 1.0)$. Urgency flag.
9.  **Loyalty Points**: $\min(\frac{\text{Points}}{5000}, 1.0)$. Marketing metric.

---

## 3. Decision Logic & Formulas 

The system uses a **Teacher-Student** hybrid approach.
*   **Teacher**: Hardcoded rules in `agent_predictor.py` (The Expert).
*   **Student**: The Neural Network (The AI) which learns to approximate the Teacher.

### A. The "Teacher" Rules (Ground Truth)
Used for **Bootstrapping** (Training the model initially) and for **Loan Amount Calculation**.

#### 1. Rejection Criteria (Strict)
An application is **Rejected** if *ANY* of these are true:
*   **Credit Score** < 600
*   **Debt-to-Income Ratio (DTI)** > 0.50 (50%)
*   **Annual Income** < ₹2,50,000

#### 2. Loan Amount Calculation (Approval Cap)
If Eligible, the **Maximum Loan Amount** is calculated as:

$$
\text{Capacity}_{\text{Income}} = \text{Annual Income} \times 5
$$
$$
\text{Capacity}_{\text{Collateral}} = \text{Collateral Value} \times 0.70 \quad (70\% \text{ LTV})
$$
$$
\text{Total Capacity} = \text{Capacity}_{\text{Income}} + \text{Capacity}_{\text{Collateral}}
$$

**Risk Adjustment**:
If $\text{Credit Score} < 700$:
$$
\text{Total Capacity} = \text{Total Capacity} \times 0.80 \quad (\text{20\% Penalty})
$$

**Final Approved Amount**:
$$
\text{Approved} = \min(\text{Requested Amount}, \text{Total Capacity})
$$

### B. The "Student" Prediction (Inference)
Used for the **Probability Score** and **Risk Level**.

*   **Eligibility Probability ($P$)**: Output of the Neural Network.
    *   If $P > 0.5$: **Status = Approved**
    *   If $P \le 0.5$: **Status = Rejected**
*   **Risk Classification**:
    *   If $P > 0.8$: **Low Risk**
    *   If $0.5 < P \le 0.8$: **Medium Risk**
    *   If $P \le 0.5$: **High Risk**

---

## 4. Data Generation Strategy (`generate_data.py`) 

The generator uses the `Faker` library mapped to the `en_IN` (India) locale to create realistic data.

### Synthetic Pattern Generation:
*   **Income**: Pareto-like distribution using `random.uniform` (Ranges: ₹3L - ₹30L).
*   **Credit Score**: Biased random integers (300-900). Unemployed people get lower scores (300-650).
*   **DTI Calculation**: Derived from Income and random Debt.
*   **Collateral**: Random assignment (Residential, Vehicle, Gold) or None.

### Dynamic Interaction Loop:
1.  **Morning Batch**: Generates `BATCH_SIZE` (e.g., 10) fresh applicants.
2.  **Afternoon Updates**: Selects random *existing* applicants and mutates their profiles (e.g., changes Employment Status from 'Salaried' to 'Unemployed') to test if the system correctly re-evaluates them.

---

## 5. Dashboard Design & Tech Stack (`app.py`) 

### Tech Stack
*   **Framework**: Streamlit (Python)
*   **Visualization**: Plotly Express & GraphObjects
*   **Styling**: Custom CSS (Injected via `st.markdown`)

### Sections Detail
1.  **Live Dashboard**:
    *   **KPI Metrics**: Uses `st.metric` with `delta` to show real-time changes.
    *   **Charts**:
        *   *Pie Chart*: Status distribution (color-mapped: Green/Approved, Red/Rejected).
        *   *Scatter Plot*: Log-log scale plot of `Income` vs `Request Amount` to visualize affordability trends.
2.  **Apply for Loan**:
    *   A multi-column form layout (`st.columns`) grouping fields logically (Personal -> Financial -> Loan).
    *   Real-time validations (e.g., preventing submitting without a Name).
3.  **Check Status**:
    *   **Result Card**: A custom HTML/CSS component (`<div class="result-card">`) that dynamically changes color based on status (Green Gradient for Approved, Red for Rejected).
    *   **Gauge Chart**: A Plotly Indicator chart showing the `Eligibility Score` (0-100) with colored bands (Red: 0-50, Yellow: 50-80, Green: 80-100).
    *   **Reasoning Expander**: Shows the specific text generated by the predictor agent (e.g., "CIBIL Score 550 is below minimum 600").

---

## 6. Database Schema (PostgreSQL) 

The database is normalized to **3rd Normal Form (3NF)**.

### Tables
1.  **`Applicants`**: Static identity data.
    *   `ApplicantID` (PK), `FirstName`, `LastName`, `Email`, `EmploymentStatus`...
2.  **`FinancialProfile`**: Dynamic financial data (One-to-One with Applicants).
    *   `ProfileID` (PK), `ApplicantID` (FK), `AnnualIncome`, `CreditScore`, `DebtToIncomeRatio`...
3.  **`LoanApplications`**: The simulation requests (One-to-Many with Applicants).
    *   `ApplicationID` (PK), `ApplicantID` (FK), `RequestAmount`, `Status` (Pending/Approved/Rejected)...
4.  **`Predictions`**: The AI's output log (One-to-One with Applications).
    *   `PredictionID` (PK), `ApplicationID` (FK), `PredictedEligibilityScore`, `ModelRiskLevel`, `Reasoning`...

---

## 7. Operational Workflow 

To run the full agentic simulation:

1.  **Database**: Ensure PostgreSQL is running and credentials in `db_config.py` are correct.
2.  **Start Generator**: 
    ```bash
    python generate_data.py
    ```
    *Output*: "Day 1... Generated 10 applicants... Updated 2..."
3.  **Start Predictor** (in a separate terminal):
    ```bash
    python agent_predictor.py
    ```
    *Output*: "Bootstrapping Model... Training... Batch processed."
4.  **Start Dashboard** (in a separate terminal):
    ```bash
    streamlit run app.py
    ```
    *Access*: `http://localhost:8501` to view the UI.

---

## 8. Change Logs 

### Version 1.2.0 - "Project Bharat" Logic Overhaul (Latest)
*   **Indian Market Adaptation (BFSI Standard)**:
    *   **Currency**: Complete overhaul to **INR (₹)** with Lakhs/Crores logic.
    *   **Credit Scoring**: Aligned with **CIBIL** standards (300-900 scale).
    *   **Data Generator**: Integrated `Faker('en_IN')` to generate realistic Indian Names, Addresses, and Phone Numbers.
    *   **Decision Rules**:
        *   Minimum Income Threshold set to **₹2.5 LPA**.
        *   Loan Eligibility Multiplier set to **5x Annual Income** (Standard Housing/Personal Norm).
*   **Generative Engine Upgrade**:
    *   Added `simulate_day()` logic to evolve applicant financial status over time (e.g., salary hikes, new debts).
    *   Implemented "Re-evaluation Triggers" where the `Predictor` re-scores applicants when their data changes.

### Version 1.1.0 - UI & Experience Overhaul
*   **Visual Redesign**:
    *   Implemented "Glassmorphism" inspired CSS for Metric Cards.
    *   Added `Inter` font for modern typography.
    *   Created dynamic "Result Cards" with status-based gradients (Green/Red/Orange).
*   **Dashboard Analytics**:
    *   Added **Plotly** Pie Charts for Status Distribution.
    *   Added Log-Log Scatter Plots for Income vs. Loan Amount analysis.
    *   **Fixed**: Removed `LIMIT 100` restraint to show full dataset history.
    *   **Fixed**: Enabled horizontal scrolling for data tables.
*   **Application Flow**:
    *   Split the long form into 3 logical sections (Personal, Financial, Loan).
    *   Added real-time validation for missing fields.

### Version 1.0.0 - Core Engine
*   Basic Streamlit app with raw data table.
*   Simple Neural Network implementation.
*   Initial database schema setup.

---

## 9. Troubleshooting & Known Challenges 

### 1. "Reasoning" Column showing "Initial Training Data"
*   **Issue**: The bootstrapping process originally hardcoded text for the initial training dataset, making the "Reasoning" column unhelpful.
*   **Fix**: Modified `agent_predictor.py` to capture the specific rule violation (e.g., "Score < 600") during the bootstrapping phase.

### 2. Dashboard Table Truncated
*   **Issue**: Streamlit's `st.dataframe` or the SQL query was limiting the view to the top 100 rows, hiding recent applications.
*   **Fix**: Removed `LIMIT 100` from the SQL query in `app.py`.

### 3. Gauge Chart Clipped
*   **Issue**: The bottom half of the Plotly gauge chart (Eligibility Score) was cut off due to insufficient margins.
*   **Fix**: Added `margin=dict(l=30, r=30, t=50, b=50)` and increased `height=400` in the chart layout.

### 5. Database Connection Stability
*   **Issue**: Long-running agents (Generator/Predictor) may experience connection timeouts.
*   **Solution**: Ensure `db_config.py` reconnects cleanly instead of crashing. (Addressed in agent main loops).

---

## 10. Development Challenges & Rectifications (Retrospective) 

During the development of the **Project Bharat** iteration, we encountered and resolved over 50+ technical challenges. Key categories include:

### A. Data Engineering & Generation
1.  **Locale Specificity**: `Faker` defaults to US/EU formats.
    *   *Fix*: Implemented `Faker('en_IN')` to ensure Indian names, addresses, and +91 phone formats.
2.  **Negative Financials**: Random generation often produced negative `Debt` or `Income`.
    *   *Fix*: Added `max(0, value)` clamps and logical sorting (e.g., `Income > Debt`).
3.  **Dependency Hell**: `psycopg2` vs `psycopg2-binary` caused installation issues on Windows.
    *   *Fix*: Standardized on `psycopg2-binary` for local development.

### B. Neural Network & Training
4.  **NaN Loss during Training**: High variance in input features (e.g., Income ₹30,00,000 vs Age 25) caused gradient explosion.
    *   *Fix*: Implemented strict **Min-Max Normalization** for all inputs (scaled to 0-1 range).
5.  **Shape Mismatches**: The input vector size (9) didn't match the first linear layer (8).
    *   *Fix*: Audit of `prepare_features` function to ensure exact alignment with `LoanNet` input definition.
6.  **Overfitting on Noise**: The model was learning from 'Account Age' instead of 'Credit Score'.
    *   *Fix*: Increased the ratio of "Signal" features and adjusted the "Teacher" rules to be stricter, forcing the model to ignore noise.

### C. Dashboard & Visualization
7.  **Altair/Plotly Conflict**: Streamlit native charts didn't support the interactive tooltips we needed.
    *   *Fix*: Migrated all charts to **Plotly Graph Objects** for full control.
8.  **Render Loop**: The app would refresh infinitely when updating the database from the UI.
    *   *Fix*: Separated the `INSERT` logic from the rendering loop using `st.form`.
9.  **CSS Injection Failures**: Custom styles weren't applying to nested elements.
    *   *Fix*: Used `unsafe_allow_html=True` and targeted specific `data-testid` attributes.

### D. Database & Integrity
10. **Foreign Key Violations**: Generating a Loan Application for a non-existent Applicant ID.
    *   *Fix*: Forced the Generator to create the Applicant *first*, retrieve the ID, and then create the Loan Application in the same transaction.
11. **Decimal vs Float**: Python `bfloat` vs Postgres `NUMERIC` caused precision errors.
    *   *Fix*: Implemented a helper `run_float()` to sanitize all inputs coming from the DB.
