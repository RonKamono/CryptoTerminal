import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.storage.memory import MemoryStorage

from utils.send_logic import TradingDB, send_to_bot, get_actual_position
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (замените на свой)
API_TOKEN = '8218318461:AAE6t5wlDAI9wu0bpst6iNt6Ec6Ir1k8xpo'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
db = TradingDB('trading.db')


# Состояния FSM
class PositionStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_percent = State()
    waiting_for_take_profit = State()
    waiting_for_stop_loss = State()
    waiting_for_position_type = State()
    waiting_for_edit_choice = State()
    waiting_for_edit_value = State()


# Клавиатуры
def get_main_keyboard():
    """Главная клавиатура"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить позицию")],
            [KeyboardButton(text="📋 Список позиций"), KeyboardButton(text="🔍 Найти позицию")],
            [KeyboardButton(text="📊 Актуальные позиции"), KeyboardButton(text="❌ Закрыть позицию")],
            [KeyboardButton(text="⚙️ Редактировать позицию"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )


def get_position_type_keyboard():
    """Клавиатура для выбора типа позиции"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📈 LONG"), KeyboardButton(text="📉 SHORT")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_yes_no_keyboard():
    """Клавиатура Да/Нет"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_edit_keyboard():
    """Клавиатура для выбора поля редактирования"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Изменить имя")],
            [KeyboardButton(text="📊 Изменить процент")],
            [KeyboardButton(text="🎯 Изменить Take Profit")],
            [KeyboardButton(text="🛡 Изменить Stop Loss")],
            [KeyboardButton(text="🔄 Изменить тип позиции")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Что хотите изменить?"
    )


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = """
    🤖 *Торговый бот для управления позициями*

    *Доступные команды:*
    /start - Начать работу с ботом
    /add - Добавить новую позицию
    /list - Показать все позиции
    /active - Показать активные позиции
    /find - Найти позицию по имени
    /help - Показать справку

    *Или используйте кнопки ниже:*
    """

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


# Команда /help
@dp.message(Command("help"))
@dp.message(F.text == "❓ Помощь")
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """
    *📖 Руководство по использованию бота:*

    *Добавление позиции:*
    1. Нажмите "➕ Добавить позицию"
    2. Введите название актива (только буквы)
    3. Введите процент от баланса (1-100%)
    4. Введите Take Profit цену
    5. Введите Stop Loss цену
    6. Выберите тип позиции (LONG/SHORT)

    *Проверка логики:*
    - Для LONG: Take Profit > Stop Loss
    - Для SHORT: Take Profit < Stop Loss

    *Просмотр позиций:*
    - "📋 Список позиций" - все позиции
    - "📊 Актуальные позиции" - только активные
    - "🔍 Найти позицию" - поиск по имени

    *Управление позициями:*
    - "⚙️ Редактировать позицию" - изменить параметры
    - "❌ Закрыть позицию" - деактивировать позицию

    *База данных:* `C:\\DataBase\\trading.db`
    """

    await message.answer(help_text, parse_mode="Markdown")


# Команда /add или кнопка "Добавить позицию"
@dp.message(Command("add"))
@dp.message(F.text == "➕ Добавить позицию")
async def add_position_start(message: types.Message, state: FSMContext):
    """Начало процесса добавления позиции"""
    await state.set_state(PositionStates.waiting_for_name)
    await message.answer(
        "📝 *Введите название актива:*\n"
        "(Только буквы, например: Apple, Tesla, Bitcoin)",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )


# Отмена операции
@dp.message(F.text == "🔙 Назад")
async def cancel_operation(message: types.Message, state: FSMContext):
    """Отмена текущей операции"""
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer(
        "❌ Операция отменена.",
        reply_markup=get_main_keyboard()
    )


# Шаг 1: Получение имени
@dp.message(PositionStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    """Обработка имени актива"""
    name = message.text.strip()

    # Валидация имени
    if not name.replace(' ', '').isalpha():
        await message.answer(
            "❌ *Неверное имя!*\n"
            "Имя должно содержать только буквы и пробелы.\n"
            "Попробуйте снова:",
            parse_mode="Markdown"
        )
        return

    await state.update_data(name=name)
    await state.set_state(PositionStates.waiting_for_percent)

    await message.answer(
        f"✅ Имя принято: *{name}*\n\n"
        "📊 *Введите процент от баланса (1-100%):*",
        parse_mode="Markdown"
    )


# Шаг 2: Получение процента
@dp.message(PositionStates.waiting_for_percent)
async def process_percent(message: types.Message, state: FSMContext):
    """Обработка процента"""
    try:
        percent = int(message.text)

        if not 1 <= percent <= 100:
            await message.answer(
                "❌ *Неверный процент!*\n"
                "Процент должен быть от 1 до 100.\n"
                "Попробуйте снова:",
                parse_mode="Markdown"
            )
            return

        await state.update_data(percent=percent)
        await state.set_state(PositionStates.waiting_for_take_profit)

        await message.answer(
            f"✅ Процент принят: *{percent}%*\n\n"
            "🎯 *Введите цену Take Profit:*",
            parse_mode="Markdown"
        )

    except ValueError:
        await message.answer(
            "❌ *Неверный формат!*\n"
            "Введите число от 1 до 100.\n"
            "Попробуйте снова:",
            parse_mode="Markdown"
        )


# Шаг 3: Получение Take Profit
@dp.message(PositionStates.waiting_for_take_profit)
async def process_take_profit(message: types.Message, state: FSMContext):
    """Обработка Take Profit"""
    try:
        take_profit = float(message.text)

        if take_profit <= 0:
            await message.answer(
                "❌ *Неверная цена!*\n"
                "Take Profit должен быть больше 0.\n"
                "Попробуйте снова:",
                parse_mode="Markdown"
            )
            return

        await state.update_data(take_profit=take_profit)
        await state.set_state(PositionStates.waiting_for_stop_loss)

        await message.answer(
            f"✅ Take Profit принят: *{take_profit}*\n\n"
            "🛡 *Введите цену Stop Loss:*",
            parse_mode="Markdown"
        )

    except ValueError:
        await message.answer(
            "❌ *Неверный формат!*\n"
            "Введите число (например: 150.50).\n"
            "Попробуйте снова:",
            parse_mode="Markdown"
        )


# Шаг 4: Получение Stop Loss
@dp.message(PositionStates.waiting_for_stop_loss)
async def process_stop_loss(message: types.Message, state: FSMContext):
    """Обработка Stop Loss"""
    try:
        stop_loss = float(message.text)

        if stop_loss <= 0:
            await message.answer(
                "❌ *Неверная цена!*\n"
                "Stop Loss должен быть больше 0.\n"
                "Попробуйте снова:",
                parse_mode="Markdown"
            )
            return

        # Получаем данные из состояния
        data = await state.get_data()
        take_profit = data.get('take_profit')

        if take_profit == stop_loss:
            await message.answer(
                "❌ *Ошибка логики!*\n"
                "Take Profit и Stop Loss не могут быть равны.\n"
                "Введите Stop Loss снова:",
                parse_mode="Markdown"
            )
            return

        await state.update_data(stop_loss=stop_loss)
        await state.set_state(PositionStates.waiting_for_position_type)

        await message.answer(
            f"✅ Stop Loss принят: *{stop_loss}*\n\n"
            "📈 *Выберите тип позиции:*",
            parse_mode="Markdown",
            reply_markup=get_position_type_keyboard()
        )

    except ValueError:
        await message.answer(
            "❌ *Неверный формат!*\n"
            "Введите число (например: 140.75).\n"
            "Попробуйте снова:",
            parse_mode="Markdown"
        )


# Шаг 5: Выбор типа позиции
@dp.message(PositionStates.waiting_for_position_type)
async def process_position_type(message: types.Message, state: FSMContext):
    """Обработка типа позиции"""
    text = message.text.lower()

    if text not in ['📈 long', '📉 short', 'long', 'short']:
        await message.answer(
            "❌ *Неверный выбор!*\n"
            "Выберите тип позиции с помощью кнопок:",
            parse_mode="Markdown",
            reply_markup=get_position_type_keyboard()
        )
        return

    # Извлекаем тип из текста кнопки
    if 'long' in text:
        pos_type = 'long'
    else:
        pos_type = 'short'

    # Получаем все данные
    data = await state.get_data()
    name = data.get('name')
    percent = data.get('percent')
    take_profit = data.get('take_profit')
    stop_loss = data.get('stop_loss')

    # Проверка логики
    if pos_type == 'long' and take_profit <= stop_loss:
        await message.answer(
            "❌ *Ошибка логики для LONG!*\n"
            f"Для LONG позиции:\n"
            f"Take Profit ({take_profit}) должен быть > Stop Loss ({stop_loss})\n\n"
            "🔄 Попробуйте выбрать другой тип позиции:",
            parse_mode="Markdown",
            reply_markup=get_position_type_keyboard()
        )
        return
    elif pos_type == 'short' and take_profit >= stop_loss:
        await message.answer(
            "❌ *Ошибка логики для SHORT!*\n"
            f"Для SHORT позиции:\n"
            f"Take Profit ({take_profit}) должен быть < Stop Loss ({stop_loss})\n\n"
            "🔄 Попробуйте выбрать другой тип позиции:",
            parse_mode="Markdown",
            reply_markup=get_position_type_keyboard()
        )
        return

    # Сохраняем тип
    data['pos_type'] = pos_type

    # Показываем сводку
    summary = f"""
    📋 *Сводка позиции:*

    📝 *Название:* {name}
    📊 *Процент:* {percent}%
    🎯 *Take Profit:* {take_profit}
    🛡 *Stop Loss:* {stop_loss}
    📈 *Тип позиции:* {pos_type.upper()}
    """

    # Клавиатура подтверждения
    confirm_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Подтвердить"), KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(summary, parse_mode="Markdown", reply_markup=confirm_keyboard)

    # Сохраняем данные и ждем подтверждения
    await state.set_data(data)
    await state.set_state(PositionStates.waiting_for_edit_choice)


# Подтверждение или отмена создания
@dp.message(PositionStates.waiting_for_edit_choice)
async def confirm_position(message: types.Message, state: FSMContext):
    """Подтверждение создания позиции"""
    if message.text == "✅ Подтвердить":
        # Получаем данные
        data = await state.get_data()

        # Добавляем позицию в БД
        success = send_to_bot(
            name=data['name'],
            percent=data['percent'],
            take_profit=data['take_profit'],
            stop_loss=data['stop_loss'],
            pos_type=data['pos_type']
        )

        if success:
            await message.answer(
                "✅ *Позиция успешно добавлена в базу данных!*\n"
                f"📁 Путь к БД: `C:\\DataBase\\trading.db`",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                "❌ *Не удалось добавить позицию!*\n"
                "Проверьте логи для подробностей.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )

        await state.clear()

    elif message.text == "❌ Отменить":
        await message.answer(
            "❌ *Создание позиции отменено.*",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            "❓ *Подтвердите или отмените создание позиции:*",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ Подтвердить"), KeyboardButton(text="❌ Отменить")]
                ],
                resize_keyboard=True
            )
        )


# Команда /list или кнопка "Список позиций"
@dp.message(Command("list"))
@dp.message(F.text == "📋 Список позиций")
async def list_positions(message: types.Message):
    """Показать все позиции"""
    positions = db.get_all_positions()

    if not positions:
        await message.answer(
            "📭 *База данных пуста.*",
            parse_mode="Markdown"
        )
        return

    response = f"📋 *Все позиции ({len(positions)}):*\n\n"

    for i, pos in enumerate(positions, 1):
        status = "✅ Активна" if pos['is_active'] else "❌ Закрыта"
        response += (
            f"{i}. *{pos['name']}* ({pos['id']})\n"
            f"   Тип: {pos['pos_type'].upper()}\n"
            f"   Процент: {pos['percent']}%\n"
            f"   TP: {pos['take_profit']} | SL: {pos['stop_loss']}\n"
            f"   Статус: {status}\n"
            f"   Создана: {pos['created_at'][:19]}\n\n"
        )

    await message.answer(response, parse_mode="Markdown")


# Команда /active или кнопка "Актуальные позиции"
@dp.message(Command("active"))
@dp.message(F.text == "📊 Актуальные позиции")
async def active_positions(message: types.Message):
    """Показать активные позиции"""
    positions = get_actual_position()  # Используем вашу функцию

    if not positions:
        await message.answer(
            "📭 *Нет активных позиций.*",
            parse_mode="Markdown"
        )
        return

    response = f"📊 *Актуальные позиции ({len(positions)}):*\n\n"

    for i, pos in enumerate(positions, 1):
        response += (
            f"{i}. *{pos['name']}* ({pos['id']})\n"
            f"   Тип: {pos['pos_type'].upper()}\n"
            f"   Процент: {pos['percent']}%\n"
            f"   TP: {pos['take_profit']} | SL: {pos['stop_loss']}\n"
            f"   Создана: {pos['created_at'][:19]}\n\n"
        )

    await message.answer(response, parse_mode="Markdown")


# Команда /find или кнопка "Найти позицию"
@dp.message(Command("find"))
@dp.message(F.text == "🔍 Найти позицию")
async def find_position_start(message: types.Message, state: FSMContext):
    """Начало поиска позиции"""
    await message.answer(
        "🔍 *Введите название актива для поиска:*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🔙 Назад")]],
            resize_keyboard=True
        )
    )
    # Можно использовать состояние для поиска, но в данном случае просто обработаем сразу


@dp.message(F.text.startswith("🔍"))
async def find_position(message: types.Message):
    """Поиск позиции по имени"""
    search_name = message.text.replace("🔍 ", "").strip()

    if not search_name:
        await message.answer(
            "❌ *Введите название для поиска!*",
            parse_mode="Markdown"
        )
        return

    positions = db.get_all_positions_by_name(search_name)

    if not positions:
        await message.answer(
            f"❌ *Позиции с именем '{search_name}' не найдены.*",
            parse_mode="Markdown"
        )
        return

    response = f"🔍 *Найдено позиций '{search_name}' ({len(positions)}):*\n\n"

    for i, pos in enumerate(positions, 1):
        status = "✅ Активна" if pos['is_active'] else "❌ Закрыта"
        response += (
            f"{i}. *{pos['name']}* ({pos['id']})\n"
            f"   Тип: {pos['pos_type'].upper()}\n"
            f"   Процент: {pos['percent']}%\n"
            f"   TP: {pos['take_profit']} | SL: {pos['stop_loss']}\n"
            f"   Статус: {status}\n"
            f"   Создана: {pos['created_at'][:19]}\n\n"
        )

    await message.answer(response, parse_mode="Markdown")


# Кнопка "Закрыть позицию"
@dp.message(F.text == "❌ Закрыть позицию")
async def close_position_start(message: types.Message):
    """Начало закрытия позиции"""
    # Получаем активные позиции
    positions = get_actual_position()

    if not positions:
        await message.answer(
            "📭 *Нет активных позиций для закрытия.*",
            parse_mode="Markdown"
        )
        return

    # Создаем inline-клавиатуру с позициями
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for pos in positions[:10]:  # Ограничиваем 10 позициями
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{pos['name']} ({pos['pos_type'].upper()}) - ID: {pos['id']}",
                callback_data=f"close_{pos['id']}"
            )
        ])

    await message.answer(
        "❌ *Выберите позицию для закрытия:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# Обработчик inline1-кнопок для закрытия
@dp.callback_query(F.data.startswith("close_"))
async def close_position_callback(callback: types.CallbackQuery):
    """Обработка закрытия позиции"""
    position_id = int(callback.data.split("_")[1])

    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE positions SET is_active = 0 WHERE id = ?",
                (position_id,)
            )
            conn.commit()

            # Получаем информацию о позиции
            cursor.execute("SELECT name FROM positions WHERE id = ?", (position_id,))
            position_name = cursor.fetchone()[0]

            await callback.message.answer(
                f"✅ *Позиция '{position_name}' (ID: {position_id}) закрыта!*",
                parse_mode="Markdown"
            )

    except Exception as e:
        await callback.message.answer(
            f"❌ *Ошибка при закрытии позиции:* {e}",
            parse_mode="Markdown"
        )

    await callback.answer()


# Кнопка "Редактировать позицию"
@dp.message(F.text == "⚙️ Редактировать позицию")
async def edit_position_start(message: types.Message):
    """Начало редактирования позиции"""
    positions = get_actual_position()

    if not positions:
        await message.answer(
            "📭 *Нет активных позиций для редактирования.*",
            parse_mode="Markdown"
        )
        return

    # Создаем inline-клавиатуру с позициями
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for pos in positions[:10]:  # Ограничиваем 10 позициями
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{pos['name']} ({pos['pos_type'].upper()})",
                callback_data=f"edit_{pos['id']}"
            )
        ])

    await message.answer(
        "⚙️ *Выберите позицию для редактирования:*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# Обработчик inline-кнопок для редактирования
@dp.callback_query(F.data.startswith("edit_"))
async def edit_position_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора позиции для редактирования"""
    position_id = int(callback.data.split("_")[1])

    # Сохраняем ID позиции в состоянии
    await state.update_data(edit_position_id=position_id)

    # Получаем информацию о позиции
    try:
        with db.connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
            position = dict(cursor.fetchone())

            # Показываем информацию о позиции
            info = f"""
            📝 *Редактирование позиции:*

            ID: {position['id']}
            Название: {position['name']}
            Процент: {position['percent']}%
            Take Profit: {position['take_profit']}
            Stop Loss: {position['stop_loss']}
            Тип: {position['pos_type'].upper()}
            """

            await callback.message.answer(
                info,
                parse_mode="Markdown",
                reply_markup=get_edit_keyboard()
            )

    except Exception as e:
        await callback.message.answer(
            f"❌ *Ошибка при получении информации о позиции:* {e}",
            parse_mode="Markdown"
        )

    await callback.answer()


# Обработка выбора поля для редактирования
@dp.message(F.text.startswith("📝 Изменить") |
            F.text.startswith("📊 Изменить") |
            F.text.startswith("🎯 Изменить") |
            F.text.startswith("🛡 Изменить") |
            F.text.startswith("🔄 Изменить"))
async def choose_edit_field(message: types.Message, state: FSMContext):
    """Выбор поля для редактирования"""
    text = message.text

    # Определяем какое поле редактируем
    field_map = {
        "📝 Изменить имя": "name",
        "📊 Изменить процент": "percent",
        "🎯 Изменить Take Profit": "take_profit",
        "🛡 Изменить Stop Loss": "stop_loss",
        "🔄 Изменить тип позиции": "pos_type"
    }

    if text not in field_map:
        await message.answer(
            "❌ *Неверный выбор!*",
            parse_mode="Markdown",
            reply_markup=get_edit_keyboard()
        )
        return

    field = field_map[text]
    await state.update_data(edit_field=field)

    # Запрашиваем новое значение
    prompts = {
        "name": "📝 *Введите новое название актива:*",
        "percent": "📊 *Введите новый процент (1-100%):*",
        "take_profit": "🎯 *Введите новый Take Profit:*",
        "stop_loss": "🛡 *Введите новый Stop Loss:*",
        "pos_type": "🔄 *Выберите новый тип позиции:*"
    }

    reply_markup = None
    if field == "pos_type":
        reply_markup = get_position_type_keyboard()

    await message.answer(
        prompts[field],
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await state.set_state(PositionStates.waiting_for_edit_value)


# Обработка нового значения
@dp.message(PositionStates.waiting_for_edit_value)
async def process_edit_value(message: types.Message, state: FSMContext):
    """Обработка нового значения для редактирования"""
    data = await state.get_data()
    field = data.get('edit_field')
    position_id = data.get('edit_position_id')
    value = message.text

    try:
        # Валидация и преобразование значения
        if field == "percent":
            value = int(value)
            if not 1 <= value <= 100:
                raise ValueError("Процент должен быть от 1 до 100")
        elif field in ["take_profit", "stop_loss"]:
            value = float(value)
            if value <= 0:
                raise ValueError("Значение должно быть больше 0")
        elif field == "pos_type":
            value = value.lower()
            if value not in ['long', 'short']:
                raise ValueError("Тип должен быть 'long' или 'short'")

        # Обновляем поле в базе данных
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE positions SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (value, position_id)
            )
            conn.commit()

            # Логируем изменение
            cursor.execute(
                "INSERT INTO position_history (position_id, name, percent, take_profit, stop_loss, pos_type) "
                "SELECT id, name, percent, take_profit, stop_loss, pos_type FROM positions WHERE id = ?",
                (position_id,)
            )
            conn.commit()

            await message.answer(
                f"✅ *Поле '{field}' успешно обновлено!*",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )

    except ValueError as e:
        await message.answer(
            f"❌ *Ошибка валидации:* {e}\n"
            "Попробуйте снова:",
            parse_mode="Markdown"
        )
        return
    except Exception as e:
        await message.answer(
            f"❌ *Ошибка при обновлении:* {e}",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )

    await state.clear()


# Обработчик неизвестных команд
@dp.message()
async def unknown_command(message: types.Message):
    """Обработка неизвестных команд"""
    await message.answer(
        "🤔 *Неизвестная команда.*\n"
        "Используйте /help для справки.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


# Главная функция
async def main():
    """Главная функция бота"""
    print("🤖 Бот запускается...")
    print(f"📁 База данных: {db.db_path}")

    # Проверяем существование базы данных
    if not os.path.exists(db.db_path):
        print("⚠️ База данных не найдена, создаем новую...")

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Для Windows может потребоваться настройка event loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")