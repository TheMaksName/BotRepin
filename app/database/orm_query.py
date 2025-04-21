import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.database.models import News, Theme, Material, CategoryTheme, UserCode, Participant

logger = logging.getLogger(__name__)


async def check_user_code(session: AsyncSession, code: str) -> Tuple[bool, Optional[int]]:
    """
    Проверяет наличие кода участника в базе.
    Возвращает (exists, participant_id), где:
    - exists: True если код существует
    - participant_id: ID участника или None
    """
    try:
        result = await session.execute(
            select(UserCode)
            .where(UserCode.code == code)
        )
        print(result.scalars())
        user_code = result.scalar_one_or_none()

        if user_code:
            return True, user_code.participant_id
        return False, None
    except SQLAlchemyError as e:
        logger.error(f"Check user code error: {e}")
        return False, None


async def verify_user_code(
        session: AsyncSession,
        code: str,
        telegram_username: str,
        telegram_chat_id: int
) -> bool:
    """
    Обновляет статус верификации кода пользователя.
    Возвращает True если обновление прошло успешно.
    """
    try:
        result = await session.execute(
            update(UserCode)
            .where(UserCode.code == code)
            .values(
                telegram_username=telegram_username,
                telegram_chat_id=telegram_chat_id,
                is_verified=True,
                verified_at=datetime.utcnow()
            )
        )
        await session.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        logger.error(f"Verify user code error: {e}")
        await session.rollback()
        return False


async def get_verified_user_by_chat_id(session: AsyncSession, chat_id: int) -> Optional[UserCode]:
    """
    Получает верифицированного пользователя по chat_id.
    """
    try:
        result = await session.execute(
            select(UserCode)
            .where(
                and_(
                    UserCode.telegram_chat_id == chat_id,
                    UserCode.is_verified == True
                )
            )
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"Get user by chat_id error: {e}")
        return None


async def get_all_news(session: AsyncSession) -> List[News]:
    """Получает все новости"""
    try:
        result = await session.execute(select(News).order_by(News.date.desc()))
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Get news error: {e}")
        return []


async def get_materials_batch(session: AsyncSession, batch_num: int, batch_size: int = 5) -> List[Material]:
    """Получает материалы пачками"""
    try:
        offset = (batch_num - 1) * batch_size
        result = await session.execute(
            select(Material)
            .offset(offset)
            .limit(batch_size)
        )
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Get materials error: {e}")
        return []

async def orm_get_all_themes_by_category_id(session: AsyncSession, category_id: int) -> List[Theme]:
    """Получает все темы по category_id с предварительной загрузкой категории."""
    try:
        query = (
            select(Theme)
            .options(selectinload(Theme.category))
            .where(Theme.category_id == category_id)
        )
        result = await session.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении тем category_id={category_id}: {e}")
        return []


async def orm_get_theme_by_id(session: AsyncSession, theme_id: int) -> Optional[Theme]:
    """Получает тему по ID."""
    try:
        return await session.get(Theme, theme_id)
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении темы id={theme_id}: {e}")
        return None


async def get_participant_by_id(session: AsyncSession, participant_id: int) -> Optional[Participant]:
    """Асинхронно получает участника по его ID"""
    try:
        result = await session.execute(
            select(Participant)
            .where(Participant.id == participant_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"Get participant by id error: {e}")
        return None

async def get_participant_theme_and_work(session: AsyncSession, participant_id: int) -> Optional[Dict[str, str]]:
    """Асинхронно получает тему и ссылку на работу участника"""
    try:
        participant = await get_participant_by_id(session, participant_id)
        if participant:
            return {
                "theme": participant.theme,
                "work_link": participant.work_link
            }
        return None
    except SQLAlchemyError as e:
        logger.error(f"Get participant theme and work error: {e}")
        return None