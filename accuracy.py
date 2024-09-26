import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error
from tensorflow.keras.models import load_model
import joblib
from sklearn.preprocessing import MinMaxScaler

# Load the trained model
model = load_model('model.h5')

# Load historical stock data from CSV file
stock_data = pd.read_csv('static/data/MEL_stock_data.csv')

# Preprocess data (assuming 'Date' is present and 'LTP' is the target feature)
stock_data['Date'] = pd.to_datetime(stock_data['Date'])  # Convert 'Date' to datetime
stock_data.set_index('Date', inplace=True)  # Set 'Date' as the index

# Create additional features: Moving Averages and Percentage Change
stock_data['MA_10'] = stock_data['LTP'].rolling(window=10).mean()
stock_data['MA_50'] = stock_data['LTP'].rolling(window=50).mean()
stock_data['Pct_Change'] = stock_data['LTP'].pct_change()

# Drop rows with missing values (due to rolling window calculations)
stock_data.dropna(inplace=True)

# Rename 'LTP' to 'Close' to match the feature name used during model training
stock_data.rename(columns={'LTP': 'Close'}, inplace=True)

# Define features and target columns
features = ['Close', 'MA_10', 'MA_50', 'Pct_Change']
target = 'Close'

# Split the data into training and testing sets based on a split date
split_date = '2024-05-01'
train_data = stock_data[stock_data.index < split_date]
test_data = stock_data[stock_data.index >= split_date]

# Create and save the scaler for 'Close' prices
scaler_close = MinMaxScaler()
scaler_close.fit(train_data[['Close']])
joblib.dump(scaler_close, 'scaler_close.pkl')

# Create and save the scaler for additional features
scaler_features = MinMaxScaler()
scaler_features.fit(train_data[['MA_10', 'MA_50', 'Pct_Change']])
joblib.dump(scaler_features, 'scaler_features.pkl')

# Feature set (X) and target (y)
X_train, y_train = train_data[features], train_data[target]
X_test, y_test = test_data[features], test_data[target]

# Separate 'Close' and other features for scaling
X_test_close = X_test[['Close']]
X_test_features = X_test[['MA_10', 'MA_50', 'Pct_Change']]

# Scale the 'Close' feature using the pre-fitted scaler for 'Close'
X_test_close_scaled = scaler_close.transform(X_test_close)

# Scale the additional features (MA_10, MA_50, Pct_Change)
X_test_features_scaled = scaler_features.transform(X_test_features)

# Combine the scaled features into one array (if needed for the model input)
X_test_scaled = np.hstack([X_test_close_scaled, X_test_features_scaled])

# Generate predictions for the test data
y_pred_scaled = model.predict(X_test_scaled)

# Inverse transform the predictions and the true values
y_test_scaled = scaler_close.transform(y_test.values.reshape(-1, 1))
y_pred_inv = scaler_close.inverse_transform(y_pred_scaled)
y_test_inv = scaler_close.inverse_transform(y_test_scaled)

# Plot the actual vs predicted stock prices
plt.plot(test_data.index.to_numpy(), y_test_inv, label='Actual Prices', color='blue')
plt.plot(test_data.index.to_numpy(), y_pred_inv, label='Predicted Prices', color='orange')

# Add labels and title to the plot
plt.title('Stock Price Prediction vs Actual (Backtesting)')
plt.xlabel('Date')
plt.ylabel('Stock Price')
plt.legend()

# Show the plot
plt.show()

# Calculate performance metrics
mae = mean_absolute_error(y_test_inv, y_pred_inv)
mse = mean_squared_error(y_test_inv, y_pred_inv)
rmse = np.sqrt(mse)

# Print performance metrics
print(f"Mean Absolute Error (MAE): {mae}")
print(f"Mean Squared Error (MSE): {mse}")
print(f"Root Mean Squared Error (RMSE): {rmse}")
