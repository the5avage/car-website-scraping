import yaml
import re
import os
from transformers import BertTokenizer
from typing import Dict, Any, Tuple

def load_vehicle_data(file_path: str) -> Dict[str, Any]:
    """Load and parse the vehicle YAML data"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        data = yaml.unsafe_load(content)
        vehicle_data = dict(data.items()) if hasattr(data, 'items') else data
    except yaml.YAMLError as e:
        print(f"Error with unsafe_load: {e}")
        # Fallback approach
        cleaned_content = re.sub(r'!!python/object/apply:collections\.defaultdict\s*', '', content)
        cleaned_content = re.sub(r'args:\s*- !!python/name:builtins\.dict\s*\'\'?\s*', '', cleaned_content)
        data = yaml.safe_load(cleaned_content)
        vehicle_data = data['dictitems'] if 'dictitems' in data else data
    
    return vehicle_data

def extract_non_details_text(vehicle_data: Dict[str, Any]) -> str:
    """Extract details_list and information_dict text (parts that won't be cut)"""
    text_parts = []
    
    if 'details_list' in vehicle_data:
        text_parts.extend(vehicle_data['details_list'])
    
    if 'information_dict' in vehicle_data:
        for key, value in vehicle_data['information_dict'].items():
            text_parts.append(f"{key}: {value}")
    
    return ' '.join(text_parts)

def get_total_token_count(vehicle_data: Dict[str, Any], tokenizer: BertTokenizer) -> int:
    """Get total token count for a vehicle listing"""
    text_parts = []
    
    if 'details_text' in vehicle_data:
        text_parts.append(vehicle_data['details_text'])
    
    if 'details_list' in vehicle_data:
        text_parts.extend(vehicle_data['details_list'])
    
    if 'information_dict' in vehicle_data:
        for key, value in vehicle_data['information_dict'].items():
            text_parts.append(f"{key}: {value}")
    
    full_text = ' '.join(text_parts)
    return len(tokenizer.encode(full_text, add_special_tokens=False))

def truncate_by_sentences(details_text: str, fixed_text: str, token_limit: int, tokenizer: BertTokenizer) -> str:
    """Truncate details_text by complete sentences"""
    if not details_text:
        return details_text
    
    # Find sentence separators (. and ;)
    sentence_pattern = r'[.;]'
    sentences = re.split(sentence_pattern, details_text)
    
    # If no sentence separators found, return original text for word-based truncation
    if len(sentences) <= 1:
        return details_text
    
    # Rebuild sentences with their separators
    separators = re.findall(sentence_pattern, details_text)
    reconstructed_sentences = []
    
    for i, sentence in enumerate(sentences[:-1]):  # Exclude last empty part after final separator
        if i < len(separators):
            reconstructed_sentences.append(sentence + separators[i])
    
    # Add last sentence if it exists and doesn't end with separator
    if sentences[-1].strip():
        reconstructed_sentences.append(sentences[-1])
    
    # Find the longest valid truncation
    truncated_details = ""
    for i, sentence in enumerate(reconstructed_sentences):
        candidate_details = truncated_details + sentence
        candidate_full_text = ' '.join([candidate_details, fixed_text]).strip()
        
        if len(tokenizer.encode(candidate_full_text, add_special_tokens=False)) <= token_limit:
            truncated_details = candidate_details
        else:
            break
    
    return truncated_details.strip()

def truncate_by_words(details_text: str, fixed_text: str, token_limit: int, tokenizer: BertTokenizer) -> str:
    """Truncate details_text by 10-word chunks"""
    if not details_text:
        return details_text
    
    words = details_text.split()
    truncated_details = ""
    
    # Try chunks of 10 words
    for i in range(0, len(words), 10):
        candidate_words = words[:i + 10]
        candidate_details = ' '.join(candidate_words)
        candidate_full_text = ' '.join([candidate_details, fixed_text]).strip()
        
        if len(tokenizer.encode(candidate_full_text, add_special_tokens=False)) <= token_limit:
            truncated_details = candidate_details
        else:
            break
    
    # If no 10-word chunk fits, try word by word
    if not truncated_details:
        for i in range(1, len(words)):
            candidate_details = ' '.join(words[:i])
            candidate_full_text = ' '.join([candidate_details, fixed_text]).strip()
            
            if len(tokenizer.encode(candidate_full_text, add_special_tokens=False)) <= token_limit:
                truncated_details = candidate_details
            else:
                break
    
    return truncated_details

def truncate_vehicle_text(vehicle_data: Dict[str, Any], token_limit: int, tokenizer: BertTokenizer) -> Tuple[Dict[str, Any], bool]:
    """Truncate vehicle text to stay within token limit"""
    # Check if truncation is needed
    current_tokens = get_total_token_count(vehicle_data, tokenizer)
    
    if current_tokens <= token_limit:
        return vehicle_data, False
    
    # Get the fixed parts (details_list and information_dict)
    fixed_text = extract_non_details_text(vehicle_data)
    
    # Check if fixed parts already exceed limit
    fixed_tokens = len(tokenizer.encode(fixed_text, add_special_tokens=False))
    if fixed_tokens > token_limit:
        print(f"Warning: Fixed text already exceeds limit ({fixed_tokens} > {token_limit})")
        return vehicle_data, False
    
    # Get details_text
    details_text = vehicle_data.get('details_text', '')
    
    # Try sentence-based truncation first
    truncated_details = truncate_by_sentences(details_text, fixed_text, token_limit, tokenizer)
    
    # If sentence-based truncation didn't work well, try word-based
    if not truncated_details or truncated_details == details_text:
        truncated_details = truncate_by_words(details_text, fixed_text, token_limit, tokenizer)
    
    # Update vehicle data
    updated_vehicle_data = vehicle_data.copy()
    updated_vehicle_data['details_text'] = truncated_details
    
    return updated_vehicle_data, True

def process_vehicle_data(input_file: str, output_file: str, token_limit: int = 400):
    """Process all vehicle data and truncate where necessary"""
    # Initialize tokenizer
    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    
    # Load data
    print(f"Loading vehicle data from {input_file}...")
    vehicle_data = load_vehicle_data(input_file)
    print(f"Loaded {len(vehicle_data)} vehicle listings")
    
    # Process each vehicle
    truncated_count = 0
    processed_data = {}
    
    for url, data in vehicle_data.items():
        processed_vehicle, was_truncated = truncate_vehicle_text(data, token_limit, tokenizer)
        processed_data[url] = processed_vehicle
        
        if was_truncated:
            truncated_count += 1
            original_tokens = get_total_token_count(data, tokenizer)
            new_tokens = get_total_token_count(processed_vehicle, tokenizer)
            print(f"Truncated: {url}")
            print(f"  Tokens: {original_tokens} -> {new_tokens}")
    
    # Save processed data
    print(f"\nSaving processed data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(processed_data, f, default_flow_style=False, allow_unicode=True)
    
    # Summary
    print(f"\nProcessing complete:")
    print(f"Total vehicles: {len(vehicle_data)}")
    print(f"Truncated: {truncated_count}")
    print(f"Percentage truncated: {truncated_count/len(vehicle_data)*100:.1f}%")
    
    # Verify results
    print("\nVerifying results...")
    over_limit_count = 0
    for url, data in processed_data.items():
        tokens = get_total_token_count(data, tokenizer)
        if tokens > token_limit:
            over_limit_count += 1
            print(f"Still over limit: {url} ({tokens} tokens)")
    
    print(f"Vehicles still over limit: {over_limit_count}")

def main():
    """Main function"""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))

    input_file = os.path.join(base_dir, "translated_vehicles_data.yaml")
    output_file = os.path.join(base_dir, "truncated_vehicles_data.yaml")
    token_limit = 400  # Set your desired token limit here
    
    process_vehicle_data(input_file, output_file, token_limit)

if __name__ == "__main__":
    main() 
