import requests
import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class StravaService:
    def __init__(self, cache_file='strava_cache.json'):
        self.client_id = os.getenv('STRAVA_CLIENT_ID')
        self.client_secret = os.getenv('STRAVA_CLIENT_SECRET')
        self.refresh_token = os.getenv('STRAVA_REFRESH_TOKEN')
        self.access_token = None
        self.base_url = 'https://www.strava.com/api/v3'

        # 12-hour cache duration (43200 seconds)
        self.cache_duration = 43200
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()

        # Check if credentials are available
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            print("Warning: Strava credentials not found in .env file")
            self.mock_mode = True
        else:
            self.mock_mode = False
            print("Strava service initialized with API credentials")

    def _load_cache(self):
        """Load cache from file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    # Clean expired entries on load
                    return self._clean_expired_cache(cache_data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading cache: {e}")
        return {}

    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            print(f"Error saving cache: {e}")

    def _clean_expired_cache(self, cache_data):
        """Remove expired entries from cache"""
        now = time.time()
        cleaned_cache = {}

        for key, (data, timestamp) in cache_data.items():
            if now - timestamp < self.cache_duration:
                cleaned_cache[key] = (data, timestamp)

        return cleaned_cache

    def _is_cache_valid(self, key):
        """Check if cache entry is still valid"""
        if key not in self.cache:
            return False

        _, timestamp = self.cache[key]
        return time.time() - timestamp < self.cache_duration

    def _get_cache_age(self, key):
        """Get age of cache entry in hours"""
        if key not in self.cache:
            return None

        _, timestamp = self.cache[key]
        age_seconds = time.time() - timestamp
        return round(age_seconds / 3600, 1)

    def get_cached_or_fetch(self, key, fetch_function):
        """Get data from cache or fetch fresh data"""
        if self._is_cache_valid(key):
            data, _ = self.cache[key]
            cache_age = self._get_cache_age(key)
            print(f"Using cached {key} (age: {cache_age}h)")
            return data

        print(f"Cache miss or expired for {key}, fetching fresh data...")
        data = fetch_function()

        if data:
            self.cache[key] = (data, time.time())
            self._save_cache()
            print(f"Cached fresh {key} data")

        return data

    def get_access_token(self):
        """Get a fresh access token using refresh token"""
        if self.mock_mode:
            return None

        # Check if we have a cached valid token
        if self._is_cache_valid('access_token'):
            token_data, _ = self.cache['access_token']
            self.access_token = token_data['access_token']
            return self.access_token

        url = 'https://www.strava.com/oauth/token'
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']

                # Cache the token with shorter duration (1 hour)
                self.cache['access_token'] = (token_data, time.time())
                self._save_cache()

                print("Successfully refreshed Strava access token")
                return self.access_token
            else:
                print(f"Failed to refresh token: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None

    def make_request(self, endpoint):
        """Make authenticated request to Strava API"""
        if self.mock_mode:
            return None

        if not self.access_token:
            if not self.get_access_token():
                return None

        headers = {'Authorization': f'Bearer {self.access_token}'}

        try:
            response = requests.get(f'{self.base_url}{endpoint}',
                                    headers=headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token expired, try to refresh
                print("Token expired, refreshing...")
                # Clear cached token
                if 'access_token' in self.cache:
                    del self.cache['access_token']
                    self._save_cache()

                if self.get_access_token():
                    headers = {'Authorization': f'Bearer {self.access_token}'}
                    response = requests.get(f'{self.base_url}{endpoint}',
                                            headers=headers, timeout=10)
                    if response.status_code == 200:
                        return response.json()

            print(f"API request failed: {response.status_code}")
            return None

        except Exception as e:
            print(f"Error making API request: {e}")
            return None

    def calculate_avg_speed(self, distance_meters, moving_time_seconds):
        """Calculate average speed in mph"""
        if moving_time_seconds == 0:
            return 0

        # Convert distance from meters to miles
        distance_miles = distance_meters * 0.000621371
        # Convert time from seconds to hours
        time_hours = moving_time_seconds / 3600
        # Calculate speed in mph
        avg_speed = distance_miles / time_hours
        return round(avg_speed, 1)

    def get_athlete_stats(self):
        """Get athlete statistics with caching"""
        if self.mock_mode:
            return self._mock_athlete_stats()

        def fetch_stats():
            athlete = self.make_request('/athlete')
            if athlete:
                athlete_id = athlete['id']
                return self.make_request(f'/athletes/{athlete_id}/stats')
            return None

        return self.get_cached_or_fetch('athlete_stats', fetch_stats)

    def get_recent_activities(self, limit=10):
        """Get recent activities with caching"""
        if self.mock_mode:
            return self._mock_recent_activities()

        def fetch_activities():
            return self.make_request(f'/athlete/activities?per_page={limit}')

        return self.get_cached_or_fetch(f'recent_activities_{limit}', fetch_activities)

    def get_ytd_stats(self):
        """Get year-to-date statistics with caching"""
        if self.mock_mode:
            return self._mock_ytd_stats()

        def fetch_ytd():
            stats = self.get_athlete_stats()
            if stats:
                ytd_ride = stats.get('ytd_ride_totals', {})

                # Calculate average speed for YTD
                total_distance = ytd_ride.get('distance', 0)
                total_time = ytd_ride.get('moving_time', 0)
                avg_speed = self.calculate_avg_speed(total_distance, total_time)

                return {
                    'distance': round(ytd_ride.get('distance', 0) * 0.000621371, 1),
                    'elevation': round(ytd_ride.get('elevation_gain', 0) * 3.28084),
                    'time': round(ytd_ride.get('moving_time', 0) / 3600, 1),
                    'count': ytd_ride.get('count', 0),
                    'avg_speed': avg_speed
                }
            return None

        result = self.get_cached_or_fetch('ytd_stats', fetch_ytd)
        return result if result else self._mock_ytd_stats()

    def format_recent_activities(self):
        """Format recent activities for display with caching"""
        if self.mock_mode:
            return self._mock_formatted_activities()

        def fetch_formatted():
            activities = self.get_recent_activities(5)
            if not activities:
                return None

            formatted = []
            for activity in activities:
                if activity['type'] in ['Ride', 'VirtualRide']:
                    # Calculate average speed for this activity
                    avg_speed = self.calculate_avg_speed(
                        activity.get('distance', 0),
                        activity.get('moving_time', 0)
                    )

                    formatted.append({
                        'name': activity['name'],
                        'distance': round(activity['distance'] * 0.000621371, 1),
                        'elevation': round(activity['total_elevation_gain'] * 3.28084),
                        'time': self.format_time(activity['moving_time']),
                        'date': datetime.strptime(
                            activity['start_date'],
                            '%Y-%m-%dT%H:%M:%SZ'
                        ).strftime('%B %d, %Y'),
                        'avg_speed': avg_speed
                    })

            return formatted[:3] if formatted else None

        result = self.get_cached_or_fetch('formatted_activities', fetch_formatted)
        return result if result else self._mock_formatted_activities()

    def get_cache_status(self):
        """Get status of all cached items"""
        status = {}
        for key in self.cache:
            if key != 'access_token':  # Don't expose token info
                age = self._get_cache_age(key)
                valid = self._is_cache_valid(key)
                status[key] = {
                    'age_hours': age,
                    'valid': valid,
                    'expires_in_hours': round((self.cache_duration - (time.time() - self.cache[key][1])) / 3600, 1)
                }
        return status

    def clear_cache(self, key=None):
        """Clear cache (specific key or all)"""
        if key:
            if key in self.cache:
                del self.cache[key]
                print(f"Cleared cache for {key}")
            else:
                print(f"No cache found for {key}")
        else:
            self.cache.clear()
            print("Cleared all cache")

        self._save_cache()

    def format_time(self, seconds):
        """Convert seconds to readable time format"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    # Mock data methods for fallback (unchanged)
    def _mock_ytd_stats(self):
        return {
            'distance': 2450.5,
            'count': 127,
            'elevation': 45600,
            'time': 156.2,
            'avg_speed': 15.7
        }

    def _mock_formatted_activities(self):
        return [
            {
                'name': 'Morning Training Ride',
                'distance': 25.3,
                'elevation': 1200,
                'time': '1h 45m',
                'date': 'January 5, 2025',
                'avg_speed': 14.5
            },
            {
                'name': 'Weekend Century',
                'distance': 102.1,
                'elevation': 3500,
                'time': '5h 30m',
                'date': 'January 3, 2025',
                'avg_speed': 18.6
            },
            {
                'name': 'Recovery Spin',
                'distance': 15.2,
                'elevation': 400,
                'time': '45m',
                'date': 'January 1, 2025',
                'avg_speed': 20.3
            }
        ]

    def _mock_recent_activities(self):
        return []

    def _mock_athlete_stats(self):
        return None