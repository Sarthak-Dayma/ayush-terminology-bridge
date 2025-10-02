"""
Database Models and Connection for AYUSH Terminology Bridge
Supports: SQLite (development), PostgreSQL (production)
"""

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional, List, Dict
import json
import os

# ============= DATABASE CONFIGURATION =============

# Database URL - defaults to SQLite for development
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./ayush_terminology.db"
)

# For PostgreSQL in production, use:
# DATABASE_URL = "postgresql://user:password@localhost/ayush_terminology"

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False  # Set to True for SQL query logging
    )
else:
    engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# ============= DATABASE MODELS =============

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    role = Column(String(50), nullable=False)  # practitioner, researcher, auditor, admin
    abha_id = Column(String(50), unique=True, index=True)
    abha_address = Column(String(255))
    facility = Column(String(255))
    specialization = Column(String(255))
    license_number = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

class AuditLog(Base):
    """Audit log model for tracking all system activities"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String(50), index=True)
    user_role = Column(String(50))
    action_type = Column(String(100), index=True)
    endpoint = Column(String(255))
    method = Column(String(10))
    ip_address = Column(String(50))
    user_agent = Column(Text)
    response_status = Column(Integer)
    response_time_ms = Column(Float)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

class SearchLog(Base):
    """Search activity log for analytics"""
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String(50), index=True)
    query = Column(String(500), index=True)
    results_count = Column(Integer)
    top_result_code = Column(String(50))
    ml_enabled = Column(Boolean, default=False)
    response_time_ms = Column(Float)

class TranslationLog(Base):
    """Translation activity log for analytics"""
    __tablename__ = "translation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String(50), index=True)
    namaste_code = Column(String(50), index=True)
    target_system = Column(String(50))
    target_codes = Column(JSON)
    confidence_score = Column(Float)
    ml_enhanced = Column(Boolean, default=False)
    success = Column(Boolean, default=True)
    response_time_ms = Column(Float)

class FHIRResourceLog(Base):
    """FHIR resource creation log"""
    __tablename__ = "fhir_resource_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String(50), index=True)
    resource_type = Column(String(50), index=True)
    resource_id = Column(String(100), unique=True)
    patient_id = Column(String(100), index=True)
    abha_id = Column(String(50), index=True, nullable=True)
    namaste_code = Column(String(50))
    icd_codes = Column(JSON)
    resource_json = Column(Text)

class Session(Base):
    """User session model"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(50), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(50))
    user_agent = Column(Text)

class CodeMapping(Base):
    """Store NAMASTE to ICD-11 mappings"""
    __tablename__ = "code_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    namaste_code = Column(String(50), index=True)
    namaste_display = Column(String(500))
    icd11_code = Column(String(50), index=True)
    icd11_display = Column(String(500))
    linearization = Column(String(20))  # 'tm2' or 'mms'
    equivalence = Column(String(20))  # 'equivalent', 'narrower', 'broader', 'related'
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(50))
    verified = Column(Boolean, default=False)

# ============= DATABASE FUNCTIONS =============

def init_db():
    """Initialize database - create all tables"""
    print("🔄 Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")

def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_default_users(db: Session):
    """Create default demo users"""
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    default_users = [
        {
            "user_id": "DR001",
            "name": "Dr. Rajesh Kumar",
            "email": "dr.rajesh@example.com",
            "role": "practitioner",
            "abha_id": "12-3456-7890-1234",
            "abha_address": "drrajesh@abdm",
            "facility": "AIIMS Delhi",
            "specialization": "Ayurveda",
            "license_number": "AY/DL/2020/12345",
            "hashed_password": pwd_context.hash("demo_password")
        },
        {
            "user_id": "DR002",
            "name": "Dr. Priya Sharma",
            "email": "dr.priya@example.com",
            "role": "practitioner",
            "abha_id": "98-7654-3210-5678",
            "abha_address": "drpriya@abdm",
            "facility": "Banaras Hindu University",
            "specialization": "Unani",
            "license_number": "UN/UP/2019/67890",
            "hashed_password": pwd_context.hash("demo_password")
        },
        {
            "user_id": "ADMIN001",
            "name": "System Administrator",
            "email": "admin@ayush.gov.in",
            "role": "admin",
            "abha_id": "11-1111-1111-1111",
            "abha_address": "admin@abdm",
            "facility": "AYUSH Ministry HQ",
            "specialization": "System Administration",
            "license_number": "ADMIN/2024/001",
            "hashed_password": pwd_context.hash("admin_password")
        },
        {
            "user_id": "RESEARCHER001",
            "name": "Dr. Amit Verma",
            "email": "amit.verma@research.in",
            "role": "researcher",
            "abha_id": "22-2222-2222-2222",
            "abha_address": "researcher@abdm",
            "facility": "CCRAS",
            "specialization": "Research",
            "license_number": "RES/2023/001",
            "hashed_password": pwd_context.hash("research_password")
        },
        {
            "user_id": "AUDITOR001",
            "name": "Ms. Sneha Patel",
            "email": "sneha.patel@audit.gov.in",
            "role": "auditor",
            "abha_id": "33-3333-3333-3333",
            "abha_address": "auditor@abdm",
            "facility": "AYUSH Quality Assurance",
            "specialization": "Compliance",
            "license_number": "AUD/2024/001",
            "hashed_password": pwd_context.hash("audit_password")
        }
    ]
    
    for user_data in default_users:
        # Check if user already exists
        existing = db.query(User).filter(User.user_id == user_data["user_id"]).first()
        if not existing:
            user = User(**user_data)
            db.add(user)
    
    db.commit()
    print(f"✅ Created {len(default_users)} default users")

# ============= DATABASE UTILITIES =============

class DatabaseManager:
    """Database manager for common operations"""
    
    @staticmethod
    def log_audit(db: Session, **kwargs):
        """Log audit entry"""
        log = AuditLog(**kwargs)
        db.add(log)
        db.commit()
        return log
    
    @staticmethod
    def log_search(db: Session, **kwargs):
        """Log search activity"""
        log = SearchLog(**kwargs)
        db.add(log)
        db.commit()
        return log
    
    @staticmethod
    def log_translation(db: Session, **kwargs):
        """Log translation activity"""
        log = TranslationLog(**kwargs)
        db.add(log)
        db.commit()
        return log
    
    @staticmethod
    def log_fhir_resource(db: Session, **kwargs):
        """Log FHIR resource creation"""
        log = FHIRResourceLog(**kwargs)
        db.add(log)
        db.commit()
        return log
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by user_id"""
        return db.query(User).filter(User.user_id == user_id, User.is_active == True).first()
    
    @staticmethod
    def get_recent_audit_logs(db: Session, limit: int = 50) -> List[AuditLog]:
        """Get recent audit logs"""
        return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_user_statistics(db: Session, user_id: str) -> Dict:
        """Get statistics for a user"""
        total_searches = db.query(SearchLog).filter(SearchLog.user_id == user_id).count()
        total_translations = db.query(TranslationLog).filter(TranslationLog.user_id == user_id).count()
        total_fhir = db.query(FHIRResourceLog).filter(FHIRResourceLog.user_id == user_id).count()
        
        return {
            "total_searches": total_searches,
            "total_translations": total_translations,
            "total_fhir_resources": total_fhir
        }

# ============= INITIALIZATION =============

def setup_database():
    """Setup database with tables and default data"""
    init_db()
    
    # Create default users
    db = SessionLocal()
    try:
        create_default_users(db)
    finally:
        db.close()
    
    print("✅ Database setup complete")

if __name__ == "__main__":
    setup_database()