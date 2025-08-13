#!/usr/bin/env python3

import os
import json
from typing import Dict, List, Any
import utils


def consolidate_manual_duplicates(brands_data: List[Dict]) -> List[Dict]:
    """Consolidate brands with duplicate IDs by selecting highest mention name and summing totals"""
    
    # Sort by ID first, then by total_mentions descending within each ID
    brands_data.sort(key=lambda x: (x['id'], -x['total_mentions']))
    
    seen_ids = {}
    consolidated = []
    
    for brand in brands_data:
        brand_id = brand['id']
        
        if brand_id not in seen_ids:
            # First occurrence - use this name (highest mentions), start with its mentions
            seen_ids[brand_id] = len(consolidated)  # track index
            consolidated.append({
                'id': brand_id,
                'name': brand['name'], 
                'total_mentions': brand['total_mentions']
            })
            print(f"📦 ID {brand_id}: Using name '{brand['name']}' ({brand['total_mentions']} mentions)")
        else:
            # Add mentions to existing brand
            idx = seen_ids[brand_id]
            consolidated[idx]['total_mentions'] += brand['total_mentions']
            print(f"📦 ID {brand_id}: Added {brand['total_mentions']} mentions from '{brand['name']}' (total now {consolidated[idx]['total_mentions']})")
    
    # Sort final result by name (ascending) for verification
    consolidated.sort(key=lambda x: x['name'].lower())
    
    return consolidated


def main():
    utils.print_phase_header(4, "Brand Deduplication with Manual ID Consolidation")
    
    # Get search parameters from environment
    search_term = os.environ.get('SEARCH_TERM', 'python')
    subreddit_name = os.environ['SUBREDDIT_NAME']
    
    # Get search-specific directory
    output_dir = utils.get_search_output_dir(search_term, subreddit_name)
    
    # Ensure output directory exists
    utils.ensure_output_directory()
    
    # Load Phase 3 raw brands data from search-specific directory
    brands_file = os.path.join(output_dir, 'raw_brands.json')
    if not os.path.exists(brands_file):
        print(f"❌ Raw brands file not found: {brands_file}")
        print("Please run Phase 3 first to generate raw_brands.json")
        return
    
    print(f"📖 Loading brands from {brands_file}")
    with open(brands_file, 'r', encoding='utf-8') as f:
        original_brands_data = json.load(f)
    
    print(f"Found {len(original_brands_data)} brands to analyze for manual ID consolidation")
    
    # Step 1: Consolidate brands with duplicate IDs
    print("\n📦 Consolidating brands with duplicate IDs...")
    consolidated_brands = consolidate_manual_duplicates(original_brands_data)
    
    # Save deduplicated brands to file
    dedup_file = os.path.join(output_dir, 'dedup_brands.json')
    utils.save_json_file(consolidated_brands, dedup_file, "deduplicated brands", compact_array=True)
    
    # Print completion stats
    utils.print_phase_complete(4, {
        "Original brands": len(original_brands_data),
        "Deduplicated brands": len(consolidated_brands),
        "Output file": dedup_file
    })

if __name__ == "__main__":
    main()