import os
from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username

    @staticmethod
    def get(username):
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        if username == admin_username:
            return User(username)
        return None

    @staticmethod
    def authenticate(username, password):
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'password')

        if username == admin_username and password == admin_password:
            return User(username)
        return None