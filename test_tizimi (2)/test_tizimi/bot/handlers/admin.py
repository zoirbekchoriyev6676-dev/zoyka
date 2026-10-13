from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from bot.database import BotDB

router = Router()

@router.message(Command("publish"))
async def cmd_publish(message: Message):
    """
    5-qadam: Admin buyrug'i (/publish {group_id})
    Guruh statusini 'published' ga o'zgartiradi va AI tahlillarini sinxronlaydi.
    """
    sender_id = message.from_user.id if message.from_user else 0
    if not BotDB.is_admin(sender_id):
        await message.answer(
            "⛔ *Ruxsat berilmadi!*\n\n"
            "Ushbu buyruq faqat tizim administratori uchun mo'ljallangan.",
            parse_mode="Markdown"
        )
        return

    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ Foydalanish: `/publish {group_id}`\n\n"
            "Misol: `/publish 1`",
            parse_mode="Markdown"
        )
        return

    try:
        group_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Guruh ID raqam bo'lishi kerak. Misol: `/publish 1`", parse_mode="Markdown")
        return

    success = BotDB.publish_group(group_id)
    if success:
        group = BotDB.get_group_by_id(group_id)
        g_name = group["group_name"] if group else f"#{group_id}"
        await message.answer(
            f"✅ *{g_name} Guruhi muvaffaqiyatli e'lon qilindi!*\n\n"
            f"• Guruh statusi: `published`\n"
            f"• Imtihon natijalari saqlandi va talabalarga ko'rish ochildi.\n"
            f"• Endi bot foydalanuvchilari ushbu guruh hisoboti va AI tahlilini ko'rishlari mumkin.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(f"❌ #{group_id} raqamli guruh topilmadi.")
