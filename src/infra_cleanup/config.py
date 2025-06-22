import os

# Default region and account info
REGION = os.getenv('AWS_REGION', 'us-east-1')
ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID', '123456789012')

# Optional credentials - leave blank to use default credential chain
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_SESSION_TOKEN = os.getenv('AWS_SESSION_TOKEN', '')
