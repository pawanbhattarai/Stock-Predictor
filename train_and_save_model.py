import pandas as pd
from data_preprocessing import preprocess_data
from model_training import build_and_train_model
import joblib
from nepse_scraper import scrape_merolagani_data

# Scrape data
symbol = 'ANLB'  # Replace with the symbol of your choice
df = scrape_merolagani_data(symbol)

# Preprocess data
X_train, X_test, y_train, y_test, scaler = preprocess_data(df)

# Train the model
model = build_and_train_model(X_train, y_train)

# Save the model and scaler
joblib.dump(model, 'model.pkl')
joblib.dump(scaler, 'scaler.pkl')

print("Model and scaler saved successfully.")
