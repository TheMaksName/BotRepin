import secrets
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from time import time
from typing import Dict, Tuple

import aiosmtplib
from config import settings

logger = logging.getLogger(__name__)
users_token: Dict[int, Tuple[str, float]] = {}
TOKEN_TIMEOUT = 600 # 10 минут

def generate_verification_token() -> str:
    """Генерирует безопасный токен для верификации."""
    return secrets.token_urlsafe(8)

async def send_verification_mail(mail: str, token: str) -> None:
    """Отправляет письмо с кодом верификации."""
    body = f'Пожалуйста, подтвердите ваш email, введя этот код в Телеграм-боте: {token}'
    msg = MIMEMultipart()
    msg['From'] = settings.sender_email
    msg['To'] = mail
    msg['Subject'] = 'Подтверждение email'
    msg.attach(MIMEText(body, 'plain'))

    try:
        smtp_client = aiosmtplib.SMTP(
            hostname=settings.smtp_server,
            port=settings.port,
            use_tls=False,
            start_tls=True
        )
        await smtp_client.connect()
        await smtp_client.login(settings.sender_email, settings.sender_password)
        await smtp_client.send_message(msg)
        logger.info(f"Письмо с токеном {token} отправлено на {mail}")
    except Exception as e:
        logger.error(f"Ошибка отправки письма на {mail}: {e}")
        raise  # Пробрасываем исключение для обработки в вызывающем коде
    finally:
        await smtp_client.quit()

async def start_verify_mail(mail: str, user_id: int) -> None:
    """Запускает процесс верификации email."""
    token = generate_verification_token()
    users_token[user_id] = (token, time())
    await send_verification_mail(mail, token)
    logger.debug(f"Токен для user_id={user_id}: {token}")

def check_verify_code(code: str, user_id: int) -> bool:
    if user_id in users_token:
        token, timestamp = users_token[user_id]
        if time() - timestamp > TOKEN_TIMEOUT:
            del users_token[user_id]
            logger.warning(f"Токен для user_id={user_id} истек")
            return False
        if token == code:
            del users_token[user_id]
            logger.info(f"Код верификации для user_id={user_id} подтвержден")
            return True
    logger.warning(f"Неверный код или токен истек для user_id={user_id}")
    return False