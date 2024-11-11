import asyncio
import random
import httpx
from googletrans import Translator
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
import os

# Загружаем токен из файла .env
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

# Проверка на наличие токена
if not API_TOKEN:
    raise ValueError("Токен бота не найден. Убедитесь, что он указан в файле .env")

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Изначальный список ID администраторов (укажите ID основного администратора)
ADMIN_IDS = {1395549662}  # Замените на реальный ID основного администратора

# Локальные фразы и их переводы
local_phrases = [
    "Hello!", "Good morning!", "How are you?", "Thank you!", "See you later!",
    "Good night!", "Have a great day!", "Excuse me!", "I love learning English.",
    "Could you help me?"
]

# Предварительный перевод локальных фраз (оптимизация)
translator = Translator()
pretranslated_phrases = {phrase: translator.translate(phrase, src='en', dest='ru').text for phrase in local_phrases}

# Определение состояния для ожидания вопроса
class QuestionState(StatesGroup):
    waiting_for_question = State()

# Кнопки для команд с иконками
buttons = [
    [KeyboardButton(text="🗣️ Задать вопрос"), KeyboardButton(text="💬 Получить фразу")]
]
keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Создаем экземпляр клиента для API один раз
client = httpx.AsyncClient()
last_phrase = None  # Переменная для кеширования последней фразы

# Обработчик команды /start
@dp.message(Command("start"))
async def send_welcome(message: Message, state: FSMContext):
    await message.answer("👋 Привет! Добро пожаловать в *Informal English*.\nВыберите действие ниже:", reply_markup=keyboard, parse_mode="Markdown")
    await state.clear()

# Обработчик команды /myid для получения ID пользователя
@dp.message(Command("myid"))
async def send_user_id(message: Message):
    await message.answer(f"Ваш ID: `{message.from_user.id}`", parse_mode="Markdown")

# Обработчик для просмотра списка администраторов
@dp.message(Command("list_admins"))
async def list_admins(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для просмотра администраторов.")
        return

    if ADMIN_IDS:
        admin_list = "\n".join([f"- {admin_id}" for admin_id in ADMIN_IDS])
        await message.answer(f"🛠 Список администраторов:\n{admin_list}")
    else:
        await message.answer("Список администраторов пуст.")

# Универсальная функция для добавления и удаления администратора
async def manage_admin_list(message: Message, add=True):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для управления администраторами.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Неправильный формат команды. Укажите ID пользователя.", parse_mode="Markdown")
        return

    try:
        target_id = int(parts[1])
        if add:
            if target_id in ADMIN_IDS:
                await message.answer("❗ Пользователь уже является администратором.")
            else:
                ADMIN_IDS.add(target_id)
                await message.answer(f"✅ Пользователь с ID {target_id} добавлен в администраторы.")
        else:
            if target_id not in ADMIN_IDS:
                await message.answer("❗ Этот ID не найден в списке администраторов.")
            else:
                ADMIN_IDS.discard(target_id)
                await message.answer(f"✅ Пользователь с ID {target_id} удален из администраторов.")
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом.")

# Обработчик команды /add_admin
@dp.message(Command("add_admin"))
async def add_admin(message: Message):
    await manage_admin_list(message, add=True)

# Обработчик команды /remove_admin
@dp.message(Command("remove_admin"))
async def remove_admin(message: Message):
    await manage_admin_list(message, add=False)

# Обработчик команды /answer для отправки ответа пользователю
@dp.message(Command("answer"))
async def answer_user(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для отправки ответов.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("❌ Неправильный формат команды. Используйте: `/answer <user_id> <ответ>`", parse_mode="Markdown")
        return

    try:
        user_id = int(parts[1])
        answer_text = parts[2]
        await bot.send_message(user_id, f"Ответ от администратора:\n{answer_text}")
        await message.answer("✅ Ответ успешно отправлен.")
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке ответа: {e}")

# Обработчик для кнопки "Получить фразу" с автоматическим переводом
@dp.message(F.text == "💬 Получить фразу")
async def send_phrase(message: Message, state: FSMContext):
    phrase = await get_random_phrase()
    translated_phrase = pretranslated_phrases.get(phrase) or await translate_phrase(phrase)
    await message.answer(f"🇬🇧 *English*: _{phrase}_\n\n🇷🇺 *Перевод*: _{translated_phrase}_", parse_mode="Markdown")
    await state.clear()

# Асинхронная функция для получения случайной фразы из API ZenQuotes
async def get_random_phrase():
    global last_phrase
    url = "https://zenquotes.io/api/random"
    try:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()[0]
            last_phrase = data['q']
            return last_phrase
        else:
            return last_phrase or random.choice(list(pretranslated_phrases.keys()))
    except httpx.RequestError:
        return last_phrase or random.choice(list(pretranslated_phrases.keys()))

# Асинхронная функция для перевода фразы, если она не была переведена заранее
async def translate_phrase(phrase):
    try:
        translation = await asyncio.to_thread(translator.translate, phrase, src='en', dest='ru')
        return translation.text
    except Exception as e:
        print(f"Ошибка при переводе: {e}")
        return "Не удалось перевести фразу"

# Обработчик для кнопки "Задать вопрос" — активируем состояние ожидания вопроса
@dp.message(F.text == "🗣️ Задать вопрос")
async def ask_question(message: Message, state: FSMContext):
    await message.answer("✍️ Напишите ваш вопрос, и я отправлю его администратору.")
    await state.set_state(QuestionState.waiting_for_question)

# Обработчик для отправки вопроса администратору при состоянии ожидания вопроса
@dp.message(StateFilter(QuestionState.waiting_for_question))
async def send_question_to_admins(message: Message, state: FSMContext):
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    question_text = message.text

    question_sent = False
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"Вопрос от пользователя {user_name} (ID: {user_id}):\n{question_text}"
            )
            question_sent = True
        except Exception as e:
            print(f"Ошибка при отправке вопроса админу с ID {admin_id}: {e}")

    if question_sent:
        await message.answer("✅ Ваш вопрос был успешно отправлен администратору.")
    else:
        await message.answer("❌ Не удалось отправить ваш вопрос. Пожалуйста, попробуйте позже.")
    
    await state.clear()

# Основная функция запуска бота
async def main():
    await dp.start_polling(bot)

# Закрытие клиента после завершения работы
async def shutdown():
    await client.aclose()

# Запуск бота с обработкой завершения
if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        asyncio.run(shutdown())
