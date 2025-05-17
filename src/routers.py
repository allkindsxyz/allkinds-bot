from src.handlers.system import router as system_router
from src.handlers.groups import router as groups_router
from src.handlers.onboarding import router as onboarding_router
from src.handlers.questions import router as questions_router

all_routers = [
    system_router,
    groups_router,
    onboarding_router,
    questions_router,
] 