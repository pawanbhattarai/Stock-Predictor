from flask import Flask, flash, json, request, session, redirect, jsonify, url_for, render_template
from flask_bcrypt import Bcrypt
import joblib
import psycopg2
import logging
from contextlib import closing
from data_preprocessing import preprocess_data
from predictor import predict_multiple_days
import os
from nepse_scraper import scrape_merolagani_data,scrape_company_symbols

import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
bcrypt = Bcrypt(app)

#for admin we declare static username and password
ADMIN_USERNAME = "Admin"
ADMIN_PASSWORD = "Admin"

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

@app.route('/profile')
def profile():
    return render_template('profile.html')  # Rendering profile.html

# If you want to handle the redirect explicitly
@app.route('/redirect_to_profile')
def redirect_to_profile():
    return redirect(url_for('profile'))

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
    session.clear()
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
   
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['is_admin'] = True  # Set session for admin
        return jsonify({'redirect_url': url_for('admin_panel')}), 200
    else:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
                user = cursor.fetchone()

                if user and bcrypt.check_password_hash(user[2], password):
                    session['user_id'] = user[0]
                    session['username'] = username
                    session['has_predicted'] = False
                    session['is_admin'] = False
                    return jsonify({'redirect_url': url_for('dashboard')}), 200  # Send redirect URL for regular users
                else:
                    return jsonify({'error': 'Invalid username or password'}), 401
        except Exception as e:
            logging.error(f'Error during login: {e}')
            return jsonify({'error': 'Internal Server Error'}), 500
    
@app.route('/admin_panel')
def admin_panel():
    if session.get('is_admin'):
        # Render the admin dashboard
        return render_template('admin_panel.html',user_logged_in=True)

    
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
    
@app.route('/save_portfolio', methods=['POST'])
def save_portfolio():
    # Check if user is authenticated
    if 'username' not in session:
        logging.error("Unauthorized access attempt.")
        return jsonify({'error': 'Unauthorized'}), 403

    # Log the incoming request data
    data = request.get_json()
    logging.info(f"Received data: {data}")
    
    symbol = data.get('symbol')
    qty = data.get('quantity')
    price=data.get('price')
    
    # Default qty to 0 if not provided
    if not qty:
        qty = 0

    if not symbol:
        logging.error("Invalid input: symbol is missing.")
        return jsonify({'error': 'Invalid input'}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Assuming user_id is stored in the session
            user_id = session.get('user_id')

            # Log user_id for debug purposes
            if user_id:
                logging.info(f"User ID from session: {user_id}")
            else:
                logging.error("User ID not found in session.")
                return jsonify({'error': 'User ID missing'}), 400

            # Insert the stock symbol and quantity into the database
            cursor.execute('''
                INSERT INTO myprotfolio (u_id, stock_symbol, qty,price)
                VALUES (%s, %s, %s,%s)
            ''', (user_id, symbol, qty,price))

            conn.commit()
            logging.info(f"Successfully added stock {symbol} with quantity {qty} for user {user_id}")
            return jsonify({'success': True}), 200

    except Exception as e:
        logging.error(f'Error saving stock: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500


@app.route('/get_portfolio', methods=['GET'])
def get_portfolio():
    username = session.get('username')

    if not username:
        return jsonify({'error': 'User not logged in'}), 401

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sp.stock_symbol, sp.qty,sp.price
                FROM myprotfolio sp
                JOIN users u ON sp.u_id = u.id
                WHERE u.username = %s
            ''', (username,))
            
            portfolio = cursor.fetchall()

            if not portfolio:
                return jsonify({'portfolio': []})
            
            # Extract both stock symbol and quantity
            portfolio_data = [{'symbol': row[0], 'quantity': row[1], 'price': row[2]} for row in portfolio]

        return jsonify({'portfolio': portfolio_data})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_stock', methods=['POST'])
def delete_stock():
    data = request.get_json()
    stock_symbol = data.get('symbol')
    username = session.get('username')

    if not username:
        return jsonify({'error': 'User not logged in'}), 401

    if not stock_symbol:
        return jsonify({'error': 'No stock symbol provided'}), 400

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM myprotfolio
                WHERE stock_symbol = %s
                AND u_id = (SELECT id FROM users WHERE username = %s)
            ''', (stock_symbol, username))
            conn.commit()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_portfolio_stock', methods=['GET'])
def get_portfolio_stock():
    username = session.get('username')

    if not username:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sp.stock_symbol
                FROM myprotfolio sp
                JOIN users u ON sp.u_id = u.id
                WHERE u.username = %s
            ''', (username,))
            portfolio = cursor.fetchall()
            stock_list = [{'symbol': stock[0]} for stock in portfolio]  # List of stock symbols
        return jsonify({'portfolio': stock_list})
    except Exception as e:
        logging.error(f'Error fetching portfolio: {e}')
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
    if session['is_admin']==False:
        if 'username' not in session:
            return jsonify({'error': 'Unauthorized'}), 403

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if session['is_admin']==True:

                # Admin can access any prediction
                cursor.execute('''
                    SELECT sp.prediction
                    FROM savedprediction sp
                    JOIN users u ON sp.u_id = u.id
                    WHERE sp.p_id = %s
                ''', (p_id,))
            else:
                # Regular users can only access their own predictions
                cursor.execute('''
                    SELECT sp.prediction
                    FROM savedprediction sp
                    JOIN users u ON sp.u_id = u.id
                    WHERE sp.p_id = %s AND u.username = %s
                ''', (p_id, session['username']))
            result = cursor.fetchone()
            
            if result:
                prediction = result[0]
                if isinstance(prediction, str):
                    prediction = json.loads(prediction)
                return jsonify({'success': True, 'prediction': prediction}), 200
            else:
                return jsonify({'error': 'Prediction not found'}), 404
    except Exception as e:
        logging.error(f'Error fetching saved prediction details: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/get_user_details', methods=['GET'])
def get_user_details():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    username = session['username']
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT username, email,password FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()

            # Check if user is found and if the returned tuple has the expected data
            if user is None:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            if len(user) < 2:
                return jsonify({'success': False, 'error': 'Incomplete user data'}), 500

            # Return the user details
            return jsonify({
                'success': True,
                'name': user[0],  # username
                'email': user[1],
                'password':user[2]
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    username = session['username']
    data = request.form
    new_email = data.get('email')
    new_password = data.get('password')

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Fetch the current hashed password from the database
            cursor.execute('SELECT password FROM users WHERE username = %s', (username,))
            current_hashed_password = cursor.fetchone()[0]

            # If a new password is provided, check if it's already hashed
            if new_password:
                if current_hashed_password== new_password:
                    # The new password is already hashed, do not update it
                    cursor.execute('UPDATE users SET email = %s WHERE username = %s',
                                   (new_email, username))
                else:
                    # The new password is plain text, so hash it and update the password
                    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                    cursor.execute('UPDATE users SET email = %s, password = %s WHERE username = %s',
                                   (new_email, hashed_password, username))
            else:
                # Only update the email if no new password is provided
                cursor.execute('UPDATE users SET email = %s WHERE username = %s',
                               (new_email, username))

            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_all_users', methods=['GET'])
def get_all_users():
    if session.get('is_admin'):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Fetch all users
                cursor.execute("SELECT id, username, email FROM users")
                users = cursor.fetchall()
                
                # Fetch prediction history for each user
                cursor.execute("SELECT * FROM savedprediction")
                predictions = cursor.fetchall()
                
                conn.close()
                user_list = [{'id': user[0], 'username': user[1], 'email': user[2]} for user in users]

                return jsonify({
                    'success': True,
                    'users': user_list,
                    'predictions': predictions
                })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/get_user_predictions/<int:user_id>', methods=['GET'])
def get_user_predictions(user_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Fetch saved predictions for the user
            cursor.execute("SELECT p_id, symbol, created_at FROM savedprediction WHERE u_id = %s", (user_id,))
            predictions = cursor.fetchall()

        conn.close()

        if predictions:
            # Prepare the data for JSON response
            prediction_data = [{
                'p_id': p[0],
                'symbol': p[1],
                'created_at': p[2]
            } for p in predictions]

            return jsonify({'success': True, 'saved_predictions': prediction_data})
        else:
            return jsonify({'success': False, 'error': 'No saved predictions found for this user'})
    except Exception as e:
        print(f"Error fetching saved predictions: {e}")
        return jsonify({'success': False, 'error': 'Error occurred while fetching saved predictions'})


@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if session.get('is_admin'):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Delete the user and their prediction history
                print(user_id)
                cursor.execute("DELETE FROM savedprediction WHERE u_id = %s", (user_id,))
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()

                conn.close()
                return jsonify({'success': True, 'message': 'User deleted successfully'})
        except Exception as e:
            print(f"Error deleting user: {e}")
            return jsonify({'success': False, 'error': 'Database error occurred'}), 500
    else:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

@app.route('/delete_prediction/<int:p_id>', methods=['DELETE'])
def delete_prediction(p_id):
    if session['is_admin']==False:
        if 'username' not in session:
            return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if session['is_admin']:
                # Admins can delete any prediction
                cursor.execute('DELETE FROM savedprediction WHERE p_id = %s', (p_id,))
            else:
                # Regular users can only delete their own predictions
                cursor.execute('''
                    DELETE FROM savedprediction
                    WHERE p_id = %s AND u_id = (SELECT id FROM users WHERE username = %s)
                ''', (p_id, session['username']))

            conn.commit()

            if cursor.rowcount > 0:
                return jsonify({'success': True, 'message': 'Prediction deleted successfully'}), 200
            else:
                return jsonify({'error': 'Prediction not found or not authorized'}), 404
    except Exception as e:
        logging.error(f'Error deleting prediction: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/scrape_stocks', methods=['GET'])
def scrape_stocks():
    if session.get('is_admin'):  # Check if the user is an admin
        try:
            # Scrape the stock symbols and company names
            symbols = scrape_company_symbols()

            # Insert stock symbols into the database
            with get_db_connection() as conn:
                cursor = conn.cursor()

                for symbol, name in symbols:
                    # Insert only if the symbol does not already exist
                    cursor.execute('''
                        INSERT INTO listed_stocks_nepse (symbol, name)
                        VALUES (%s, %s)
                        ON CONFLICT (symbol) DO NOTHING
                    ''', (symbol, name))

                conn.commit()

            # Return success response
            return jsonify({'success': True})

        except Exception as e:
            logging.error(f"Error occurred: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
@app.route('/all_stocks', methods=['GET'])
def get_all_stocks():
    try:
        # Insert stock symbols into the database
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Fetch all saved stocks from the database
            cursor.execute("SELECT * FROM listed_stocks_nepse")
            listed_stocks = cursor.fetchall()

        # Return the scraped symbols and listed stocks
        return jsonify({
            'success': True,
            'listed_stocks': [{'Symbol': stock[1], 'Name': stock[2]} for stock in listed_stocks]
        })
    except Exception as e:
        logging.error(f"Error occurred: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error occurred during scraping'})

        
if __name__ == '__main__':
    app.run(debug=True)  