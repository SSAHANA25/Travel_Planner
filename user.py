from flask import Blueprint, request, jsonify, session
from app import get_db_connection
import mysql.connector
from datetime import datetime

user_bp = Blueprint('user', __name__)

def require_auth():
    """Decorator to require authentication"""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    return None

@user_bp.route('/user', methods=['GET'])
def get_user():
    """Get current user information"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT id, username, email, first_name, last_name, created_at FROM users WHERE id = %s",
            (session['user_id'],)
        )
        
        user = cursor.fetchone()
        if user and user['created_at']:
            user['created_at'] = user['created_at'].isoformat()
        
        return jsonify(user), 200
        
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {e}'}), 500
    finally:
        cursor.close()
        connection.close()

@user_bp.route('/user/stats', methods=['GET'])
def get_user_stats():
    """Get user statistics for dashboard"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Total trips count
        cursor.execute("SELECT COUNT(*) as total_trips FROM trips WHERE user_id = %s", (session['user_id'],))
        total_trips = cursor.fetchone()['total_trips']
        
        # Upcoming trips count (trips with start_date in future)
        cursor.execute("SELECT COUNT(*) as upcoming_trips FROM trips WHERE user_id = %s AND start_date > CURDATE()", (session['user_id'],))
        upcoming_trips = cursor.fetchone()['upcoming_trips']
        
        # Unique destinations count
        cursor.execute('''
            SELECT COUNT(DISTINCT destination_name) as unique_destinations 
            FROM trip_destinations td 
            JOIN trips t ON td.trip_id = t.id 
            WHERE t.user_id = %s
        ''', (session['user_id'],))
        unique_destinations = cursor.fetchone()['unique_destinations']
        
        # Total days traveling
        cursor.execute('''
            SELECT SUM(DATEDIFF(COALESCE(end_date, start_date), start_date) + 1) as total_days 
            FROM trips 
            WHERE user_id = %s AND start_date IS NOT NULL
        ''', (session['user_id'],))
        result = cursor.fetchone()
        total_days = result['total_days'] if result['total_days'] else 0
        
        return jsonify({
            'total_trips': total_trips,
            'upcoming_trips': upcoming_trips,
            'destinations': unique_destinations,
            'days_traveling': total_days
        }), 200
        
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {e}'}), 500
    finally:
        cursor.close()
        connection.close()