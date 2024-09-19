from flask import Flask, flash, json, request, session, redirect, jsonify, url_for, render_template
from flask_bcrypt import Bcrypt
import joblib
import psycopg2
import logging
from contextlib import closing
from nepse_scraper import scrape_merolagani_data
from data_preprocessing import preprocess_data
from predictor import predict_multiple_days
import matplotlib.pyplot as plt
import os
import io
import numpy as np
import base64
import pandas as pd
from tensorflow.keras.models import load_model

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
bcrypt = Bcrypt(app)

logging.basicConfig(level=logging.INFO)

# Load model and scaler
model = load_model('model.h5')
scaler = joblib.load('scaler.pkl')

# PostgreSQL connection
def get_db_connection():
    conn = psycopg2.connect(
        user="adempiere",
        password="adempiere",
        host="localhost",
        port="5432",
        database="StockAnalysis"
    )
    return closing(conn)

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET'])
def login():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        return jsonify({'error': 'All fields are required'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()

            if user:
                return jsonify({'error': 'Username already exists'}), 409

            cursor.execute('INSERT INTO users (username, password, email) VALUES (%s, %s, %s)', (username, hashed_password, email))
            conn.commit()
            return jsonify({'message': 'Registration successful'}), 201
    except Exception as e:
        logging.error(f'Error during registration: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    session.pop('has_predicted', None)  # Remove has_predicted from session
    return redirect(url_for('dashboard'))  # Redirect to login page

@app.route('/login', methods=['POST'])
def login_post():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()

            if user and bcrypt.check_password_hash(user[2], password):
                session['username'] = username
                session['has_predicted'] = False
                return redirect(url_for('dashboard'))
            else:
                return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as e:
        logging.error(f'Error during login: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/dashboard')
def dashboard():
    user_logged_in = 'username' in session
    return render_template('dashboard.html', user_logged_in=user_logged_in)

@app.route('/predict', methods=['POST'])
def predict():
    
    if request.content_type != 'application/json':
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    symbol = data.get('symbol')
    days = data.get('days')

    if not symbol or not days:
        return jsonify({"error": "Symbol or days not provided"}), 400

    if 'username' not in session:
        if session.get('has_predicted', False):
            return jsonify({"error": "logging required"}), 403
        else:
            session['has_predicted'] = True

    try:
        save_directory = "static/data/"
        csv_file = os.path.join(save_directory, f"{symbol}_stock_data.csv")

        if not os.path.exists(csv_file):
            try:
                from nepse_scraper import scrape_merolagani_data  
                df = scrape_merolagani_data(symbol)
                if df.empty:
                    return jsonify({"error": "Failed to scrape stock data"}), 404
                df.to_csv(csv_file, index=False)
            except Exception as scrape_error:
                logging.error(f"Error while scraping data: {scrape_error}")
                return jsonify({"error": "Failed to scrape stock data"}), 500
        else:
            df = pd.read_csv(csv_file)

        if 'LTP' not in df.columns:
            return jsonify({"error": "LTP (Close) data not found in CSV"}), 500

        historical_ltp = df['LTP'].tolist()
        ltp=historical_ltp[0]
        print("etest ltp is {ltp}")
        if len(historical_ltp) < days:
            historical_ltp_last_n_days = historical_ltp + ['-' for _ in range(days - len(historical_ltp))]
        else:
            historical_ltp_last_n_days = historical_ltp[:days]
        while True:
                X_train, X_test, y_train, y_test, scaler = preprocess_data(df)
                model = load_model('model.h5')
                predictions = predict_multiple_days(model, X_test, scaler, days)

                predictions = list(predictions)

                if (predictions[0] != predictions[1]) and ((predictions[0] < (ltp+ltp*0.06) and predictions[0] > ltp) or (predictions[0] > (ltp-ltp*0.06) and predictions[0] < ltp)):
                    break
        results = {
            "predictions": [
                {
                    "day": f"Day {i+1}",
                    "predicted_close": round(float(pred), 2),
                    "historical_close": historical_ltp_last_n_days[i] if historical_ltp_last_n_days[i] != '-' else '-'
                } for i, pred in enumerate(predictions)
            ]
        }

        return jsonify(results), 200

    except Exception as e:
        logging.error(f'Error during prediction: {e}')
        return jsonify({"error": str(e)}), 500
    
@app.route('/save_prediction', methods=['POST'])
def save_prediction():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    username = session['username']
    data = request.get_json()
    symbol = data.get('symbol')
    prediction = data.get('prediction')

    if not symbol or not prediction:
        return jsonify({'error': 'Invalid input'}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Fetch user id
            cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
            user_id = cursor.fetchone()[0]

            # Insert prediction
            cursor.execute('''
                INSERT INTO savedPrediction (u_id, prediction,symbol)
                VALUES (%s, %s,%s)
            ''', (user_id, json.dumps(prediction),symbol))

            conn.commit()
            return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f'Error saving prediction: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500
    
@app.route('/saved_predictions', methods=['GET'])
def saved_predictions():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    username = session['username']
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sp.p_id, sp.created_at, sp.symbol
                FROM savedPrediction sp
                JOIN users u ON sp.u_id = u.id
                WHERE u.username = %s
            ''', (username,))
            predictions = cursor.fetchall()
            
            results = []
            for row in predictions:
                p_id, created_at, symbol = row
                results.append({
                    'p_id': p_id,
                    'symbol': symbol,
                    'created_at': created_at
                })
            return jsonify({'saved_predictions': results}), 200
    except Exception as e:
        logging.error(f'Error fetching saved predictions: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500
    
@app.route('/saved_prediction/<int:p_id>', methods=['GET'])
def saved_prediction(p_id):
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sp.prediction, sp.symbol
                FROM savedPrediction sp
                JOIN users u ON sp.u_id = u.id
                WHERE sp.p_id = %s AND u.username = %s
            ''', (p_id, session['username']))
            result = cursor.fetchone()
            
            if result:
                prediction, symbol = result
                return jsonify({'prediction': prediction, 'symbol': symbol}), 200
            else:
                return jsonify({'error': 'Prediction not found'}), 404
    except Exception as e:
        logging.error(f'Error fetching saved prediction details: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500


if __name__ == '__main__':
    app.run(debug=True)  