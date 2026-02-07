import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from decimal import Decimal

# Define the Feed-Forward Neural Network
class LoanNet(nn.Module):
    def __init__(self, input_size=9): # Increased input size to include noise
        super(LoanNet, self).__init__()
        # Input: [Income, Score, Debt, DTI, Collateral, AccountAge, AvgTrans, Priority, Loyalty]
        self.fc1 = nn.Linear(input_size, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1) # Output: Probability of Eligibility (0-1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        out = self.relu(out)
        out = self.fc3(out)
        out = self.sigmoid(out)
        return out

class LoanDataset(Dataset):
    def __init__(self, features, labels):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32).unsqueeze(1) # [N, 1]

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

def run_float(val):
    if isinstance(val, Decimal):
        return float(val)
    if val is None:
        return 0.0
    return float(val)

def prepare_features(row):
    # Extracts features from a raw DB row
    # Row expected: [Income, CreditScore, Debt, DTI, Collateral, AccountAge, AvgTrans, Priority, Loyalty]
    
    # 1. Core Financial Features (Signal)
    annual_income = run_float(row[0])
    credit_score = float(row[1]) if row[1] else 0.0
    existing_debt = run_float(row[2])
    dti = run_float(row[3])
    collateral = run_float(row[4])
    
    # 2. Noise Features (The agent should learn to ignore these)
    account_age_days = float(row[5]) if row[5] else 0.0
    avg_trans_count = float(row[6]) if row[6] else 0.0
    processing_priority = float(row[7]) if row[7] else 0.0
    loyalty_points = float(row[8]) if row[8] else 0.0

    # Normalization (Scaling to 0-1 range approx)
    norm_income = min(annual_income / 3000000.0, 1.0) 
    norm_score = credit_score / 900.0
    norm_debt = min(existing_debt / 1000000.0, 1.0)
    norm_dti = min(dti / 1.0, 1.0) # DTI > 1 is rare/bad
    norm_collateral = min(collateral / 5000000.0, 1.0)
    
    # Noise Normalization
    norm_account_age = min(account_age_days / 5000.0, 1.0)
    norm_avg_trans = min(avg_trans_count / 100.0, 1.0)
    norm_priority = min(processing_priority / 10.0, 1.0)
    norm_loyalty = min(loyalty_points / 5000.0, 1.0)
    
    return [norm_income, norm_score, norm_debt, norm_dti, norm_collateral,
            norm_account_age, norm_avg_trans, norm_priority, norm_loyalty]

def train_model(features, labels, epochs=5):
    print("Initializing training...")
    dataset = LoanDataset(features, labels)
    dataloader = DataLoader(dataset, batch_size=64, shuffle=True)
    
    model = LoanNet()
    criterion = nn.BCELoss() # Binary Cross Entropy for Probability
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    for epoch in range(epochs):
        total_loss = 0
        for batch_features, batch_labels in dataloader:
            optimizer.zero_grad()
            outputs = model(batch_features)
            loss = criterion(outputs, batch_labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(dataloader):.4f}")
        
    return model

def predict_single(model, feature_vector):
    # Inference
    model.eval()
    with torch.no_grad():
        inputs = torch.tensor([feature_vector], dtype=torch.float32)
        output = model(inputs)
        return output.item()
