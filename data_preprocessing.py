import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

def preprocess_data(df):
    if 'Date' not in df.columns or 'LTP' not in df.columns:
        raise ValueError("DataFrame must contain 'Date' and 'LTP' columns.")
    
    if df.empty:
        raise ValueError("DataFrame is empty. Please check your data source.")
    
    # Ensure 'LTP' column is of string type before applying .str methods
    df['LTP'] = df['LTP'].astype(str)
    df['LTP'] = df['LTP'].str.replace(',', '', regex=False).astype(float)
    df = df.dropna(subset=['LTP'])

    # Convert 'Date' column to datetime, handling any conversion issues
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Apply MinMaxScaler to 'LTP' column
    scaler = MinMaxScaler(feature_range=(0, 1))
    df['LTP'] = scaler.fit_transform(df[['LTP']])
    
    # Create sequences
    data = df['LTP'].values
    X, y = [], []
    for i in range(3, len(data)):
        X.append(data[i-3:i])
        y.append(data[i])
    
    X, y = np.array(X), np.array(y)
    
    # Reshape X to 3D array for LSTM (samples, timesteps, features)
    X = X.reshape((X.shape[0], X.shape[1], 1))
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    return X_train, X_test, y_train, y_test, scaler
