"""
Complete AYUSH Terminology Bridge API
With ABHA Auth, Audit Trail, ML Matching, Real ICD-11 Integration
CORS FIXED VERSION
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import time

from typing import List, Dict

from services.csv_parser import NAMASTEParser
from services.icd11_client import ICD11Client
from services.mapping_engine import MappingEngine
from services.fhir_generator import FHIRGenerator
from services.ml_matcher import SemanticMatcher
from services.audit_service import AuditService
from services.abha_auth import ABHAAuthService, AuthMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="AYUSH Terminology Bridge API",
    description="FHIR-compliant API for NAMASTE-ICD11 mapping with ABHA authentication",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ============= CORS FIX - CRITICAL =============
# This fixes the "blocked by CORS policy" error
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "null",  # For file:// protocol during development
        "*"  # Allow all origins in development (remove in production!)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # Important: expose response headers to frontend
)

# Initialize services
print("🔄 Initializing services...")
namaste_parser = NAMASTEParser('data/namaste_sample.csv')
namaste_parser.load_csv()
print(f"✅ Loaded {len(namaste_parser.codes)} NAMASTE codes")

icd_client = ICD11Client('config/icd11_credentials.json')
print("✅ ICD-11 client initialized")

mapping_engine = MappingEngine('data/concept_mappings.json', icd_client, namaste_parser)
print("✅ Mapping engine ready")

fhir_gen = FHIRGenerator()
print("✅ FHIR generator ready")

ml_matcher = SemanticMatcher()
print("✅ ML matcher initialized")

audit_service = AuditService()
print("✅ Audit service ready")

auth_service = ABHAAuthService()
auth_middleware = AuthMiddleware(auth_service)
print("✅ ABHA authentication ready")

# Request/Response Models
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

class FHIRBundleRequest(BaseModel):
    resource_type: Literal["Bundle"] = "Bundle"
    entries: List[Dict]

# Dependency for authentication
async def get_current_user(request: Request, authorization: Optional[str] = Header(None)):
    """Dependency to extract and verify user from token"""
    # Allow OPTIONS requests to pass without authentication for CORS preflight
    if request.method == "OPTIONS":
        return None

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    user = auth_middleware.authenticate_request(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user

# Middleware for request timing and audit
@app.middleware("http")
async def audit_middleware_func(request: Request, call_next):
    start_time = time.time()
    
    # Extract user info if available
    auth_header = request.headers.get('authorization')
    user_id = None
    user_role = None
    
    if auth_header:
        user = auth_middleware.authenticate_request(auth_header)
        if user:
            user_id = user.get('user_id')
            user_role = user.get('role')
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    response_time = (time.time() - start_time) * 1000
    
    # Log to audit trail (skip health checks and OPTIONS)
    if not request.url.path.endswith('/health') and request.method != 'OPTIONS':
        audit_service.log_api_call(
            action_type=f"{request.method}_{request.url.path}",
            user_id=user_id,
            user_role=user_role,
            endpoint=str(request.url.path),
            method=request.method,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get('user-agent'),
            response_status=response.status_code,
            response_time_ms=response_time
        )
    
    # Add custom headers
    response.headers["X-Response-Time"] = f"{response_time:.2f}ms"
    response.headers["X-API-Version"] = "2.0.0"
    
    return response

# ============= AUTHENTICATION ENDPOINTS =============

@app.post("/api/auth/login", tags=["Authentication"])
async def login(request: LoginRequest):
    """
    Login with ABHA credentials (mock implementation)
    Returns JWT token for subsequent API calls
    """
    result = auth_service.generate_mock_abha_token(request.user_id, request.password)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    session_id = auth_service.create_session(request.user_id)
    result['session_id'] = session_id
    """
    audit_service.log_api_call(
        action_type="LOGIN",
        user_id=request.user_id,
        endpoint="/api/auth/login",
        method="POST",
        response_status=200,
        metadata={'session_id': session_id}
    )
    """
    
    return result

@app.get("/api/auth/userinfo", tags=["Authentication"])
async def get_userinfo(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@app.post("/api/auth/logout", tags=["Authentication"])
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout and invalidate session"""
    audit_service.log_api_call(
        action_type="LOGOUT",
        user_id=current_user['user_id'],
        endpoint="/api/auth/logout",
        method="POST",
        response_status=200
    )
    
    return {"message": "Logged out successfully"}

# ============= TERMINOLOGY ENDPOINTS =============

@app.get("/", tags=["General"])
def root():
    """API root endpoint"""
    return {
        "message": "AYUSH Terminology Bridge API v2.0",
        "features": [
            "NAMASTE Code Management",
            "ICD-11 Integration (TM2 + Biomedicine)",
            "ML-based Semantic Matching",
            "FHIR R4 Compliance",
            "ABHA OAuth2 Authentication",
            "Complete Audit Trail"
        ],
        "documentation": "/api/docs"
    }

@app.get("/api/terminology/search", tags=["Terminology"])
async def search_namaste(
    q: str,
    limit: int = 10,
    use_ml: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Search NAMASTE codes with optional ML semantic matching
    Requires authentication
    """
    start_time = time.time()
    
    # Basic fuzzy search
    results = namaste_parser.search_codes(q, limit)
    
    # Enhanced ML semantic search if requested
    if use_ml and results:
        # Use ML matcher to re-rank results
        enhanced_results = []
        for result in results:
            semantic_score = ml_matcher.compute_similarity(q, result['display'])
            result['semantic_score'] = semantic_score
            result['combined_score'] = (result['match_score'] + semantic_score) / 2
            enhanced_results.append(result)
        
        enhanced_results.sort(key=lambda x: x['combined_score'], reverse=True)
        results = enhanced_results
    
    # Log search
    top_result = results[0]['code'] if results else None
    audit_service.log_search(
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

@app.post("/api/terminology/translate", tags=["Terminology"])
async def translate_code(
    request: TranslateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Translate NAMASTE code to ICD-11 (TM2 + Biomedicine)
    Uses hybrid fuzzy + ML semantic matching
    """
    start_time = time.time()
    
    # Get basic mapping
    mapping = mapping_engine.translate_namaste_to_icd(request.namaste_code)
    
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
            match['ml_score'] = ml_matcher.compute_similarity(
                namaste_data['display'],
                match['title']
            )
        
        for match in bio_matches:
            match['ml_score'] = ml_matcher.compute_similarity(
                namaste_data['display'],
                match['title']
            )
        
        # Sort by ML score
        tm2_matches.sort(key=lambda x: x.get('ml_score', 0), reverse=True)
        bio_matches.sort(key=lambda x: x.get('ml_score', 0), reverse=True)
        
        mapping['ml_enhanced'] = True

        mapping['icd11_tm2_matches'] = tm2_matches
        mapping['icd11_biomedicine_matches'] = bio_matches

        tm2_matches = mapping.get('icd11_tm2_matches', [])
        bio_matches = mapping.get('icd11_biomedicine_matches', [])

# Get the top match for each category to log, if they exist
        top_tm2_match = tm2_matches[0] if tm2_matches else {}
        top_bio_match = bio_matches[0] if bio_matches else {}

    audit_service.log_translation(
        user_id=current_user['user_id'],
        namaste_code=request.namaste_code,
        icd11_tm2=top_tm2_match.get('code'),
        icd11_bio=top_bio_match.get('code'),
        confidence_tm2=top_tm2_match.get('ml_score') or top_tm2_match.get('confidence'),
        confidence_bio=top_bio_match.get('ml_score') or top_bio_match.get('confidence'),
        mapping_method='ml_enhanced' if request.use_ml else 'algorithmic'
    )
    
    # Log translation
    
    response_time = (time.time() - start_time) * 1000
    mapping['response_time_ms'] = round(response_time, 2)
    
    return mapping

@app.get("/api/terminology/namaste/{code}", tags=["Terminology"])
async def get_namaste_code(
    code: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed information about a NAMASTE code"""
    code_data = namaste_parser.get_code_by_id(code)
    
    if not code_data:
        raise HTTPException(status_code=404, detail=f"NAMASTE code {code} not found")
    
    return {
        "code": code,
        "details": code_data,
        "system": "http://namaste.ayush.gov.in",
        "version": "1.0"
    }

@app.get("/api/terminology/icd11/{code}", tags=["Terminology"])
async def get_icd11_entity(
    code: str,
    linearization: str = "mms",
    current_user: dict = Depends(get_current_user)
):
    """
    Get ICD-11 entity details
    Supports both TM2 (Traditional Medicine 2) and MMS (Biomedicine) linearizations
    """
    try:
        entity = icd_client.get_entity(code, linearization)
        
        if not entity:
            raise HTTPException(status_code=404, detail=f"ICD-11 code {code} not found")
        
        return {
            "code": code,
            "linearization": linearization,
            "entity": entity,
            "system": "http://id.who.int/icd/release/11/mms" if linearization == "mms" else "http://id.who.int/icd/release/11/tm2"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============= FHIR ENDPOINTS =============

@app.post("/api/fhir/Condition", tags=["FHIR"])
async def create_condition_resource(
    request: ConditionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create FHIR R4 Condition resource with dual coding
    Links NAMASTE code with ICD-11 codes (TM2 + Biomedicine)
    """
    # Validate NAMASTE code
    namaste_data = namaste_parser.get_code_by_id(request.namaste_code)
    if not namaste_data:
        raise HTTPException(status_code=404, detail=f"NAMASTE code {request.namaste_code} not found")
    
    # Create FHIR Condition
    condition = fhir_gen.create_condition(
        namaste_code=request.namaste_code,
        namaste_display=namaste_data['display'],
        icd_codes=request.icd_codes,
        patient_id=request.patient_id,
        abha_id=request.abha_id
    )
    
    # Log FHIR resource creation
    audit_service.log_fhir_resource(
        user_id=current_user['user_id'],
        resource_type='Condition',
        resource_id=condition['id'],
        patient_id=request.patient_id,
        codes=[request.namaste_code] + request.icd_codes
    )
    
    return condition

@app.post("/api/fhir/ConceptMap", tags=["FHIR"])
async def create_concept_map(
    source_code: str,
    target_codes: List[str],
    current_user: dict = Depends(get_current_user)
):
    """
    Create FHIR R4 ConceptMap resource
    Maps NAMASTE code to ICD-11 codes
    """
    # Validate source code
    namaste_data = namaste_parser.get_code_by_id(source_code)
    if not namaste_data:
        raise HTTPException(status_code=404, detail=f"NAMASTE code {source_code} not found")
    
    # Get mapping details
    mapping = mapping_engine.translate_namaste_to_icd(source_code)
    
    # Create ConceptMap
    concept_map = fhir_gen.create_concept_map(
        source_code=source_code,
        source_display=namaste_data['display'],
        target_codes=target_codes
    )
    
    audit_service.log_fhir_resource(
        user_id=current_user['user_id'],
        resource_type='ConceptMap',
        resource_id=concept_map['id'],
        codes=[source_code] + target_codes
    )
    
    return concept_map

@app.get("/api/fhir/ValueSet", tags=["FHIR"])
async def get_value_set(
    system: str = "namaste",
    filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get FHIR ValueSet for NAMASTE or ICD-11 codes
    """
    if system.lower() == "namaste":
        codes = namaste_parser.codes
        if filter:
            codes = [c for c in codes if filter.lower() in c['display'].lower()]
        
        value_set = fhir_gen.create_value_set(
            codes=codes[:50],  # Limit to 50 for performance
            system_name="NAMASTE"
        )
    else:
        raise HTTPException(status_code=400, detail="Only NAMASTE ValueSet supported currently")
    
    return value_set

# ============= ANALYTICS & AUDIT ENDPOINTS =============

@app.get("/api/audit/recent", tags=["Audit"])
async def get_recent_audit_logs(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get recent audit logs (admin only)"""
    if current_user.get('role') not in ['admin', 'auditor']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    logs = audit_service.get_audit_logs(limit)
    return {
        "logs": logs,
        "count": len(logs)
    }

@app.get("/api/audit/user/{user_id}", tags=["Audit"])
async def get_user_activity(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get activity logs for specific user"""
    # Users can only view their own logs unless admin
    if current_user['user_id'] != user_id and current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    logs = audit_service.get_user_activity(user_id)
    stats = audit_service.get_user_statistics(user_id)
    
    return {
        "user_id": user_id,
        "logs": logs,
        "statistics": stats
    }

@app.get("/api/analytics/popular-searches", tags=["Analytics"])
async def get_popular_searches(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get most popular search queries"""
    if current_user.get('role') not in ['admin', 'researcher']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    popular = audit_service.get_popular_searches(limit)
    return {
        "popular_searches": popular,
        "count": len(popular)
    }

@app.get("/api/analytics/translation-stats", tags=["Analytics"])
async def get_translation_statistics(
    current_user: dict = Depends(get_current_user)
):
    """Get translation usage statistics"""
    if current_user.get('role') not in ['admin', 'researcher']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    stats = audit_service.get_translation_statistics()
    return stats

@app.get("/api/analytics/dashboard-stats", tags=["Analytics"])
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive dashboard statistics"""
    if current_user.get('role') not in ['admin', 'researcher']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    """
    return {
        "total_searches": audit_service.get_total_searches(),
        "total_translations": audit_service.get_total_translations(),
        "total_users": audit_service.get_total_users(),
        "popular_codes": audit_service.get_popular_codes(10),
        "recent_activity": audit_service.get_recent_logs(20),
        "translation_stats": audit_service.get_translation_statistics()
    }
    """

    return audit_service.get_analytics_summary()
# ============= HEALTH CHECK =============

@app.get("/api/health", tags=["General"])
async def health_check():
    """Health check endpoint (no auth required)"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "namaste_parser": "active",
            "icd11_client": "active",
            "mapping_engine": "active",
            "fhir_generator": "active",
            "ml_matcher": "active",
            "audit_service": "active",
            "auth_service": "active"
        },
        "timestamp": time.time()
    }

# ============= OPTIONS HANDLER (CORS PREFLIGHT) =============

@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle CORS preflight requests"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept",
            "Access-Control-Max-Age": "3600"
        }
    )

# ============= ERROR HANDLERS =============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting AYUSH Terminology Bridge API v2.0")
    print("📚 Documentation: http://localhost:8000/api/docs")
    print("🔐 Authentication: ABHA OAuth2")
    print("📊 Features: ML Matching + Audit Trail + FHIR R4")
    print("🌐 CORS: Enabled for localhost:3000 and localhost:8080\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")