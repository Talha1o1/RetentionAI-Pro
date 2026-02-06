# train_engine.py
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
import joblib

print("⚙️ STARTING TRAINING ENGINE...")

# 1. LOAD & CLEAN
df = pd.read_csv('churn.csv') # Ensure churn.csv is in the folder
df.drop('customerID', axis=1, inplace=True)
df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce').fillna(0)
df['Churn'] = df['Churn'].map({'Yes': 1, 'No': 0})
df_clean = pd.get_dummies(df)

# Force numeric
for col in df_clean.columns:
    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)

# 2. SPLIT
X = df_clean.drop('Churn', axis=1)
y = df_clean['Churn']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. WRAPPER CLASS (Must be defined here to be pickle-able)
class NumericXGBWrapper:
    def __init__(self, model):
        self.model = model
    def predict_proba(self, X):
        return self.model.predict_proba(X.astype(float))
    def predict(self, X):
        return self.model.predict(X.astype(float))

# 4. TRAIN
print("🤖 Training XGBoost...")
raw_model = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
raw_model.fit(X_train, y_train)

# Wrap it
final_model = NumericXGBWrapper(raw_model)

# 5. SAVE ARTIFACTS
print("💾 Saving Model & Data for App...")
joblib.dump(final_model, 'churn_model.pkl')
joblib.dump(X_test, 'X_test_data.pkl') # Save test data so we can pick customers
joblib.dump(list(X.columns), 'features.pkl') # Save column names

print("✅ DONE! You can now run the App.")