from datetime import datetime
import uuid
from typing import List, Dict

class FHIRGenerator:
    def __init__(self):
        self.base_url = "http://terminology.ayush.gov.in"
    
    def generate_codesystem(self, namaste_codes: List[Dict]) -> Dict:
        """Generate FHIR CodeSystem for NAMASTE"""
        concepts = []
        for code in namaste_codes:
            # Use .get() for safer access
            concept = {
                'code': code.get('code'),
                'display': code.get('display'),
                'definition': code.get('description'),
                'designation': [
                    {
                        'language': 'sa',
                        'value': code.get('sanskrit')
                    }
                ],
                'property': [
                    {'code': 'system', 'valueString': code.get('system')},
                    {'code': 'category', 'valueString': code.get('category')}
                ]
            }
            concepts.append(concept)
        
        codesystem = {
            'resourceType': 'CodeSystem',
            'id': 'namaste-ayush-codes',
            'url': f'{self.base_url}/CodeSystem/namaste',
            'version': '1.0.0',
            'name': 'NAMASTE_AYUSH_Codes',
            'title': 'National AYUSH Morbidity and Standardized Terminologies',
            'status': 'active',
            'date': datetime.now().isoformat(),
            'publisher': 'Ministry of AYUSH, Government of India',
            'description': 'Standardized terminology codes for AYUSH systems',
            'content': 'complete',
            'count': len(concepts),
            'concept': concepts
        }
        
        return codesystem
    
    def generate_conceptmap(self, mappings: List[Dict]) -> Dict:
        """Generate FHIR ConceptMap for NAMASTE ↔ ICD-11"""
        elements = []
        
        for mapping in mappings:
            targets = []
            
            # Add TM2 mapping
            tm2_map = mapping.get('icd11_tm2')
            if tm2_map: # Check if the key exists and is not empty/null
                targets.append({
                    'code': tm2_map.get('code'),
                    'display': tm2_map.get('display'),
                    'equivalence': 'equivalent',
                    'comment': f"Confidence: {tm2_map.get('confidence')}"
                })
            
            # Add biomedicine mapping
            biomed_map = mapping.get('icd11_biomedicine')
            if biomed_map:
                targets.append({
                    'code': biomed_map.get('code'),
                    'display': biomed_map.get('display'),
                    'equivalence': 'relatedto',
                    'comment': f"Confidence: {biomed_map.get('confidence')}"
                })
            
            elements.append({
                'code': mapping.get('namaste_code'),
                'display': mapping.get('namaste_term'), # Use .get() for safety
                'target': targets
            })
        
        conceptmap = {
            'resourceType': 'ConceptMap',
            'id': 'namaste-icd11-map',
            'url': f'{self.base_url}/ConceptMap/namaste-icd11',
            'version': '1.0.0',
            'name': 'NAMASTE_ICD11_Mapping',
            'title': 'NAMASTE to ICD-11 Concept Mapping',
            'status': 'active',
            'date': datetime.now().isoformat(),
            'publisher': 'Ministry of AYUSH',
            'sourceUri': f'{self.base_url}/CodeSystem/namaste',
            'targetUri': 'http://id.who.int/icd/release/11/2024-01',
            'group': [{
                'source': f'{self.base_url}/CodeSystem/namaste',
                'target': 'http://id.who.int/icd/release/11/2024-01',
                'element': elements
            }]
        }
        
        return conceptmap
    
    # CHANGED: The entire function signature and body was corrected to match your API usage
    def create_condition(self, namaste_code: str, namaste_display: str, icd_codes: List[str], patient_id: str, abha_id: str = None) -> Dict:
        """Generate FHIR Condition resource (ProblemList entry)"""
        condition_id = str(uuid.uuid4())
        
        # Start with the NAMASTE code
        coding = [
            {
                'system': f'{self.base_url}/CodeSystem/namaste',
                'code': namaste_code,
                'display': namaste_display
            }
        ]
        
        # Add ICD-11 codes (which are strings from the request)
        for icd_code_str in icd_codes:
            coding.append({
                'system': 'http://id.who.int/icd/release/11/mms', # Default to mms
                'code': icd_code_str
            })
        
        condition = {
            'resourceType': 'Condition',
            'id': condition_id,
            'clinicalStatus': {
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/condition-clinical',
                    'code': 'active'
                }]
            },
            'verificationStatus': {
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/condition-ver-status',
                    'code': 'confirmed'
                }]
            },
            'category': [{
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/condition-category',
                    'code': 'problem-list-item',
                    'display': 'Problem List Item'
                }]
            }],
            'code': {
                'coding': coding,
                'text': namaste_display
            },
            'subject': {
                'reference': f'Patient/{patient_id}'
            },
            'recordedDate': datetime.now().isoformat()
        }
        
        return condition