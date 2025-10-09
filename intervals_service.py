import os
import time
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

class IntervalsIcuService:
    def __init__(self, cache_file='intervals_cache.json'):
        self.api_key = os.getenv('INTERVALS_API_KEY')
        self.athlete_id = os.getenv('INTERVALS_ATHLETE_ID')
        self.base_url = "https://intervals.icu/api/v1"
        self.cache_duration = 43200  # 12 hours
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
        self.mock_mode = not all([self.api_key, self.athlete_id])
        if self.mock_mode:
            print("Warning: Intervals.icu credentials missing; running mock mode")
        else:
            print("Intervals.icu service initialized")

    # Cache helpers
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

    # HTTP
    def _headers(self):
        # Intervals.icu API key is used via Basic auth where the key is the username and no password.
        # Many clients supply it as the full "Basic base64(key:)" pre-encoded, but the API also accepts:
        return {"Authorization": f"Basic {self.api_key}"}

    def _get(self, path, params=None):
        if self.mock_mode:
            return None
        try:
            url = f"{self.base_url}{path}"
            r = requests.get(url, headers=self._headers(), params=params, timeout=12)
            if r.status_code == 200:
                return r.json()
            print(f"Intervals.icu GET {path} failed: {r.status_code} {r.text}")
            return None
        except Exception as e:
            print(f"Intervals.icu request error: {e}")
            return None

    # Units/helpers
    @staticmethod
    def meters_to_miles(m): return m * 0.000621371
    @staticmethod
    def meters_to_feet(m): return m * 3.28084

    @staticmethod
    def sec_to_hhmm(seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{int(h)}h {int(m)}m" if h > 0 else f"{int(m)}m"

    def calculate_avg_speed(self, distance_m, moving_s):
        if not moving_s:
            return 0
        mph = self.meters_to_miles(distance_m) / (moving_s / 3600)
        return round(mph, 1)

    # Public API (match previous Strava shapes)
    def get_ytd_stats(self):
        if self.mock_mode:
            return {"distance": 2450.5, "count": 127, "elevation": 45600, "time": 156.2, "avg_speed": 15.7}

        def fetch():
            start = datetime(datetime.utcnow().year, 1, 1).date().isoformat()
            end = datetime.utcnow().date().isoformat()
            activities = self._get(f"/athlete/{self.athlete_id}/activities", params={"from": start, "to": end})
            if not activities:
                return None

            total_dist = total_elev = total_time = 0
            count = 0
            for a in activities:
                sport = (a.get("sport") or "").lower()
                if sport in ["ride", "virtualride", "gravel ride", "mtb", "e-bike ride", "indoor cycling", "cycling"]:
                    dist = a.get("distance", 0) or 0
                    elev = a.get("elev_gain", 0) or 0
                    moving = a.get("moving_time", a.get("elapsed_time", 0)) or 0
                    total_dist += dist
                    total_elev += elev
                    total_time += moving
                    count += 1

            return {
                "distance": round(self.meters_to_miles(total_dist), 1),
                "elevation": round(self.meters_to_feet(total_elev)),
                "time": round(total_time / 3600, 1),
                "count": count,
                "avg_speed": self.calculate_avg_speed(total_dist, total_time),
            }

        return self.get_cached_or_fetch("icu_ytd_stats", fetch) or {"distance": 0, "count": 0, "elevation": 0, "time": 0, "avg_speed": 0}

    def format_recent_activities(self):
        if self.mock_mode:
            return [
                {"name": "Intervals.icu Mock Ride", "distance": 26.1, "elevation": 980, "time": "1h 38m", "date": "January 6, 2025", "avg_speed": 16.0}
            ]

        def fetch():
            end = datetime.utcnow().date().isoformat()
            start = (datetime.utcnow().date() - timedelta(days=14)).isoformat()
            activities = self._get(
                f"/athlete/{self.athlete_id}/activities",
                params={"from": start, "to": end, "page": 1, "per_page": 50},
            )
            if not activities:
                return None

            formatted = []
            for a in activities:
                sport = (a.get("sport") or "").lower()
                if sport in ["ride", "virtualride", "gravel ride", "mtb", "e-bike ride", "indoor cycling", "cycling"]:
                    name = a.get("name") or "Cycling Activity"
                    distance_m = a.get("distance", 0) or 0
                    elev_m = a.get("elev_gain", 0) or 0
                    moving = a.get("moving_time", a.get("elapsed_time", 0)) or 0
                    start_ts = a.get("start_date") or a.get("start_time") or a.get("date")
                    try:
                        dt = datetime.fromisoformat((start_ts or "").replace("Z", "+00:00"))
                    except Exception:
                        dt = datetime.utcnow()

                    formatted.append({
                        "name": name,
                        "distance": round(self.meters_to_miles(distance_m), 1),
                        "elevation": round(self.meters_to_feet(elev_m)),
                        "time": self.sec_to_hhmm(moving),
                        "date": dt.strftime("%B %d, %Y"),
                        "avg_speed": self.calculate_avg_speed(distance_m, moving),
                    })

            return formatted[:5]

        return self.get_cached_or_fetch("icu_formatted_activities", fetch) or []