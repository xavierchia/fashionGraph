#!/usr/bin/env python3

import os
import json
import anthropic
from typing import Dict, List, Any

def test_claude_connection(context: str = "general") -> bool:
    """Test basic Claude API connection with context-specific message"""
    try:
        client = anthropic.Anthropic(api_key=os.environ.get('CLAUDE_API_KEY'))
        
        context_messages = {
            "general": "Hello! Can you help me with data analysis? Just respond with 'Yes, I can help!'",
            "brands": "Hello! Can you help me analyze fashion brands? Just respond with 'Yes, I can help!'", 
            "deduplication": "Hello! Can you help me deduplicate brand data? Just respond with 'Yes, I can help!'",
            "categories": "Hello! Can you help me analyze category data? Just respond with 'Yes, I can help!'"
        }
        
        message = context_messages.get(context, context_messages["general"])
        
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=100,
            messages=[{
                "role": "user", 
                "content": message
            }]
        )
        
        print("✅ Claude API connection successful!")
        print(f"Response: {response.content[0].text}")
        return True
        
    except Exception as e:
        print(f"❌ Claude API connection failed: {e}")
        return False

def get_claude_client() -> anthropic.Anthropic:
    """Get configured Claude client"""
    return anthropic.Anthropic(api_key=os.environ.get('CLAUDE_API_KEY'))

def normalize_brand_name(name: str) -> str:
    """Remove punctuation, spaces, convert to lowercase for brand matching"""
    return ''.join(c.lower() for c in name if c.isalnum())

def ensure_output_directory():
    """Ensure output directory exists"""
    os.makedirs('output', exist_ok=True)

def get_search_folder_name(search_term: str, subreddit_name: str) -> str:
    """Generate folder name from search term and subreddit"""
    safe_search = ''.join(c.lower() for c in search_term if c.isalnum())
    safe_subreddit = ''.join(c.lower() for c in subreddit_name if c.isalnum())
    return f"{safe_search}-{safe_subreddit}"

def get_search_output_dir(search_term: str, subreddit_name: str) -> str:
    """Get the output directory path for a specific search"""
    folder_name = get_search_folder_name(search_term, subreddit_name)
    return f"output/{folder_name}"

def ensure_search_output_directory(search_term: str, subreddit_name: str) -> str:
    """Ensure search-specific output directory exists and return path"""
    output_dir = get_search_output_dir(search_term, subreddit_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def load_json_file(file_path: str, description: str = "file") -> Dict[str, Any]:
    """Load and parse JSON file with error handling"""
    if not os.path.exists(file_path):
        print(f"❌ {description.title()} not found: {file_path}")
        return None
    
    try:
        print(f"📖 Loading {description} from {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data) if isinstance(data, list) else 'data'} from {description}")
        return data
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing {description}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading {description}: {e}")
        return None

def save_json_file(data: Any, file_path: str, description: str = "file", indent: int = 2, compact_array: bool = True):
    """Save data to JSON file with error handling"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            if compact_array and isinstance(data, list):
                # Custom formatting: each array item on its own line
                f.write('[\n')
                for i, item in enumerate(data):
                    if i > 0:
                        f.write(',\n')
                    f.write('  ' + json.dumps(item, ensure_ascii=False))
                f.write('\n]')
            else:
                json.dump(data, f, indent=indent, ensure_ascii=False)
        print(f"✅ Saved {description} to {file_path}")
    except Exception as e:
        print(f"❌ Error saving {description}: {e}")

def validate_required_files(required_files: List[str]) -> bool:
    """Check if all required files exist"""
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    return True

def print_phase_header(phase_number: int, phase_name: str):
    """Print consistent phase header"""
    print(f"🚀 Starting Phase {phase_number}: {phase_name}")

def print_phase_complete(phase_number: int, stats: Dict[str, Any] = None):
    """Print consistent phase completion message with stats"""
    print(f"\n🎉 Phase {phase_number} complete!")
    if stats:
        for key, value in stats.items():
            print(f"📁 {key}: {value}")