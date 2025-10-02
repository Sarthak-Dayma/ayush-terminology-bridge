import json
from typing import List, Dict, Tuple
from difflib import SequenceMatcher

class MappingEngine:
    def __init__(self, mappings_path: str, icd_client, namaste_parser):
        with open(mappings_path, 'r') as f:
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
    
    def translate_namaste_to_icd(self, namaste_code: str) -> Dict:
        """
        Main translation function.
        CHANGED: This function now ONLY uses the predefined mappings from concept_mappings.json.
        The fuzzy matching and external API calls have been removed as requested.
        """
        # Get NAMASTE code details
        namaste_data = self.namaste_parser.get_code_by_id(namaste_code)
        if not namaste_data:
            return {'error': 'NAMASTE code not found'} 
        
        # Check predefined mapping
        predefined = self.get_predefined_mapping(namaste_code)
        
        if predefined:
            # FIXED: Correctly reads 'icd11_mms' from your JSON file.
            # The frontend expects 'icd11_biomedicine_matches', so we rename the key here for consistency.
            tm2_matches = predefined.get('icd11_tm2', [])
            biomedicine_matches = predefined.get('icd11_mms', [])

            # To maintain compatibility with the frontend, let's rename the keys in the final output.
            # We also need to add 'title' to match what the old API call provided.
            for match in tm2_matches:
                match['title'] = match.get('display')
            for match in biomedicine_matches:
                match['title'] = match.get('display')

            return {
                'namaste': namaste_data,
                'icd11_tm2_matches': tm2_matches,
                'icd11_biomedicine_matches': biomedicine_matches,
                'mapping_source': 'predefined'
            }
        else:
            # CHANGED: If no predefined mapping is found, return a clear message.
            return {
                'namaste': namaste_data,
                'icd11_tm2_matches': [],
                'icd11_biomedicine_matches': [],
                'mapping_source': 'predefined',
                'message': 'No predefined mapping found for this code.'
            }