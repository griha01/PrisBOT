import asyncio
import re
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

# ================= НАСТРОЙКИ =================
TOKEN = "ВАШ_ТОКЕН"
DELAY_SECONDS = 1.0  # Время ожидания следующего сообщения (в секундах)
# =============================================

# Словари данных (как в прошлом коде)
WEAPONS = ['яд', 'самопал', 'пал', 'финка', 'фин', 'финки']
HIT_TYPES = {
    'ухо': 'head', 'колено': 'head',
    'пах': 'groin',
    'глаза': 'eyes', 'глаз': 'eyes',
    'грудь': 'chest', 'удар в грудь': 'chest'
}

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# Хранилище для буферизации сообщений
# Структура: { chat_id: { "text": "накопленный текст", "task": asyncio.Task } }
user_buffers = {}


def clean_line(text):
    text = re.sub(r'^\d+[\.\)\-]\s*', '', text)
    return text.strip().lower()


def calculate_restoration(text):
    """Логика подсчета (только восстановление)"""
    lines = text.split('\n')
    results = []

    current_boss_name = None
    restore_cost = 0
    used_hits = {}

    def save_current_boss():
        if current_boss_name:
            results.append(f"⚡️ <b>{current_boss_name}</b>: <code>{restore_cost}₽</code>")

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped: continue

        boss_match = re.search(r'Босс:\s*(.+)', line_stripped, re.IGNORECASE)
        if boss_match:
            save_current_boss()
            current_boss_name = boss_match.group(1).strip()
            restore_cost = 0
            used_hits = {}
            continue

        if current_boss_name:
            move = clean_line(line_stripped)
            if move in WEAPONS: continue

            hit_type = HIT_TYPES.get(move)
            if hit_type:
                if used_hits.get(hit_type, 0) > 0:
                    restore_cost += 3
                else:
                    used_hits[hit_type] = 1
                used_hits[hit_type] += 1

    save_current_boss()
    return results


async def process_buffered_message(chat_id: int):
    """Функция, которая запускается после таймера"""
    await asyncio.sleep(DELAY_SECONDS)

    # Если задача была отменена (пришло новое сообщение), код ниже не выполнится
    # Но на всякий случай проверим наличие данных
    if chat_id not in user_buffers:
        return

    data = user_buffers.pop(chat_id)  # Забираем данные и удаляем из буфера
    full_text = data["text"]

    try:
        results = calculate_restoration(full_text)
        if results:
            response = "<b>⚡️ Итоговая стоимость восстановления:</b>\n\n" + "\n".join(results)
            await bot.send_message(chat_id, response, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка обработки: {e}")


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Пересылай сообщения, я объединю их и посчитаю.")


@dp.message()
async def handle_message(message: Message):
    chat_id = message.chat.id
    text = message.text or message.caption or ""

    if not text: return

    # Если для этого юзера уже есть таймер - отменяем его
    if chat_id in user_buffers:
        existing_task = user_buffers[chat_id]["task"]
        if existing_task:
            existing_task.cancel()

        # Добавляем новый текст к старому через перенос строки
        user_buffers[chat_id]["text"] += "\n" + text
    else:
        # Создаем новую запись
        user_buffers[chat_id] = {"text": text, "task": None}

    # Создаем новую задачу (таймер)
    task = asyncio.create_task(process_buffered_message(chat_id))
    user_buffers[chat_id]["task"] = task


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())