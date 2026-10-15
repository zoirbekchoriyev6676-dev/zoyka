# pyrefly: ignore [missing-import]
from aiogram import Router, F
# pyrefly: ignore [missing-import]
from aiogram.types import Message, CallbackQuery
# pyrefly: ignore [missing-import]
from aiogram.filters import Command
from bot.database import BotDB
from bot.keyboards import get_groups_keyboard, get_group_menu_keyboard, get_back_to_menu_keyboard

router = Router()

@router.message(Command("start", "help"))
async def cmd_start(message: Message):
    """Start yoki help buyrug'i."""
    groups = BotDB.get_active_groups()
    if not groups:
        await message.answer("Tizimda hozircha faol guruhlar mavjud emas.")
        return

    kb = get_groups_keyboard(groups)
    await message.answer(
        "👋 *Assalomu alaykum! AI Exam Report Botiga xush kelibsiz.*\n\n"
        "Qaysi guruhning hisobotini bilmoqchisiz?\n"
        "Quyidagi ro'yxatdan kerakli guruhni tanlang:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@router.message(F.text & ~F.text.startswith("/"))
async def handle_any_text(message: Message):
    """
    3.1-qadam: Foydalanuvchi ixtiyoriy matn (salom, qale va h.k.) yozganda
    faol guruhlar ro'yxatini Inline tugma shaklida chiqaradi.
    """
    groups = BotDB.get_active_groups()
    if not groups:
        await message.answer("Tizimda hozircha faol guruhlar mavjud emas.")
        return

    kb = get_groups_keyboard(groups)
    await message.answer(
        "Qaysi guruhning hisobotini bilmoqchisiz?",
        reply_markup=kb
    )

@router.callback_query(F.data == "back_to_groups")
async def cb_back_to_groups(callback: CallbackQuery):
    """Guruhlar ro'yxatiga qaytish."""
    groups = BotDB.get_active_groups()
    kb = get_groups_keyboard(groups)
    await callback.message.edit_text(
        "Qaysi guruhning hisobotini bilmoqchisiz?",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("menu_"))
async def cb_menu(callback: CallbackQuery):
    """Guruhning 3 ta tahlil menyusiga qaytish."""
    try:
        group_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("Noto'g'ri guruh identifikatori.", show_alert=True)
        return

    group = BotDB.get_group_by_id(group_id)
    if not group:
        await callback.answer("Guruh topilmadi.", show_alert=True)
        return

    kb = get_group_menu_keyboard(group_id)
    await callback.message.edit_text(
        f"📋 *{group['group_name']} Guruhi bo'yicha hisobot menyusi:*\n\n"
        f"Kerakli hisobot turini tanlang:",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.regexp(r"^group_\d+$"))
async def cb_group_select(callback: CallbackQuery):
    """
    3.2-qadam: Guruh holatini tekshirish (Status Verification)
    - Agar status != 'published' bo'lsa: "Natijalar hali admin tarafidan e'lon qilinmagan."
    - Agar status == 'published' bo'lsa: 3 ta asosiy hisobot tugmasi ko'rsatiladi.
    """
    group_id = int(callback.data.split("_")[1])
    group = BotDB.get_group_by_id(group_id)

    if not group:
        await callback.answer("Guruh topilmadi.", show_alert=True)
        return

    status = (group.get("status") or "").lower()

    if status != "published":
        # Ogohlantirish xabari (protsess shu yerda to'xtaydi)
        await callback.answer(
            "👉 Natijalar hali admin tarafidan e'lon qilinmagan.",
            show_alert=True
        )
        return

    # 3.3-qadam: Tahlillar menyusini chiqarish
    kb = get_group_menu_keyboard(group_id)
    await callback.message.edit_text(
        f"✅ *{group['group_name']} Guruhi Imtihoni Yakunlangan!*\n\n"
        f"Natijalar e'lon qilingan. Quyidagi bo'limlardan birini tanlang:",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("res_"))
async def cb_group_results(callback: CallbackQuery):
    """
    4.1-qadam: Guruh natijalari tugmasi bosilganda
    O'quvchilar ro'yxati va ularning ballarini chiroyli formatda yuborish.
    """
    group_id = int(callback.data.split("_")[1])
    group = BotDB.get_group_by_id(group_id)
    group_name = group["group_name"] if group else f"Guruh #{group_id}"

    results = BotDB.get_group_results(group_id)
    kb = get_back_to_menu_keyboard(group_id)

    if not results:
        text = f"📊 *{group_name} Guruhi Natijalari*\n\nHozircha topshirilgan natijalar mavjud emas."
    else:
        text = f"📊 *{group_name} Guruhi Imtihon Natijalari:*\n\n"
        for i, r in enumerate(results, 1):
            score = r.get("score", 0.0)
            score_emoji = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
            text += f"{i}. {score_emoji} *{r['student_name']}* — `{score}%`\n"

        avg_score = round(sum(r.get("score", 0.0) for r in results) / len(results), 1)
        text += f"\n━━━━━━━━━━━━━━━\n"
        text += f"👥 Jami o'quvchilar: *{len(results)}* nafar\n"
        text += f"📈 O'rtacha ko'rsatkich: *{avg_score}%*"

    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("ai_g_"))
async def cb_group_ai(callback: CallbackQuery):
    """
    4.2-qadam: Guruh AI tahlili tugmasi bosilganda
    Bazadan saqlangan sun'iy intellekt tahlili matnini yuborish.
    """
    group_id = int(callback.data.split("_")[2])
    ai_text = BotDB.get_group_ai_analysis(group_id)
    kb = get_back_to_menu_keyboard(group_id)

    await callback.message.edit_text(ai_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("ai_s_"))
async def cb_school_ai(callback: CallbackQuery):
    """
    4.3-qadam: Maktab tahlili tugmasi bosilganda
    Guruh tegishli bo'lgan maktabning umumiy AI tahlilini yuborish.
    """
    group_id = int(callback.data.split("_")[2])
    school_text = BotDB.get_school_ai_analysis(group_id)
    kb = get_back_to_menu_keyboard(group_id)

    await callback.message.edit_text(school_text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()
