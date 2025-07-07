import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    # AWS Settings 
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'eu-west-1')
    
    # S3 Buckets
    SOURCE_BUCKET = os.getenv('SOURCE_BUCKET', 'mammalweb-original-images')
    DEST_BUCKET = os.getenv('DEST_BUCKET', 'mammalweb-compressed-images')
    
    # Database
    DB_HOST = os.getenv('DB_HOST')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('DB_NAME')