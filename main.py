import os
import json
import logging
from flask import Flask, request, jsonify
import psycopg2
from google.cloud import secretmanager

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to retrieve DATABASE_URL from Secret Manager
def get_secret(secret_name):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{os.environ.get('GCP_PROJECT')}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')


@app.route('/', methods=['POST'])
def github_webhook():
    try:
        data = request.get_json()
        logging.info(f"Received webhook data: {data}")

        if not data or 'head_commit' not in data:
            logging.error("Invalid webhook payload.")
            return jsonify({'status': 'error', 'message': 'Invalid webhook data'}), 400

        commit = data['head_commit']
        commit_sha = commit.get('id')
        author_name = commit.get('author', {}).get('name')
        author_email = commit.get('author', {}).get('email')
        commit_message = commit.get('message')
        timestamp = commit.get('timestamp')

        DATABASE_URL = get_secret("your-secret-name")  # Replace with your secret name

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO commits (commit_sha, author_name, author_email, commit_message, timestamp) VALUES (%s, %s, %s, %s, %s)",
                (commit_sha, author_name, author_email, commit_message, timestamp)
            )
            conn.commit()
            logging.info(f"Commit {commit_sha} successfully recorded.")
            return jsonify({'status': 'success'}), 201

        except psycopg2.IntegrityError as e:
            logging.warning(f"Duplicate commit detected: {commit_sha}")
            return jsonify({'status': 'warning', 'message': f"Duplicate commit detected: {commit_sha}"}), 200

        except psycopg2.Error as e:
            logging.exception(f"Database error: {e}")
            return jsonify({'status': 'error', 'message': 'Database error'}), 500

        finally:
            cur.close()
            conn.close()

    except json.JSONDecodeError:
        logging.error("Invalid JSON data received.")
        return jsonify({'status': 'error', 'message': 'Invalid JSON data'}), 400
    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error'}), 500


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
