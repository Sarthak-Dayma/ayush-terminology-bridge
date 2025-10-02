"""
Modular route definitions for AYUSH Terminology Bridge API
Separates concerns: auth, terminology, FHIR, analytics, audit
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import time

# Import services (will be injected)
from services.csv_parser import NAMASTEParser
from services.icd11_client import ICD11Client
from services.mapping_engine import MappingEngine
from services.fhir_generator import FHIRGenerator
from services.ml_matcher import SemanticMatcher
from services.audit_service import AuditService
from services.abha_auth import ABHAAuthService, AuthMiddleware

# ============= REQUEST/RESPONSE MODELS =============

class LoginRequest(BaseModel):
    user_id: str = Field(..., example="DR001")
    password: str = Field(..., example="demo_password")

class SearchRequest(BaseModel):
    query: str = Field(..., example="diabetes")
    limit: Optional[int] = Field(10, ge=1, le=50)
    use_ml: Optional[bool] = Field(True, description="Use ML semantic matching")

class TranslateRequest(BaseModel):
    namaste_code: str = Field(..., example="NAM0004")
    use_ml: Optional[bool] = Field(True, description="Use ML hybrid matching")

class ConditionRequest(BaseModel):
    namaste_code: str = Field(..., example="NAM0004")
    icd_codes: List[str] = Field(..., example=["TM2.7", "5A00"])
    patient_id: str = Field(..., example="PATIENT-001")
    abha_id: Optional[str] = Field(None, example="12-3456-7890-1234")

class ConceptMapRequest(BaseModel):
    source_code: str = Field(..., example="NAM0004")
    target_codes: List[str] = Field(..., example=["TM2.7", "5A00"])

class BatchTranslateRequest(BaseModel):
    namaste_codes: List[str] = Field(..., example=["NAM0001", "NAM0004", "NAM0010"])
    use_ml: Optional[bool] = Field(True)

# ============= DEPENDENCY INJECTION =============

class ServiceContainer:
    """Container for all services - injected at app startup"""
    def __init__(
        self,
        namaste_parser: NAMASTEParser,
        icd_client: ICD11Client,
        mapping_engine: MappingEngine,
        fhir_gen: FHIRGenerator,
        ml_matcher: SemanticMatcher,
        audit_service: AuditService,
        auth_service: ABHAAuthService,
        auth_middleware: AuthMiddleware
    ):
        self.namaste_parser = namaste_parser
        self.icd_client = icd_client
        self.mapping_engine = mapping_engine
        self.fhir_gen = fhir_gen
        self.ml_matcher = ml_matcher
        self.audit_service = audit_service
        self.auth_service = auth_service
        self.auth_middleware = auth_middleware

# Global service container (initialized in main.py)
services: Optional[ServiceContainer] = None

def get_services() -> ServiceContainer:
    """Dependency to get service container"""
    if services is None:
        raise RuntimeError("Services not initialized")
    return services

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency to extract and verify user from token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    svc = get_services()
    user = svc.auth_middleware.authenticate_request(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

# ============= AUTHENTICATION ROUTES =============

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@auth_router.post("/login")
async def login(request: LoginRequest, svc: ServiceContainer = Depends(get_services)):
    """
    Login with ABHA credentials (mock implementation)
    Returns JWT token for subsequent API calls
    """
    result = svc.auth_service.generate_mock_abha_token(request.user_id, request.password)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    session_id = svc.auth_service.create_session(request.user_id)
    result['session_id'] = session_id
    
    svc.audit_service.log_api_call(
        action_type="LOGIN",
        user_id=request.user_id,
        endpoint="/api/auth/login",
        method="POST",
        response_status=200,
        metadata={'session_id': session_id}
    )
    
    return result

@auth_router.get("/userinfo")
async def get_userinfo(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@auth_router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Logout and invalidate session"""
    svc.audit_service.log_api_call(
        action_type="LOGOUT",
        user_id=current_user['user_id'],
        endpoint="/api/auth/logout",
        method="POST",
        response_status=200
    )
    
    return {"message": "Logged out successfully"}

@auth_router.post("/refresh")
async def refresh_token(
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Refresh JWT token"""
    new_token = svc.auth_service.generate_mock_abha_token(
        current_user['user_id'],
        "refresh"  # Mock password for refresh
    )
    
    return new_token

# ============= TERMINOLOGY ROUTES =============

terminology_router = APIRouter(prefix="/api/terminology", tags=["Terminology"])

@terminology_router.get("/search")
async def search_namaste(
    q: str,
    limit: int = 10,
    use_ml: bool = False,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """
    Search NAMASTE codes with optional ML semantic matching
    Requires authentication
    """
    start_time = time.time()
    
    # Basic fuzzy search
    results = svc.namaste_parser.search_codes(q, limit)
    
    # Enhanced ML semantic search if requested
    if use_ml and results:
        enhanced_results = []
        for result in results:
            semantic_score = svc.ml_matcher.compute_similarity(q, result['display'])
            result['semantic_score'] = semantic_score
            result['combined_score'] = (result['match_score'] + semantic_score) / 2
            enhanced_results.append(result)
        
        enhanced_results.sort(key=lambda x: x['combined_score'], reverse=True)
        results = enhanced_results
    
    # Log search
    top_result = results[0]['code'] if results else None
    svc.audit_service.log_search(
        user_id=current_user['user_id'],
        query=q,
        results_count=len(results),
        top_result=top_result
    )
    
    response_time = (time.time() - start_time) * 1000
    
    return {
        "query": q,
        "results": results,
        "count": len(results),
        "ml_enabled": use_ml,
        "response_time_ms": round(response_time, 2)
    }

@terminology_router.post("/translate")
async def translate_code(
    request: TranslateRequest,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """
    Translate NAMASTE code to ICD-11 (TM2 + Biomedicine)
    Uses hybrid fuzzy + ML semantic matching
    """
    start_time = time.time()
    
    # Get basic mapping
    mapping = svc.mapping_engine.translate_namaste_to_icd(request.namaste_code)
    
    if 'error' in mapping:
        raise HTTPException(status_code=404, detail=mapping['error'])
    
    # Enhance with ML if requested
    if request.use_ml:
        namaste_data = mapping['namaste']
        
        # Get ICD candidates for re-ranking
        tm2_matches = mapping.get('icd11_tm2_matches', [])
        bio_matches = mapping.get('icd11_biomedicine_matches', [])
        
        # Re-rank using ML semantic similarity
        for match in tm2_matches:
            match['ml_score'] = svc.ml_matcher.compute_similarity(
                namaste_data['display'],
                match['title']
            )
        
        for match in bio_matches:
            match['ml_score'] = svc.ml_matcher.compute_similarity(
                namaste_data['display'],
                match['title']
            )
        
        # Sort by ML score
        tm2_matches.sort(key=lambda x: x.get('ml_score', 0), reverse=True)
        bio_matches.sort(key=lambda x: x.get('ml_score', 0), reverse=True)
        
        mapping['ml_enhanced'] = True
    
    # Log translation
    svc.audit_service.log_translation(
        user_id=current_user['user_id'],
        source_code=request.namaste_code,
        target_system='ICD-11',
        target_codes=[m['code'] for m in mapping.get('icd11_tm2_matches', [])[:3]],
        confidence_score=mapping.get('confidence', 0)
    )
    
    response_time = (time.time() - start_time) * 1000
    mapping['response_time_ms'] = round(response_time, 2)
    
    return mapping

@terminology_router.post("/translate/batch")
async def batch_translate(
    request: BatchTranslateRequest,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Batch translate multiple NAMASTE codes"""
    results = []
    
    for code in request.namaste_codes:
        try:
            mapping = svc.mapping_engine.translate_namaste_to_icd(code)
            
            if request.use_ml and 'error' not in mapping:
                # ML enhancement
                namaste_data = mapping['namaste']
                tm2_matches = mapping.get('icd11_tm2_matches', [])
                
                for match in tm2_matches:
                    match['ml_score'] = svc.ml_matcher.compute_similarity(
                        namaste_data['display'],
                        match['title']
                    )
                tm2_matches.sort(key=lambda x: x.get('ml_score', 0), reverse=True)
            
            results.append({
                "namaste_code": code,
                "success": True,
                "mapping": mapping
            })
        except Exception as e:
            results.append({
                "namaste_code": code,
                "success": False,
                "error": str(e)
            })
    
    return {
        "total": len(request.namaste_codes),
        "successful": len([r for r in results if r['success']]),
        "results": results
    }

@terminology_router.get("/namaste/{code}")
async def get_namaste_code(
    code: str,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Get detailed information about a NAMASTE code"""
    code_data = svc.namaste_parser.get_code_by_id(code)
    
    if not code_data:
        raise HTTPException(status_code=404, detail=f"NAMASTE code {code} not found")
    
    return {
        "code": code,
        "details": code_data,
        "system": "http://namaste.ayush.gov.in",
        "version": "1.0"
    }

@terminology_router.get("/icd11/{code}")
async def get_icd11_entity(
    code: str,
    linearization: str = "mms",
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """
    Get ICD-11 entity details
    Supports both TM2 and MMS linearizations
    """
    try:
        entity = svc.icd_client.get_entity(code, linearization)
        
        if not entity:
            raise HTTPException(status_code=404, detail=f"ICD-11 code {code} not found")
        
        return {
            "code": code,
            "linearization": linearization,
            "entity": entity,
            "system": f"http://id.who.int/icd/release/11/{linearization}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============= FHIR ROUTES =============

fhir_router = APIRouter(prefix="/api/fhir", tags=["FHIR"])

@fhir_router.post("/Condition")
async def create_condition_resource(
    request: ConditionRequest,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Create FHIR R4 Condition resource with dual coding"""
    # Validate NAMASTE code
    namaste_data = svc.namaste_parser.get_code_by_id(request.namaste_code)
    if not namaste_data:
        raise HTTPException(status_code=404, detail=f"NAMASTE code {request.namaste_code} not found")
    
    # Create FHIR Condition
    condition = svc.fhir_gen.create_condition(
        namaste_code=request.namaste_code,
        namaste_display=namaste_data['display'],
        icd_codes=request.icd_codes,
        patient_id=request.patient_id,
        abha_id=request.abha_id
    )
    
    # Log FHIR resource creation
    svc.audit_service.log_fhir_resource(
        user_id=current_user['user_id'],
        resource_type='Condition',
        resource_id=condition['id'],
        patient_id=request.patient_id,
        codes=[request.namaste_code] + request.icd_codes
    )
    
    return condition

@fhir_router.post("/ConceptMap")
async def create_concept_map(
    request: ConceptMapRequest,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Create FHIR R4 ConceptMap resource"""
    # Validate source code
    namaste_data = svc.namaste_parser.get_code_by_id(request.source_code)
    if not namaste_data:
        raise HTTPException(status_code=404, detail=f"NAMASTE code {request.source_code} not found")
    
    # Create ConceptMap
    concept_map = svc.fhir_gen.create_concept_map(
        source_code=request.source_code,
        source_display=namaste_data['display'],
        target_codes=request.target_codes
    )
    
    svc.audit_service.log_fhir_resource(
        user_id=current_user['user_id'],
        resource_type='ConceptMap',
        resource_id=concept_map['id'],
        codes=[request.source_code] + request.target_codes
    )
    
    return concept_map

@fhir_router.get("/ValueSet")
async def get_value_set(
    system: str = "namaste",
    filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Get FHIR ValueSet for NAMASTE codes"""
    if system.lower() == "namaste":
        codes = svc.namaste_parser.codes
        if filter:
            codes = [c for c in codes if filter.lower() in c['display'].lower()]
        
        value_set = svc.fhir_gen.create_value_set(
            codes=codes[:50],
            system_name="NAMASTE"
        )
    else:
        raise HTTPException(status_code=400, detail="Only NAMASTE ValueSet supported currently")
    
    return value_set

# ============= AUDIT ROUTES =============

audit_router = APIRouter(prefix="/api/audit", tags=["Audit"])

@audit_router.get("/recent")
async def get_recent_audit_logs(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Get recent audit logs (admin only)"""
    if current_user.get('role') not in ['admin', 'auditor']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    logs = svc.audit_service.get_recent_logs(limit)
    return {
        "logs": logs,
        "count": len(logs)
    }

@audit_router.get("/user/{user_id}")
async def get_user_activity(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Get activity logs for specific user"""
    # Users can only view their own logs unless admin
    if current_user['user_id'] != user_id and current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    logs = svc.audit_service.get_user_activity(user_id)
    stats = svc.audit_service.get_user_statistics(user_id)
    
    return {
        "user_id": user_id,
        "logs": logs,
        "statistics": stats
    }

@audit_router.get("/export")
async def export_audit_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Export audit logs (admin only)"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    logs = svc.audit_service.export_logs(start_date, end_date)
    return {
        "logs": logs,
        "count": len(logs),
        "format": "json"
    }

# ============= ANALYTICS ROUTES =============

analytics_router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@analytics_router.get("/popular-searches")
async def get_popular_searches(
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Get most popular search queries"""
    if current_user.get('role') not in ['admin', 'researcher']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    popular = svc.audit_service.get_popular_searches(limit)
    return {
        "popular_searches": popular,
        "count": len(popular)
    }

@analytics_router.get("/translation-stats")
async def get_translation_statistics(
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Get translation usage statistics"""
    if current_user.get('role') not in ['admin', 'researcher']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    stats = svc.audit_service.get_translation_statistics()
    return stats

@analytics_router.get("/dashboard-stats")
async def get_dashboard_statistics(
    current_user: dict = Depends(get_current_user),
    svc: ServiceContainer = Depends(get_services)
):
    """Get comprehensive dashboard statistics"""
    if current_user.get('role') not in ['admin', 'researcher']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return {
        "total_searches": svc.audit_service.get_total_searches(),
        "total_translations": svc.audit_service.get_total_translations(),
        "total_users": svc.audit_service.get_total_users(),
        "popular_codes": svc.audit_service.get_popular_codes(10),
        "recent_activity": svc.audit_service.get_recent_logs(20),
        "translation_stats": svc.audit_service.get_translation_statistics()
    }