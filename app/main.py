from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import models
from app.database.connection import engine
from app.routes import auth_routes, wallet_routes, idea_routes, marketplace_routes, user_routes, problem_routes, admin_routes
from app.config.settings import settings

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_routes.router)
app.include_router(wallet_routes.router)
app.include_router(idea_routes.router)
app.include_router(marketplace_routes.router)
app.include_router(user_routes.router)
app.include_router(problem_routes.router)
app.include_router(admin_routes.router)

@app.get("/")
def read_root():
    return {
        "platform": settings.PROJECT_NAME,
        "status": "Online",
        "currency": "Invox (Ʉ)"
    }

@app.get("/kaithheathcheck")
def health():
    return {"status": "ok"}