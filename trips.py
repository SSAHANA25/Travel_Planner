from flask import Blueprint, request, jsonify, session
from app import get_db_connection
import mysql.connector
from datetime import datetime

trips_bp = Blueprint('trips', __name__)

def require_auth():
    """Decorator to require authentication"""
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    return None

@trips_bp.route('/trips', methods=['GET'])
def get_trips():
    """Get all trips for the authenticated user"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute('''
            SELECT t.*, COUNT(td.id) as destination_count 
            FROM trips t 
            LEFT JOIN trip_destinations td ON t.id = td.trip_id 
            WHERE t.user_id = %s 
            GROUP BY t.id 
            ORDER BY t.created_at DESC
        ''', (session['user_id'],))
        
        trips = cursor.fetchall()
        
        # Convert dates to strings for JSON serialization
        for trip in trips:
            if trip['start_date']:
                trip['start_date'] = trip['start_date'].isoformat()
            if trip['end_date']:
                trip['end_date'] = trip['end_date'].isoformat()
            if trip['created_at']:
                trip['created_at'] = trip['created_at'].isoformat()
        
        return jsonify(trips), 200
        
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {e}'}), 500
    finally:
        cursor.close()
        connection.close()

@trips_bp.route('/trips', methods=['POST'])
def create_trip():
    """Create a new trip"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    data = request.get_json()
    
    if not data or not data.get('title'):
        return jsonify({'error': 'Trip title is required'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Parse dates
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else None
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None
        
        cursor.execute('''
            INSERT INTO trips (user_id, title, description, start_date, end_date, travelers_count)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            session['user_id'],
            data['title'],
            data.get('description', ''),
            start_date,
            end_date,
            data.get('travelers_count', 1)
        ))
        
        connection.commit()
        trip_id = cursor.lastrowid
        
        return jsonify({
            'message': 'Trip created successfully',
            'trip_id': trip_id
        }), 201
        
    except ValueError as e:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {e}'}), 500
    finally:
        cursor.close()
        connection.close()

@trips_bp.route('/trips/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    """Get a specific trip with details"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Get trip basic info
        cursor.execute('''
            SELECT * FROM trips WHERE id = %s AND user_id = %s
        ''', (trip_id, session['user_id']))
        
        trip = cursor.fetchone()
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404
        
        # Get destinations
        cursor.execute('''
            SELECT * FROM trip_destinations WHERE trip_id = %s ORDER BY arrival_date
        ''', (trip_id,))
        destinations = cursor.fetchall()
        
        # Get activities
        cursor.execute('''
            SELECT a.*, td.destination_name 
            FROM activities a 
            LEFT JOIN trip_destinations td ON a.destination_id = td.id 
            WHERE a.trip_id = %s 
            ORDER BY a.activity_date, a.activity_time
        ''', (trip_id,))
        activities = cursor.fetchall()
        
        # Get accommodations
        cursor.execute('''
            SELECT ac.*, td.destination_name 
            FROM accommodations ac 
            LEFT JOIN trip_destinations td ON ac.destination_id = td.id 
            WHERE ac.trip_id = %s 
            ORDER BY ac.check_in
        ''', (trip_id,))
        accommodations = cursor.fetchall()
        
        # Convert dates to strings
        for item in [trip] + destinations + activities + accommodations:
            for key, value in item.items():
                if isinstance(value, datetime) or hasattr(value, 'isoformat'):
                    item[key] = value.isoformat()
        
        return jsonify({
            'trip': trip,
            'destinations': destinations,
            'activities': activities,
            'accommodations': accommodations
        }), 200
        
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {e}'}), 500
    finally:
        cursor.close()
        connection.close()

@trips_bp.route('/trips/<int:trip_id>', methods=['PUT'])
def update_trip(trip_id):
    """Update a trip"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    data = request.get_json()
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Verify trip belongs to user
        cursor.execute('SELECT id FROM trips WHERE id = %s AND user_id = %s', (trip_id, session['user_id']))
        if not cursor.fetchone():
            return jsonify({'error': 'Trip not found'}), 404
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        if 'title' in data:
            update_fields.append("title = %s")
            update_values.append(data['title'])
        
        if 'description' in data:
            update_fields.append("description = %s")
            update_values.append(data['description'])
        
        if 'start_date' in data:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data['start_date'] else None
            update_fields.append("start_date = %s")
            update_values.append(start_date)
        
        if 'end_date' in data:
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data['end_date'] else None
            update_fields.append("end_date = %s")
            update_values.append(end_date)
        
        if 'travelers_count' in data:
            update_fields.append("travelers_count = %s")
            update_values.append(data['travelers_count'])
        
        if update_fields:
            update_values.append(trip_id)
            cursor.execute(
                f"UPDATE trips SET {', '.join(update_fields)} WHERE id = %s",
                update_values
            )
            connection.commit()
        
        return jsonify({'message': 'Trip updated successfully'}), 200
        
    except ValueError as e:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {e}'}), 500
    finally:
        cursor.close()
        connection.close()

@trips_bp.route('/trips/<int:trip_id>', methods=['DELETE'])
def delete_trip(trip_id):
    """Delete a trip"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Verify trip belongs to user
        cursor.execute('SELECT id FROM trips WHERE id = %s AND user_id = %s', (trip_id, session['user_id']))
        if not cursor.fetchone():
            return jsonify({'error': 'Trip not found'}), 404
        
        cursor.execute('DELETE FROM trips WHERE id = %s', (trip_id,))
        connection.commit()
        
        return jsonify({'message': 'Trip deleted successfully'}), 200
        
    except mysql.connector.Error as e:
        return jsonify({'error': f'Database error: {e}'}), 500
    finally:
        cursor.close()
        connection.close()