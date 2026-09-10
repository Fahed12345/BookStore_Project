import os

class Config:
    SECRET_KEY = 'your-secret-key-change-in-production'
    # MySQL connection string (adjust username, password, database name)
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:NewPassword123!@localhost/bookstore_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Session settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 86400  # 1 day in seconds