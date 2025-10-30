import os

class Config:
    # Secret key for sessions (change this to something random)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-me'
    
    # Database location
    SQLALCHEMY_DATABASE_URI = 'sqlite:///inventory.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email settings for alerts (use Gmail)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'your-email@gmail.com'  # Change this
    MAIL_PASSWORD = 'your-app-password'      # Change this (use App Password)
    ADMIN_EMAIL = 'admin@example.com'        # Where to send alerts
    
    # Low stock threshold
    LOW_STOCK_THRESHOLD = 5