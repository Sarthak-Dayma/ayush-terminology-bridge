import csv
import json
from typing import List, Dict

class NAMASTEParser:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.codes = []
    
    def load_csv(self) -> List[Dict]:
        """Load and parse NAMASTE CSV file"""
        with open(self.csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Parse synonyms (pipe-separated)
                synonyms = row['Synonyms'].split('|') if row['Synonyms'] else []
                
                code_entry = {
                    'code': row['Code'].strip(),
                    'display': row['Disease_Name'].strip(),
                    'system': row['System'].strip(),
                    'category': row['Category'].strip(),
                    'synonyms': [s.strip() for s in synonyms],
                    'description': row['Description'].strip(),
                    'sanskrit': row['Sanskrit_Term'].strip()
                }
                self.codes.append(code_entry)
        
        return self.codes
    
    def search_codes(self, query: str, limit: int = 10) -> List[Dict]:
        """Fuzzy search in NAMASTE codes"""
        from difflib import SequenceMatcher
        
        results = []
        query_lower = query.lower()
        
        for code in self.codes:
            # Search in display name
            score1 = SequenceMatcher(None, query_lower, code['display'].lower()).ratio()
            
            # Search in synonyms
            score2 = max([SequenceMatcher(None, query_lower, syn.lower()).ratio() 
                         for syn in code['synonyms']] + [0])
            
            # Search in Sanskrit term
            score3 = SequenceMatcher(None, query_lower, code['sanskrit'].lower()).ratio()
            
            max_score = max(score1, score2, score3)
            
            if max_score > 0.3:  # Threshold
                results.append({
                    **code,
                    'match_score': round(max_score, 3)
                })
        
        # Sort by score and limit
        results.sort(key=lambda x: x['match_score'], reverse=True)
        return results[:limit]
    
    def get_code_by_id(self, code_id: str) -> Dict:
        """Get specific code by ID"""
        for code in self.codes:
            if code['code'] == code_id:
                return code
        return None