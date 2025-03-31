from mailbox import Message

from aiogram import Router

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.orm_query import orm_add_news, orm_edit_news_by_id, orm_get_all_user

news_channel_router = Router()


@news_channel_router.channel_post()
async def channel_post_handler(post: Message, session: AsyncSession):
    if post.photo:
        if post.caption:
            await orm_add_news(session=session, post_id=post.message_id,
                               text=post.caption,
                               photo=post.photo[-1].file_id)
            if "#Важное" in post.caption:
                all_users = await orm_get_all_user(session)
                for user in all_users:
                    await post.bot.forward_message(chat_id=user, from_chat_id=post.chat.id, message_id=post.message_id)
        else:
            await orm_add_news(session=session, post_id=post.message_id,
                               text="Без текста",
                               photo=post.photo[-1].file_id)
    else:
        await orm_add_news(session=session, post_id=post.message_id ,
                           text=post.text,
                           photo="Без фото")

@news_channel_router.edited_channel_post()
async def edited_channel_post_handler(post: Message, session: AsyncSession):

    if post.photo:
        if post.caption:
            await orm_edit_news_by_id(session=session, post_id=post.message_id,
                                      text=post.caption,
                                      photo=post.photo[-1].file_id)
        else:
            await orm_edit_news_by_id(session=session, post_id=post.message_id,
                               text="Без текста",
                               photo=post.photo[-1].file_id)
    else:
        await orm_edit_news_by_id(session=session, post_id=post.message_id ,
                           text=post.text,
                           photo="Без фото")
