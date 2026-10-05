from fastapi import FastAPI

from app.api import health

app = FastAPI(title="FoodScape Dallas API")

app.include_router(health.router)
