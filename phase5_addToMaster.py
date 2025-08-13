#!/usr/bin/env python3

import os
import json
from typing import Dict, List, Any
import utils


def load_master_brands() -> List[Dict]:
    """Load existing master brands file or create empty list"""
    master_file = 'output/master_brands.json'
    
    if os.path.exists(master_file):
        print(f"📖 Loading existing master brands from {master_file}")
        with open(master_file, 'r', encoding='utf-8') as f:
            master_brands = json.load(f)
        print(f"Found {len(master_brands)} existing master brands")
        return master_brands
    else:
        print("📝 No existing master brands file found, starting fresh")
        return []


def load_master_brandtobrand() -> List[Dict]:
    """Load existing master brand-to-brand file or create empty list"""
    brandtobrand_file = 'output/master_brandtobrand.json'
    
    if os.path.exists(brandtobrand_file):
        print(f"📖 Loading existing brand-to-brand relationships from {brandtobrand_file}")
        with open(brandtobrand_file, 'r', encoding='utf-8') as f:
            brandtobrand_data = json.load(f)
        print(f"Found {len(brandtobrand_data)} existing brand relationships")
        return brandtobrand_data
    else:
        print("📝 No existing brand-to-brand file found, starting fresh")
        return []


def update_brand_to_brand_relationships(dedup_brands: List[Dict], master_brands: List[Dict], search_id: int, brandtobrand_data: List[Dict]) -> tuple:
    """Update brand-to-brand relationships using search_id as brand_id_1"""
    
    # Create lookup dict for master brands by name (case-insensitive) to get IDs
    name_to_id = {}
    for brand in master_brands:
        name_to_id[brand['name'].lower()] = brand['id']
    
    # Create lookup dict for existing brand-to-brand relationships
    relationship_lookup = {}
    for rel in brandtobrand_data:
        key = (rel['brand_id_1'], rel['brand_id_2'])
        relationship_lookup[key] = rel
    
    relationships_added = 0
    relationships_updated = 0
    
    for dedup_brand in dedup_brands:
        brand_name = dedup_brand['name']
        brand_name_lower = brand_name.lower()
        mentions = dedup_brand['total_mentions']
        
        # Find the master brand ID for this dedup brand
        if brand_name_lower in name_to_id:
            brand_id_2 = name_to_id[brand_name_lower]
            
            # Skip if it's the same as search_id (no self-relationships)
            if brand_id_2 == search_id:
                continue
                
            # Create relationship key (ensure smaller ID comes first for consistency)
            if search_id < brand_id_2:
                rel_key = (search_id, brand_id_2)
            else:
                rel_key = (brand_id_2, search_id)
            
            if rel_key in relationship_lookup:
                # Update existing relationship
                old_mentions = relationship_lookup[rel_key]['total_mentions']
                relationship_lookup[rel_key]['total_mentions'] += mentions
                relationships_updated += 1
                print(f"📈 Updated relationship {rel_key}: {old_mentions} -> {relationship_lookup[rel_key]['total_mentions']} mentions")
            else:
                # Add new relationship
                new_relationship = {
                    'brand_id_1': rel_key[0],
                    'brand_id_2': rel_key[1], 
                    'total_mentions': mentions
                }
                brandtobrand_data.append(new_relationship)
                relationship_lookup[rel_key] = new_relationship
                relationships_added += 1
                print(f"✨ Added new relationship ({rel_key[0]}, {rel_key[1]}) with {mentions} mentions")
    
    # Sort relationships by brand_id_1, then brand_id_2 for consistency
    brandtobrand_data.sort(key=lambda x: (x['brand_id_1'], x['brand_id_2']))
    
    return brandtobrand_data, relationships_added, relationships_updated


def merge_brands_to_master(dedup_brands: List[Dict], master_brands: List[Dict]) -> List[Dict]:
    """Merge deduplicated brands into master brands list"""
    
    # Create lookup dict for master brands by name (case-insensitive)
    master_lookup = {}
    for i, brand in enumerate(master_brands):
        master_lookup[brand['name'].lower()] = i
    
    # Get next available ID
    max_id = max([brand['id'] for brand in master_brands], default=0)
    next_id = max_id + 1
    
    brands_added = 0
    brands_updated = 0
    
    for dedup_brand in dedup_brands:
        brand_name = dedup_brand['name']
        brand_name_lower = brand_name.lower()
        mentions = dedup_brand['total_mentions']
        
        if brand_name_lower in master_lookup:
            # Update existing brand
            idx = master_lookup[brand_name_lower]
            old_mentions = master_brands[idx]['total_mentions']
            master_brands[idx]['total_mentions'] += mentions
            brands_updated += 1
            print(f"📈 Updated '{brand_name}': {old_mentions} -> {master_brands[idx]['total_mentions']} mentions")
        else:
            # Add new brand
            new_brand = {
                'id': next_id,
                'name': brand_name,
                'total_mentions': mentions
            }
            master_brands.append(new_brand)
            master_lookup[brand_name_lower] = len(master_brands) - 1
            next_id += 1
            brands_added += 1
            print(f"✨ Added new brand '{brand_name}' with {mentions} mentions")
    
    # Sort by name for consistency
    master_brands.sort(key=lambda x: x['name'].lower())
    
    return master_brands, brands_added, brands_updated


def main():
    utils.print_phase_header(5, "Add Deduplicated Brands to Master and Update Brand Relationships")
    
    # Get search parameters from environment
    search_term = os.environ.get('SEARCH_TERM', 'python')
    subreddit_name = os.environ['SUBREDDIT_NAME']
    search_id = int(os.environ.get('SEARCH_ID', '1'))
    
    print(f"🔍 Using SEARCH_ID: {search_id} for brand relationships")
    
    # Get search-specific directory
    output_dir = utils.get_search_output_dir(search_term, subreddit_name)
    
    # Ensure main output directory exists
    utils.ensure_output_directory()
    
    # Load deduplicated brands from search-specific directory
    dedup_file = os.path.join(output_dir, 'dedup_brands.json')
    if not os.path.exists(dedup_file):
        print(f"❌ Deduplicated brands file not found: {dedup_file}")
        print("Please run Phase 4 first to generate dedup_brands.json")
        return
    
    print(f"📖 Loading deduplicated brands from {dedup_file}")
    with open(dedup_file, 'r', encoding='utf-8') as f:
        dedup_brands = json.load(f)
    
    print(f"Found {len(dedup_brands)} deduplicated brands to process")
    
    # Load existing master brands
    master_brands = load_master_brands()
    
    # Merge brands
    print("\n🔄 Merging brands into master list...")
    updated_master, brands_added, brands_updated = merge_brands_to_master(dedup_brands, master_brands)
    
    # Save updated master brands
    master_file = 'output/master_brands.json'
    utils.save_json_file(updated_master, master_file, "master brands")
    
    # Load and update brand-to-brand relationships
    brandtobrand_data = load_master_brandtobrand()
    
    print("\n🔗 Updating brand-to-brand relationships...")
    updated_brandtobrand, relationships_added, relationships_updated = update_brand_to_brand_relationships(
        dedup_brands, updated_master, search_id, brandtobrand_data
    )
    
    # Save updated brand-to-brand relationships
    brandtobrand_file = 'output/master_brandtobrand.json'
    utils.save_json_file(updated_brandtobrand, brandtobrand_file, "brand-to-brand relationships")
    
    # Print completion stats
    utils.print_phase_complete(5, {
        "Total master brands": len(updated_master),
        "Brands added": brands_added,
        "Brands updated": brands_updated,
        "Total brand relationships": len(updated_brandtobrand),
        "Relationships added": relationships_added,
        "Relationships updated": relationships_updated,
        "Master brands file": master_file,
        "Brand relationships file": brandtobrand_file
    })


if __name__ == "__main__":
    main()