import logging
from aiogram import Bot as AiogramBot, executor, Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import configparser
from db import *
config = configparser.ConfigParser()
config.read("configuration.ini")
gc = gspread.service_account(filename='credentials.json')
token = config["SETTINGS"]['telegram_token']
logging.basicConfig(level=logging.INFO)

bot = AiogramBot(token=token)
class States(StatesGroup):
    wait_for_answer = State()
storage = MemoryStorage()
dp = Dispatcher(bot= bot, storage = storage)

@dp.message_handler(commands='start', state = '*')
async def message_start(message:types.Message):
    user = user_get_or_create(message.chat.id)
    kb = types.InlineKeyboardMarkup()
    if user[1] != '0':
        kb.add(types.InlineKeyboardButton(text = 'Продолжить викторину', callback_data='quiz_continue'))
    kb.add(types.InlineKeyboardButton(text = 'Начать новую викторину', callback_data= 'quiz_new'))
    kb.add(types.InlineKeyboardButton(text = 'Посмотреть свои результаты', callback_data='get_results'))
    await message.answer('Салам алейкум', reply_markup= kb)
@dp.callback_query_handler(lambda query: query.data == 'start')
async def start_callback(callback_query: types.CallbackQuery):
    await message_start(callback_query.message)
    await callback_query.answer()
    await callback_query.message.delete()
@dp.callback_query_handler(lambda query: query.data == 'get_results')
async def get_result(callback_query: types.CallbackQuery):
    results = get_score(callback_query.message.chat.id)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text = 'Главное меню', callback_data='start'))
    await callback_query.message.answer(results, reply_markup= kb)
    await callback_query.answer()
    await callback_query.message.delete()
@dp.callback_query_handler(lambda query: query.data == 'quiz_new')
async def start_quiz(callback_query: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup()
    quizes = get_all_quizes()
    for quiz in quizes:
        kb.add(types.InlineKeyboardButton(text = quiz, callback_data=f'newquiz_{quizes[quiz]}'))
    kb.add(types.InlineKeyboardButton(text = 'Главное меню', callback_data='start'))
    await callback_query.message.answer('Выберите викторину:', reply_markup=kb)
    await callback_query.answer()
    await callback_query.message.delete()
@dp.callback_query_handler(lambda query: query.data.startswith('newquiz_'))
async def newquiz(callback_query: types.CallbackQuery, state: FSMContext):
    link = callback_query.data[callback_query.data.find('_')+1:]
    start_newquiz(callback_query.message.chat.id,link)
    question_number = get_question_number(callback_query.message.chat.id)
    question = get_quiz_question(link,question_number)
    answer = question[1]
    points = question[2]
    question = question[0]
    await States.wait_for_answer.set()
    async with state.proxy() as data:
        data['answer'] = answer
        data['points'] = points
    await callback_query.message.answer(question)
    await callback_query.answer()
    await callback_query.message.delete()
@dp.callback_query_handler(lambda query: query.data == 'quiz_continue')
async def quiz_continue(callback_query: types.CallbackQuery, state: FSMContext):
    link = get_current_quiz_link(callback_query.message.chat.id)
    question_number = get_question_number(callback_query.message.chat.id)
    question = get_quiz_question(link, question_number)
    answer = question[1]
    points = question[2]
    question = question[0]
    await States.wait_for_answer.set()
    async with state.proxy() as data:
        data['answer'] = answer
        data['points'] = points
    await callback_query.message.answer(question)
    await callback_query.answer()
    await callback_query.message.delete()
@dp.message_handler(state = States.wait_for_answer)
async def get_answer(message:types.Message, state: FSMContext):
    given_answer = message.text
    async with state.proxy() as data:
        answer = data['answer']
        points = data['points']
    if given_answer.lower() == answer.lower():
        give_points(message.chat.id, points)
        await message.answer('Правильный ответ')
    else:
        await message.answer('Неверный ответ')
    if check_questions(message.chat.id):
        question = next_question(message.chat.id)
        answer = question[1]
        points = question[2]
        question = question[0]
        await States.wait_for_answer.set()
        async with state.proxy() as data:
            data['answer'] = answer
            data['points'] = points
        await message.answer(question)
    else:
        msg = finish_quiz(message.chat.id, message.chat.username)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text = 'Главное меню', callback_data='start'))
        await message.answer(msg, reply_markup=kb)
        await state.finish()

if __name__ == "__main__":
    start_sheet()
    executor.start_polling(dp, skip_updates=True)