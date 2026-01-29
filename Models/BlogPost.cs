namespace PersonalSite.Models;

public class BlogPost
{
    public int Id { get; set; }
    public string Slug { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
    public string HtmlContent { get; set; } = string.Empty;
    public string Excerpt { get; set; } = string.Empty;
    public string Category { get; set; } = "Uncategorized";
    public List<string> Tags { get; set; } = new();
    public DateTime PublishedDate { get; set; }
    public DateTime? UpdatedDate { get; set; }
    public string Author { get; set; } = "Blake Ridgway";
    public bool IsDraft { get; set; }
    public string FilePath { get; set; } = string.Empty;
    public int ReadTime { get; set; } = 5; // Estimated reading time in minutes
}

public class BlogPostMetadata
{
    public string? Title { get; set; }
    public string? Slug { get; set; }
    public DateTime? Date { get; set; }
    public string? Category { get; set; }
    public List<string>? Tags { get; set; }
    public string? Excerpt { get; set; }
    public bool Draft { get; set; }
    public string? Author { get; set; }
}
