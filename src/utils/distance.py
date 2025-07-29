"""
Distance calculation utilities for match display
"""
import math
from typing import Optional
from src.models import GroupMember


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """
    Calculate distance between two GPS coordinates using Haversine formula
    Returns distance in kilometers (rounded)
    """
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    # Calculate distance and round to nearest km
    distance_km = c * r
    return round(distance_km)


def get_match_distance_info(member1: GroupMember, member2: GroupMember) -> str:
    """
    Get distance information for match display
    
    Returns formatted distance string:
    - If both have coordinates: "📍 23 км away"
    - If same city: "📍 Same city"
    - If different cities same country: "📍 Different city, Russia"
    - If different countries: "📍 Moscow, Russia"
    - If no location data: "📍 Location not specified"
    """
    import logging
    
    # Debug logging
    logging.warning(f"[get_match_distance_info] member1: lat={getattr(member1, 'geolocation_lat', None)}, lon={getattr(member1, 'geolocation_lon', None)}, city={getattr(member1, 'city', None)}, country={getattr(member1, 'country', None)}")
    logging.warning(f"[get_match_distance_info] member2: lat={getattr(member2, 'geolocation_lat', None)}, lon={getattr(member2, 'geolocation_lon', None)}, city={getattr(member2, 'city', None)}, country={getattr(member2, 'country', None)}")
    
    # Check if both users have GPS coordinates
    if all([
        member1.geolocation_lat, member1.geolocation_lon,
        member2.geolocation_lat, member2.geolocation_lon
    ]):
        distance_km = calculate_distance_km(
            member1.geolocation_lat, member1.geolocation_lon,
            member2.geolocation_lat, member2.geolocation_lon
        )
        return f"📍 {distance_km} км away"
    
    # Check if both users have city/country data
    if member1.city and member2.city:
        # Same city
        if member1.city.lower() == member2.city.lower():
            return "📍 Same city"
        
        # Different cities, same country
        if (member1.country and member2.country and 
            member1.country.lower() == member2.country.lower()):
            return f"📍 Different city, {member1.country}"
        
        # Different countries - show other user's location
        if member2.country:
            return f"📍 {member2.city}, {member2.country}"
        else:
            return f"📍 {member2.city}"
    
    # Fallback cases
    if member2.city:
        if member2.country:
            return f"📍 {member2.city}, {member2.country}"
        else:
            return f"📍 {member2.city}"
    
    return "📍 Location not specified" 