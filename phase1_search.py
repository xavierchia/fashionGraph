#!/usr/bin/env python3

import praw
import os
import json
from datetime import datetime

def main():
    print("=== PHASE 1: SEARCH POSTS ===", flush=True)
    
    # Search posts
    search_term = os.environ.get('SEARCH_TERM', 'python')
    search_sort = os.environ.get('SEARCH_SORT', 'relevance')
    time_filter = os.environ.get('TIME_FILTER', 'all')
    limit = int(os.environ.get('POST_LIMIT', '10'))
    
    print(f"Searching Reddit for '{search_term}' (sort: {search_sort}, time: {time_filter}, limit: {limit})...", flush=True)
    
    print("Connecting to Reddit API...", flush=True)
    
    # Reddit API credentials from environment variables
    reddit = praw.Reddit(
        client_id=os.environ.get('REDDIT_CLIENT_ID'),
        client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
        user_agent='fashionGraph/1.0 by /u/Substantial_Purple_1'
    )
    
    subreddit = reddit.subreddit('BuyItForLife')
    posts_data = []
    
    for post in subreddit.search(search_term, sort=search_sort, time_filter=time_filter, limit=limit):
        post_info = {
            'id': post.id,
            'title': post.title,
            'author': str(post.author) if post.author else '[deleted]',
            'score': post.score,
            'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
            'num_comments': post.num_comments,
            'selftext': post.selftext[:200] + '...' if len(post.selftext) > 200 else post.selftext,
            'subreddit': str(post.subreddit)
        }
        posts_data.append(post_info)

    print(f"Found {len(posts_data)} posts", flush=True)
    
    print("Saving data...", flush=True)
    
    # Save data
    output_dir = '/app/output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_file = os.path.join(output_dir, 'reddit_posts.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(posts_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Phase 1 complete! Data saved to {output_file}", flush=True)
    print(f"Next: Set PHASE=2 to fetch full post details", flush=True)

if __name__ == "__main__":
    main()