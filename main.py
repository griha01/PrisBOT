import asyncio
import re
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

# ================= НАСТРОЙКИ =================
TOKEN = "6021062306:AAHTS2uu15SPOCb5RxKhYVLTHldi6fAOn3A"
DELAY_SECONDS = 1.0
# =============================================

# Оружие (для определения строк с ударами)
WEAPONS = ['яд', 'самопал', 'пал', 'финка', 'фин', 'финки']

# Типы ударов для расчета
HIT_TYPES = {
    'ухо': 'head', 'колено': 'head',
    'пах': 'groin',
    'глаза': 'eyes', 'глаз': 'eyes',
    'грудь': 'chest', 'удар в грудь': 'chest'
}

# Списки имен для категоризации
CAT_BESPREDEL = ['сизый', 'махно', 'лютый', 'шайба']
CAT_VERTUKHAI = ['палыч', 'циклоп', 'бес', 'паленый', 'борзов', 'бурят', 'хирург', 'раиса', 'близнецы', 'дюбель']

# Объединенный список всех имен для поиска в тексте
ALL_BOSS_NAMES = CAT_BESPREDEL + CAT_VERTUKHAI

# Словарь для красивого форматирования режимов
MODES_MAP = {
    'пац': '(Пацанский)',
    'блат': '(Блатной)',
    'авто': '(Авторитетный)'
}

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

user_buffers = {}


def clean_line(text):
    """
    Очищает строку от цифр и нумерации в начале.
    '1. Грудь' -> 'грудь'
    '1 грудь' -> 'грудь'
    """
    # Удаляем цифры, точки, скобки, тире в начале строки
    text = re.sub(r'^[\d\.\)\-\s]+', '', text)
    return text.strip().lower()


def identify_category(boss_name):
    """Определяет категорию (Беспредельщик или Вертухай)"""
    name_lower = boss_name.lower()
    for name in CAT_BESPREDEL:
        if name in name_lower: return 'bespredel'
    for name in CAT_VERTUKHAI:
        if name in name_lower: return 'vertuhai'
    return 'other'


def parse_boss_header(line):
    """
    Пытается понять, является ли строка заголовком босса.
    Возвращает красивое имя или None.
    Примеры:
    'Сизый пац ☠️' -> 'Сизый (Пацанский)'
    'Босс: Бес (Авто)' -> 'Бес (Авторитетный)'
    """
    line_lower = line.lower()

    # 1. Ищем имя босса в строке
    found_name = None
    for name in ALL_BOSS_NAMES:
        # Проверяем, есть ли имя босса как отдельное слово или в составе
        if name in line_lower:
            found_name = name.capitalize()  # Делаем с большой буквы
            break

    if not found_name:
        return None

    # 2. Ищем режим (пац, блат, авто)
    found_mode = ""
    for key, value in MODES_MAP.items():
        if key in line_lower:
            found_mode = value
            break

    # Если режим не нашли, но строка явно содержит "Босс:", оставляем как есть
    if not found_mode and "босс" not in line_lower:
        # Если это просто имя босса (например "Сизый") и это не похоже на удар,
        # то считаем заголовком без режима, если в строке нет слов-ударов
        is_hit = any(w in line_lower for w in WEAPONS + list(HIT_TYPES.keys()))
        if is_hit:
            return None  # Это строка с ударом, где случайно упомянули босса (редко, но бывает)

    return f"{found_name} {found_mode}".strip()


def parse_and_calculate(text):
    lines = text.split('\n')
    parsed_data = []

    current_boss_name = None
    restore_cost = 0
    used_hits = {}
    current_moves_list = []

    def save_current_boss():
        if current_boss_name:
            category = identify_category(current_boss_name)
            parsed_data.append({
                'name': current_boss_name,
                'cost': restore_cost,
                'category': category,
                'combo': current_moves_list
            })

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped: continue

        # 1. Проверяем, является ли строка Боссом (новый метод)
        boss_header = parse_boss_header(line_stripped)

        if boss_header:
            save_current_boss()
            current_boss_name = boss_header
            restore_cost = 0
            used_hits = {}
            current_moves_list = []
            continue

        # 2. Обрабатываем удары
        if current_boss_name:
            move = clean_line(line_stripped)

            is_weapon = move in WEAPONS
            is_hit = HIT_TYPES.get(move) is not None

            if is_weapon or is_hit:
                current_moves_list.append(move)

                # Считаем деньги (только удары)
                if not is_weapon and is_hit:
                    hit_type = HIT_TYPES.get(move)
                    if used_hits.get(hit_type, 0) > 0:
                        restore_cost += 3
                    else:
                        used_hits[hit_type] = 1
                    used_hits[hit_type] += 1

    save_current_boss()
    return parsed_data


def format_response(data):
    if not data: return None

    # Группировка
    bespredel_list = [x for x in data if x['category'] == 'bespredel']
    vertuhai_list = [x for x in data if x['category'] == 'vertuhai']
    other_list = [x for x in data if x['category'] == 'other']

    # Сортировка по цене
    bespredel_list.sort(key=lambda x: x['cost'])
    vertuhai_list.sort(key=lambda x: x['cost'])
    other_list.sort(key=lambda x: x['cost'])

    response_lines = []

    def add_section(title, items):
        if items:
            response_lines.append(f"<b>{title}</b>")
            for item in items:
                combo_text = " ".join(item['combo'])
                line = (
                    f"⚡️ {item['name']} — <b>{item['cost']} руб.</b>\n"
                    f"<tg-spoiler><code>{combo_text}</code></tg-spoiler>"
                )
                response_lines.append(line)
            response_lines.append("")

    add_section("👹 Беспредельщики:", bespredel_list)
    add_section("👮‍♂️ Вертухаи:", vertuhai_list)
    add_section("❓ Остальные:", other_list)

    return "\n".join(response_lines).strip()


async def process_buffered_message(chat_id: int):
    await asyncio.sleep(DELAY_SECONDS)
    if chat_id not in user_buffers: return

    data = user_buffers.pop(chat_id)
    try:
        calculated_data = parse_and_calculate(data["text"])
        final_text = format_response(calculated_data)

        if final_text:
            await bot.send_message(chat_id, final_text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error: {e}")


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я готов обрабатывать любые форматы комбо.")


@dp.message()
async def handle_message(message: Message):
    chat_id = message.chat.id
    text = message.text or message.caption or ""
    if not text: return

    if chat_id in user_buffers:
        user_buffers[chat_id]["task"].cancel()
        user_buffers[chat_id]["text"] += "\n" + text
    else:
        user_buffers[chat_id] = {"text": text, "task": None}

    user_buffers[chat_id]["task"] = asyncio.create_task(process_buffered_message(chat_id))


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())