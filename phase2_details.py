#!/usr/bin/env python3

import praw
import os
import json
from datetime import datetime
import utils

def main():
    print("=== PHASE 2: FETCH FULL POST DETAILS ===")
    
    # Get search parameters from environment
    search_term = os.environ.get('SEARCH_TERM', 'python')
    subreddit_name = os.environ['SUBREDDIT_NAME']
    post_limit = int(os.environ.get('POST_LIMIT', 5))
    
    # Get search-specific directory
    output_dir = utils.get_search_output_dir(search_term, subreddit_name)
    input_file = os.path.join(output_dir, 'reddit_posts.json')
    
    # Check if Phase 1 data exists
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found. Run Phase 1 first (PHASE=1)")
        return
    
    # Load Phase 1 data
    with open(input_file, 'r', encoding='utf-8') as f:
        posts_data = json.load(f)
    
    print(f"Loading {len(posts_data)} posts from {input_file}")
    print("Connecting to Reddit API...")
    
    # Reddit API credentials
    reddit = praw.Reddit(
        client_id=os.environ.get('REDDIT_CLIENT_ID'),
        client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
        user_agent='fashionGraph/1.0 by /u/Substantial_Purple_1'
    )
    
    print("Fetching full post details and comments...")
    print("This will take 5-15 minutes due to rate limits...")
    
    super_output = []
    
    for i, post_data in enumerate(posts_data[:post_limit], 1):
        print(f"Processing post {i}/{min(post_limit, len(posts_data))}: {post_data['title'][:50]}...")
        
        post_id = post_data.get('id')
        if not post_id:
            print(f"  Skipping - no post ID found")
            continue
            
        try:
            # Fetch full post details
            submission = reddit.submission(id=post_id)
            
            # Expand all comments (handles "load more" comments)
            submission.comments.replace_more(limit=None)
            
            # Collect all comments
            comments = []
            for comment in submission.comments.list():
                comments.append({
                    'body': comment.body,
                    'score': comment.score,
                    'author': str(comment.author) if comment.author else '[deleted]',
                    'created_utc': datetime.fromtimestamp(comment.created_utc).isoformat()
                })
            
            full_post = {
                'post_id': post_id,
                'original_data': post_data,
                'full_selftext': submission.selftext,
                'comments': comments,
                'total_comments': len(comments)
            }
            
            super_output.append(full_post)
            print(f"  ✓ Got {len(comments)} comments")
            
        except Exception as e:
            print(f"  ✗ Error processing post: {e}")
            continue
    
    # Save Phase 2 data to search-specific directory
    output_file = os.path.join(output_dir, 'superOutput.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(super_output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Phase 2 complete! Full data saved to {output_file}")
    print(f"Processed {len(super_output)} posts with full details and comments")

if __name__ == "__main__":
    main()