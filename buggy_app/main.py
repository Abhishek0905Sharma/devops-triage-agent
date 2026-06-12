from fastapi import FastAPI
from buggy_app.routers.users import router as users_router

app = FastAPI(
    title="DevOps Incident Triage Demo - Users API",
    description="A simple, intentionally buggy FastAPI service to test the triage agent.",
    version="1.0.0"
)

app.include_router(users_router, tags=["Users"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Users API. Status: Operational (with hidden bugs!)."}
