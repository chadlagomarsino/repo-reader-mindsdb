from dotenv import load_dotenv
import os

# Explicitly load .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Test if GITHUB_API_KEY is loaded
github_key = os.getenv('GITHUB_API_KEY')

if github_key:
    print(f"GitHub API Key loaded successfully: {github_key}")
else:
    print("Error: GITHUB_API_KEY is not set.")
