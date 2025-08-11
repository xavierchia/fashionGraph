#!/usr/bin/env python3

import os
import json
import anthropic
from typing import Dict, List, Any

def normalize_brand_name(name: str) -> str:
    """Remove punctuation, spaces, convert to lowercase for brand matching"""
    return ''.join(c.lower() for c in name if c.isalnum())

def test_claude_connection():
    """Test basic Claude API connection"""
    try:
        client = anthropic.Anthropic(api_key=os.environ.get('CLAUDE_API_KEY'))
        
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=100,
            messages=[{
                "role": "user", 
                "content": "Hello! Can you help me analyze fashion data? Just respond with 'Yes, I can help!'"
            }]
        )
        
        print("✅ Claude API connection successful!")
        print(f"Response: {response.content[0].text}")
        return True
        
    except Exception as e:
        print(f"❌ Claude API connection failed: {e}")
        return False

def analyze_post_for_brands(post_data: Dict[str, Any], client: anthropic.Anthropic) -> Dict[str, Any]:
    """Analyze a single post for potential brand mentions"""
    
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
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error for post {post_data.get('post_id', 'unknown')}: {e}")
        print(f"Raw response was: {response.content[0].text}")
        return {}
    except Exception as e:
        print(f"Error analyzing post {post_data.get('post_id', 'unknown')}: {e}")
        return {}

def main():
    print("🚀 Starting Phase 3: Fashion Data Analysis with Claude")
    
    # Ensure output directory exists
    os.makedirs('output', exist_ok=True)
    
    # Test Claude connection first
    if not test_claude_connection():
        return
    
    # Load Phase 2 data
    input_file = 'output/superOutput.json'
    if not os.path.exists(input_file):
        print(f"❌ Phase 2 output file not found: {input_file}")
        return
    
    print(f"📖 Loading Phase 2 data from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        posts_data = json.load(f)
    
    print(f"Found {len(posts_data)} posts to analyze")
    
    # Get search term from environment (the brand_a)
    search_term = os.environ.get('SEARCH_TERM', 'levis').lower()
    
    # Initialize Claude client
    client = anthropic.Anthropic(api_key=os.environ.get('CLAUDE_API_KEY'))
    
    # Process all posts and accumulate brand mentions
    brand_accumulator = {}
    
    for i, post in enumerate(posts_data[:5], 1):
        post_title = post.get('original_data', {}).get('title', 'No title')
        print(f"\n📊 Analyzing post {i}/{len(posts_data)}: {post_title[:50]}...")
        
        analysis = analyze_post_for_brands(post, client)
        
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
    
    # Create brands.json with IDs
    brand_list = sorted(brand_accumulator.items(), key=lambda x: x[1], reverse=True)
    brands_json = [
        {"id": i+1, "name": name, "total_mentions": count}
        for i, (name, count) in enumerate(brand_list)
    ]
    
    # Find search term brand ID using normalized matching
    search_brand_id = None
    normalized_search = normalize_brand_name(search_term)
    
    for brand in brands_json:
        normalized_brand = normalize_brand_name(brand['name'])
        if normalized_search == normalized_brand:
            search_brand_id = brand['id']
            break
    
    # Create brand_brand_mentions.json (search_term -> other_brands)
    brand_relationships = []
    if search_brand_id:
        for brand in brands_json:
            if brand['id'] != search_brand_id:  # Don't include self-reference
                brand_relationships.append({
                    "brand_a_id": search_brand_id,
                    "brand_b_id": brand['id'], 
                    "mentions": brand['total_mentions']
                })
    
    # Save brands.json
    brands_file = 'output/brands.json'
    print(f"\n💾 Saving brands to {brands_file}")
    with open(brands_file, 'w', encoding='utf-8') as f:
        json.dump(brands_json, f, indent=2, ensure_ascii=False)
    
    # Save brand_brand_mentions.json
    relationships_file = 'output/brand_brand_mentions.json'
    print(f"💾 Saving brand relationships to {relationships_file}")
    with open(relationships_file, 'w', encoding='utf-8') as f:
        json.dump(brand_relationships, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Analysis complete! Processed {len(posts_data[:5])} posts")
    print(f"📁 Found {len(brands_json)} unique brands")
    print(f"📁 Search term brand ID: {search_brand_id}")
    print(f"📁 Generated {len(brand_relationships)} brand relationships")
    print(f"📁 Files saved: {brands_file}, {relationships_file}")

if __name__ == "__main__":
    main()