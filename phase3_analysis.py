#!/usr/bin/env python3

import os
import json
import anthropic
import time
from typing import Dict, List, Any
import utils

def analyze_post_with_token_management(post_data: Dict[str, Any], client: anthropic.Anthropic, token_tracker: Dict[str, int]) -> Dict[str, Any]:
    """Analyze a single post with proactive token limit management"""
    
    # Check if we're approaching rate limit (45K out of 50K)
    current_tokens = token_tracker.get('minute_tokens', 0)
    if current_tokens >= 30000:
        print(f"⏳ Approaching token limit ({current_tokens}/50,000). Sleeping 60 seconds to reset...")
        time.sleep(60)
        token_tracker['minute_tokens'] = 0
        token_tracker['minute_start'] = time.time()
    
    # Extract text content
    title = post_data.get('original_data', {}).get('title', '')
    selftext = post_data.get('full_selftext', '')
    comments = post_data.get('comments', [])
    
    # Combine all text
    all_text = f"Title: {title}\n\nPost: {selftext}\n\n"
    all_text += "Comments:\n"
    for comment in comments:  # Limit to first 10 comments for cost
        all_text += f"- {comment.get('body', '')}\n"
    
    # Create analysis prompt
    prompt = f"""
Analyze this Reddit post and extract ALL potential brand names, company names, or labels mentioned. 

Be VERY INCLUSIVE - include:
- Any capitalized words that could be brand names
- Product names that might be brands
- Store names or retailer names
- Any proper nouns that could potentially be brands
- Lesser-known or niche brands

Do NOT be restrictive - if something could possibly be a brand, include it. I will filter later.

Text to analyze:
{all_text}

IMPORTANT: Respond with ONLY valid JSON, no explanatory text before or after. Use this exact format:
{{
  "brands": [
    {{"name": "Brand Name", "mentions": 3}}
  ]
}}
"""
    
    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse JSON response
        raw_response = response.content[0].text
        analysis = json.loads(raw_response)
        
        # Track token usage
        usage = response.usage
        total_used = usage.input_tokens + usage.output_tokens
        
        # Update token tracker
        token_tracker['minute_tokens'] += total_used
        
        print(f"🔍 Tokens used: {total_used} (Minute total: {token_tracker['minute_tokens']}/50,000)")
        
        # Add usage info to response
        analysis['_token_usage'] = {
            'input_tokens': usage.input_tokens,
            'output_tokens': usage.output_tokens
        }
        
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error for post {post_data.get('post_id', 'unknown')}: {e}")
        print(f"Raw response was: {response.content[0].text}")
        return {}
    except Exception as e:
        print(f"Error analyzing post {post_data.get('post_id', 'unknown')}: {e}")
        return {}


def analyze_post_for_brands(post_data: Dict[str, Any], client: anthropic.Anthropic, token_tracker: Dict[str, int] = None) -> Dict[str, Any]:
    """Analyze a single post for potential brand mentions"""
    if token_tracker is None:
        token_tracker = {'minute_tokens': 0, 'minute_start': time.time()}
    return analyze_post_with_token_management(post_data, client, token_tracker)

def main():
    utils.print_phase_header(3, "Fashion Data Analysis with Claude")
    
    # Get search parameters from environment
    search_term = os.environ.get('SEARCH_TERM', 'python')
    subreddit_name = os.environ['SUBREDDIT_NAME']
    post_limit = int(os.environ.get('POST_LIMIT', 5))
    
    # Get search-specific directory
    output_dir = utils.get_search_output_dir(search_term, subreddit_name)
    
    # Test Claude connection first
    if not utils.test_claude_connection("brands"):
        return
    
    # Load Phase 2 data from search-specific directory
    input_file = os.path.join(output_dir, 'superOutput.json')
    if not os.path.exists(input_file):
        print(f"❌ Phase 2 output file not found: {input_file}")
        return
    
    print(f"📖 Loading Phase 2 data from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        posts_data = json.load(f)
    
    print(f"Found {len(posts_data)} posts to analyze")
    
    # Initialize Claude client and token tracker
    client = utils.get_claude_client()
    token_tracker = {'minute_tokens': 0, 'minute_start': time.time()}
    
    # Process all posts and accumulate brand mentions
    brand_accumulator = {}
    total_input_tokens = 0
    total_output_tokens = 0
    
    for i, post in enumerate(posts_data[:post_limit], 1):
        post_title = post.get('original_data', {}).get('title', 'No title')
        print(f"\n📊 Analyzing post {i}/{min(post_limit, len(posts_data))}: {post_title[:50]}...")
        
        analysis = analyze_post_for_brands(post, client, token_tracker)
        
        # Track token usage
        if analysis and '_token_usage' in analysis:
            total_input_tokens += analysis['_token_usage']['input_tokens']
            total_output_tokens += analysis['_token_usage']['output_tokens']
        
        if analysis and 'brands' in analysis:
            print(f"✅ Found {len(analysis['brands'])} brands")
            
            # Accumulate brand mentions
            for brand in analysis['brands']:
                brand_name = brand['name']
                mentions = brand['mentions']
                
                if brand_name in brand_accumulator:
                    brand_accumulator[brand_name] += mentions
                else:
                    brand_accumulator[brand_name] = mentions
        else:
            print("❌ Analysis failed")
    
    # Filter out brands with only 1 mention, then create brands.json with IDs (sorted alphabetically by name)
    filtered_brands = {name: count for name, count in brand_accumulator.items() if count > 1}
    brand_list = sorted(filtered_brands.items(), key=lambda x: x[0].lower())
    brands_json = [
        {"id": i+1, "name": name, "total_mentions": count}
        for i, (name, count) in enumerate(brand_list)
    ]
    
    # Report filtering results
    original_count = len(brand_accumulator)
    filtered_count = len(filtered_brands)
    removed_count = original_count - filtered_count
    print(f"🔍 Filtered out {removed_count} brands with only 1 mention ({original_count} → {filtered_count} brands)")
    
    # Save raw_brands.json to search-specific directory
    brands_file = os.path.join(output_dir, 'raw_brands.json')
    utils.save_json_file(brands_json, brands_file, "brands", compact_array=True)
    
    # Phase completion summary
    print(f"\n📊 Total token usage: Input: {total_input_tokens:,}, Output: {total_output_tokens:,}, Total: {total_input_tokens + total_output_tokens:,}")
    
    stats = {
        "Posts processed": min(post_limit, len(posts_data)),
        "Unique brands found": len(brands_json),
        "Brands before filtering": original_count,
        "Brands filtered out": removed_count,
        "Total tokens used": f"{total_input_tokens + total_output_tokens:,}",
        "Files saved": brands_file
    }
    utils.print_phase_complete(3, stats)

if __name__ == "__main__":
    main()