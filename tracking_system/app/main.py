from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.db import init_db
from app.routes import health, orders, samples

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    await init_db()
    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

app.include_router(health.router)
app.include_router(orders.router)
app.include_router(samples.router)