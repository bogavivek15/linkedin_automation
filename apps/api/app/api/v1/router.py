from apps.api.app.api.v1.agents import router as agents_router
from apps.api.app.api.v1.health import router as health_router
from apps.api.app.api.v1.jobs import router as jobs_router
from apps.api.app.api.v1.memory import router as memory_router
from apps.api.app.api.v1.notifications import router as notifications_router
from apps.api.app.api.v1.resumes import router as resumes_router
from apps.api.app.api.v1.network import router as network_router
from apps.api.app.api.v1.profiles import router as profiles_router
from apps.api.app.api.v1.search import router as search_router
from apps.api.app.api.v1.trust import router as trust_router
from apps.api.app.api.v1.presence import router as presence_router
from apps.api.app.api.v1.images import router as images_router
from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(resumes_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(trust_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(profiles_router)
api_v1_router.include_router(agents_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(network_router)
api_v1_router.include_router(presence_router)
api_v1_router.include_router(images_router)
