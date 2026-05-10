from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Channels"), KeyboardButton(text="Transfer")],
            [KeyboardButton(text="Parsers"), KeyboardButton(text="Runtime")],
            [KeyboardButton(text="Settings"), KeyboardButton(text="Logs")],
        ],
        resize_keyboard=True,
    )


def channels_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Add", callback_data="channels:add")
    builder.button(text="📋 List", callback_data="channels:list")
    builder.button(text="🗑 Delete", callback_data="channels:delete")
    builder.button(text="🔁 Toggle", callback_data="channels:toggle")
    builder.adjust(2, 2)
    return builder.as_markup()


def parser_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Start", callback_data="parser:start")
    builder.button(text="⏸ Pause", callback_data="parser:pause")
    builder.button(text="🔄 Restart", callback_data="parser:restart")
    builder.button(text="📊 Stats", callback_data="parser:stats")
    builder.button(text="🧵 Queue", callback_data="parser:queue")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def transfer_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Start", callback_data="transfer:start")
    builder.button(text="📡 Live", callback_data="transfer:live")
    builder.button(text="⏸ Pause", callback_data="transfer:pause")
    builder.button(text="⏯ Resume", callback_data="transfer:resume")
    builder.button(text="⛔ Cancel", callback_data="transfer:cancel")
    builder.button(text="📈 Progress", callback_data="transfer:progress")
    builder.adjust(2, 2, 2)
    return builder.as_markup()


def settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👁 Show", callback_data="settings:show")
    builder.button(text="🔁 Replacer", callback_data="settings:replacer")
    builder.button(text="🚫 Deny words", callback_data="settings:deny")
    builder.button(text="😀 Reactions", callback_data="settings:reactions")
    builder.button(text="⏱ Delays", callback_data="settings:delays")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def logs_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🧾 Latest", callback_data="logs:latest")
    builder.button(text="📡 Live", callback_data="logs:live")
    builder.button(text="📤 Export", callback_data="logs:export")
    builder.adjust(2, 1)
    return builder.as_markup()
