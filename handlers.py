import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from config import ADMINS, CHANNELS, CHAT_RULES, INFO_TEXT, WARNINGS_ENABLED, STANDART_COUNT, ADMIN_PANEL_MENU_TX, ADMIN_PANEL_START_IFNOADMIN_TX, LS_SPAM_FALSE_TX, LS_SPAM_TRUE_TX, ADMIN_PANEL_NOLOGS_TX, GROUP_SPAM_WARN_TX, GROUP_SPAM_TX, GROUP_SPAM_BAN_TX  
from states import AdminStates
from keyboards import admin_panel
from detector import SpamDetector
from warnings_ import WarningManager

logger = logging.getLogger(__name__)

def register_handlers(dp: Dispatcher, bot: Bot, detector: SpamDetector, warn_mgr: WarningManager):
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        if message.from_user.id in ADMINS:
            await message.answer(ADMIN_PANEL_MENU_TX, reply_markup=admin_panel)
        else:
            await message.answer(ADMIN_PANEL_START_IFNOADMIN_TX)

    @dp.message(Command("info"))
    async def cmd_info(message: types.Message):
        await message.answer(INFO_TEXT)

    @dp.channel_post()
    async def handle_channel_post(message: types.Message):
        if message.chat.id in CHANNELS:
            try:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=CHAT_RULES,
                    reply_to_message_id=message.message_id
                )
                logger.info(f"Отправлены правила под постом: {message.message_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки правил: {e}")

    @dp.message()
    async def filter_messages(message: types.Message):
        if message.sender_chat and message.sender_chat.id not in CHANNELS:
            logger.info(f"Игнор анонимное сообщение от {message.sender_chat.title} ({message.sender_chat.id})")
            return

        if message.sender_chat and message.sender_chat.id in CHANNELS:
            try:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=CHAT_RULES,
                    reply_to_message_id=message.message_id
                )
                logger.info(f"Ответ на сообщение от канала {message.sender_chat.title} правилами.")
            except Exception as e:
                logger.error(f"Ошибка отправки правил: {e}")
            return

        if not message.text or not message.from_user:
            return

        user_id = message.from_user.id
        username = message.from_user.username or "unknown"
        is_spam, probs = detector.predict(message.text)
        logger.info(f"Проверка сообщения от @{username}: спам={is_spam} ({probs})")

        # ЛС
        if message.chat.type == 'private':
            await message.answer(LS_SPAM_TRUE_TX if is_spam else LS_SPAM_FALSE_TX)
            return

        # Группа
        if is_spam and not warn_mgr.is_banned(user_id):
            try:
                if message.chat.type in ['group', 'supergroup']:
                    count = warn_mgr.log_violation(user_id, username, message.text)
                    max_warnings = warn_mgr.get_user(user_id).get("max_warnings", STANDART_COUNT)

                    if WARNINGS_ENABLED and count < max_warnings:
                        await message.answer(
                            f"@{username}, {GROUP_SPAM_TX} "
                            f"{GROUP_SPAM_WARN_TX} {count}/{max_warnings}."
                        )
                        await message.delete()
                        return

                    await bot.restrict_chat_member(
                        chat_id=message.chat.id,
                        user_id=user_id,
                        permissions=types.ChatPermissions(
                            can_send_messages=False,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_add_web_page_previews=False
                        )
                    )
                    warn_mgr.ban_user(user_id)
                    await message.answer(f"@{username} {GROUP_SPAM_BAN_TX}")

                    for admin_id in ADMINS:
                        try:
                            await bot.send_message(
                                admin_id,
                                f"🚫 Пользователь @{username} (ID: {user_id}) был ограничен за спам.\nСообщение:\n{message.text}"
                            )
                        except Exception as e:
                            logger.warning(f"Не удалось уведомить админа {admin_id}: {e}")
                else:
                    logger.warning("Ограничение возможно только в группах.")
            except Exception as e:
                logger.error(f"Ошибка при ограничении пользователя: {e}")



    @dp.callback_query()
    async def process_callback(callback: types.CallbackQuery, state: FSMContext):
        if callback.from_user.id not in ADMINS:
            await callback.answer(ADMIN_PANEL_START_IFNOADMIN_TX)
            return

        data = callback.data
        if data == "logs":
            logs = warn_mgr.get_logs()
            if not logs:
                await callback.message.edit_text(ADMIN_PANEL_NOLOGS_TX)
            else:
                text = "Логи:\n"
                for uid, info in logs.items():
                    status = "Забанен" if info.get("banned") else "Активен"
                    msg_list = "\n  - ".join(info["messages"])
                    text += f"ID {uid} (@{info['username']}): {info['count']}/{info['max_warnings']} | {status}\n  - {msg_list}\n\n"
                await callback.message.edit_text(text[:4096])

        await callback.answer()

    @dp.message(AdminStates.waiting_for_unban)
    async def process_unban(message: types.Message, state: FSMContext):
        await _process_ban_action(bot, message, state, warn_mgr, unban=True)

    @dp.message(AdminStates.waiting_for_ban)
    async def process_ban(message: types.Message, state: FSMContext):
        await _process_ban_action(bot, message, state, warn_mgr, unban=False)


async def _process_ban_action(bot: Bot, message: types.Message, state: FSMContext, warn_mgr: WarningManager, unban: bool):
    input_text = message.text.strip()
    warnings = warn_mgr.get_logs()
    chat_id = message.chat.id

    if input_text.startswith('@'):
        username = input_text[1:]
        user_id = next((uid for uid, data in warnings.items() if data["username"] == username), None)
    else:
        user_id = input_text

    if not user_id or user_id not in warnings:
        await message.answer(f"Пользователь {input_text} не найден.")
    else:
        try:
            user_id_int = int(user_id)
            if unban:
                await bot.unban_chat_member(chat_id=chat_id, user_id=user_id_int)
                warn_mgr.unban_user(user_id_int)
                await message.answer(f"@{warnings[user_id]['username']} разбанен.")
            else:
                await bot.ban_chat_member(chat_id=chat_id, user_id=user_id_int)
                warn_mgr.ban_user(user_id_int)
                await message.answer(f"@{warnings[user_id]['username']} забанен.")
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
            logger.error(f"Ошибка при {'разбане' if unban else 'бане'}: {e}")

    await state.clear()
