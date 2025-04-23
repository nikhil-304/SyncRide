from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models.ride import Ride, RideRequest, Rating
from app.models.user import User
from app.utils.distance import calculate_distance

def get_ride_matches(user_id, start_lat, start_lon, end_lat, end_lon, departure_time, max_results=5):
    """
    Find the best matching rides for a user based on multiple factors:
    - Route similarity (start and end points)
    - Schedule compatibility
    - User ratings
    - Past ride history
    
    Returns a list of rides sorted by match score (higher is better)
    """
    user = User.query.get(user_id)
    if not user:
        return []
    
    # Get active rides that haven't departed yet
    current_time = datetime.utcnow()
    available_rides = Ride.query.filter(
        Ride.status == 'active',
        Ride.departure_time > current_time,
        Ride.available_seats > 0,
        Ride.rider_id != user_id  # Exclude user's own rides
    ).all()
    
    if not available_rides:
        return []
    
    # Calculate match scores for each ride
    scored_rides = []
    for ride in available_rides:
        score = calculate_match_score(
            user, ride, 
            start_lat, start_lon, 
            end_lat, end_lon, 
            departure_time
        )
        scored_rides.append((ride, score))
    
    # Sort by score (descending) and return top matches
    scored_rides.sort(key=lambda x: x[1], reverse=True)
    return scored_rides[:max_results]

def calculate_match_score(user, ride, start_lat, start_lon, end_lat, end_lon, preferred_time):
    """
    Calculate a match score between a user and a ride based on multiple factors.
    Higher score means better match.
    """
    # Base score
    score = 50.0
    
    # 1. Route similarity (0-40 points)
    route_score = calculate_route_similarity(
        start_lat, start_lon, end_lat, end_lon,
        ride.start_latitude, ride.start_longitude, 
        ride.end_latitude, ride.end_longitude
    )
    score += route_score * 40
    
    # 2. Schedule compatibility (0-30 points)
    time_diff = abs((ride.departure_time - preferred_time).total_seconds() / 3600)  # hours
    time_score = max(0, 1 - (time_diff / 24))  # Normalize: 0 hours = 1, 24+ hours = 0
    score += time_score * 30
    
    # 3. Rider rating (0-15 points)
    rider = User.query.get(ride.rider_id)
    avg_rating = get_user_average_rating(rider.id)
    rating_score = avg_rating / 5.0 if avg_rating else 0.6  # Default to slightly above average if no ratings
    score += rating_score * 15
    
    # 4. Past ride history (0-15 points)
    history_score = calculate_history_score(user.id, rider.id)
    score += history_score * 15
    
    return score

def calculate_route_similarity(user_start_lat, user_start_lon, user_end_lat, user_end_lon,
                              ride_start_lat, ride_start_lon, ride_end_lat, ride_end_lon):
    """
    Calculate similarity between two routes (0-1 scale)
    1 = perfect match, 0 = completely different routes
    """
    # Calculate distances between start points and end points
    start_distance = calculate_distance(
        user_start_lat, user_start_lon,
        ride_start_lat, ride_start_lon
    )
    
    end_distance = calculate_distance(
        user_end_lat, user_end_lon,
        ride_end_lat, ride_end_lon
    )
    
    # Calculate total route length for normalization
    user_route_length = calculate_distance(
        user_start_lat, user_start_lon,
        user_end_lat, user_end_lon
    )
    
    ride_route_length = calculate_distance(
        ride_start_lat, ride_start_lon,
        ride_end_lat, ride_end_lon
    )
    
    # Avoid division by zero
    if user_route_length < 0.1 or ride_route_length < 0.1:
        return 0
    
    # Normalize distances by route lengths
    start_similarity = max(0, 1 - (start_distance / (user_route_length * 0.5)))
    end_similarity = max(0, 1 - (end_distance / (user_route_length * 0.5)))
    
    # Calculate direction similarity
    user_direction = calculate_direction(user_start_lat, user_start_lon, user_end_lat, user_end_lon)
    ride_direction = calculate_direction(ride_start_lat, ride_start_lon, ride_end_lat, ride_end_lon)
    direction_diff = min(abs(user_direction - ride_direction), 360 - abs(user_direction - ride_direction))
    direction_similarity = max(0, 1 - (direction_diff / 180))
    
    # Combine similarities (weighted average)
    return (start_similarity * 0.4) + (end_similarity * 0.4) + (direction_similarity * 0.2)

def calculate_direction(start_lat, start_lon, end_lat, end_lon):
    """Calculate the direction (bearing) from start to end in degrees"""
    import math
    
    # Convert to radians
    start_lat_rad = math.radians(start_lat)
    start_lon_rad = math.radians(start_lon)
    end_lat_rad = math.radians(end_lat)
    end_lon_rad = math.radians(end_lon)
    
    # Calculate bearing
    y = math.sin(end_lon_rad - start_lon_rad) * math.cos(end_lat_rad)
    x = math.cos(start_lat_rad) * math.sin(end_lat_rad) - \
        math.sin(start_lat_rad) * math.cos(end_lat_rad) * math.cos(end_lon_rad - start_lon_rad)
    bearing = math.atan2(y, x)
    
    # Convert to degrees
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing

def get_user_average_rating(user_id):
    """Get the average rating for a user"""
    avg_rating = db.session.query(func.avg(Rating.rating)).filter(
        Rating.to_user_id == user_id
    ).scalar()
    
    return float(avg_rating) if avg_rating else None

def calculate_history_score(user_id, rider_id):
    """
    Calculate a score based on ride history between users
    Returns a value between 0-1
    """
    # Check if they've had successful rides together before
    completed_rides = RideRequest.query.filter(
        RideRequest.traveler_id == user_id,
        RideRequest.status == 'completed'
    ).join(Ride).filter(
        Ride.rider_id == rider_id
    ).count()
    
    # Check if there were any issues (cancellations, etc.)
    problem_rides = RideRequest.query.filter(
        RideRequest.traveler_id == user_id,
        RideRequest.status.in_(['cancelled', 'rejected'])
    ).join(Ride).filter(
        Ride.rider_id == rider_id
    ).count()
    
    # Calculate history score
    if completed_rides == 0 and problem_rides == 0:
        return 0.5  # Neutral if no history
    
    total_interactions = completed_rides + problem_rides
    if total_interactions == 0:
        return 0.5
    
    # More weight to completed rides
    return min(1.0, (completed_rides * 1.5) / (total_interactions * 1.0))