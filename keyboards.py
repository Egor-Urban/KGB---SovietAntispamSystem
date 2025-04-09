from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_PANEL_LOG_BTN

admin_panel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=ADMIN_PANEL_LOG_BTN, callback_data="logs")],
])
