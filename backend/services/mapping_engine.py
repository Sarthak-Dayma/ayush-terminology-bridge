import json
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

class MappingEngine:
    def __init__(self, mappings_path: str, icd_client, namaste_parser):
        with open(mappings_path, 'r') as f:
            # CHANGED: Safely load mappings to prevent crash if 'mappings' key is missing
            loaded_json = json.load(f)
            self.predefined_mappings = loaded_json.get('mappings', [])
        
        self.icd_client = icd_client
        self.namaste_parser = namaste_parser
    
    def get_predefined_mapping(self, namaste_code: str) -> Dict:
        """Check if pre-mapped exists"""
        for mapping in self.predefined_mappings:
            if mapping.get('namaste_code') == namaste_code:
                return mapping
        return None
    
    def fuzzy_match_to_icd(self, namaste_term: str) -> List[Dict]:
        """Use fuzzy matching to find ICD-11 codes"""
        # Search ICD-11 API
        icd_results = self.icd_client.search_icd11(namaste_term)
        
        matches = []
        for result in icd_results[:5]:  # Top 5
            # Calculate similarity score
            title = result.get('title', {}).get('@value', '')
            score = SequenceMatcher(None, namaste_term.lower(), title.lower()).ratio()
            
            matches.append({
                'code': result.get('theCode', 'N/A'),
                'display': title,
                'uri': result.get('@id', ''),
                'confidence': round(score, 3),
                'match_type': 'fuzzy'
            })
        
        return matches
    
    def translate_namaste_to_icd(self, namaste_code: str) -> Dict:
        """Main translation function"""
        # Get NAMASTE code details
        namaste_data = self.namaste_parser.get_code_by_id(namaste_code)
        if not namaste_data:
            return {'error': 'NAMASTE code not found'}
        
        # Check predefined mapping first
        predefined = self.get_predefined_mapping(namaste_code)
        if predefined:
            return {
                'namaste': namaste_data,
                # CHANGED: Use .get() to safely access keys, returning [] if a key is missing
                'icd11_tm2': predefined.get('icd11_tm2', []),
                'icd11_biomedicine': predefined.get('icd11_biomedicine', []),
                'mapping_source': 'predefined'
            }
        
        # Otherwise, use fuzzy matching
        display_name = namaste_data['display']
        icd_matches = self.fuzzy_match_to_icd(display_name)
        
        # Separate TM2 and biomedicine
        tm2_matches = [m for m in icd_matches if m.get('code') and 'TM2' in m['code']]
        bio_matches = [m for m in icd_matches if m.get('code') and 'TM2' not in m['code']]
        
        return {
            'namaste': namaste_data,
            'icd11_tm2_matches': tm2_matches[:3],
            'icd11_biomedicine_matches': bio_matches[:3],
            'mapping_source': 'algorithmic'
        }