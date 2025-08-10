#!/usr/bin/env python3

import praw
import os
import json
from datetime import datetime

def main():
    print("=== PHASE 2: FETCH FULL POST DETAILS ===")
    
    # Check if Phase 1 data exists
    input_file = '/app/output/reddit_posts.json'
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
    
    for i, post_data in enumerate(posts_data, 1):
        print(f"Processing post {i}/{len(posts_data)}: {post_data['title'][:50]}...")
        
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
    
    # Save Phase 2 data
    output_file = '/app/output/superOutput.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(super_output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Phase 2 complete! Full data saved to {output_file}")
    print(f"Processed {len(super_output)} posts with full details and comments")

if __name__ == "__main__":
    main()