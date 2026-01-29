namespace PersonalSite.Models;

public class CyclingStats
{
    public double Distance { get; set; }      // Miles
    public int Elevation { get; set; }        // Feet
    public double Time { get; set; }          // Hours
    public int Count { get; set; }            // Activity count
    public double AvgSpeed { get; set; }      // MPH
}

public class CyclingActivity
{
    public string Name { get; set; } = string.Empty;
    public double Distance { get; set; }      // Miles
    public int Elevation { get; set; }        // Feet
    public string Duration { get; set; } = string.Empty;  // "1h 38m"
    public string Date { get; set; } = string.Empty;       // "January 15, 2026"
    public double AvgSpeed { get; set; }      // MPH
}

public class IntervalsIcuOptions
{
    public string ApiKey { get; set; } = string.Empty;
    public string BaseUrl { get; set; } = "https://intervals.icu/api/v1";
    public string AthleteId { get; set; } = "0";
    public int CacheDurationHours { get; set; } = 12;
}
