from fastapi import APIRouter

from routes.v1 import lobby, prompt, user

router = APIRouter(prefix="/v1")

router.include_router(user.router)
router.include_router(prompt.router)
router.include_router(lobby.router)
