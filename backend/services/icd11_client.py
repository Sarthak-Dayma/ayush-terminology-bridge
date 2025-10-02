import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict

class ICD11Client:
    def __init__(self, credentials_path: str):
        with open(credentials_path, 'r') as f:
            self.config = json.load(f)
        
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self) -> str:
        """Get OAuth2 access token"""
        if self.access_token and self.token_expiry > datetime.now():
            return self.access_token
        
        # Request new token
        payload = {
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret'],
            'scope': 'icdapi_access',
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(
            self.config['token_endpoint'],
            data=payload,
            verify=True,
            timeout=60  # ADD THIS LINE: Timeout in seconds
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            # Token expires in ~3600 seconds
            self.token_expiry = datetime.now() + timedelta(seconds=3500)
            return self.access_token
        else:
            raise Exception(f"Failed to get token: {response.text}")
    
    def search_icd11(self, query: str, use_flexisearch: bool = True) -> List[Dict]:
        """Search ICD-11 codes using API"""
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Accept-Language': 'en',
            'API-Version': 'v2'
        }
        
        # Use flexisearch for better matching
        search_type = 'flexisearch' if use_flexisearch else 'search'
        url = f"{self.config['api_base_url']}/mms/{search_type}"
        
        params = {
            'q': query,
            'useFlexisearch': use_flexisearch,
            'flatResults': True
        }
        
        response = requests.get(url, headers=headers, 
            params=params,
            timeout=15  # ADD THIS LINE: Timeout in seconds
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('destinationEntities', [])
        else:
            return []
    
    def get_entity_details(self, entity_uri: str) -> Dict:
        """Get detailed information about an ICD-11 entity"""
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Accept-Language': 'en',
            'API-Version': 'v2'
        }
        
        response = requests.get(entity_uri, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
