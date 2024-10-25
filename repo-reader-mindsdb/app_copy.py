from flask import Flask, render_template, request
import requests
import pandas as pd
import os
from apscheduler.schedulers.background import BackgroundScheduler
import plotly.express as px

app = Flask(__name__)

MINDSDB_SQL_API = "http://localhost:47334/api/sql/query"  # MindsDB SQL API URL

# Helper function to interact with MindsDB's SQL API
def query_mindsdb(sql_query):
    try:
        response = requests.post(MINDSDB_SQL_API, json={"query": sql_query})
        response_json = response.json()
        if 'data' in response_json:
            return pd.DataFrame(response_json['data'])
        else:
            error_message = response_json.get('error_message', 'Unknown error')
            print(f"Error querying MindsDB: {error_message}")
            return pd.DataFrame()
    except Exception as e:
        print(f"Exception occurred while querying MindsDB: {e}")
        return pd.DataFrame()

# Function to save GitHub data to a CSV file
def save_data_to_csv(issue_data):
    df = pd.DataFrame(issue_data)
    csv_file_path = 'github_issues_data.csv'
    df.to_csv(csv_file_path, index=False)
    print(f"Data saved to {csv_file_path}")

# Function to create a dataset in MindsDB from the CSV file
def create_dataset_in_mindsdb():
    create_dataset_query = """
    CREATE DATASET github_issues_data
    FROM FILE 'github_issues_data.csv'
    WITH COLUMNS ('issue_id', 'issue_title', 'issue_body', 'comment_user', 'comment_text');
    """
    response = query_mindsdb(create_dataset_query)
    print(f"Create Dataset Response: {response}")

# Function to fetch the most commented issues from MindsDB
def fetch_data_from_mindsdb():
    query = """
    SELECT issue_title, COUNT(*) as total_comments 
    FROM github_issues_data 
    GROUP BY issue_title
    ORDER BY total_comments DESC;
    """
    result = query_mindsdb(query)
    return result

# Function to scrape GitHub issues and comments (simplified for this example)
def fetch_github_data():
    # Example GitHub API call (you should replace this with your actual data scraping logic)
    issue_data = [
        {
            'issue_id': 12345,
            'issue_title': 'Issue 1',
            'issue_body': 'This is the first issue',
            'comment_user': 'user1',
            'comment_text': 'First comment on issue 1'
        },
        {
            'issue_id': 67890,
            'issue_title': 'Issue 2',
            'issue_body': 'This is the second issue',
            'comment_user': 'user2',
            'comment_text': 'First comment on issue 2'
        }
    ]
    return issue_data

# Route for the dashboard
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    # Fetch GitHub data (or load it from GitHub if needed)
    issue_data = fetch_github_data()
    
    # Save the data to a CSV file
    save_data_to_csv(issue_data)
    
    # Create a dataset in MindsDB from the CSV file
    create_dataset_in_mindsdb()

    # Fetch the most commented issues from MindsDB
    comment_data = fetch_data_from_mindsdb()

    # Visualize the data
    if 'issue_title' in comment_data.columns and 'total_comments' in comment_data.columns:
        fig1 = px.bar(comment_data, x='issue_title', y='total_comments', title='Most Commented Issues')
        comment_chart = fig1.to_html(full_html=False)
    else:
        comment_chart = "<p>No data available.</p>"

    return render_template('dashboard.html', comment_chart=comment_chart)

# Schedule regular data collection and dataset creation
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_github_data, trigger="interval", hours=1)
scheduler.add_job(func=create_dataset_in_mindsdb, trigger="interval", hours=1)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True)

