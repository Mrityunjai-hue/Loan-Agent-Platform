-- Create Tables for PostgreSQL (Supabase/Neon)

-- 1. Applicants Table (Personal Details)
CREATE TABLE IF NOT EXISTS Applicants (
    ApplicantID SERIAL PRIMARY KEY,
    FirstName VARCHAR(100),
    LastName VARCHAR(100),
    Age INT,
    Email VARCHAR(200),
    Address VARCHAR(255),          -- PII/High Cardinality
    PhoneNumber VARCHAR(20),       -- PII
    MaidenName VARCHAR(100),       -- Noise
    SocialMediaHandle VARCHAR(100),-- Noise
    LastLoginIP VARCHAR(50),       -- Noise
    LoyaltyPoints INT,             -- Noise
    EmploymentStatus VARCHAR(50), 
    JobTitle VARCHAR(100),
    YearsExperience INT,
    CreatedAt TIMESTAMP DEFAULT NOW()
);

-- 2. FinancialProfile Table (Income, Assets, Credit)
CREATE TABLE IF NOT EXISTS FinancialProfile (
    ProfileID SERIAL PRIMARY KEY,
    ApplicantID INT REFERENCES Applicants(ApplicantID),
    AnnualIncome DECIMAL(18, 2),
    CreditScore INT, -- 300 to 850
    ExistingDebt DECIMAL(18, 2),
    DebtToIncomeRatio DECIMAL(5, 2), 
    CollateralValue DECIMAL(18, 2),
    CollateralType VARCHAR(100),
    AccountAgeDays INT,              -- Noise
    AvgTransactionCount INT,         -- Noise
    LastBranchVisited VARCHAR(100)   -- Noise
);

-- 3. LoanApplications Table (The Request)
CREATE TABLE IF NOT EXISTS LoanApplications (
    ApplicationID SERIAL PRIMARY KEY,
    ApplicantID INT REFERENCES Applicants(ApplicantID),
    RequestAmount DECIMAL(18, 2),
    LoanPurpose VARCHAR(200), 
    LoanToCostRatio DECIMAL(5, 2),
    ApplicationSource VARCHAR(50),   -- Noise
    ReferralCode VARCHAR(50),        -- Noise
    ProcessingPriority INT,          -- Noise
    ApplicationDate TIMESTAMP DEFAULT NOW(),
    Status VARCHAR(50) DEFAULT 'Pending' -- Pending, Approved, Rejected
);

-- 4. Predictions Table (Agent Output)
CREATE TABLE IF NOT EXISTS Predictions (
    PredictionID SERIAL PRIMARY KEY,
    ApplicationID INT REFERENCES LoanApplications(ApplicationID),
    PredictedEligibilityScore DECIMAL(5, 2), -- 0.0 to 1.0
    RecommendedLoanAmount DECIMAL(18, 2),
    ModelRiskLevel VARCHAR(50), -- Low, Medium, High
    Reasoning TEXT,
    GeneratedAt TIMESTAMP DEFAULT NOW()
);
