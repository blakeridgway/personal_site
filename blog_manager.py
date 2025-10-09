import json
import os
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(os.getenv("DATA_DIR", "/personalsite/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

class BlogManager:
    def __init__(self, data_file: str | None = None):
        self.data_file = Path(data_file) if data_file else DATA_DIR / "blog_posts.json"
        self.ensure_data_file()

    def ensure_data_file(self):
        """Ensure the data file and directory exist"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            self.data_file.write_text("[]", encoding="utf-8")

    def load_posts(self):
        """Load all blog posts"""
        try:
            return json.loads(self.data_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_posts(self, posts):
        """Save all blog posts"""
        self.data_file.write_text(json.dumps(posts, indent=2), encoding="utf-8")

    def get_next_id(self):
        """Get the next available ID"""
        posts = self.load_posts()
        return (max((p["id"] for p in posts), default=0) + 1)

    def create_post(self, title, content, category, excerpt=None):
        """Create a new blog post"""
        posts = self.load_posts()
        if not excerpt:
            excerpt = content[:150] + "..." if len(content) > 150 else content

        new_post = {
            "id": self.get_next_id(),
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "category": category,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "created_at": datetime.now().isoformat(),
        }

        posts.append(new_post)
        self.save_posts(posts)
        return new_post

    def get_post(self, post_id):
        """Get a specific post by ID"""
        return next((p for p in self.load_posts() if p["id"] == post_id), None)

    def update_post(self, post_id, title, content, category, excerpt=None):
        """Update an existing post"""
        posts = self.load_posts()
        post = next((p for p in posts if p["id"] == post_id), None)
        if not post:
            return None

        if not excerpt:
            excerpt = content[:150] + "..." if len(content) > 150 else content

        post.update(
            {
                "title": title,
                "content": content,
                "excerpt": excerpt,
                "category": category,
                "updated_at": datetime.now().isoformat(),
            }
        )

        self.save_posts(posts)
        return post

    def delete_post(self, post_id):
        """Delete a post"""
        posts = [p for p in self.load_posts() if p["id"] != post_id]
        self.save_posts(posts)
        return True