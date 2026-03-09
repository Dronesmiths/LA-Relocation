import random
from datetime import datetime

def fetch_reviews(city):
    """Mocks fetching reviews from Google Places/Yelp."""
    return [
        [city, f"{city} Real Estate Pros", "Google Places", "4.8", str(random.randint(50, 200)), "Great experience finding a home here.", datetime.now().isoformat()],
        [city, f"The {city} Diner", "Yelp", "4.5", str(random.randint(100, 500)), "Best local spot in town.", datetime.now().isoformat()],
        [city, f"{city} Plumbers LLC", "Google Places", "4.9", str(random.randint(20, 100)), "Fast and reliable service.", datetime.now().isoformat()]
    ]
