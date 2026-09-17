# MetroLens (मेट्रोलेंस) ⚖️🔍
### AI-Powered Statutory Compliance Verification System for Packaged Commodities
**Under the Legal Metrology Act, 2009 & Legal Metrology (Packaged Commodities) Rules, 2011 (PCR 2011)**  
*Department of Consumer Affairs (DoCA) — Ministry of Consumer Affairs, Food & Public Distribution, Government of India*

---

## 🏛️ Problem Statement & Background

Packaged commodities are distributed at immense scale across brick-and-mortar retail stores, supermarkets, warehouses, and e-commerce platforms throughout India. Under the **Legal Metrology Act, 2009** and the **Legal Metrology (Packaged Commodities) Rules, 2011 (PCR 2011)**, every packaged commodity must bear mandatory statutory declarations in a prescribed format, font size, and location to ensure fair trade practices, market transparency, and consumer protection.

Manual market surveillance and inspection of millions of retail Stock Keeping Units (SKUs) is labour-intensive, subjective, error-prone, and geographically constrained.

**MetroLens** solves this critical national challenge by delivering an end-to-end, automated, AI-driven statutory compliance platform that:
1. Instantly scans retail product labels and package surfaces via image upload or live camera.
2. Extracts declarations using high-precision dual-engine OCR (OpenCV image pre-processing, text detection, and Gemini multimodal vision intelligence).
3. Evaluates every statutory declaration against **Rule 6 of PCR 2011** and applicable **FSSAI packaged food regulations**.
4. Automatically flags missing or non-compliant declarations, calculates legal risk scores, and recommends compounding penalties under **Section 48 of the Legal Metrology Act, 2009**.
5. Generates tamper-proof, court-admissible PDF / Word inspection reports with Section 65B Indian Evidence Act audit trails.

---

## ✨ Key Features & Capabilities

- **Dual-Engine Multimodal Vision & OCR**:
  - Image binarization, adaptive thresholding, and contour extraction via **OpenCV**.
  - High-accuracy regional text recognition with bounding box mapping via **EasyOCR**.
  - Semantic vision understanding with structured statutory extraction via **Google Gemini Flash**.
- **Rule 6 Statutory Compliance Engine**:
  - **Rule 6(1)(a)**: Name & complete address of manufacturer / packer / importer.
  - **Rule 6(1)(b)**: Generic or common name of the commodity.
  - **Rule 6(1)(c)**: Net quantity in standard SI metric units (kg, g, L, ml, m, N) with Rule 12 unit validation.
  - **Rule 6(1)(d)**: Month and year of manufacture / pre-packing / import.
  - **Rule 6(1)(da)**: Mandatory **Unit Sale Price (USP)** (e.g., `₹0.12 / g`, `₹25.00 / kg`).
  - **Rule 6(1)(e)**: Maximum Retail Price (**MRP**) inclusive of all taxes.
  - **Rule 6(1)(f)**: Country of origin declaration (mandatory for all imports).
  - **Rule 6(2)**: Complete consumer care details (Officer name/designation, physical postal address, telephone/toll-free number, and grievance email).
- **FSSAI Food Regulation Verifications**:
  - 14-digit FSSAI food license number validation.
  - Vegetarian / Non-Vegetarian statutory green/brown logo verification.
  - "Best Before" / Date of Expiry verification for perishable packaged goods.
- **Section 48 Statutory Compounding & Adjudication**:
  - Enforcement officers can adjudicate violations, record official hearing notes, and issue compounding orders under Section 48.
  - Fine scheduling based on statutory first-offence and subsequent offence thresholds (₹25,000 to ₹50,000+).
- **Court-Admissible Legal Evidence**:
  - One-click generation of statutory inspection certificates, notice of forfeiture, and show-cause notices in PDF and DOCX formats.
  - Section 65B Indian Evidence Act certificate section with cryptographic hash verification and digital timestamps.
- **Secure 3-Tier Role-Based Access Control (RBAC)**:
  - Strict separation of duties between System Administrators, Enforcement Officers, and Field Inspectors.
  - Tamper-proof, append-only digital audit logging for every statutory operation.

---

## 👥 Role-Based Governance & Access Control

MetroLens adheres strictly to the statutory chain of custody prescribed by the Department of Consumer Affairs:

| Role | Badge ID | System Scope & Permissions | Default Demo Credentials |
|---|---|---|---|
| **System Administrator** (`admin`) | `DOCA-ADMIN-01` | Pre-seeded chief administrator. User account activation/deactivation, statutory audit trail review, officer onboarding. *Restricted: Cannot be registered via public signup.* | `admin@doca.gov.in`<br>`Admin@DoCA2026!` |
| **Enforcement Officer** (`officer`) | `OFF-2026-001` | Section 48 compounding adjudication, penalty order issuance, formal inquiry & show-cause management, state-level analytics. | `admin@example.com`<br>`admin123` |
| **Field Inspector** (`inspector`) | `INS-2026-101` | Mobile/desktop field scans, live camera inspections, label text bounding-box reviews, evidence report generation. | `officer@example.com`<br>`123456` |

---

## 🏗️ Architecture & Technology Stack

```
                                  [ Retail Package / Label Image ]
                                                │
                                                ▼
                         ┌──────────────────────────────────────────────┐
                         │   OpenCV Preprocessing & Binarization        │
                         │   - Adaptive Thresholding & Denoising        │
                         │   - Bounding Box Regional Segmentation       │
                         └──────────────────────┬───────────────────────┘
                                                │
                                                ▼
                         ┌──────────────────────────────────────────────┐
                         │   EasyOCR + Gemini Flash Vision              │
                         │   - Multilingual Text Extraction             │
                         │   - Zero-Shot Statutory Semantic Parser      │
                         └──────────────────────┬───────────────────────┘
                                                │
                                                ▼
                         ┌──────────────────────────────────────────────┐
                         │   PCR 2011 Rule 6 Deterministic Engine       │
                         │   - Mandatory 7-Field Metrology Verification │
                         │   - Unit Sale Price (USP) Calculation Check  │
                         │   - FSSAI License & Logo Inspection          │
                         └──────────────────────┬───────────────────────┘
                                                │
                     ┌──────────────────────────┴──────────────────────────┐
                     ▼                                                     ▼
      ┌─────────────────────────────┐                       ┌─────────────────────────────┐
      │   Adjudication & RBAC       │                       │   Evidence & Reporting      │
      │   - Section 48 Compounding  │                       │   - ReportLab Statutory PDF │
      │   - Section 65B Audit Log   │                       │   - Python-docx Legal Brief │
      │   - SQLite / SQLAlchemy ORM │                       │   - Annotated Image Overlay │
      └─────────────────────────────┘                       └─────────────────────────────┘
```

- **Backend**: Python 3.11 - 3.13, FastAPI (high-performance asynchronous ASGI framework).
- **Database & ORM**: SQLite with SQLAlchemy 2.0 (relational persistence, indexed queries, foreign keys).
- **Computer Vision & AI**: OpenCV (`opencv-python`), EasyOCR, Google Gemini Flash API (`google-genai`).
- **Document Generation**: ReportLab (vector PDF generation), Python-docx (editable notices).
- **Security & Authentication**: PBKDF2-HMAC-SHA256 password hashing (100,000 iterations), HMAC-SHA256 signed session cookies, password complexity verification, comprehensive audit logging.
- **Frontend**: Jinja2 HTML5 templates, TailwindCSS styling, Lucide icons, responsive mobile camera scanner.

---

## 📁 Directory Layout

```
MetroLens/
├── .env.example                 # Environment variable template
├── .gitignore                    # Git exclusions (WAL files, test caches, dynamic uploads)
├── auth_helper.py                # PBKDF2 cryptography, HMAC session tokens & security policies
├── database.py                   # SQLAlchemy engine, session maker & Base declaration
├── database.db                   # SQLite statutory persistence store
├── dependencies.py               # Shared FastAPI dependencies, Jinja2 setup & RBAC helpers
├── main.py                       # Modular application entrypoint (~50 lines)
├── models.py                     # SQLAlchemy models (User, Inspection, Product, Company, etc.)
├── requirements.txt              # Production and test Python dependencies
├── seed.py                       # Pre-populated demonstration enforcement database
├── routers/                      # Modular FastAPI APIRouters
│   ├── __init__.py               # Package marker
│   ├── auth.py                   # Authentication & session controllers
│   ├── views.py                  # Public views, dashboard & registry controllers
│   ├── inspections.py            # OCR scanning, AI evaluation & compounding controllers
│   └── admin.py                  # Administrator directory & audit log controllers
├── services/                     # Core business logic and computation engines
│   ├── __init__.py               # Service package exports
│   ├── ocr_service.py            # OpenCV preprocessing and EasyOCR detection
│   ├── gemini_service.py         # Google Gemini multimodal declaration extraction
│   ├── rule_engine.py            # Legal Metrology Rule 6 & FSSAI compliance verification
│   └── report_service.py         # Statutory PDF and DOCX report generation
├── static/                       # Static web assets
│   ├── css/                      # Stylesheets
│   ├── js/                       # Interactive JavaScript utilities
│   └── uploads/                  # Managed upload store
│       ├── .gitkeep
│       ├── annotated/            # Visual bounding-box overlays (.gitkeep)
│       └── reports/              # Generated PDF/DOCX evidence files (.gitkeep)
├── templates/                    # Jinja2 HTML templates
│   ├── base.html                 # Master portal template with navbar & flash alerts
│   ├── home.html                 # Public landing page
│   ├── login.html                # Officer authentication
│   ├── register.html             # Field inspector registration
│   ├── dashboard.html            # Enforcement analytics dashboard
│   ├── new_inspection.html       # Package image upload & live camera scan portal
│   ├── inspection_history.html   # Statutory inspection ledger
│   ├── inspection_result.html    # Detailed findings, bounding boxes & Section 48 adjudication
│   ├── companies.html            # Registered manufacturers & packers directory
│   ├── products.html             # Packaged commodities catalogue
│   ├── reports.html              # Statutory report downloads portal
│   ├── admin_users.html          # Administrator officer directory & status toggles
│   ├── admin_audit_logs.html     # Administrator statutory audit trail (IT Act 65B)
│   └── admin_rules.html          # Legal Metrology statutory rules reference manual
└── tests/                        # Comprehensive automated test suite (21 unit tests)
    ├── __init__.py
    ├── test_auth_security.py     # PBKDF2 hashing, password entropy, HMAC tampering tests
    ├── test_rule_engine.py       # Rule 6, USP, FSSAI rules & violation grading tests
    ├── test_rbac_admin.py        # Pre-seeded admin, role separation, 403 Forbidden tests
    └── test_api_endpoints.py     # Public, protected, scan & dashboard endpoint tests
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- Python 3.11, 3.12, or 3.13 installed.
- Git installed.

### 2. Clone and Setup Environment
```powershell
# Clone the repository
git clone https://github.com/AdityaSudhirRana/MetroLens.git
cd MetroLens

# Create and activate a Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Edit `.env` and configure your parameters:
```ini
# Google Gemini Multimodal Vision API Key
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Security and Session Encryption
SESSION_SECRET=metrolens_statutory_secret_key_2026_super_secure_hmac

# Server Binding
HOST=127.0.0.1
PORT=8000
```
> **Note**: Even without an active Gemini API key, MetroLens operates seamlessly using its integrated deterministic fallback pattern-matching engine.

### 5. Seed Enforcement Database (Optional)
To populate the database with demonstration enforcement records, past market inspections, and registered companies:
```powershell
python seed.py
```

---

## 🧪 Running Automated Tests

MetroLens includes a comprehensive, production-grade test suite verifying authentication security, Legal Metrology Rule 6 logic, Section 48 adjudication, and RBAC authorization:

```powershell
python -m unittest discover tests
```

### Test Suite Coverage:
- **`tests/test_auth_security.py`**:
  - PBKDF2-HMAC-SHA256 password hashing with unique salt.
  - Password complexity validator (minimum 8 chars, uppercase, lowercase, digit, symbol).
  - HMAC session token signing, expiration checks, and tampering rejection.
- **`tests/test_rule_engine.py`**:
  - Rule 6(1) all-compliant package validation.
  - Missing mandatory declaration violation detection.
  - Unit Sale Price (USP) compliance evaluation.
  - FSSAI packaged food rules (14-digit license check, veg/non-veg indicator).
- **`tests/test_rbac_admin.py`**:
  - Pre-seeded system administrator validation.
  - Prevention of unauthorized administrative account self-registration.
  - Enforcement of 403 Forbidden status on privileged endpoints for unauthorized roles.
  - Administrative officer deactivation and activation toggles.
  - Audit log recording for sensitive statutory actions.
- **`tests/test_api_endpoints.py`**:
  - Public route accessibility (login, register).
  - Unauthenticated redirect handling for protected routes.
  - Authenticated access for inspectors and officers.
  - API dashboard statistics endpoint payload format.

---

## 🚀 Running the Application

Start the high-performance ASGI server:
```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
or simply:
```powershell
python main.py
```

Access the web portal in your browser:
👉 **`http://127.0.0.1:8000`**

### Available Login Accounts:
| Role | Email | Password |
|---|---|---|
| **System Administrator** | `admin@doca.gov.in` | `Admin@DoCA2026!` |
| **Enforcement Officer** | `admin@example.com` | `admin123` |
| **Field Inspector** | `officer@example.com` | `123456` |

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description | Role Required |
|---|---|---|---|
| `GET` | `/` | Public portal landing page | Public |
| `GET` | `/login` | Official login portal | Public |
| `POST` | `/login` | Authenticate and issue secure session cookie | Public |
| `GET` | `/register` | Field inspector self-registration | Public (Inspector only) |
| `POST` | `/register` | Register new inspector profile | Public |
| `GET` | `/logout` | Invalidate session cookie | Authenticated |
| `GET` | `/dashboard` | Main enforcement analytics and KPI metrics | Inspector / Officer / Admin |
| `GET` | `/new-inspection` | Package image upload & live camera scanner | Inspector / Officer / Admin |
| `POST` | `/api/scan` | Multi-stage image analysis (OCR + Gemini + Rule Engine) | Inspector / Officer / Admin |
| `GET` | `/inspections/{id}` | Detailed inspection findings & Section 48 panel | Inspector / Officer / Admin |
| `PATCH` | `/api/inspections/{id}/decision` | Inspector confirmed or flagged status decision | Field Inspector / Officer |
| `POST` | `/api/inspections/{id}/compound` | Register Section 48 compounding order & penalty | Enforcement Officer / Admin |
| `GET` | `/history` | Searchable statutory inspection register | Inspector / Officer / Admin |
| `GET` | `/companies` | Directory of registered manufacturers & packers | Inspector / Officer / Admin |
| `GET` | `/products` | Catalog of inspected packaged commodities | Inspector / Officer / Admin |
| `GET` | `/reports` | Statutory report repository | Inspector / Officer / Admin |
| `GET` | `/api/reports/{id}/pdf` | Download sealed PDF inspection certificate | Inspector / Officer / Admin |
| `GET` | `/api/reports/{id}/docx` | Download editable Legal Metrology show-cause brief | Inspector / Officer / Admin |
| `GET` | `/api/inspections/{id}/json` | Export inspection record in JSON format | Inspector / Officer / Admin |
| `GET` | `/api/dashboard` | Real-time JSON stats for analytics and live feed | Authenticated |
| `GET` | `/admin/users` | Officer directory and account status management | System Admin only |
| `POST` | `/api/admin/users/create` | Provision new officer profile | System Admin only |
| `POST` | `/api/admin/users/{id}/toggle-status` | Activate or deactivate officer account | System Admin only |
| `POST` | `/api/admin/users/{id}/change-role` | Promote or demote officer role tier | System Admin only |
| `GET` | `/admin/audit-logs` | Tamper-proof digital audit trail log (IT Act 65B) | System Admin only |
| `GET` | `/admin/rules` | Statutory Legal Metrology rules reference manual | System Admin only |

---

## 🔒 Security & Statutory Compliance Standards

- **Indian Evidence Act / IT Act Section 65B Compliance**: Digital certificates generated by MetroLens preserve image hashes (SHA-256), client IP addresses, officer badges, and UTC timestamps for court admissibility.
- **Strict Role Separation**: Public registration for the administrative role is mathematically blocked; the administrator account is pre-provisioned directly into the database engine.
- **Tamper-Proof Audit Trails**: Every statutory adjudication, fine imposition, inspection review, and user status change is recorded in an immutable audit ledger (`AuditLog`).
- **OWASP-Compliant Session Management**: Secure `HttpOnly`, `SameSite=Lax` cookies with cryptographic signature validation protect against XSS and session hijacking.

---

## 📜 Legal Notice & Statutory Disclaimer

*This software was developed to enforce compliance with the **Legal Metrology Act, 2009** (Act No. 1 of 2010), the **Legal Metrology (Packaged Commodities) Rules, 2011**, and associated amendments issued by the Department of Consumer Affairs, Government of India. All automated rule findings and risk scores serve as technical aids to assist authorized Legal Metrology Officers and Controllers in executing their statutory responsibilities.*
