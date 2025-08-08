# Reddit API Demo with Docker

A simple Python application that fetches posts from Reddit using the PRAW library, containerized with Docker.

## Prerequisites

1. **Reddit API Credentials**: You need to create a Reddit application to get API credentials
   - Go to https://www.reddit.com/prefs/apps
   - Click "Create App" or "Create Another App"
   - Choose "script" as the app type
   - Note down your `client_id` and `client_secret`

## Setup

1. **Create a `.env` file** in the project directory:
```bash
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
SUBREDDIT_NAME=python
POST_LIMIT=10
```

2. **Create output directory** (optional, for saving JSON data):
```bash
mkdir output
```

## Running with Docker Compose

```bash
# Build and run
docker-compose up --build

# Run in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f
```

## Running with Docker (manual)

```bash
# Build the image
docker build -t reddit-demo .

# Run the container
docker run --env-file .env reddit-demo
```

## Running Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables and run
export REDDIT_CLIENT_ID=your_client_id
export REDDIT_CLIENT_SECRET=your_client_secret
python reddit_demo.py
```

## Configuration

Environment variables:
- `REDDIT_CLIENT_ID`: Your Reddit app client ID (required)
- `REDDIT_CLIENT_SECRET`: Your Reddit app client secret (required)
- `SUBREDDIT_NAME`: Subreddit to fetch posts from (default: "python")
- `POST_LIMIT`: Number of posts to fetch (default: 10)

## Output

The script will:
1. Print post information to the console
2. Save detailed post data to `reddit_posts.json`

## Files

- `reddit_demo.py`: Main Python script
- `requirements.txt`: Python dependencies
- `Dockerfile`: Docker configuration
- `docker-compose.yml`: Docker Compose configuration
- `.env`: Environment variables (create this file)