import requests
from urllib.parse import urlencode

# Replace with your actual values from Strava API settings
CLIENT_ID = '76528'
CLIENT_SECRET = 'de46e1ec96ad277ae0be94f949301483a4cd1a4d'
REDIRECT_URI = 'http://localhost'

# Step 1: Get authorization URL
auth_url = f"https://www.strava.com/oauth/authorize?{urlencode({
    'client_id': CLIENT_ID,
    'response_type': 'code',
    'redirect_uri': REDIRECT_URI,
    'approval_prompt': 'force',
    'scope': 'read,activity:read_all'
})}"

print("=" * 60)
print("STRAVA API SETUP")
print("=" * 60)
print(f"1. Visit this URL in your browser:")
print(f"{auth_url}")
print()
print("2. Click 'Authorize' to allow access to your Strava data")
print("3. You'll be redirected to a localhost URL that won't load")
print("4. Copy the ENTIRE URL from your browser's address bar")
print("5. Look for the 'code=' parameter in that URL")
print()
print("Example: http://localhost/?state=&code=ABC123XYZ&scope=read,activity:read_all")
print("In this example, your code would be: ABC123XYZ")
print("=" * 60)

code = input("Enter the authorization code from the URL: ").strip()

if not code:
    print("No code entered. Exiting.")
    exit()

# Step 2: Exchange code for tokens
print("\nExchanging code for tokens...")
token_url = 'https://www.strava.com/oauth/token'
data = {
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'code': code,
    'grant_type': 'authorization_code'
}

response = requests.post(token_url, data=data)

if response.status_code == 200:
    tokens = response.json()
    print("\n" + "=" * 60)
    print("SUCCESS! Here are your tokens:")
    print("=" * 60)
    print(f"ACCESS_TOKEN: {tokens['access_token']}")
    print(f"REFRESH_TOKEN: {tokens['refresh_token']}")
    print(f"EXPIRES_AT: {tokens['expires_at']}")
    print()
    print("Add these to your .env file:")
    print("=" * 60)
    print(f"STRAVA_CLIENT_ID={CLIENT_ID}")
    print(f"STRAVA_CLIENT_SECRET={CLIENT_SECRET}")
    print(f"STRAVA_REFRESH_TOKEN={tokens['refresh_token']}")
    print("=" * 60)
else:
    print(f"Error: {response.status_code}")
    print(response.text)