import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.app.db.session import db_helper
from auth_service.app.schemas import LoginRequest, TokenPair
from auth_service.app.services.auth_service import AuthService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_auth_service(db: AsyncSession = Depends(db_helper.get_db_session)) -> AuthService:
    return AuthService(db)


@router.post("/login", response_model=TokenPair)
async def login(
    request_data: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
):
    tokens = await auth_service.login(request_data.login, request_data.password)
    if not tokens:
        logger.warning("Неудачная попытка входа", login=request_data.login)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
        )

    logger.info("Пользователь успешно вошел в систему", login=request_data.login)
    return tokens
