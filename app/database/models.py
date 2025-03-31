from typing import List, Optional

from sqlalchemy import String, Boolean, Text, DateTime, func, ForeignKey, Index, ForeignKeyConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Базовый класс для всех моделей
class Base(DeclarativeBase):
    """Базовый класс для всех моделей базы данных."""
    pass

# Модель для всех пользователей
class User(Base):
    """Модель всех пользователей бота."""
    __tablename__ = "user"
    __table_args__ = (Index("idx_user_user_id", "user_id"),)

    user_id: Mapped[int] = mapped_column(primary_key=True)  # Уникальный Telegram ID как первичный ключ
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)  # Никнейм пользователя
    reg_status: Mapped[bool] = mapped_column(Boolean, default=False)  # Статус регистрации

    # Связь один к одному с ActiveUser
    active_profile: Mapped[Optional["ActiveUser"]] = relationship(
        "ActiveUser",
        back_populates="user",
        uselist=False,
        lazy="selectin"
    )

# Модель для активных пользователей
class ActiveUser(Base):
    """Модель активных пользователей, участвующих в конкурсе."""
    __tablename__ = 'active_user'
    __table_args__ = (
        ForeignKeyConstraint(["user_id"], ["user.user_id"], ondelete="CASCADE"),
        Index("idx_active_user_user_id", "user_id"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("user.user_id"), primary_key=True)  # Telegram ID как первичный и внешний ключ
    name: Mapped[str] = mapped_column(String(150), nullable=False)  # ФИО пользователя
    school: Mapped[str] = mapped_column(String(100), nullable=False)  # Название школы
    phone_number: Mapped[str] = mapped_column(String(15), nullable=False)  # Номер телефона (+79991234567)
    mail: Mapped[str] = mapped_column(String(100), nullable=False)  # Электронная почта
    name_mentor: Mapped[str] = mapped_column(String(150), nullable=False)  # ФИО наставника
    post_mentor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="")  # Должность наставника
    theme: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, default="Не выбрана")  # Тема работы

    # Связь один к одному с User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="active_profile",
        lazy="selectin"
    )

# Модель для новостей
class News(Base):
    """Модель новостей для бота."""
    __tablename__ = "news"
    __table_args__ = (Index("idx_news_date", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)  # Текст новости
    image: Mapped[str] = mapped_column(String(150), nullable=True)  # Ссылка на изображение
    date: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())  # Дата создания/обновления


# Модель для администраторов
class Admin(Base):
    """Модель администраторов бота."""
    __tablename__ = "admin"
    __table_args__ = (Index("idx_admin_user_id", "user_id"),)

    user_id: Mapped[int] = mapped_column(primary_key=True)  # Уникальный Telegram ID как первичный ключ
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)  # Никнейм администратора


# Модель для категорий тем
class CategoryTheme(Base):
    """Модель категорий тем конкурса."""
    __tablename__ = "category_theme"
    __table_args__ = (Index("idx_category_theme_title", "title"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)  # Название категории

    themes: Mapped[List["Theme"]] = relationship("Theme", back_populates="category", lazy="selectin")


# Модель для тем
class Theme(Base):
    """Модель тем конкурса."""
    __tablename__ = "theme"
    __table_args__ = (Index("idx_theme_category_id", "category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)  # Название темы
    technique: Mapped[str] = mapped_column(String(50), nullable=False)  # Техника выполнения
    category_id: Mapped[int] = mapped_column(ForeignKey("category_theme.id"), nullable=False)

    category: Mapped["CategoryTheme"] = relationship("CategoryTheme", back_populates="themes", lazy="selectin")

class Material(Base):
    """Модель материалов для участников."""
    __tablename__ = "material"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)  # Название материала
    link: Mapped[str] = mapped_column(String(150), nullable=False)  # Ссылка на материал
