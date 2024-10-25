from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
import os
from apscheduler.schedulers.background import BackgroundScheduler
import plotly.express as px

# Hardcoded API keys
GITHUB_API_KEY = "YourGitHubAPIKey"  # Replace with your GitHub API key
MINDSDB_SQL_API = "YourMindsDB API Key"  # URL for the MindsDB SQL API

app = Flask(__name__)

# Set up headers for GitHub API authentication
github_headers = {
    "Authorization": f"token {GITHUB_API_KEY}"
}

# Helper function to execute MindsDB SQL queries
def query_mindsdb(sql_query):
    response = requests.post(MINDSDB_SQL_API, json={"query": sql_query})
    if response.status_code == 200:
        return pd.DataFrame(response.json()['data'])
    else:
        print(f"Failed to query MindsDB: {response.status_code} - {response.text}")
        return pd.DataFrame()

# Function to fetch GitHub issues and comments
def fetch_github_data():
    print("Starting GitHub data collection...")
    
    # GitHub API URL
    repo_owner = "mindsdb"
    repo_name = "mindsdb"
    issues_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"

    # Fetch issues
    response = requests.get(issues_api_url, headers=github_headers)
    if response.status_code != 200:
        print(f"Failed to fetch GitHub issues: {response.status_code}")
        return []
    
    issues = response.json()
    issue_data = []

    # Fetch comments for each issue
    for issue in issues:
        comments_url = issue['comments_url']
        comments_response = requests.get(comments_url, headers=github_headers)
        if comments_response.status_code == 200:
            comments = comments_response.json()
            for comment in comments:
                issue_data.append({
                    "issue_id": issue['id'],
                    "issue_title": issue['title'],
                    "issue_body": issue.get('body', ''),
                    "comment_user": comment['user']['login'],
                    "comment_text": comment['body']
                })
        else:
            print(f"Failed to fetch comments for issue {issue['id']}: {comments_response.status_code}")

    return issue_data

# Function to upload GitHub data to MindsDB as a dataset
def upload_data_to_mindsdb(issue_data):
    # Create a DataFrame
    df = pd.DataFrame(issue_data)
    
    # Upload the data to MindsDB
    csv_file_path = "/tmp/github_data.csv"
    df.to_csv(csv_file_path, index=False)

    # Query to upload the data into MindsDB
    upload_query = f"""
    CREATE OR REPLACE TABLE github_issues_data
    FROM FILE '{csv_file_path}'
    WITH COLUMNS (
        'issue_id', 'issue_title', 'issue_body', 'comment_user', 'comment_text'
    );
    """
    query_mindsdb(upload_query)

# Function to run semantic search using MindsDB model
def semantic_search(user_query):
    # Example: Create a query embedding (this part can be improved based on your model)
    embedding_query = f"SELECT PREDICT(semantic_search_model.comment_embedding) AS embedding FROM (SELECT '{user_query}' AS query_text);"
    query_embedding = query_mindsdb(embedding_query).iloc[0]['embedding']

    # SQL query to find the most similar issues/comments based on embeddings
    semantic_search_query = f"""
    SELECT issue_title, comment_text, SIMILARITY(semantic_search_model.comment_embedding, '{query_embedding}') AS similarity
    FROM github_issues_data
    WHERE SIMILARITY(semantic_search_model.comment_embedding, '{query_embedding}') > 0.8
    ORDER BY similarity DESC
    LIMIT 10;
    """
    return query_mindsdb(semantic_search_query)

# Function to rank users based on GitHub profile data
def rank_users():
    # Assuming GitHub profile data is stored in MindsDB
    user_ranking_query = """
    SELECT comment_user, 
           SUM(user_followers) * 0.6 + SUM(user_public_repos) * 0.3 + COUNT(comment_text) * 0.1 AS user_score
    FROM github_issues_data
    GROUP BY comment_user
    ORDER BY user_score DESC;
    """
    return query_mindsdb(user_ranking_query)

# Main route to display dashboard and handle search
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    # Ensure GitHub data is collected and uploaded to MindsDB
    issue_data = fetch_github_data()
    upload_data_to_mindsdb(issue_data)

    # Handle search query if present
    search_results = None
    if request.method == 'POST':
        user_query = request.form.get('query')
        search_results = semantic_search(user_query)

    # Query for the most commented issues
    comments_query = """
    SELECT issue_title, COUNT(*) as total_comments 
    FROM github_issues_data 
    GROUP BY issue_title
    ORDER BY total_comments DESC;
    """
    comment_data = query_mindsdb(comments_query)

    # Query for ranking users
    user_ranking = rank_users()

    # Visualization: Most Commented Issues
    fig1 = px.bar(comment_data, x='issue_title', y='total_comments', title='Most Commented Issues')
    comment_chart = fig1.to_html(full_html=False)

    # Visualization: User Rankings
    fig2 = px.bar(user_ranking, x='comment_user', y='user_score', title='Top Users by Score')
    ranking_chart = fig2.to_html(full_html=False)

    # Render the dashboard with search results (if any)
    return render_template('dashboard.html', 
                           comment_chart=comment_chart, 
                           ranking_chart=ranking_chart, 
                           search_results=search_results.to_dict(orient='records') if search_results is not None else None)

# Scheduler to automate GitHub data collection every hour
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_github_data, trigger="interval", hours=1)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True)
