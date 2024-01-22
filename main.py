from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.fsm import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import logging
from peewee import Model, SqliteDatabase, CharField
import gspread
import gdown
import aiogram
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os

load_dotenv()



scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
spreadsheet_url = os.getenv("spreadsheet_url")
spreadsheet = client.open_by_url(spreadsheet_url)
sheet = spreadsheet.get_worksheet(0)

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

db = SqliteDatabase('database.db')
allowed_user_ids = os.getenv("allowed_user_ids")

forward_chat_id = os.getenv("forward_chat_id")

class Machine(Model):
    name = CharField()
    reason = CharField()
    photo = CharField()
    fixed = CharField(null=True)

    class Meta:
        database = db

db.connect()
db.create_tables([Machine])

API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

class Report(StatesGroup):
    machine = State()
    reason = State()
    photo = State()

async def save_photo_to_google_drive(file_id: str, machine_name: str):
    photo_info = await bot.get_file(file_id)
    file_path = photo_info.file_path

    photo_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_path}'
    photo_name = f'{machine_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
    photo_path = f'photos/{photo_name}'

    gdown.download(photo_url, photo_path, quiet=False)

    gfile = drive.CreateFile({'title': photo_name})
    gfile.SetContentFile(photo_path)
    gfile.Upload()

    photo_drive_url = gfile['alternateLink']

    return photo_drive_url

async def send_data_to_google_sheets(machine_id, machine_name, reason, photo_drive_url):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row_data = [machine_id, machine_name, reason, photo_drive_url, current_time]
    sheet.append_row(row_data)

async def generate_machine_menu():
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    machine_names = [f"Станок {i}" for i in range(1, 16)]
    buttons = [types.InlineKeyboardButton(name, callback_data=f"machine_{index+1}") for index, name in enumerate(machine_names)]
    keyboard.add(*buttons)
    cancel_button = InlineKeyboardButton("Отмена", callback_data="machine_cancel_fix")
    keyboard.add(cancel_button)
    return keyboard

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message, state: FSMContext):
    await message.answer("Привет! Этот бот предназначен для отправки отчетов о поломках. Используй /report, чтобы начать.")


@dp.message_handler(commands=['report'],  chat_type=types.ChatType.PRIVATE)
async def start_report(message: types.Message, state: FSMContext):
    await Report.machine.set()
    machine_menu = await generate_machine_menu()
    sent_message_id1 = await message.answer("Выберите станок из меню:", reply_markup=machine_menu)
    await state.update_data(sent_message_id1=sent_message_id1.message_id)
    await state.update_data(user_id=message.from_user.username)
    await state.update_data(user_fullname=message.from_user.first_name)

@dp.callback_query_handler(lambda c: c.data.startswith('machine'), state=Report.machine)
async def process_machine(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "machine_cancel_fix":
        await callback_query.message.edit_text("Отменено.")
        return
    machine_index = int(callback_query.data.split('_')[1])
    machine_name = f"Станок {machine_index}"
    data = await state.get_data()
    sen_message_id = data.get("sent_message_id1")

    message_id = callback_query.message.message_id
    await state.update_data(message_id=message_id)
    try:
        await bot.edit_message_reply_markup(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=None
        )
        if sen_message_id:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=sen_message_id) 
    except aiogram.utils.exceptions.MessageToDeleteNotFound:
        pass
    
    
    await state.update_data(machine=machine_name)
    await Report.next()
    send_message_i = await callback_query.message.answer(f"Вы выбрали: {machine_name}. Укажите причину поломки:")
    await state.update_data(sent_message_id4=send_message_i.message_id)

@dp.message_handler(state=Report.reason)
async def process_reason(message: types.Message, state: FSMContext):
    reason = message.text
    await state.update_data(reason=reason)
    await Report.next()
    data = await state.get_data()
    sent_message_i = data.get('sent_message_id4')
    if sent_message_i:
        await bot.delete_message(chat_id=message.chat.id, message_id=sent_message_i)
    send_message_id2 = await message.answer("Прикрепите фото поломки:")
    await state.update_data(sent_message_id=send_message_id2.message_id)



@dp.message_handler(content_types=types.ContentType.PHOTO, state=Report.photo)
async def process_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1].file_id
    data = await state.get_data()
    user_id = data.get('user_id')
    user_name = data.get('user_fullname')
    machine_name = data.get('machine')
    reason = data.get('reason')
    sent_message_id2 = data.get('sent_message_id')
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    machine = Machine.create(name=machine_name, reason=reason, photo=photo)
    photo_drive_url = await save_photo_to_google_drive(photo, machine_name)
    if sent_message_id2:
        await bot.delete_message(chat_id=message.chat.id, message_id=sent_message_id2)
    await send_data_to_google_sheets(machine.id, machine_name, reason, photo_drive_url)
    await send_start_fixed_photo(
            chat_id=message.chat.id,
            photo_drive_url=photo,
            machine_name=machine_name,
            reason=reason,
            user_id=user_id,
            user_name=user_name,
            current_time=date
        )
    await send_start_fixed_photo(
            chat_id=forward_chat_id,
            photo_drive_url=photo,
            machine_name=machine_name,
            reason=reason,
            user_id=user_id,
            user_name=user_name,
            current_time=date
        )

    machine.save()

    await state.finish()
    message_answer = await message.answer("Данные сохранены и обработаны!")
    await state.update_data(sent_message_id=message_answer.message_id)


    

async def send_fixed_photo(chat_id, photo_drive_url, machine_name, reason, current_time, user_id, user_name):
    caption = f"Поломка закрыта\n\nСтанок: {machine_name}\nПричина: {reason}\nОтправил: {user_id}  {user_name}\nВремя закрытия: {current_time}"
    await bot.send_photo(chat_id=chat_id, photo=photo_drive_url, caption=caption)

async def send_start_fixed_photo(chat_id, photo_drive_url, machine_name, reason, current_time, user_id, user_name):
    caption = f"Поломка \n\nСтанок: {machine_name}\nПричина: {reason}\nОтправил: {user_id}  {user_name}\nВремя открытия: {current_time}"
    await bot.send_photo(chat_id=chat_id, photo=photo_drive_url, caption=caption)

async def send_message(chat_id, text, reply_markup=None):
    return await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

async def display_broken_machines(message, broken_machines):
    keyboard = InlineKeyboardMarkup()
    for machine in broken_machines:
        button_text = f"{machine.name} - {machine.reason}"
        button = InlineKeyboardButton(button_text, callback_data=f"fix_{machine.id}")
        keyboard.add(button)
        
    cancel_button = InlineKeyboardButton("Отмена", callback_data="cancel_fix")
    keyboard.add(cancel_button)

    sent_message = await send_message(
        chat_id=message.chat.id,
        text="Выберите станок для закрытия поломки:",
        reply_markup=keyboard
    )
    return sent_message.message_id

@dp.message_handler(commands=['fix'], chat_type=types.ChatType.PRIVATE)
async def start_fix(message: types.Message, state: FSMContext):
    broken_machines = Machine.select().where(Machine.fixed.is_null())
    data = await state.get_data()
    message_answer = data.get('message_answer')
    await state.update_data(user_id=message.from_user.username)
    await state.update_data(user_name=message.from_user.first_name)

    if message_answer:
        await bot.delete_message(chat_id=message.chat.id, message_id=message_answer)

    if broken_machines:
        sent_message2 = await display_broken_machines(message, broken_machines)
        await state.update_data(sent_message2=sent_message2)
    else:
        await message.answer("В данный момент нет открытых поломок.")

@dp.callback_query_handler(lambda c: c.data.startswith('fix'), chat_type=types.ChatType.PRIVATE)
async def process_fix_callback(callback_query: types.CallbackQuery, state: FSMContext):
    _, machine_id = callback_query.data.split('_')
    machine_id = int(machine_id)
    if callback_query.data == "cancel_fix":
        await callback_query.message.edit_text("Отменено.")
        return

    try:
        data = await state.get_data()
        user_id = data.get('user_id')
        user_name = data.get('user_name')
        message_answer = data.get('sent_message2')

        machine = Machine.get(id=machine_id, fixed=None)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        machine.fixed = current_time

        try:
            await bot.edit_message_reply_markup(
                chat_id=callback_query.message.chat.id,
                message_id=message_answer,
                reply_markup=None
            )
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=message_answer)
        except aiogram.utils.exceptions.MessageToDeleteNotFound:
            pass

        await send_fixed_photo(
            chat_id=callback_query.message.chat.id,
            photo_drive_url=machine.photo,
            machine_name=machine.name,
            reason=machine.reason,
            user_id=user_id,
            user_name=user_name,
            current_time=current_time
        )
        
        await send_fixed_photo(
            chat_id=forward_chat_id,
            photo_drive_url=machine.photo,
            machine_name=machine.name,
            reason=machine.reason,
            user_id=user_id,
            user_name=user_name,
            current_time=current_time
        )

        machine.save()

        try:
            sheet = spreadsheet.get_worksheet(0)
            cell = sheet.find(str(machine.id))

            if cell is not None:
                sheet.update_cell(cell.row, 6, current_time)
            else:
                await callback_query.message.edit_text("Станок не найден в таблице. Возможно, он уже был закрыт.")
        except Exception as e:
            logging.error(f"Ошибка при отправке данных в Google Docs: {e}")
            await callback_query.message.edit_text("Произошла ошибка при закрытии поломки. Попробуйте еще раз.")
    except Machine.DoesNotExist:
        await callback_query.message.edit_text("Станок с таким номером не найден или поломка уже закрыта.")



if __name__ == '__main__':
    try:
        from aiogram import executor
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logging.exception(f"An error occurred: {e}")
