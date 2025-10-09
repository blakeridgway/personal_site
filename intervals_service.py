import os
import time
import json
import requests
import base64
from datetime import datetime, timedelta
from pathlib import Path

class IntervalsIcuService:
    def __init__(self, cache_file='intervals_cache.json'):
        self.api_key = os.getenv('INTERVALS_API_KEY')
        self.athlete_id = "0"  # Use "0" to access your own data
        self.base_url = "https://intervals.icu/api/v1"
        self.cache_duration = 43200  # 12 hours
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.mock_mode = not bool(self.api_key)
        if self.mock_mode:
            print("Warning: Intervals.icu credentials missing; running mock mode")
        else:
            print("Intervals.icu service initialized")
            print(f"API key: {self.api_key[:8]}..." if self.api_key else "No API key")

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    return self._clean_expired_cache(data)
            except Exception as e:
                print(f"Error loading cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def _clean_expired_cache(self, cache_data):
        now = time.time()
        cleaned = {}
        for k, (v, ts) in cache_data.items():
            if now - ts < self.cache_duration:
                cleaned[k] = (v, ts)
        return cleaned

    def _is_cache_valid(self, key):
        if key not in self.cache:
            return False
        _, ts = self.cache[key]
        return time.time() - ts < self.cache_duration

    def _get_cache_age(self, key):
        if key not in self.cache:
            return None
        _, ts = self.cache[key]
        return round((time.time() - ts) / 3600, 1)

    def get_cached_or_fetch(self, key, fetch_fn):
        if self._is_cache_valid(key):
            data, _ = self.cache[key]
            print(f"Using cached {key} (age {self._get_cache_age(key)}h)")
            return data
        print(f"Cache miss for {key}, fetching...")
        data = fetch_fn()
        if data is not None:
            self.cache[key] = (data, time.time())
            self._save_cache()
        return data

    def _headers(self):
        # Correct authentication: username="API_KEY", password=actual_api_key
        credentials = base64.b64encode(f"API_KEY:{self.api_key}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json"
        }

    def _get(self, path, params=None):
        if self.mock_mode:
            return None
        try:
            url = f"{self.base_url}{path}"
            print(f"Making request to: {url}")
            print(f"Params: {params}")
            
            headers = self._headers()
            r = requests.get(url, headers=headers, params=params, timeout=12)
            print(f"Response status: {r.status_code}")
            
            if r.status_code == 200:
                data = r.json()
                print(f"Success! Got {len(data) if isinstance(data, list) else 'object'} from API")
                return data
            else:
                print(f"Intervals.icu GET {path} failed: {r.status_code}")
                print(f"Response: {r.text}")
                return None
                
        except Exception as e:
            print(f"Intervals.icu request error: {e}")
            return None

    def test_connection(self):
        """Test API connection"""
        if self.mock_mode:
            return False
            
        print("\U0001f9ea Testing Intervals.icu API connection...")
        
        # Test with athlete endpoint using "0" for own data
        athlete_info = self._get(f"/athlete/{self.athlete_id}")
        if athlete_info:
            name = athlete_info.get('name', 'Unknown')
            print(f"\u2705 Connection successful! Athlete: {name}")
            return True
        else:
            print("\u274c Connection failed!")
            return False

    # Units/helpers
    @staticmethod
    def meters_to_miles(m): 
        return m * 0.000621371

    @staticmethod
    def meters_to_feet(m): 
        return m * 3.28084

    @staticmethod
    def sec_to_hhmm(seconds):
        if not seconds:
            return "0m"
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m" if h > 0 else f"{m}m"

    def calculate_avg_speed(self, distance_m, moving_s):
        if not moving_s:
            return 0
        mph = self.meters_to_miles(distance_m) / (moving_s / 3600)
        return round(mph, 1)

    def get_ytd_stats(self):
        if self.mock_mode:
            return {"distance": 2450.5, "count": 127, "elevation": 45600, "time": 156.2, "avg_speed": 15.7}

        def fetch():
            # Get activities for current year using athlete ID "0"
            current_year = datetime.now().year
            start_date = f"{current_year}-01-01"
            
            activities = self._get(f"/athlete/{self.athlete_id}/activities", 
                                 params={"oldest": start_date})
                                 
            if not activities:
                print("No activities returned from API")
                return None

            print(f"Got {len(activities)} activities from API")
            
            total_dist = total_elev = total_time = 0
            count = 0
            
            for a in activities:
                # Check if it's a cycling activity
                activity_type = (a.get("type") or "").lower()
                if any(word in activity_type for word in ["ride", "cycl", "bike"]):
                    dist = float(a.get("distance", 0) or 0)
                    elev = float(a.get("total_elevation_gain", 0) or 0)
                    moving = float(a.get("moving_time", 0) or 0)
                    
                    total_dist += dist
                    total_elev += elev
                    total_time += moving
                    count += 1

            print(f"Processed {count} cycling activities")
            
            return {
                "distance": round(self.meters_to_miles(total_dist), 1),
                "elevation": round(self.meters_to_feet(total_elev)),
                "time": round(total_time / 3600, 1),
                "count": count,
                "avg_speed": self.calculate_avg_speed(total_dist, total_time) if total_time > 0 else 0,
            }

        return self.get_cached_or_fetch("icu_ytd_stats", fetch) or {"distance": 0, "count": 0, "elevation": 0, "time": 0, "avg_speed": 0}

    def format_recent_activities(self):
        if self.mock_mode:
            return [{"name": "Intervals.icu Mock Ride", "distance": 26.1, "elevation": 980, "time": "1h 38m", "date": "January 6, 2025", "avg_speed": 16.0}]

        def fetch():
            # Get recent activities (last 2 weeks)
            start_date = (datetime.now().date() - timedelta(days=14)).isoformat()
            
            activities = self._get(f"/athlete/{self.athlete_id}/activities", 
                                 params={"oldest": start_date})
                                 
            if not activities:
                return []

            formatted = []
            # Sort by date (newest first) and take cycling activities
            activities.sort(key=lambda x: x.get("start_date_local", ""), reverse=True)
            
            for a in activities:
                activity_type = (a.get("type") or "").lower()
                if any(word in activity_type for word in ["ride", "cycl", "bike"]):
                    name = a.get("name") or "Cycling Activity"
                    distance_m = float(a.get("distance", 0) or 0)
                    elev_m = float(a.get("total_elevation_gain", 0) or 0)
                    moving = float(a.get("moving_time", 0) or 0)
                    
                    # Parse start date
                    start_date_str = a.get("start_date_local") or a.get("start_date") or ""
                    try:
                        if start_date_str:
                            dt = datetime.fromisoformat(start_date_str.replace("Z", ""))
                        else:
                            dt = datetime.now()
                    except:
                        dt = datetime.now()

                    formatted.append({
                        "name": name,
                        "distance": round(self.meters_to_miles(distance_m), 1),
                        "elevation": round(self.meters_to_feet(elev_m)),
                        "time": self.sec_to_hhmm(moving),
                        "date": dt.strftime("%B %d, %Y"),
                        "avg_speed": self.calculate_avg_speed(distance_m, moving),
                    })
                    
                    if len(formatted) >= 5:  # Limit to 5 activities
                        break

            return formatted

        return self.get_cached_or_fetch("icu_formatted_activities", fetch) or []