import numpy as np
from tqdm import tqdm
from sklearn.preprocessing import MinMaxScaler

# Stock Data (Replace this with real stock data)
stock_data = np.array([], dtype=float)

# Normalize data
scaler = MinMaxScaler(feature_range=(0, 1))
stock_data_normalized = scaler.fit_transform(stock_data.reshape(-1, 1)).flatten()

# Sequence length
sequence_length = 3

# Prepare data sequences
def create_sequences(data, seq_length):
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i + seq_length])
        y.append(data[i + seq_length])
    return np.array(X), np.array(y)

train_X, train_y = create_sequences(stock_data_normalized, sequence_length)

# Xavier initialization
def initWeights(input_size, output_size):
    return np.random.uniform(-1, 1, (output_size, input_size)) * np.sqrt(6 / (input_size + output_size))

# Activation functions
def sigmoid(x, derivative=False):
    x = np.clip(x, -500, 500)
    if derivative:
        return x * (1 - x)
    return 1 / (1 + np.exp(-x))

def tanh(x, derivative=False):
    if derivative:
        return 1 - x ** 2
    return np.tanh(x)


class LSTM:
    def __init__(self, input_size, hidden_size, output_size, num_epochs, learning_rate):
        self.learning_rate = learning_rate
        self.hidden_size = hidden_size
        self.num_epochs = num_epochs

        # Initialize weights for gates
        self.wf = initWeights(input_size + hidden_size, hidden_size)  # shape (hidden_size, input_size + hidden_size)
        self.bf = np.zeros((hidden_size, 1))

        self.wi = initWeights(input_size + hidden_size, hidden_size)  # shape (hidden_size, input_size + hidden_size)
        self.bi = np.zeros((hidden_size, 1))

        self.wc = initWeights(input_size + hidden_size, hidden_size)  # shape (hidden_size, input_size + hidden_size)
        self.bc = np.zeros((hidden_size, 1))

        self.wo = initWeights(input_size + hidden_size, hidden_size)  # shape (hidden_size, input_size + hidden_size)
        self.bo = np.zeros((hidden_size, 1))

        # Output weight
        self.wy = initWeights(hidden_size, output_size)  # shape (output_size, hidden_size)
        self.by = np.zeros((output_size, 1))


    def reset(self):
        self.hidden_states = {-1: np.zeros((self.hidden_size, 1))}
        self.cell_states = {-1: np.zeros((self.hidden_size, 1))}
        self.outputs = {}

    def forward(self, inputs):
        self.reset()
        outputs = []

        for t in range(len(inputs)):
            # Take a single value at time step t (not the entire sequence)
            input_t = inputs[t].reshape(1, 1)  # Reshape to (1, 1), representing (input_size, 1)

            print(f"Shape of input_t: {input_t.shape}")
            print(f"Shape of hidden_state: {self.hidden_states[t - 1].shape}")

            # Concatenate hidden state and input at time t
            concat_input = np.concatenate((self.hidden_states[t - 1], input_t), axis=0)
            print(f"Shape of concat_input: {concat_input.shape}")

            # Apply gates
            ft = sigmoid(np.dot(self.wf, concat_input) + self.bf)
            it = sigmoid(np.dot(self.wi, concat_input) + self.bi)
            ct_tilde = tanh(np.dot(self.wc, concat_input) + self.bc)
            ot = sigmoid(np.dot(self.wo, concat_input) + self.bo)

            # Update cell state and hidden state
            self.cell_states[t] = ft * self.cell_states[t - 1] + it * ct_tilde
            self.hidden_states[t] = ot * tanh(self.cell_states[t])

            # Output layer
            output = np.dot(self.wy, self.hidden_states[t]) + self.by
            outputs.append(output)

        return outputs



    def backward(self, errors, inputs):
        # Backpropagation steps omitted for clarity (same as before)
        pass

    def train(self, X, y):
        for epoch in tqdm(range(self.num_epochs)):
            # Run the forward pass to get predictions
            predictions = self.forward(X)

            # y is already a scalar (single value), so no need to reshape or loop through it
            error = y - predictions[-1]  # Calculate the error with the last prediction

            # Run the backward pass to adjust the weights (if implemented)
            self.backward([error], X)  # Backward expects a list of errors


    def predict(self, X):
        return self.forward(X)

# Training the LSTM
input_size = 1  # Fix input size to 1, as each time step provides one input value
hidden_size = 25
output_size = 1
num_epochs = 500
learning_rate = 0.01

lstm = LSTM(input_size, hidden_size, output_size, num_epochs, learning_rate)

# Reshape input for LSTM
print(train_X.shape)
train_X_reshaped = train_X.reshape((train_X.shape[0], sequence_length, 1))
for i in range(len(train_X_reshaped)):
    lstm.train(train_X_reshaped[i], train_y[i])

# Predict next 7 days
def predict_next_days(model, data, days):
    predictions = []
    current_seq = data[-sequence_length:]
    
    for _ in range(days):
        current_seq_reshaped = current_seq.reshape((sequence_length, 1))  # Reshape for LSTM
        next_pred = model.predict(current_seq_reshaped)[-1]
        predictions.append(next_pred)
        current_seq = np.append(current_seq[1:], next_pred)  # Shift window for next prediction
        
    return predictions

predictions = predict_next_days(lstm, stock_data_normalized, 7)
predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))

print(predictions)
