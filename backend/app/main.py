from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.core.database import engine, Base, SessionLocal
from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User  # noqa: F401 — needed for Base.metadata
from app.models.cv import CVProfile, GeneratedCV  # noqa: F401
from app.routers import auth, users, profile, cv

settings = get_settings()


def seed_admin():
    """Create admin user if it doesn't exist yet."""
    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not exists:
            admin = User(
                username=settings.ADMIN_USERNAME,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                display_name="Administrador",
                is_admin=True,
            )
            db.add(admin)
            db.flush()
            db.add(CVProfile(user_id=admin.id))
            db.commit()
            print(f"[seed] Admin '{settings.ADMIN_USERNAME}' criado.")
        else:
            print(f"[seed] Admin '{settings.ADMIN_USERNAME}' já existe.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin()
    yield


app = FastAPI(title="CV Tailor API", lifespan=lifespan)

# API routes
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profile.router)
app.include_router(cv.router)

# Serve frontend static files
STATIC_DIR = "/app/frontend"
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(f"{STATIC_DIR}/index.html")

