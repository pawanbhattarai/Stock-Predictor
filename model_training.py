import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib

def preprocess_data(df):
    scaler = MinMaxScaler(feature_range=(0, 1))
    df['Scaled_Close'] = scaler.fit_transform(df[['Close']])
    
    X, y = [], []
    for i in range(60, len(df)):
        X.append(df['Scaled_Close'].iloc[i-60:i].values)
        y.append(df['Scaled_Close'].iloc[i])
    
    X, y = np.array(X), np.array(y)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    return X_train, X_test, y_train, y_test, scaler

def build_and_train_model(X_train, y_train, scaler, X_val, y_val):
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])))
    model.add(Dropout(0.3))
    model.add(LSTM(units=50, return_sequences=False))
    model.add(Dropout(0.3))
    model.add(Dense(1))
    optimizer = Adam(learning_rate=0.001)
    model.compile(loss='mean_squared_error', optimizer=optimizer, metrics=['mean_absolute_error'])
    early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
    model.fit(X_train, y_train, epochs=100, batch_size=32, validation_data=(X_val, y_val), callbacks=[early_stopping])
    model.save('model.h5')  # Save the model
    joblib.dump(scaler, 'scaler.pkl')  # Save the scaler
    return model

if __name__ == "__main__":
    df = pd.read_csv('path_to_your_data.csv')  # Replace with your data path
    X_train, X_test, y_train, y_test, scaler = preprocess_data(df)
    model = build_and_train_model(X_train, y_train, scaler, X_test, y_test)
