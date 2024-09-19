import numpy as np
def predict_multiple_days(model, X_test, scaler, days=7):
    if X_test is None or len(X_test) == 0:
        raise ValueError("Test data is empty or not available.")
    
    if not hasattr(model, 'predict'):
        raise TypeError("Model is not a Keras model. Ensure it is correctly loaded.")
    
    # Ensure dropout is disabled during inference
    model.trainable = False
    
    # Debugging information
    print(f"Initial X_test shape: {X_test.shape}")

    X_test = np.array(X_test)
    last_sequence = X_test[-1]
    
    predictions = []

    for day in range(days):
        last_sequence = np.array(last_sequence)
        reshaped_sequence = last_sequence.reshape(1, last_sequence.shape[0], last_sequence.shape[1])
        
        # Debugging information
        print(f"Day {day + 1} - Shape of reshaped_sequence: {reshaped_sequence.shape}")

        try:
            prediction = model.predict(reshaped_sequence)
        except Exception as e:
            print(f"Prediction error: {e}")
            raise
        
        prediction_value = float(scaler.inverse_transform(prediction)[0])
        predictions.append(prediction_value)
        
        # Debugging information
        print(f"Day {day + 1} - Prediction value: {prediction_value}")

        # Prepare input for the next prediction
        scaled_prediction = scaler.transform([[prediction_value]])
        last_sequence = np.append(last_sequence[1:], scaled_prediction)
        last_sequence = last_sequence.reshape(-1, 1)
    
    return predictions
