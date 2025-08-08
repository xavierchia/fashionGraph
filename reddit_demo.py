#!/usr/bin/env python3

import praw
import os
import json
from datetime import datetime

def main():
    # Reddit API credentials from environment variables
    reddit = praw.Reddit(
        client_id=os.environ.get('REDDIT_CLIENT_ID'),
        client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
        user_agent='fashionGraph/1.0 by /u/Substantial_Purple_1'
    )
    
    # Fetch posts from a popular subreddit
    subreddit_name = os.environ.get('SUBREDDIT_NAME', 'python')
    limit = int(os.environ.get('POST_LIMIT', '10'))
    
    print(f"Fetching {limit} hot posts from r/{subreddit_name}...")
    
    subreddit = reddit.subreddit(subreddit_name)
    posts_data = []
    
    for post in subreddit.hot(limit=limit):
        post_info = {
            'title': post.title,
            'author': str(post.author) if post.author else '[deleted]',
            'score': post.score,
            'url': post.url,
            'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
            'num_comments': post.num_comments,
            'selftext': post.selftext[:200] + '...' if len(post.selftext) > 200 else post.selftext
        }
        posts_data.append(post_info)
        
        print(f"📝 {post_info['title'][:60]}{'...' if len(post_info['title']) > 60 else ''}")
        print(f"   👤 u/{post_info['author']} | 👍 {post_info['score']} | 💬 {post_info['num_comments']}")
        print()
    
    # Save data to JSON file
    output_dir = '/app/output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_file = os.path.join(output_dir, 'reddit_posts.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(posts_data, f, indent=2, ensure_ascii=False)
    
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    main()