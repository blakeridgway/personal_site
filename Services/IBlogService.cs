using PersonalSite.Models;

namespace PersonalSite.Services;

public interface IBlogService
{
    Task<IEnumerable<BlogPost>> GetAllPostsAsync();
    Task<IEnumerable<BlogPost>> GetPostsAsync(int page, int pageSize, string? category = null);
    Task<BlogPost?> GetPostBySlugAsync(string slug);
    Task<BlogPost?> GetPostByIdAsync(int id);
    Task<IEnumerable<string>> GetCategoriesAsync();
    Task<int> GetTotalCountAsync(string? category = null);
    Task<IEnumerable<BlogPost>> GetRecentPostsAsync(int count = 3);
    Task<BlogPost> SavePostAsync(BlogPost post);
    Task DeletePostAsync(string slug);
}
