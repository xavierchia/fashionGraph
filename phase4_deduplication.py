#!/usr/bin/env python3

import os
import json
import anthropic
from typing import Dict, List, Any, Tuple
import shutil
import utils


def backup_original_data():
    """Create backups of original data files before modification"""
    backup_dir = 'output/backup_before_dedup'
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'output/brands.json',
        'output/brand_brand_mentions.json'
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"📁 Backed up {file_path} to {backup_path}")

def deduplicate_brands_with_claude(brands_data: List[Dict], client: anthropic.Anthropic) -> Dict[str, Any]:
    """Send brand list to Claude for deduplication analysis"""
    
    # Create brand list for Claude to analyze
    brand_names = [brand['name'] for brand in brands_data]
    brand_list_text = "\n".join([f"{i+1}. {name}" for i, name in enumerate(brand_names)])
    
    prompt = f"""
I have a list of {len(brand_names)} brand names extracted from fashion discussions. Many are duplicates or variations of the same brand. Please identify duplicates and group them together.

Brand List:
{brand_list_text}

Please identify which brands are duplicates/variations and group them. Consider:
- Punctuation differences: "Naked and Famous" vs "Naked & Famous"
- Plural forms: "Iron Heart" vs "Iron Hearts" 
- Abbreviations: "Levi's Vintage Clothing" vs "LVC"
- Capitalization: "Studio d'Artisan" vs "Studio D'Artisan"
- Common misspellings or variations
- Store vs brand names that refer to same entity

IMPORTANT: Respond with ONLY valid JSON, no explanatory text. Use this exact format:
{{
  "brand_groups": [
    {{
      "canonical_name": "Iron Heart",
      "group_members": ["Iron Heart", "Iron Hearts"],
      "original_ids": [7, 53]
    }},
    {{
      "canonical_name": "Naked & Famous", 
      "group_members": ["Naked and Famous", "Naked & Famous"],
      "original_ids": [12, 30]
    }}
  ]
}}

Only include groups that have 2+ members. Single brands don't need to be listed.
"""
    
    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_response = response.content[0].text
        print(f"🤖 Claude deduplication analysis complete")
        
        # Parse response
        dedup_analysis = json.loads(raw_response)
        return dedup_analysis
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error in deduplication: {e}")
        print(f"Raw response was: {raw_response}")
        return {"brand_groups": []}
    except Exception as e:
        print(f"❌ Error in Claude deduplication: {e}")
        return {"brand_groups": []}

def consolidate_brands(brands_data: List[Dict], dedup_analysis: Dict) -> Tuple[List[Dict], Dict]:
    """Consolidate duplicate brands based on Claude's analysis"""
    
    # Create mapping from original brand name to its data
    original_brands = {brand['name']: brand for brand in brands_data}
    
    # Track which brands are part of groups
    grouped_brand_names = set()
    
    # Start with empty consolidated list
    consolidated_brands = []
    brand_id_mapping = {}  # old_id -> new_id
    next_id = 1
    
    # Process groups first
    for group in dedup_analysis.get('brand_groups', []):
        canonical_name = group['canonical_name']
        group_members = group['group_members']
        
        # Calculate total mentions for this group
        total_mentions = 0
        old_ids = []
        
        for member_name in group_members:
            if member_name in original_brands:
                brand_data = original_brands[member_name]
                total_mentions += brand_data['total_mentions']
                old_ids.append(brand_data['id'])
                grouped_brand_names.add(member_name)
        
        # Create consolidated brand entry
        consolidated_brand = {
            "id": next_id,
            "name": canonical_name,
            "total_mentions": total_mentions
        }
        consolidated_brands.append(consolidated_brand)
        
        # Map all old IDs to this new ID
        for old_id in old_ids:
            brand_id_mapping[old_id] = next_id
            
        print(f"📦 Consolidated group: {canonical_name} (IDs {old_ids} -> {next_id}, {total_mentions} mentions)")
        next_id += 1
    
    # Add remaining brands that weren't grouped
    for brand in brands_data:
        if brand['name'] not in grouped_brand_names:
            consolidated_brand = {
                "id": next_id,
                "name": brand['name'],
                "total_mentions": brand['total_mentions']
            }
            consolidated_brands.append(consolidated_brand)
            brand_id_mapping[brand['id']] = next_id
            next_id += 1
    
    # Sort by mentions (descending)
    consolidated_brands.sort(key=lambda x: x['total_mentions'], reverse=True)
    
    return consolidated_brands, brand_id_mapping

def create_brand_aliases(brands_data: List[Dict], dedup_analysis: Dict, brand_id_mapping: Dict) -> List[Dict]:
    """Create brand aliases lookup table"""
    
    aliases = []
    seen_aliases = set()  # Track normalized aliases to avoid duplicates
    
    # Create mapping from original brand data
    original_brands = {brand['name']: brand for brand in brands_data}
    
    # Add aliases from consolidated groups
    for group in dedup_analysis.get('brand_groups', []):
        canonical_name = group['canonical_name']
        group_members = group['group_members']
        
        # Find the new ID for this group
        new_id = None
        for member_name in group_members:
            if member_name in original_brands:
                old_id = original_brands[member_name]['id']
                new_id = brand_id_mapping.get(old_id)
                break
        
        if new_id:
            # Add each group member as an alias, but avoid duplicates
            for member_name in group_members:
                # Normalize for search
                normalized_alias = member_name.lower().strip()
                alias_key = f"{normalized_alias}_{new_id}"  # Include brand_id in key to allow same alias for different brands
                
                if alias_key not in seen_aliases:
                    seen_aliases.add(alias_key)
                    aliases.append({
                        "alias": normalized_alias,
                        "brand_id": new_id,
                        "is_canonical": member_name == canonical_name
                    })
    
    # Add single brands (not part of groups) as their own aliases
    grouped_brand_names = set()
    for group in dedup_analysis.get('brand_groups', []):
        grouped_brand_names.update(group['group_members'])
    
    for brand in brands_data:
        if brand['name'] not in grouped_brand_names:
            new_id = brand_id_mapping.get(brand['id'])
            if new_id:
                normalized_alias = brand['name'].lower().strip()
                alias_key = f"{normalized_alias}_{new_id}"
                
                if alias_key not in seen_aliases:
                    seen_aliases.add(alias_key)
                    aliases.append({
                        "alias": normalized_alias,
                        "brand_id": new_id,
                        "is_canonical": True
                    })
    
    return aliases

def create_brand_relationships(consolidated_brands: List[Dict]) -> List[Dict]:
    """Create brand_brand_mentions.json using search term and consolidated brands"""
    
    # Get search term from environment (the brand_a)
    search_term = os.environ.get('SEARCH_TERM', 'levis').lower()
    
    # Find search term brand ID using normalized matching
    search_brand_id = None
    normalized_search = utils.normalize_brand_name(search_term)
    
    for brand in consolidated_brands:
        normalized_brand = utils.normalize_brand_name(brand['name'])
        if normalized_search == normalized_brand:
            search_brand_id = brand['id']
            break
    
    # Create brand_brand_mentions.json (search_term -> other_brands)
    brand_relationships = []
    if search_brand_id:
        for brand in consolidated_brands:
            if brand['id'] != search_brand_id:  # Don't include self-reference
                brand_relationships.append({
                    "brand_a_id": search_brand_id,
                    "brand_b_id": brand['id'], 
                    "mentions": brand['total_mentions']
                })
    else:
        print(f"⚠️  Search term '{search_term}' not found in consolidated brands")
    
    return brand_relationships

def main():
    utils.print_phase_header(4, "Brand Deduplication with Claude")
    
    # Ensure output directory exists
    utils.ensure_output_directory()
    
    # Test Claude connection first
    if not utils.test_claude_connection("deduplication"):
        return
    
    # Load Phase 3 brands data
    brands_file = 'output/brands.json'
    if not os.path.exists(brands_file):
        print(f"❌ Brands file not found: {brands_file}")
        print("Please run Phase 3 first to generate brands.json")
        return
    
    print(f"📖 Loading brands from {brands_file}")
    with open(brands_file, 'r', encoding='utf-8') as f:
        original_brands_data = json.load(f)
    
    print(f"Found {len(original_brands_data)} brands to analyze for deduplication")
    
    # Backup original data
    print("💾 Creating backup of original data...")
    backup_original_data()
    
    # Initialize Claude client
    client = utils.get_claude_client()
    
    # Step 1: Send brand list to Claude for deduplication analysis
    print("\n🔍 Analyzing brands for duplicates with Claude...")
    dedup_analysis = deduplicate_brands_with_claude(original_brands_data, client)
    
    groups_found = len(dedup_analysis.get('brand_groups', []))
    print(f"✅ Found {groups_found} brand groups with duplicates")
    
    if groups_found == 0:
        print("ℹ️  No duplicates found. Brands are already clean!")
        return
    
    # Step 2: Consolidate duplicate brands
    print("\n📦 Consolidating duplicate brands...")
    consolidated_brands, brand_id_mapping = consolidate_brands(original_brands_data, dedup_analysis)
    
    print(f"✅ Consolidated {len(original_brands_data)} brands into {len(consolidated_brands)} unique brands")
    
    # Step 3: Create brand aliases lookup table
    print("\n🏷️  Creating brand aliases lookup table...")
    brand_aliases = create_brand_aliases(original_brands_data, dedup_analysis, brand_id_mapping)
    
    print(f"✅ Created {len(brand_aliases)} searchable aliases")
    
    # Step 4: Create brand relationships with consolidated IDs
    print("\n🔗 Creating brand relationships with consolidated IDs...")
    brand_relationships = create_brand_relationships(consolidated_brands)
    
    print(f"✅ Created {len(brand_relationships)} brand relationships")
    
    # Step 5: Save all updated files
    print("\n💾 Saving consolidated data...")
    
    # Save consolidated brands.json
    brands_output = 'output/brands.json'
    with open(brands_output, 'w', encoding='utf-8') as f:
        json.dump(consolidated_brands, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved consolidated brands to {brands_output}")
    
    # Save brand aliases
    aliases_output = 'output/brand_aliases.json'
    with open(aliases_output, 'w', encoding='utf-8') as f:
        json.dump(brand_aliases, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved brand aliases to {aliases_output}")
    
    # Save brand relationships
    relationships_output = 'output/brand_brand_mentions.json'
    utils.save_json_file(brand_relationships, relationships_output, "brand relationships")
    
    # Phase completion summary
    stats = {
        "Brands consolidated": f"{len(original_brands_data)} → {len(consolidated_brands)}",
        "Duplicates removed": len(original_brands_data) - len(consolidated_brands),
        "Aliases created": len(brand_aliases),
        "Brand relationships": len(brand_relationships),
        "Files saved": f"{brands_output}, {aliases_output}, {relationships_output}"
    }
    utils.print_phase_complete(4, stats)

if __name__ == "__main__":
    main()