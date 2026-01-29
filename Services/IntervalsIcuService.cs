using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Options;
using PersonalSite.Models;

namespace PersonalSite.Services;

public class IntervalsIcuService : ICyclingService
{
    private readonly HttpClient _httpClient;
    private readonly IMemoryCache _cache;
    private readonly ILogger<IntervalsIcuService> _logger;
    private readonly IntervalsIcuOptions _options;
    private readonly TimeSpan _cacheDuration;

    private const string YtdStatsCacheKey = "cycling_ytd_stats";
    private const string RecentActivitiesCacheKey = "cycling_recent_activities";

    public bool IsAvailable => !string.IsNullOrEmpty(_options.ApiKey);

    public IntervalsIcuService(
        HttpClient httpClient,
        IMemoryCache cache,
        IOptions<IntervalsIcuOptions> options,
        ILogger<IntervalsIcuService> logger)
    {
        _httpClient = httpClient;
        _cache = cache;
        _options = options.Value;
        _logger = logger;
        _cacheDuration = TimeSpan.FromHours(_options.CacheDurationHours);

        if (IsAvailable)
        {
            var credentials = Convert.ToBase64String(
                Encoding.ASCII.GetBytes($"API_KEY:{_options.ApiKey}"));
            _httpClient.DefaultRequestHeaders.Authorization =
                new AuthenticationHeaderValue("Basic", credentials);
            _httpClient.BaseAddress = new Uri(_options.BaseUrl);
            _httpClient.Timeout = TimeSpan.FromSeconds(12);
            _logger.LogInformation("Intervals.icu service initialized");
        }
        else
        {
            _logger.LogWarning("Intervals.icu API key not configured, using mock data");
        }
    }

    public async Task<CyclingStats> GetYtdStatsAsync()
    {
        if (_cache.TryGetValue(YtdStatsCacheKey, out CyclingStats? cached) && cached != null)
        {
            _logger.LogDebug("Returning cached YTD stats");
            return cached;
        }

        if (!IsAvailable)
        {
            return GetFallbackStats();
        }

        try
        {
            var startDate = new DateTime(DateTime.Now.Year, 1, 1).ToString("yyyy-MM-dd");
            var response = await _httpClient.GetAsync(
                $"athlete/{_options.AthleteId}/activities?oldest={startDate}");

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning("Failed to fetch activities: {StatusCode}", response.StatusCode);
                return GetFallbackStats();
            }

            var json = await response.Content.ReadAsStringAsync();
            var activities = JsonSerializer.Deserialize<List<IntervalsActivity>>(json,
                new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower });

            if (activities == null || activities.Count == 0)
            {
                _logger.LogWarning("No activities returned from API");
                return GetFallbackStats();
            }

            var stats = CalculateStats(activities);
            _cache.Set(YtdStatsCacheKey, stats, _cacheDuration);
            return stats;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching YTD stats from Intervals.icu");
            return GetFallbackStats();
        }
    }

    public async Task<IEnumerable<CyclingActivity>> GetRecentActivitiesAsync(int count = 5)
    {
        if (_cache.TryGetValue(RecentActivitiesCacheKey, out IEnumerable<CyclingActivity>? cached) && cached != null)
        {
            _logger.LogDebug("Returning cached recent activities");
            return cached.Take(count);
        }

        if (!IsAvailable)
        {
            return GetFallbackActivities();
        }

        try
        {
            var startDate = DateTime.Now.AddDays(-14).ToString("yyyy-MM-dd");
            var response = await _httpClient.GetAsync(
                $"athlete/{_options.AthleteId}/activities?oldest={startDate}");

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogWarning("Failed to fetch recent activities: {StatusCode}", response.StatusCode);
                return GetFallbackActivities();
            }

            var json = await response.Content.ReadAsStringAsync();
            var activities = JsonSerializer.Deserialize<List<IntervalsActivity>>(json,
                new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower });

            if (activities == null || activities.Count == 0)
            {
                return GetFallbackActivities();
            }

            var formatted = FormatActivities(activities, count);
            _cache.Set(RecentActivitiesCacheKey, formatted, _cacheDuration);
            return formatted;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error fetching recent activities from Intervals.icu");
            return GetFallbackActivities();
        }
    }

    private CyclingStats CalculateStats(List<IntervalsActivity> activities)
    {
        double totalDistance = 0;
        double totalElevation = 0;
        double totalTime = 0;
        int count = 0;

        foreach (var activity in activities)
        {
            if (IsCyclingActivity(activity.Type))
            {
                totalDistance += activity.Distance ?? 0;
                totalElevation += activity.TotalElevationGain ?? 0;
                totalTime += activity.MovingTime ?? 0;
                count++;
            }
        }

        var distanceMiles = MetersToMiles(totalDistance);
        var timeHours = totalTime / 3600;

        return new CyclingStats
        {
            Distance = Math.Round(distanceMiles, 1),
            Elevation = (int)Math.Round(MetersToFeet(totalElevation)),
            Time = Math.Round(timeHours, 1),
            Count = count,
            AvgSpeed = timeHours > 0 ? Math.Round(distanceMiles / timeHours, 1) : 0
        };
    }

    private List<CyclingActivity> FormatActivities(List<IntervalsActivity> activities, int count)
    {
        return activities
            .Where(a => IsCyclingActivity(a.Type))
            .OrderByDescending(a => a.StartDateLocal ?? a.StartDate)
            .Take(count)
            .Select(a =>
            {
                var distanceMeters = a.Distance ?? 0;
                var movingSeconds = a.MovingTime ?? 0;
                var distanceMiles = MetersToMiles(distanceMeters);

                DateTime date;
                if (!string.IsNullOrEmpty(a.StartDateLocal))
                    DateTime.TryParse(a.StartDateLocal, out date);
                else if (!string.IsNullOrEmpty(a.StartDate))
                    DateTime.TryParse(a.StartDate, out date);
                else
                    date = DateTime.Now;

                return new CyclingActivity
                {
                    Name = a.Name ?? "Cycling Activity",
                    Distance = Math.Round(distanceMiles, 1),
                    Elevation = (int)Math.Round(MetersToFeet(a.TotalElevationGain ?? 0)),
                    Duration = FormatDuration((int)movingSeconds),
                    Date = date.ToString("MMMM d, yyyy"),
                    AvgSpeed = movingSeconds > 0
                        ? Math.Round(distanceMiles / (movingSeconds / 3600), 1)
                        : 0
                };
            })
            .ToList();
    }

    private static bool IsCyclingActivity(string? type)
    {
        if (string.IsNullOrEmpty(type)) return false;
        var lower = type.ToLower();
        return lower.Contains("ride") || lower.Contains("cycl") || lower.Contains("bike");
    }

    private static double MetersToMiles(double meters) => meters * 0.000621371;
    private static double MetersToFeet(double meters) => meters * 3.28084;

    private static string FormatDuration(int seconds)
    {
        if (seconds <= 0) return "0m";
        var hours = seconds / 3600;
        var minutes = (seconds % 3600) / 60;
        return hours > 0 ? $"{hours}h {minutes}m" : $"{minutes}m";
    }

    private static CyclingStats GetFallbackStats() => new()
    {
        Distance = 2450.5,
        Elevation = 45600,
        Time = 156.2,
        Count = 127,
        AvgSpeed = 15.7
    };

    private static List<CyclingActivity> GetFallbackActivities() => new()
    {
        new CyclingActivity
        {
            Name = "Morning Endurance Ride",
            Distance = 42.5,
            Elevation = 1250,
            Duration = "2h 38m",
            Date = DateTime.Now.AddDays(-1).ToString("MMMM d, yyyy"),
            AvgSpeed = 16.2
        },
        new CyclingActivity
        {
            Name = "Hill Intervals",
            Distance = 28.3,
            Elevation = 2100,
            Duration = "1h 55m",
            Date = DateTime.Now.AddDays(-3).ToString("MMMM d, yyyy"),
            AvgSpeed = 14.8
        },
        new CyclingActivity
        {
            Name = "Recovery Spin",
            Distance = 18.7,
            Elevation = 450,
            Duration = "1h 14m",
            Date = DateTime.Now.AddDays(-4).ToString("MMMM d, yyyy"),
            AvgSpeed = 15.1
        }
    };

    // Internal model for deserializing Intervals.icu API response
    private class IntervalsActivity
    {
        public string? Name { get; set; }
        public string? Type { get; set; }
        public double? Distance { get; set; }
        public double? TotalElevationGain { get; set; }
        public double? MovingTime { get; set; }
        public string? StartDate { get; set; }
        public string? StartDateLocal { get; set; }
    }
}
