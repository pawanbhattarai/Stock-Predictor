import numpy as np
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import LSTM, Dense
import pandas as pd

# Load the historical stock data
file_path = 'static/data/RURU_stock_data.csv'
stock_data = pd.read_csv(file_path)

# Prepare the data for LSTM
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(stock_data['LTP'].values.reshape(-1, 1))

# Define the training and testing dataset
train_data_len = int(len(scaled_data) * 0.8)
train_data = scaled_data[:train_data_len]
test_data = scaled_data[train_data_len:]

# Create training dataset in sequences of 60 time-steps
def create_dataset(data, time_step=60):
    x, y = [], []
    for i in range(len(data) - time_step):
        x.append(data[i:i + time_step, 0])
        y.append(data[i + time_step, 0])
    return np.array(x), np.array(y)

time_step = 60
X_train, y_train = create_dataset(train_data, time_step)

# Reshape X_train for LSTM input
X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)

# Build the LSTM model
model = Sequential()
model.add(LSTM(units=50, return_sequences=True, input_shape=(X_train.shape[1], 1)))
model.add(LSTM(units=50, return_sequences=False))
model.add(Dense(units=25))
model.add(Dense(units=1))

# Compile the model
model.compile(optimizer='adam', loss='mean_squared_error')

# Train the model
model.fit(X_train, y_train, batch_size=1, epochs=10)

# Prepare test data for prediction
X_test, y_test = create_dataset(test_data, time_step)
X_test = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)

# Predict using the model
predictions = model.predict(X_test)

# Inverse scale the predictions
predictions = scaler.inverse_transform(predictions)

# Get the last 60 days from the original data for future predictions
last_60_days = scaled_data[-time_step:]
last_60_days = np.array([last_60_days])

# Predict the next 3 days using the LSTM model
last_60_days = last_60_days.reshape(last_60_days.shape[0], last_60_days.shape[1], 1)
next_3_days_prediction = model.predict(last_60_days)

# Inverse scale the predicted prices for the next 3 days
next_3_days_prediction = scaler.inverse_transform(next_3_days_prediction)

print(next_3_days_prediction)
