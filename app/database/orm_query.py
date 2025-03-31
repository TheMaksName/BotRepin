import logging
from typing import Dict, Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.database.models import ActiveUser, User, Material, Theme, News, Admin

logger = logging.getLogger(__name__)

async def orm_AddActiveUser(session: AsyncSession, data: Dict) -> Optional[ActiveUser]:
    """Добавляет нового активного пользователя и обновляет reg_status."""
    try:
        user = await session.get(User, data["user_id"])
        if not user:
            raise ValueError(f"Пользователь user_id={data['user_id']} не найден в таблице User")

        user_data = {
            "user_id": data["user_id"],
            "name": data["name_user"],
            "school": data["school"],
            "phone_number": data["phone_number"],
            "mail": data["mail"],
            "name_mentor": data["name_mentor"],
            "post_mentor": data.get("post_mentor", "")
        }
        active_user = ActiveUser(**user_data)
        session.add(active_user)
        user.reg_status = True
        await session.commit()
        logger.info(f"Пользователь user_id={data['user_id']} добавлен в active_user")
        return active_user
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка базы данных при добавлении active_user user_id={data.get('user_id')}: {e}")
        return None
    except Exception as e:
        await session.rollback()
        logger.error(f"Ошибка добавления active_user user_id={data.get('user_id')}: {e}")
        return None

async def orm_AddUser(session: AsyncSession, data: Dict) -> Optional[User]:
    """Добавляет пользователя в базу данных."""
    try:
        obj = User(
            user_id=data["user_id"],
            nickname=data["nickname"],
            reg_status=False
        )
        session.add(obj)
        await session.commit()
        logger.debug(f"Пользователь user_id={data['user_id']} добавлен в user")
        return obj
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка базы данных при добавлении user_id={data.get('user_id')}: {e}")
        return None

async def orm_get_all_user(session: AsyncSession) -> List[int]:
    """Возвращает список всех user_id из таблицы User."""
    try:
        query = select(User.user_id)
        result = await session.execute(query)
        users = result.scalars().all()
        logger.debug(f"Получено {len(users)} пользователей из user")
        return users
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении списка пользователей: {e}")
        return []

async def orm_Change_RegStaus(session: AsyncSession, user_id: int, new_reg_status: bool) -> bool:
    """Изменяет статус регистрации пользователя и управляет ActiveUser."""
    try:
        user = await session.get(User, user_id)
        if not user:
            logger.warning(f"Пользователь user_id={user_id} не найден в user")
            return False
        user.reg_status = new_reg_status
        if not new_reg_status:
            await session.execute(
                delete(ActiveUser).where(ActiveUser.user_id == user_id)
            )
        await session.commit()
        logger.info(f"Статус регистрации user_id={user_id} изменен на {new_reg_status}")
        return True
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка базы данных при изменении статуса user_id={user_id}: {e}")
        return False

async def orm_Check_avail_user(session: AsyncSession, user_id: int) -> bool:
    """Проверяет, существует ли пользователь с указанным user_id."""
    try:
        result = await session.get(User, user_id)
        return bool(result)
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при проверке user_id={user_id}: {e}")
        return False

async def orm_Check_register_user(session: AsyncSession, user_id: int) -> Optional[str]:
    """Проверяет, зарегистрирован ли пользователь как активный."""
    try:
        result = await session.get(ActiveUser, user_id)
        return result.name if result else None
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при проверке регистрации user_id={user_id}: {e}")
        return None

async def orm_Get_info_user(session: AsyncSession, user_id: int) -> Optional[ActiveUser]:
    """Получает информацию о пользователе из active_user."""
    try:
        result = await session.get(ActiveUser, user_id)
        return result
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении данных user_id={user_id}: {e}")
        return None

async def orm_Edit_user_profile(session: AsyncSession, user_id: int, data: Dict) -> bool:
    """Редактирует профиль пользователя."""
    try:
        user = await session.get(ActiveUser, user_id)
        if not user:
            logger.warning(f"Пользователь user_id={user_id} не найден в active_user")
            return False
        for key, value in data.items():
            field = key.replace("edit_", "")
            if hasattr(user, field):
                setattr(user, field, value)
        await session.commit()
        logger.info(f"Профиль user_id={user_id} обновлен")
        return True
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка базы данных при редактировании профиля user_id={user_id}: {e}")
        return False

async def orm_add_admin(session: AsyncSession, user_id: int, username: str) -> bool:
    """Добавляет администратора в базу данных."""
    try:
        obj = Admin(user_id=user_id, nickname=username)
        session.add(obj)
        await session.commit()
        logger.info(f"Администратор user_id={user_id} добавлен")
        return True
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка базы данных при добавлении admin user_id={user_id}: {e}")
        return False

async def orm_get_list_admin(session: AsyncSession) -> List[int]:
    """Возвращает список всех user_id администраторов."""
    try:
        query = select(Admin.user_id)
        result = await session.execute(query)
        admins = result.scalars().all()
        return admins
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении списка админов: {e}")
        return []

async def orm_add_news(session: AsyncSession, post_id: int, text: str, photo: str) -> bool:
    """Добавляет новость в базу данных."""
    try:
        obj = News(post_id=post_id, text=text, image=photo)
        session.add(obj)
        await session.commit()
        logger.info(f"Новость post_id={post_id} добавлена")
        return True
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка базы данных при добавлении новости post_id={post_id}: {e}")
        return False

async def orm_get_news_by_id(session: AsyncSession, id: int) -> Optional[News]:
    """Возвращает новость по её идентификатору."""
    try:
        return await session.get(News, id)
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении новости id={id}: {e}")
        return None

async def orm_edit_news_by_id(session: AsyncSession, post_id: int, text: str = None, photo: str = None) -> bool:
    """Редактирует новость по её идентификатору."""
    try:
        updates = {}
        if text is not None:
            updates["text"] = text
        if photo is not None:
            updates["image"] = photo
        if updates:
            await session.execute(
                update(News)
                .where(News.post_id == post_id)
                .values(**updates)
            )
            await session.commit()
            logger.info(f"Новость post_id={post_id} обновлена")
            return True
        return False
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Ошибка базы данных при редактировании новости post_id={post_id}: {e}")
        return False

async def orm_get_all_news(session: AsyncSession) -> List[News]:
    """Возвращает список всех новостей."""
    try:
        query = select(News)
        result = await session.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении всех новостей: {e}")
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

async def orm_get_material_by_id(session: AsyncSession, material_id: int) -> List[Material]:
    """Получает материалы по диапазону ID."""
    try:
        query = select(Material).where(
            (Material.id >= 1 + 5 * material_id) & (Material.id <= (material_id + 1) * 5)
        )
        result = await session.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении материалов material_id={material_id}: {e}")
        return []