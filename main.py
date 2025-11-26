import asyncio
import re
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message

# ================= НАСТРОЙКИ =================
TOKEN = "6021062306:AAHTS2uu15SPOCb5RxKhYVLTHldi6fAOn3A"
# =============================================

# Список оружия (для того, чтобы отличать их от мусора, но цену не считаем)
WEAPONS = [
    'яд', 'самопал', 'пал', 'финка', 'фин', 'финки'
]

# Типы ударов для группировки (первый бесплатно, повтор +3р)
HIT_TYPES = {
    'ухо': 'head', 'колено': 'head',
    'пах': 'groin',
    'глаза': 'eyes', 'глаз': 'eyes',
    'грудь': 'chest', 'удар в грудь': 'chest'
}

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)


def clean_line(text):
    """Убирает нумерацию и лишние символы"""
    text = re.sub(r'^\d+[\.\)\-]\s*', '', text)
    return text.strip().lower()


def calculate_restoration(text):
    """Парсит текст и считает ТОЛЬКО стоимость восстановления"""
    lines = text.split('\n')
    results = []

    current_boss_name = None
    restore_cost = 0
    used_hits = {}  # Отслеживание повторов

    def save_current_boss():
        if current_boss_name:
            # Формируем строку результата
            results.append(f"⚡️ <b>{current_boss_name}</b>: <code>{restore_cost}₽</code>")

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 1. Ищем Босса
        boss_match = re.search(r'Босс:\s*(.+)', line_stripped, re.IGNORECASE)

        if boss_match:
            save_current_boss()  # Сохраняем предыдущего

            # Сброс для нового
            current_boss_name = boss_match.group(1).strip()
            restore_cost = 0
            used_hits = {}
            continue

        # 2. Считаем удары
        if current_boss_name:
            move = clean_line(line_stripped)

            # Если это оружие — пропускаем (цена не нужна)
            if move in WEAPONS:
                continue

            # Если это удар — проверяем повторы
            hit_type = HIT_TYPES.get(move)
            if hit_type:
                # Если уже били в эту точку -> платим за восстановление
                if used_hits.get(hit_type, 0) > 0:
                    restore_cost += 3
                else:
                    # Первый удар бесплатно
                    used_hits[hit_type] = 1

                used_hits[hit_type] += 1

    # Сохраняем последнего
    save_current_boss()

    return results


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Пришли мне список комбо.\n"
        "Я посчитаю <b>только стоимость восстановления</b> энергии (по 3₽ за повторный удар)."
    )


@dp.message()
async def process_combo_text(message: Message):
    text = message.text or message.caption
    if not text:
        return

    try:
        results = calculate_restoration(text)

        if results:
            response = "<b>⚡️ Стоимость восстановления:</b>\n\n" + "\n".join(results)
            await message.answer(response, parse_mode="HTML")
        # Если боссы не найдены - бот молчит

    except Exception as e:
        logging.error(f"Error: {e}")


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())