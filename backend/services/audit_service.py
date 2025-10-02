"""
Audit Trail Service for AYUSH Terminology Bridge
Compliant with India's 2016 EHR Standards (ISO 22600)
"""

import sqlite3
from datetime import datetime
import json
import hashlib
from typing import Dict, List, Optional
import uuid

class AuditService:
    def __init__(self, db_path: str = 'data/audit_logs.db'):
        """Initialize audit database"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create audit tables if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                user_id TEXT,
                user_role TEXT,
                action_type TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                endpoint TEXT,
                method TEXT,
                ip_address TEXT,
                user_agent TEXT,
                request_body TEXT,
                response_status INTEGER,
                response_time_ms FLOAT,
                consent_status TEXT,
                abha_id TEXT,
                error_message TEXT,
                metadata TEXT,
                checksum TEXT NOT NULL
            )
        ''')
        
        # Search history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id TEXT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                user_id TEXT,
                search_query TEXT NOT NULL,
                results_count INTEGER,
                top_result_code TEXT,
                session_id TEXT
            )
        ''')
        
        # Translation history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translation_history (
                id TEXT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                user_id TEXT,
                namaste_code TEXT NOT NULL,
                icd11_tm2_code TEXT,
                icd11_bio_code TEXT,
                confidence_tm2 FLOAT,
                confidence_bio FLOAT,
                mapping_method TEXT,
                accepted BOOLEAN
            )
        ''')
        
        # Analytics aggregation table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_summary (
                date DATE PRIMARY KEY,
                total_searches INTEGER DEFAULT 0,
                total_translations INTEGER DEFAULT 0,
                total_fhir_resources INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0,
                avg_response_time_ms FLOAT,
                top_searched_terms TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Audit database initialized")
    
    def _generate_checksum(self, data: Dict) -> str:
        """Generate SHA-256 checksum for audit integrity"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def log_api_call(self, 
                     action_type: str,
                     user_id: Optional[str] = None,
                     user_role: Optional[str] = None,
                     endpoint: str = None,
                     method: str = None,
                     ip_address: str = None,
                     user_agent: str = None,
                     request_body: Dict = None,
                     response_status: int = None,
                     response_time_ms: float = None,
                     resource_type: str = None,
                     resource_id: str = None,
                     consent_status: str = "granted",
                     abha_id: str = None,
                     error_message: str = None,
                     metadata: Dict = None) -> str:
        """
        Log API call with full audit trail
        
        Args:
            action_type: Type of action (SEARCH, TRANSLATE, CREATE_FHIR, etc.)
            user_id: Authenticated user ID
            user_role: User role (doctor, admin, etc.)
            endpoint: API endpoint called
            method: HTTP method (GET, POST, etc.)
            ip_address: Client IP
            user_agent: Browser/client info
            request_body: Request payload
            response_status: HTTP status code
            response_time_ms: Response time in milliseconds
            resource_type: FHIR resource type if applicable
            resource_id: Resource ID if applicable
            consent_status: Patient consent status
            abha_id: ABHA ID if applicable
            error_message: Error details if any
            metadata: Additional metadata
        
        Returns:
            audit_id: Unique audit log ID
        """
        audit_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Prepare audit data
        audit_data = {
            'id': audit_id,
            'timestamp': timestamp.isoformat(),
            'user_id': user_id,
            'action_type': action_type,
            'endpoint': endpoint,
            'method': method,
            'response_status': response_status
        }
        
        checksum = self._generate_checksum(audit_data)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_logs (
                id, timestamp, user_id, user_role, action_type,
                resource_type, resource_id, endpoint, method,
                ip_address, user_agent, request_body, response_status,
                response_time_ms, consent_status, abha_id,
                error_message, metadata, checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            audit_id, timestamp, user_id, user_role, action_type,
            resource_type, resource_id, endpoint, method,
            ip_address, user_agent, 
            json.dumps(request_body) if request_body else None,
            response_status, response_time_ms, consent_status, abha_id,
            error_message,
            json.dumps(metadata) if metadata else None,
            checksum
        ))
        
        conn.commit()
        conn.close()
        
        return audit_id
    
    def log_search(self, user_id: str, query: str, results_count: int, 
                   top_result: str = None, session_id: str = None) -> str:
        """Log search activity"""
        search_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO search_history (
                id, timestamp, user_id, search_query, 
                results_count, top_result_code, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (search_id, timestamp, user_id, query, results_count, 
              top_result, session_id))
        
        conn.commit()
        conn.close()
        
        return search_id
    
    def log_translation(self, user_id: str, namaste_code: str,
                       icd11_tm2: str = None, icd11_bio: str = None,
                       confidence_tm2: float = None, confidence_bio: float = None,
                       mapping_method: str = "hybrid", accepted: bool = True) -> str:
        """Log code translation activity"""
        trans_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO translation_history (
                id, timestamp, user_id, namaste_code,
                icd11_tm2_code, icd11_bio_code,
                confidence_tm2, confidence_bio,
                mapping_method, accepted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trans_id, timestamp, user_id, namaste_code,
              icd11_tm2, icd11_bio, confidence_tm2, confidence_bio,
              mapping_method, accepted))
        
        conn.commit()
        conn.close()
        
        return trans_id
    
    def get_audit_logs(self, 
                      user_id: Optional[str] = None,
                      action_type: Optional[str] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      limit: int = 100) -> List[Dict]:
        """Retrieve audit logs with filters"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            log = dict(row)
            # Parse JSON fields
            if log['request_body']:
                log['request_body'] = json.loads(log['request_body'])
            if log['metadata']:
                log['metadata'] = json.loads(log['metadata'])
            logs.append(log)
        
        conn.close()
        return logs
    
    def get_search_history(self, user_id: Optional[str] = None, 
                          limit: int = 50) -> List[Dict]:
        """Get search history"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT * FROM search_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM search_history 
                ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_translation_history(self, user_id: Optional[str] = None,
                               limit: int = 50) -> List[Dict]:
        """Get translation history"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT * FROM translation_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM translation_history 
                ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_analytics_summary(self, start_date: datetime = None,
                             end_date: datetime = None) -> Dict:
        """Get analytics summary for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total searches
        cursor.execute('SELECT COUNT(*) FROM search_history')
        total_searches = cursor.fetchone()[0]
        
        # Total translations
        cursor.execute('SELECT COUNT(*) FROM translation_history')
        total_translations = cursor.fetchone()[0]
        
        # Total API calls
        cursor.execute('SELECT COUNT(*) FROM audit_logs')
        total_api_calls = cursor.fetchone()[0]
        
        # Unique users
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM audit_logs WHERE user_id IS NOT NULL')
        unique_users = cursor.fetchone()[0]
        
        # Average response time
        cursor.execute('SELECT AVG(response_time_ms) FROM audit_logs WHERE response_time_ms IS NOT NULL')
        avg_response_time = cursor.fetchone()[0] or 0
        
        # Top searched terms
        cursor.execute('''
            SELECT search_query, COUNT(*) as count 
            FROM search_history 
            GROUP BY search_query 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        top_searches = [{'query': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Most translated codes
        cursor.execute('''
            SELECT namaste_code, COUNT(*) as count 
            FROM translation_history 
            GROUP BY namaste_code 
            ORDER BY count DESC 
            LIMIT 10
        ''')
        top_translations = [{'code': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Success rate
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 END) * 100.0 / COUNT(*) 
            FROM audit_logs 
            WHERE response_status IS NOT NULL
        ''')
        success_rate = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_searches': total_searches,
            'total_translations': total_translations,
            'total_api_calls': total_api_calls,
            'unique_users': unique_users,
            'avg_response_time_ms': round(avg_response_time, 2),
            'success_rate': round(success_rate, 2),
            'top_searches': top_searches,
            'top_translations': top_translations
        }
    
    def verify_audit_integrity(self, audit_id: str) -> bool:
        """Verify audit log hasn't been tampered with"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM audit_logs WHERE id = ?', (audit_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False
        
        log = dict(row)
        stored_checksum = log.pop('checksum')
        
        # Recreate checksum from core data
        core_data = {
            'id': log['id'],
            'timestamp': log['timestamp'],
            'user_id': log['user_id'],
            'action_type': log['action_type'],
            'endpoint': log['endpoint'],
            'method': log['method'],
            'response_status': log['response_status']
        }
        
        computed_checksum = self._generate_checksum(core_data)
        
        return computed_checksum == stored_checksum


# Example usage
if __name__ == "__main__":
    audit = AuditService()
    
    # Log a search
    audit.log_search(
        user_id="DR001",
        query="diabetes",
        results_count=5,
        top_result="NAM0004"
    )
    
    # Log a translation
    audit.log_translation(
        user_id="DR001",
        namaste_code="NAM0004",
        icd11_tm2="TM2.7",
        icd11_bio="5A00",
        confidence_tm2=0.96,
        confidence_bio=0.92,
        mapping_method="hybrid"
    )
    
    # Get analytics
    summary = audit.get_analytics_summary()
    print(json.dumps(summary, indent=2))