#!/usr/bin/env python3

import os
import json
import anthropic
from typing import Dict, List, Any
import re

def test_claude_connection():
    """Test basic Claude API connection"""
    try:
        client = anthropic.Anthropic(api_key=os.environ.get('CLAUDE_API_KEY'))
        
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=100,
            messages=[{
                "role": "user", 
                "content": "Hello! Can you help me analyze category data? Just respond with 'Yes, I can help!'"
            }]
        )
        
        print("✅ Claude API connection successful!")
        print(f"Response: {response.content[0].text}")
        return True
        
    except Exception as e:
        print(f"❌ Claude API connection failed: {e}")
        return False

def normalize_brand_name(name: str) -> str:
    """Remove punctuation, spaces, convert to lowercase for brand matching"""
    return ''.join(c.lower() for c in name if c.isalnum())

def extract_sentence_context(text: str, brand_mention_index: int, context_window: int = 150) -> str:
    """Extract local context around a brand mention"""
    start = max(0, brand_mention_index - context_window)
    end = min(len(text), brand_mention_index + context_window)
    return text[start:end].strip()

def extract_brand_contexts(posts_data: List[Dict[str, Any]], brand_name: str) -> List[str]:
    """Extract all contexts where a brand is mentioned across all posts"""
    
    contexts = []
    normalized_brand = normalize_brand_name(brand_name)
    
    for post in posts_data:
        # Get all text sources
        title = post.get('original_data', {}).get('title', '')
        selftext = post.get('full_selftext', '')
        comments = post.get('comments', [])
        
        # Check each text source for brand mentions
        text_sources = [
            ("title", title),
            ("post", selftext)
        ]
        
        # Add comments as separate sources
        for i, comment in enumerate(comments[:20]):  # Limit to first 20 comments
            comment_body = comment.get('body', '')
            if comment_body:
                text_sources.append((f"comment_{i}", comment_body))
        
        # Search for brand in each text source
        for source_type, text in text_sources:
            if not text:
                continue
                
            normalized_text = normalize_brand_name(text)
            
            # Find all occurrences of the brand in this text
            start_pos = 0
            while True:
                pos = normalized_text.find(normalized_brand, start_pos)
                if pos == -1:
                    break
                    
                # Extract context around this mention
                context = extract_sentence_context(text, pos, context_window=100)
                if context and len(context) > 10:  # Skip very short contexts
                    contexts.append(context)
                    
                start_pos = pos + len(normalized_brand)
    
    return contexts

def process_contexts_in_batches(brand_name: str, contexts: List[str], client: anthropic.Anthropic, batch_size: int = 20) -> List[str]:
    """Process contexts in batches and extract categories"""
    
    all_categories = []
    
    # Process contexts in batches
    for i in range(0, len(contexts), batch_size):
        batch = contexts[i:i + batch_size]
        
        # Create batch prompt
        contexts_text = "\n\n".join([
            f"Context {j+1}: {context}"
            for j, context in enumerate(batch)
        ])
        
        prompt = f"""
Analyze these {len(batch)} mentions of "{brand_name}" and extract relevant categories/tags:

- Style categories (raw denim, selvedge, vintage, etc.)
- Origin/country (japanese, american, italian, etc.) 
- Price tier (premium, budget, mid-range, etc.)
- Use cases (workwear, streetwear, formal, casual, etc.)
- Brand characteristics (heavyweight, slim-fit, sustainable, etc.)

{contexts_text}

IMPORTANT: Respond with ONLY valid JSON, no explanatory text. Use this exact format:
{{
  "categories": ["category1", "category2", "category3"]
}}
"""
        
        try:
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_response = response.content[0].text
            analysis = json.loads(raw_response)
            batch_categories = analysis.get('categories', [])
            
            print(f"    📦 Batch {i//batch_size + 1}: Found {len(batch_categories)} categories")
            all_categories.extend(batch_categories)
            
        except Exception as e:
            print(f"    ❌ Error processing batch {i//batch_size + 1} for {brand_name}: {e}")
    
    return all_categories

def main():
    print("🚀 Starting Phase 4: Category Analysis with Claude")
    
    # Ensure output directory exists
    os.makedirs('output', exist_ok=True)
    
    # Test Claude connection first
    if not test_claude_connection():
        return
    
    # Load brands.json
    brands_file = 'output/brands.json'
    if not os.path.exists(brands_file):
        print(f"❌ Brands file not found: {brands_file}")
        print("Please run Phase 3 first to generate brands.json")
        return
    
    print(f"📖 Loading brands from {brands_file}")
    with open(brands_file, 'r', encoding='utf-8') as f:
        brands_data = json.load(f)
    
    # Load superOutput.json
    posts_file = 'output/superOutput.json'
    if not os.path.exists(posts_file):
        print(f"❌ Posts file not found: {posts_file}")
        return
    
    print(f"📖 Loading posts from {posts_file}")
    with open(posts_file, 'r', encoding='utf-8') as f:
        posts_data = json.load(f)
    
    print(f"Found {len(brands_data)} brands and {len(posts_data)} posts to analyze")
    
    # Initialize Claude client
    client = anthropic.Anthropic(api_key=os.environ.get('CLAUDE_API_KEY'))
    
    # Track categories across all brands
    category_accumulator = {}  # category_name -> total_mentions
    brand_category_relationships = {}  # brand_id -> {category_name -> mentions}
    
    # Process each brand (limit to first few for testing)
    for brand in brands_data[:3]:  # Test with first 3 brands
        brand_id = brand['id']
        brand_name = brand['name']
        
        print(f"\n🔍 Analyzing categories for brand: {brand_name} (ID: {brand_id})")
        
        # Phase 1: Collection - Extract all contexts for this brand
        print(f"  📚 Collecting contexts...")
        contexts = extract_brand_contexts(posts_data, brand_name)
        print(f"  ✅ Found {len(contexts)} contexts mentioning {brand_name}")
        
        if not contexts:
            print(f"  ⚠️  No contexts found for {brand_name}, skipping...")
            continue
        
        # Phase 2: Processing - Analyze contexts in batches
        print(f"  🤖 Processing {len(contexts)} contexts in batches of 20...")
        all_categories = process_contexts_in_batches(brand_name, contexts, client, batch_size=20)
        
        # Phase 3: Accumulation - Count category mentions
        brand_categories = {}  # category_name -> mentions for this brand
        for category in all_categories:
            category_lower = category.lower().strip()
            if category_lower:
                brand_categories[category_lower] = brand_categories.get(category_lower, 0) + 1
                category_accumulator[category_lower] = category_accumulator.get(category_lower, 0) + 1
        
        print(f"  🏷️  Final categories for {brand_name}: {list(brand_categories.keys())}")
        
        # Store brand-category relationships
        if brand_categories:
            brand_category_relationships[brand_id] = brand_categories
    
    # Create categories.json with IDs
    categories_list = sorted(category_accumulator.items(), key=lambda x: x[1], reverse=True)
    categories_json = [
        {"id": i+1, "name": name, "total_mentions": count}
        for i, (name, count) in enumerate(categories_list)
    ]
    
    # Create category name to ID mapping
    category_name_to_id = {cat['name']: cat['id'] for cat in categories_json}
    
    # Create brand_category_mentions.json
    brand_category_mentions = []
    for brand_id, categories in brand_category_relationships.items():
        for category_name, mentions in categories.items():
            if category_name in category_name_to_id:
                brand_category_mentions.append({
                    "brand_id": brand_id,
                    "category_id": category_name_to_id[category_name],
                    "mentions": mentions
                })
    
    # Save categories.json
    categories_file = 'output/categories.json'
    print(f"\n💾 Saving categories to {categories_file}")
    with open(categories_file, 'w', encoding='utf-8') as f:
        json.dump(categories_json, f, indent=2, ensure_ascii=False)
    
    # Save brand_category_mentions.json
    brand_categories_file = 'output/brand_category_mentions.json'
    print(f"💾 Saving brand-category relationships to {brand_categories_file}")
    with open(brand_categories_file, 'w', encoding='utf-8') as f:
        json.dump(brand_category_mentions, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Phase 4 complete!")
    print(f"📁 Found {len(categories_json)} unique categories")
    print(f"📁 Generated {len(brand_category_mentions)} brand-category relationships")
    print(f"📁 Files saved: {categories_file}, {brand_categories_file}")

if __name__ == "__main__":
    main()