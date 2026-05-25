from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.services.catalog_service import catalog_service
from app.routes import upload, session, profile, metrics, filter as filter_router, map_data, catalogs, data, decode, charts, kpis


@asynccontextmanager
async def lifespan(app: FastAPI):
    catalog_service.load()
    yield


app = FastAPI(
    title="CSV Profiling API",
    description="API para análisis y profiling de datasets CSV",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, tags=["upload"])
app.include_router(session.router, tags=["session"])
app.include_router(profile.router, tags=["profile"])
app.include_router(metrics.router, tags=["metrics"])
app.include_router(filter_router.router, tags=["filter"])
app.include_router(data.router, tags=["data"])
app.include_router(map_data.router, tags=["map"])
app.include_router(charts.router, tags=["charts"])
app.include_router(kpis.router, tags=["kpis"])
app.include_router(decode.router, tags=["decode"])
app.include_router(catalogs.router, tags=["catalogs"])


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
