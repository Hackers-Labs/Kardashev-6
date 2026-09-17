"""
MetroLens - AI-Powered Legal Metrology Compliance Verification System
Department of Consumer Affairs (DoCA) — Ministry of Consumer Affairs, Food & Public Distribution
Government of India
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from dependencies import (
    STATIC_DIR,
    UPLOADS_DIR,
    init_system_admin,
    render,
    log_audit_event,
    get_current_user,
    require_admin,
    require_supervisor
)
from routers.auth import router as auth_router
from routers.views import router as views_router
from routers.inspections import router as inspections_router
from routers.admin import router as admin_router

# Initialize Tables if not yet created
Base.metadata.create_all(bind=engine)

# Initialize pre-defined Department Administrator
init_system_admin()

# Application Instance
app = FastAPI(
    title="MetroLens - Legal Metrology Compliance Enforcement Portal",
    description="Department of Consumer Affairs, Government of India - Packaged Commodities Rules 2011 Enforcement Platform",
    version="2.0.0"
)

# Mount Static Assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount Modular Routers
app.include_router(auth_router)
app.include_router(views_router)
app.include_router(inspections_router)
app.include_router(admin_router)

@app.on_event("startup")
async def startup_event():
    init_system_admin()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
