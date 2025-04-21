import secrets
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Boolean, Text, DateTime, func, ForeignKey, Index, ForeignKeyConstraint, Column, Integer, \
    BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Базовый класс для всех моделей
class Base(DeclarativeBase):
    """Базовый класс для всех моделей базы данных."""
    pass


class Participant(Base):
    """Минимальная модель только для работы с полями Тема и Работа"""
    __tablename__ = 'reg_participant'  # Имя таблицы как в Django

    id = Column(Integer, primary_key=True)
    theme = Column(String(200))  # Поле "Тема"
    work_link = Column(String(500))  # Поле "Работа" (ссылка)

    verification_code: Mapped["UserCode"] = relationship("UserCode", back_populates="participant", uselist=False)

class UserCode(Base):
    """Модель кода верификации Telegram"""
    __tablename__ = 'usercode'
    __table_args__ = (
        Index('idx_usercode_code', 'code'),
        Index('idx_usercode_telegram', 'telegram_username'),
        Index('idx_usercode_verified', 'is_verified'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey('reg_participant.id'), unique=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)

    participant: Mapped["Participant"] = relationship("Participant", back_populates="verification_code")

    def __repr__(self):
        return f"<UserCode(code='{self.code}', participant_id={self.participant_id}, is_verified={self.is_verified})>"



# Модель для новостей
class News(Base):
    """Модель новостей для бота."""
    __tablename__ = "news"
    __table_args__ = (Index("idx_news_date", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)  # Текст новости
    image: Mapped[str] = mapped_column(String(150), nullable=True)  # Ссылка на изображение
    date: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())  # Дата создания/обновления



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
