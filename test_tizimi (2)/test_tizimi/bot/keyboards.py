# pyrefly: ignore [missing-import]
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def get_groups_keyboard(groups: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Barcha faol guruhlar uchun Inline tugmalar ro'yxati."""
    buttons = []
    # Tugmalarni 2 tadan qator qilib joylashtiramiz
    row = []
    for g in groups:
        g_name = g.get("group_name", f"Guruh {g['id']}")
        status = g.get("status", "not_started")
        status_icon = "🟢" if status == "published" else ("🟡" if status == "ongoing" else "⚪")
        btn = InlineKeyboardButton(
            text=f"{status_icon} {g_name}",
            callback_data=f"group_{g['id']}"
        )
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_group_menu_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """Natijalari e'lon qilingan guruh uchun 3 ta asosiy hisobot tugmasi."""
    buttons = [
        [InlineKeyboardButton(text="📊 Guruh natijalari", callback_data=f"res_{group_id}")],
        [InlineKeyboardButton(text="🤖 Guruh AI tahlili", callback_data=f"ai_g_{group_id}")],
        [InlineKeyboardButton(text="🏫 Maktab tahlili", callback_data=f"ai_s_{group_id}")],
        [InlineKeyboardButton(text="⬅️ Boshqa guruhni tanlash", callback_data="back_to_groups")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_menu_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """Hisobot ko'rilgandan keyin guruh menyusiga qaytish tugmasi."""
    buttons = [
        [InlineKeyboardButton(text="⬅️ Guruh menyusiga qaytish", callback_data=f"menu_{group_id}")],
        [InlineKeyboardButton(text="📋 Guruhlar ro'yxatiga qaytish", callback_data="back_to_groups")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
