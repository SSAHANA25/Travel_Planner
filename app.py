from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_session import Session
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change in production
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Initialize extensions
CORS(app, supports_credentials=True, origins=['http://127.0.0.1:5500', 'http://localhost:5500'])
bcrypt = Bcrypt(app)
Session(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',  # Change to your MySQL username
    'password': 'password',  # Change to your MySQL password
    'database': 'travelease_db'
}

def get_db_connection():
    """Create and return database connection"""
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Initialize database tables
def init_db():
    """Initialize database tables"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Trips table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trips (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    start_date DATE,
                    end_date DATE,
                    travelers_count INT DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Destinations table (for trip destinations)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trip_destinations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    trip_id INT NOT NULL,
                    destination_name VARCHAR(255) NOT NULL,
                    country VARCHAR(100),
                    arrival_date DATE,
                    departure_date DATE,
                    notes TEXT,
                    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
                )
            ''')
            
            # Activities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    trip_id INT NOT NULL,
                    destination_id INT,
                    activity_name VARCHAR(255) NOT NULL,
                    activity_date DATE,
                    activity_time TIME,
                    notes TEXT,
                    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
                    FOREIGN KEY (destination_id) REFERENCES trip_destinations(id) ON DELETE SET NULL
                )
            ''')
            
            # Accommodations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accommodations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    trip_id INT NOT NULL,
                    destination_id INT,
                    accommodation_name VARCHAR(255) NOT NULL,
                    check_in DATE,
                    check_out DATE,
                    address TEXT,
                    confirmation_number VARCHAR(100),
                    notes TEXT,
                    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
                    FOREIGN KEY (destination_id) REFERENCES trip_destinations(id) ON DELETE SET NULL
                )
            ''')
            
            connection.commit()
            print("Database tables created successfully")
            
        except Error as e:
            print(f"Error creating tables: {e}")
        finally:
            cursor.close()
            connection.close()

# Routes
from routes.auth import auth_bp
from routes.trips import trips_bp
from routes.user import user_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(trips_bp, url_prefix='/api')
app.register_blueprint(user_bp, url_prefix='/api')

@app.route('/')
def home():
    return jsonify({"message": "TravelEase API is running!"})

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    init_db()  # Initialize database tables
    app.run(debug=True, port=5000)