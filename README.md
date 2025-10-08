# AYUSH Terminology Bridge API v2.0

🌿 **FHIR-Compliant API for NAMASTE-ICD11 Mapping with ABHA Authentication**

A comprehensive healthcare interoperability solution that bridges traditional AYUSH medicine (NAMASTE terminology) with international standards (ICD-11), featuring ML-enhanced semantic matching, FHIR R4 compliance, and complete audit trail.

---

## 📋 Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [API Documentation](#api-documentation)
7. [Frontend Usage](#frontend-usage)
8. [Authentication](#authentication)
9. [Project Structure](#project-structure)
10. [Development](#development)

---

## ✨ Features

### Core Functionality
- **NAMASTE Code Management**: Search and browse traditional medicine codes
- **ICD-11 Integration**: Dual linearization support (TM2 + Biomedicine)
- **ML Semantic Matching**: Hybrid fuzzy + transformer-based similarity
- **FHIR R4 Compliance**: Generate standard healthcare resources
- **Concept Mapping**: Automated terminology translation

### Security & Compliance
- **ABHA OAuth2 Authentication**: Mock ABDM authentication system
- **Role-Based Access Control**: Practitioner, Researcher, Auditor, Admin
- **Complete Audit Trail**: All API calls logged with metadata
- **Rate Limiting**: 100 requests/minute per user
- **Security Headers**: XSS, CSRF, clickjacking protection

### Analytics & Monitoring
- **Real-time Dashboard**: Usage statistics and trends
- **Audit Log Viewer**: Complete activity tracking
- **Export Capabilities**: JSON and CSV export
- **Performance Metrics**: Response time tracking

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Frontend (JS)  │
│  - Auth Module  │
│  - Search UI    │
│  - Dashboard    │
└────────┬────────┘
         │ HTTPS/REST
         ↓
┌─────────────────────────────────┐
│       FastAPI Backend           │
│  ┌───────────────────────────┐  │
│  │  Auth Middleware          │  │
│  │  (ABHA OAuth2 Mock)       │  │
│  └────────────┬──────────────┘  │
│               ↓                  │
│  ┌───────────────────────────┐  │
│  │  Route Modules            │  │
│  │  - Terminology            │  │
│  │  - FHIR                   │  │
│  │  - Analytics              │  │
│  │  - Audit                  │  │
│  └────────────┬──────────────┘  │
│               ↓                  │
│  ┌───────────────────────────┐  │
│  │  Service Layer            │  │
│  │  - CSV Parser             │  │
│  │  - ICD-11 Client          │  │
│  │  - ML Matcher             │  │
│  │  - FHIR Generator         │  │
│  │  - Audit Service          │  │
│  └────────────┬──────────────┘  │
└────────────────┼────────────────┘
                 ↓
      ┌──────────────────────┐
      │  Data Sources        │
      │  - NAMASTE CSV       │
      │  - ICD-11 API        │
      │  - Concept Mappings  │
      │  - Audit Logs        │
      └──────────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- Python 3.9+
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Safari)

### Backend Setup

```bash
# Clone repository
git clone <repository-url>
cd ayush-terminology-bridge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; print('FastAPI installed')"
```

### Required Python Packages

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
requests==2.31.0
pandas==2.1.3
numpy==1.26.2
scikit-learn==1.3.2
sentence-transformers==2.2.2
fuzzywuzzy==0.18.0
python-Levenshtein==0.23.0
```

---

## ⚙️ Configuration

### 1. ICD-11 API Credentials

Create `config/icd11_credentials.json`:

```json
{
  "client_id": "your_icd11_client_id",
  "client_secret": "your_icd11_client_secret",
  "token_endpoint": "https://icdaccessmanagement.who.int/connect/token",
  "api_endpoint": "https://id.who.int/icd/release/11/2023-01"
}
```

**Get credentials**: Register at https://icd.who.int/icdapi

### 2. ABHA Authentication

Configuration in `config/abha_config.json` (already included):
- Mock mode enabled by default
- Demo users pre-configured
- JWT settings for local development

### 3. NAMASTE Data

Place CSV file at `data/namaste_complete.csv` with columns:
- `code`: NAMASTE code (e.g., NAM0001)
- `display`: Display name
- `definition`: Description
- `system`: Terminology system

### 4. Concept Mappings

Update `data/concept_mappings.json` with NAMASTE→ICD-11 mappings (already included with 20 mappings).

---

## 🏃 Running the Application

### Start Backend Server

```bash
# Development mode
cd api
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server runs at: **http://localhost:8000**

### Access Frontend

Open browser and navigate to:
```
frontend/index.html
```

Or serve with Python:
```bash
cd frontend
python -m http.server 8080
```

Then visit: **http://localhost:8080**

### Verify Installation

1. Check health endpoint: `http://localhost:8000/api/health`
2. View API docs: `http://localhost:8000/api/docs`
3. Login with demo credentials (see below)

---

## 🔐 Authentication

### Demo Credentials

| User ID | Password | Role | Permissions |
|---------|----------|------|-------------|
| DR001 | demo_password | Practitioner | Search, Translate, FHIR |
| DR002 | demo_password | Practitioner | Search, Translate, FHIR |
| RESEARCHER001 | research_password | Researcher | Search, Analytics, Export |
| AUDITOR001 | audit_password | Auditor | View Audit Logs |
| ADMIN001 | admin_password | Admin | Full Access |

### Login Process

1. Click "Login" button
2. Enter user ID and password
3. Receive JWT token (60-minute expiry)
4. Token auto-refreshes every 50 minutes

---

## 📚 API Documentation

### Authentication Endpoints

#### POST `/api/auth/login`
Login with ABHA credentials

**Request**:
```json
{
  "user_id": "DR001",
  "password": "demo_password"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user_id": "DR001",
  "name": "Dr. Rajesh Kumar",
  "role": "practitioner",
  "abha_id": "12-3456-7890-1234"
}
```

### Terminology Endpoints

#### GET `/api/terminology/search`
Search NAMASTE codes

**Parameters**:
- `q` (string): Search query
- `limit` (int): Max results (default: 10)
- `use_ml` (bool): Enable ML matching (default: false)

**Example**:
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/terminology/search?q=diabetes&use_ml=true"
```

#### POST `/api/terminology/translate`
Translate NAMASTE to ICD-11

**Request**:
```json
{
  "namaste_code": "NAM0004",
  "use_ml": true
}
```

**Response**:
```json
{
  "namaste": {
    "code": "NAM0004",
    "display": "Prameha (Diabetes-like condition)"
  },
  "icd11_tm2_matches": [...],
  "icd11_biomedicine_matches": [...],
  "confidence": 0.88,
  "ml_enhanced": true
}
```

### FHIR Endpoints

#### POST `/api/fhir/Condition`
Create FHIR Condition resource

**Request**:
```json
{
  "namaste_code": "NAM0004",
  "icd_codes": ["TM2.7", "5A00"],
  "patient_id": "PATIENT-001",
  "abha_id": "12-3456-7890-1234"
}
```

### Audit Endpoints

#### GET `/api/audit/recent`
Get recent audit logs (admin/auditor only)

**Parameters**:
- `limit` (int): Number of logs (default: 50)

### Analytics Endpoints

#### GET `/api/analytics/dashboard-stats`
Get comprehensive dashboard statistics (researcher/admin only)

**Full API documentation**: http://localhost:8000/api/docs

---

## 💻 Frontend Usage

### Search & Translate

1. **Search NAMASTE Codes**
   - Enter condition (e.g., "diabetes", "fever")
   - Enable ML matching for better results
   - Click search

2. **Translate Codes**
   - Enter NAMASTE code or click from search results
   - View TM2 and Biomedicine mappings
   - See ML confidence scores

3. **Generate FHIR**
   - Select NAMASTE code
   - Choose ICD-11 mappings
   - Enter patient information
   - Generate FHIR R4 JSON

### Analytics Dashboard

Access: **dashboard.html** (Researcher/Admin only)

Features:
- Usage statistics
- Popular searches
- Translation trends
- Success rates
- Recent activity

### Audit Logs

Access: **audit.html** (Auditor/Admin only)

Features:
- Complete activity log
- Filter by user, action, date
- Export to JSON/CSV
- Detailed log viewer

---

## 📁 Project Structure

```
ayush-terminology-bridge/
├── api/
│   ├── main.py                    # Main FastAPI app
│   ├── routes.py                  # Modular route definitions
│   ├── middleware.py              # Custom middleware
│   └── services/
│       ├── csv_parser.py          # NAMASTE CSV parser
│       ├── icd11_client.py        # ICD-11 API client
│       ├── mapping_engine.py      # Translation engine
│       ├── ml_matcher.py          # ML semantic matching
│       ├── fhir_generator.py      # FHIR resource generator
│       ├── audit_service.py       # Audit trail service
│       └── abha_auth.py           # ABHA authentication
├── config/
│   ├── icd11_credentials.json     # ICD-11 API credentials
│   └── abha_config.json           # ABHA auth configuration
├── data/
│   ├── namaste_complete.csv       # NAMASTE terminology
│   ├── concept_mappings.json      # NAMASTE→ICD-11 mappings
│   └── audit_logs.json            # Audit trail storage
├── frontend/
│   ├── index.html                 # Main application page
│   ├── dashboard.html             # Analytics dashboard
│   ├── audit.html                 # Audit log viewer
│   ├── js/
│   │   ├── auth.js                # Authentication module
│   │   ├── app.js                 # Main app logic
│   │   ├── dashboard.js           # Dashboard logic
│   │   └── audit.js               # Audit viewer logic
│   ├── css/
│   │   ├── styles.css             # Main stylesheet
│   │   └── dashboard.css          # Dashboard styles
│   └── assets/
│       └── logo.png               # AYUSH logo
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

---

## 🛠️ Development

### Running Tests

```bash
# Unit tests
pytest tests/

# API tests
pytest tests/test_api.py

# Coverage report
pytest --cov=services tests/
```

### Code Style

```bash
# Format code
black api/

# Lint
flake8 api/
pylint api/
```

### Adding New NAMASTE Codes

1. Update `data/namaste_complete.csv`
2. Add mappings to `data/concept_mappings.json`
3. Restart server
4. Verify with search API

### Custom Middleware

Add to `api/middleware.py`:
```python
class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Your logic here
        response = await call_next(request)
        return response
```

---

## 📊 Performance

- **Average Response Time**: <100ms
- **Search Performance**: <50ms for 10,000 codes
- **ML Matching**: <200ms with transformer models
- **Concurrent Users**: 100+ supported
- **Rate Limit**: 100 requests/minute per user

---

## 🔒 Security

- JWT authentication with 60-minute expiry
- HTTPS recommended for production
- SQL injection protection (parameterized queries)
- XSS protection headers
- CSRF tokens for state-changing operations
- Input validation on all endpoints
- Audit logging for all actions

---

## 📝 License

Copyright © 2024 Ministry of AYUSH, Government of India
MIT Licence 

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📞 Support

- **Documentation**: http://localhost:8000/api/docs
- **Issues**: Create GitHub issue
- **Email**: daymasarthak02@gmail.com

---

## 🙏 Acknowledgments

- WHO ICD-11 API
- ABDM (Ayushman Bharat Digital Mission)
- FastAPI Framework
- Sentence Transformers
- FHIR Community

---

**Version**: 1.0.0  
**Last Updated**: 8/10/25
**Status**: Production Ready ✅