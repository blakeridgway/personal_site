import json
import os
from datetime import datetime


class BlogManager:
    def __init__(self, data_file='data/blog_posts.json'):
        self.data_file = data_file
        self.ensure_data_file()

    def ensure_data_file(self):
        """Ensure the data file and directory exist"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w') as f:
                json.dump([], f)

    def load_posts(self):
        """Load all blog posts"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_posts(self, posts):
        """Save all blog posts"""
        with open(self.data_file, 'w') as f:
            json.dump(posts, f, indent=2)

    def get_next_id(self):
        """Get the next available ID"""
        posts = self.load_posts()
        if not posts:
            return 1
        return max(post['id'] for post in posts) + 1

    def create_post(self, title, content, category, excerpt=None):
        """Create a new blog post"""
        posts = self.load_posts()

        # Auto-generate excerpt if not provided
        if not excerpt:
            excerpt = content[:150] + "..." if len(content) > 150 else content

        new_post = {
            'id': self.get_next_id(),
            'title': title,
            'content': content,
            'excerpt': excerpt,
            'category': category,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'created_at': datetime.now().isoformat()
        }

        posts.append(new_post)
        self.save_posts(posts)
        return new_post

    def get_post(self, post_id):
        """Get a specific post by ID"""
        posts = self.load_posts()
        return next((p for p in posts if p['id'] == post_id), None)

    def update_post(self, post_id, title, content, category, excerpt=None):
        """Update an existing post"""
        posts = self.load_posts()
        post = next((p for p in posts if p['id'] == post_id), None)

        if not post:
            return None

        if not excerpt:
            excerpt = content[:150] + "..." if len(content) > 150 else content

        post.update({
            'title': title,
            'content': content,
            'excerpt': excerpt,
            'category': category,
            'updated_at': datetime.now().isoformat()
        })

        self.save_posts(posts)
        return post

    def delete_post(self, post_id):
        """Delete a post"""
        posts = self.load_posts()
        posts = [p for p in posts if p['id'] != post_id]
        self.save_posts(posts)
        return True