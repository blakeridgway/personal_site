using System.Text.RegularExpressions;
using Markdig;
using Microsoft.Extensions.Caching.Memory;
using PersonalSite.Models;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace PersonalSite.Services;

public class BlogService : IBlogService
{
    private readonly string _postsPath;
    private readonly IMemoryCache _cache;
    private readonly ILogger<BlogService> _logger;
    private readonly MarkdownPipeline _pipeline;
    private readonly IDeserializer _yamlDeserializer;
    private const string CacheKey = "blog_posts";
    private static readonly TimeSpan CacheDuration = TimeSpan.FromMinutes(5);

    public BlogService(IWebHostEnvironment env, IMemoryCache cache, ILogger<BlogService> logger)
    {
        _postsPath = Path.Combine(env.ContentRootPath, "Content", "posts");
        _cache = cache;
        _logger = logger;

        _pipeline = new MarkdownPipelineBuilder()
            .UseAdvancedExtensions()
            .Build();

        _yamlDeserializer = new DeserializerBuilder()
            .WithNamingConvention(CamelCaseNamingConvention.Instance)
            .IgnoreUnmatchedProperties()
            .Build();

        // Ensure posts directory exists
        if (!Directory.Exists(_postsPath))
        {
            Directory.CreateDirectory(_postsPath);
        }
    }

    public async Task<IEnumerable<BlogPost>> GetAllPostsAsync()
    {
        return await GetCachedPostsAsync();
    }

    public async Task<IEnumerable<BlogPost>> GetPostsAsync(int page, int pageSize, string? category = null)
    {
        var posts = await GetCachedPostsAsync();

        if (!string.IsNullOrEmpty(category))
        {
            posts = posts.Where(p => p.Category.Equals(category, StringComparison.OrdinalIgnoreCase));
        }

        return posts
            .OrderByDescending(p => p.PublishedDate)
            .Skip((page - 1) * pageSize)
            .Take(pageSize);
    }

    public async Task<BlogPost?> GetPostBySlugAsync(string slug)
    {
        var posts = await GetCachedPostsAsync();
        return posts.FirstOrDefault(p => p.Slug.Equals(slug, StringComparison.OrdinalIgnoreCase));
    }

    public async Task<BlogPost?> GetPostByIdAsync(int id)
    {
        var posts = await GetCachedPostsAsync();
        return posts.FirstOrDefault(p => p.Id == id);
    }

    public async Task<IEnumerable<string>> GetCategoriesAsync()
    {
        var posts = await GetCachedPostsAsync();
        return posts
            .Select(p => p.Category)
            .Distinct()
            .OrderBy(c => c);
    }

    public async Task<int> GetTotalCountAsync(string? category = null)
    {
        var posts = await GetCachedPostsAsync();

        if (!string.IsNullOrEmpty(category))
        {
            posts = posts.Where(p => p.Category.Equals(category, StringComparison.OrdinalIgnoreCase));
        }

        return posts.Count();
    }

    public async Task<IEnumerable<BlogPost>> GetRecentPostsAsync(int count = 3)
    {
        var posts = await GetCachedPostsAsync();
        return posts
            .Where(p => !p.IsDraft)
            .OrderByDescending(p => p.PublishedDate)
            .Take(count);
    }

    private async Task<IEnumerable<BlogPost>> GetCachedPostsAsync()
    {
        if (_cache.TryGetValue(CacheKey, out IEnumerable<BlogPost>? cachedPosts) && cachedPosts != null)
        {
            return cachedPosts;
        }

        var posts = await LoadPostsFromDiskAsync();
        _cache.Set(CacheKey, posts, CacheDuration);
        return posts;
    }

    private Task<IEnumerable<BlogPost>> LoadPostsFromDiskAsync()
    {
        var posts = new List<BlogPost>();

        if (!Directory.Exists(_postsPath))
        {
            return Task.FromResult<IEnumerable<BlogPost>>(posts);
        }

        var files = Directory.GetFiles(_postsPath, "*.md");
        int id = 1;

        foreach (var file in files.OrderByDescending(f => f))
        {
            try
            {
                var post = ParseMarkdownFile(file, id++);
                if (post != null && !post.IsDraft)
                {
                    posts.Add(post);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to parse blog post: {File}", file);
            }
        }

        return Task.FromResult<IEnumerable<BlogPost>>(posts.OrderByDescending(p => p.PublishedDate));
    }

    private BlogPost? ParseMarkdownFile(string filePath, int id)
    {
        var content = File.ReadAllText(filePath);
        var fileName = Path.GetFileNameWithoutExtension(filePath);

        // Extract YAML front matter
        var frontMatterMatch = Regex.Match(content, @"^---\s*\n(.*?)\n---\s*\n", RegexOptions.Singleline);

        BlogPostMetadata metadata = new();
        string markdownContent = content;

        if (frontMatterMatch.Success)
        {
            var yaml = frontMatterMatch.Groups[1].Value;
            try
            {
                metadata = _yamlDeserializer.Deserialize<BlogPostMetadata>(yaml) ?? new BlogPostMetadata();
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Failed to parse YAML front matter in {File}", filePath);
            }
            markdownContent = content.Substring(frontMatterMatch.Length);
        }

        // Generate slug from filename if not in metadata
        // Expected format: YYYY-MM-DD-slug-name.md
        var slug = metadata.Slug;
        var publishedDate = metadata.Date ?? DateTime.Now;

        if (string.IsNullOrEmpty(slug))
        {
            var dateMatch = Regex.Match(fileName, @"^(\d{4}-\d{2}-\d{2})-(.+)$");
            if (dateMatch.Success)
            {
                if (DateTime.TryParse(dateMatch.Groups[1].Value, out var parsedDate))
                {
                    publishedDate = parsedDate;
                }
                slug = dateMatch.Groups[2].Value;
            }
            else
            {
                slug = fileName;
            }
        }

        var htmlContent = Markdown.ToHtml(markdownContent.Trim(), _pipeline);
        var excerpt = metadata.Excerpt ?? GenerateExcerpt(markdownContent);

        return new BlogPost
        {
            Id = id,
            Slug = slug,
            Title = metadata.Title ?? GenerateTitleFromSlug(slug),
            Content = markdownContent.Trim(),
            HtmlContent = htmlContent,
            Excerpt = excerpt,
            Category = metadata.Category ?? "Uncategorized",
            Tags = metadata.Tags ?? new List<string>(),
            PublishedDate = publishedDate,
            Author = metadata.Author ?? "Blake Ridgway",
            IsDraft = metadata.Draft,
            FilePath = filePath,
            ReadTime = CalculateReadTime(markdownContent)
        };
    }

    private static int CalculateReadTime(string content)
    {
        // Average reading speed is ~200 words per minute
        var wordCount = content.Split(new[] { ' ', '\n', '\r', '\t' }, StringSplitOptions.RemoveEmptyEntries).Length;
        var minutes = Math.Max(1, (int)Math.Ceiling(wordCount / 200.0));
        return minutes;
    }

    private static string GenerateExcerpt(string markdown, int maxLength = 150)
    {
        // Remove markdown formatting for excerpt
        var text = Regex.Replace(markdown, @"[#*`\[\]()>-]", "");
        text = Regex.Replace(text, @"\s+", " ").Trim();

        if (text.Length <= maxLength)
        {
            return text;
        }

        return text.Substring(0, maxLength).TrimEnd() + "...";
    }

    private static string GenerateTitleFromSlug(string slug)
    {
        // Convert slug-format to Title Format
        var words = slug.Split('-', StringSplitOptions.RemoveEmptyEntries);
        return string.Join(" ", words.Select(w =>
            char.ToUpper(w[0]) + w.Substring(1).ToLower()));
    }
}
