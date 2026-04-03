import os

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', 'your-google-client-id')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', 'your-google-secret')

MICROSOFT_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID', 'your-microsoft-client-id')
MICROSOFT_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET', 'your-microsoft-secret')

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/oidc/userinfo"
