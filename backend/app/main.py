from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health_router
from app.api import chat_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.security import router as security_router
from app.api.dashboard import dashboard_router
from app.studio.router import router as studio_router
from app.model_registry.router import router as model_registry_router
from app.router.router import router as model_router_api_router
from app.gateway.router import router as inference_gateway_router
from app.gpu.router import router as gpu_router
from app.service.router import router as service_discovery_router
from app.cache.router import router as model_cache_router
from app.dashboard.router import api_router as infra_dashboard_api_router
from app.dashboard.router import demo_router as infra_dashboard_demo_router
from app.config import settings
from app.logging.middleware import RequestContextMiddleware
from app.logging.structured import configure_structured_logging
from app.monitoring.middleware import InfraMetricsMiddleware
from app.monitoring.router import router as metrics_router
from app.openapi import OPENAPI_TAGS
from app.openapi import get_api_description
from app.version import __version__
from app.api_docs import mount_api_docs

app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description=get_api_description(),
    docs_url=None,
    redoc_url=None,
    contact={
        "name": "Enterprise AI Platform",
        "url": "https://github.com/your-org/enterprise-ai-agent",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=OPENAPI_TAGS,
)

mount_api_docs(app, cdn_preset=settings.SWAGGER_UI_CDN)

if settings.ENABLE_STRUCTURED_LOGGING:

    from observability.logging.logger import configure_structured_logging

    configure_structured_logging(
        log_file=settings.STRUCTURED_LOG_FILE or None,
        service_name=settings.LOG_SERVICE_NAME,
    )


@app.get("/")
def root():

    return {
        "name": settings.APP_NAME,
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "knowledge_demo": "/api/v1/knowledge/documents",
        "dashboard_api": "/api/v1/dashboard/projects",
        "infra_dashboard_demo": "/infra/dashboard/demo",
        "infra_dashboard_api": "/api/v1/infra/dashboard/overview",
        "agent_studio": "/workflow",
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENABLE_STRUCTURED_LOGGING:

    app.add_middleware(RequestContextMiddleware)

if settings.ENABLE_INFRA_METRICS:

    app.add_middleware(InfraMetricsMiddleware)

if settings.ENABLE_API_AUTH:
    from security.auth import create_auth_middleware
    from security.auth import parse_auth_tokens

    AuthMiddleware = create_auth_middleware(
        enabled=True,
        token_map=parse_auth_tokens(settings.API_AUTH_TOKENS),
    )
    app.add_middleware(AuthMiddleware)

app.include_router(

    health_router

)

app.include_router(

    metrics_router,

)

app.include_router(

    chat_router,

    prefix="/api/v1",

    tags=["Chat"]

)

app.include_router(
    security_router,
    prefix="/api/v1",
)

app.include_router(

    knowledge_router,

    prefix="/api/v1/knowledge",

    tags=["Knowledge Assistant"],

)

app.include_router(
    dashboard_router,
    prefix="/api/v1",
)

app.include_router(studio_router)

app.include_router(
    model_registry_router,
    prefix="/api/v1",
)

app.include_router(
    model_router_api_router,
    prefix="/api/v1",
)

app.include_router(
    inference_gateway_router,
    prefix="/api/v1",
)

app.include_router(
    gpu_router,
    prefix="/api/v1",
)

app.include_router(
    service_discovery_router,
    prefix="/api/v1",
)

app.include_router(
    model_cache_router,
    prefix="/api/v1",
)

app.include_router(
    infra_dashboard_api_router,
    prefix="/api/v1",
)

app.include_router(infra_dashboard_demo_router)


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )