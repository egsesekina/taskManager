from aiogram import F, Router, html
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from datetime import datetime, timedelta

from mongo_api import Task, Notification

import re

import keyboards as kb

router = Router()

class AddTask(StatesGroup):
    title = State()
    description = State()
    deadline = State()
    confirm_getting_reminder = State()
    reminder_time = State()
    confirm_repeating_reminder = State()
    reminder_period = State()
    reminder_count = State()

class EditTask(StatesGroup):
    choosing_field = State()  
    editing_field = State()  

class SearchTask(StatesGroup):
    waiting_for_date = State()
    displaying_tasks = State()  

@router.message(CommandStart())
async def cmd_start(message: Message):
    start_text = (
        f"Hello, {html.bold(message.from_user.full_name)}!\n\n"
        "I'm here to help you manage your tasks and deadlines with ease.\n\n"
        "Here's what I can do:\n"
        "/tasks - See your current tasks\n"
        "/add_task - Create a new task\n"
        "/help - Find available commands"
    )
    await message.answer(start_text, parse_mode="HTML")

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "Hey there! I'm here to assist you.\n\n"
        "Here's a quick overview of what I can do:\n"
        "/tasks - See your current list of tasks\n"
        "/add_task - Create a new task to keep track of\n"
        "/help - Display this helpful information"
    )
    await message.answer(help_text, parse_mode="HTML")

@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    user_id = message.from_user.id
    user_tasks = Task.get_all_by_user(user_id)

    if not user_tasks:
        await message.answer("You have no tasks assigned.")
        return


    reply_markup = kb.create_task_keyboard(user_tasks)

    await message.answer("Your tasks:", reply_markup=reply_markup)


# --- TASK DETAIL CALLBACK ---
@router.callback_query(F.data.startswith("task:"))
async def task_detail_callback(callback: CallbackQuery):
    task_id = callback.data.split(":")[1]
    task = Task.get_task_by_id(task_id)

    if not task:
        await callback.answer("Task not found.", show_alert=True)
        return

    task_actions_keyboard = kb.create_task_actions_keyboard(task_id)

    deadline = task.deadline
    now = datetime.now()

    if deadline > now:
        time_left = deadline - now
        days = time_left.days
        hours, minutes = divmod(time_left.seconds // 60, 60)
        time_str = f"{days} days, {hours} hours, {minutes} minutes"
        status_text = f"Time left: {time_str}"
        status_emoji = "👍🏼" 
    else:
        time_passed = now - deadline
        days = time_passed.days
        hours, minutes = divmod(time_passed.seconds // 60, 60)
        time_str = f"{days} days, {hours} hours, {minutes} minutes"
        status_text = f"Time past: {time_str}"
        status_emoji = "👎🏼"

    deadline_formatted = deadline.strftime("%Y-%m-%d %H:%M") 

    message_text = (
        f"<b>{html.bold(task.title)}</b>\n\n"
        f"<b>Description:</b> {task.description}\n\n"
        f"<b>Deadline:</b> {deadline_formatted}\n\n"
        f"{status_emoji} {status_text}" 
    )

    await callback.message.answer(message_text, parse_mode="HTML", reply_markup=task_actions_keyboard)
    await callback.answer()

# --- Function to add a task
def add_task(
    user_id: int, title: str, description: str, deadline: datetime, reminder_time: datetime = None, reminder_count: int = 1, reminder_period: int = timedelta(days=1)) -> int:  # Return task ID
    
    added_task = Task(user_id, title, description, deadline)
    added_task.insert()

    if(reminder_time != None):
        added_notification = Notification(reminder_time, reminder_period, reminder_count, added_task._id)
        added_notification.insert()

    return added_task._id 

# --- ADD TASK COMMAND ---
@router.message(Command("add_task"))
async def cmd_add_task(message: Message, state: FSMContext):
    await state.set_state(AddTask.title)
    await message.answer("Enter the task title:")

@router.message(AddTask.title)
async def add_task_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddTask.description)
    await message.answer("Enter the task description:")

@router.message(AddTask.description)
async def add_task_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddTask.deadline)
    await message.answer("Enter the task deadline (<b>YYYY-MM-DD HH:MM</b>):")

@router.message(AddTask.deadline)
async def add_task_deadline(message: Message, state: FSMContext):
    try:
        deadline = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        if deadline < datetime.now():
            await message.answer("Deadline cannot be in the past. Please enter a future date.")
            return

        await state.update_data(deadline=deadline)
        data = await state.get_data()

        # Запрашиваем, хочет ли пользователь установить напоминание
        await state.set_state(AddTask.confirm_getting_reminder)
        await message.answer("Do you want to set a reminder? (yes/no)")

    except ValueError:
        await message.answer("Invalid date format. Please use <b>YYYY-MM-DD HH:MM</b>")

@router.message(AddTask.confirm_getting_reminder)
async def add_task_reminder_time(message: Message, state: FSMContext):
    if message.text.lower() in ["yes", "y"]:
        await message.answer("When do you want to be reminded? (Enter date and time in <b>YYYY-MM-DD HH:MM</b> format):")
        await state.set_state(AddTask.reminder_time)
    elif message.text.lower() in ["no", "n"]:
        # Если пользователь не хочет напоминание, добавляем задачу без напоминаний
        data = await state.get_data()
        add_task(
            message.from_user.id,
            data["title"],
            data["description"],
            data["deadline"],
        )

        await message.answer(
            "Task added successfully!\n"
            f"<b>Title</b>: {data['title']}\n"
            f"<b>Description</b>: {data['description']}\n"
            f"<b>Deadline</b>: {data['deadline'].strftime('%Y-%m-%d %H:%M')}"
        )
        await state.clear()
    else:
        await message.answer("Please answer with 'yes' or 'no'.")

@router.message(AddTask.reminder_time)
async def set_reminder_time(message: Message, state: FSMContext):
    try:
        reminder_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        if reminder_time < datetime.now():
            await message.answer("Reminder time cannot be in the past. Please enter a future date.")
            return

        await state.update_data(reminder_time=reminder_time)
        await state.set_state(AddTask.confirm_repeating_reminder)
        await message.answer("Do you want this reminder to repeat? (yes/no)")

    except ValueError:
        await message.answer("Invalid date format. Please use YYYY-MM-DD HH:MM")

@router.message(AddTask.confirm_repeating_reminder)
async def set_reminder_period(message: Message, state: FSMContext):
    if message.text.lower() == "yes":
        await message.answer(
        "How often do you want to repeat this reminder? (Enter the period in <b>_d_h_m</b> format):\n\n"

        "Examples:\n"
        "<b>1d12h30m</b>  (1 day 12 hours 30 minutes)\n"
        "<b>1h30m</b>  (1.30 hours)\n"
        "<b>2d</b>  (2 days)"
        )
        await state.set_state(AddTask.reminder_period)
    elif message.text.lower() == "no":
        data = await state.get_data()
        add_task(
            message.from_user.id,
            data["title"],
            data["description"],
            data["deadline"],
            data["reminder_time"]
        )

        await message.answer(
            "Task added successfully!\n"
            f"<b>Title</b>: {data['title']}\n"
            f"<b>Description</b>: {data['description']}\n"
            f"<b>Deadline</b>: {data['deadline'].strftime('%Y-%m-%d %H:%M')}\n"
            f"You will be reminded at {data["reminder_time"].strftime('%Y-%m-%d %H:%M')}"
        )
        await state.clear()
    else:
        await message.answer("Please answer with 'yes' or 'no'.")

def parse_time_input(time_input: str) -> timedelta:
    days = hours = minutes = 0
    # Регулярное выражение для разбора ввода
    matches = re.findall(r'(\d+)\s*(d|h|m)', time_input)

    for value, unit in matches:
        if unit == 'd':
            days += int(value)
        elif unit == 'h':
            hours += int(value)
        elif unit == 'm':
            minutes += int(value)

    return timedelta(days=days, hours=hours, minutes=minutes)

@router.message(AddTask.reminder_period)
async def input_reminder_period(message: Message, state: FSMContext):
    try:
        reminder_timedelta = parse_time_input(message.text)
        if reminder_timedelta.total_seconds() <= 0:
            await message.answer("Please enter a valid positive time period.")
            return

        await state.update_data(reminder_period=reminder_timedelta)
        await state.set_state(AddTask.reminder_count)
        await message.answer("How many times do you want to repeat this reminder? (Enter a number):")

    except Exception as e:
        await message.answer("Please enter a valid time period in the format <b>_d_h_m</b>.")

def format_timedelta(timedelta_obj):
    total_seconds = int(timedelta_obj.total_seconds())
    days, remainder = divmod(total_seconds, 86400)  # 86400 секунд в дне
    hours, remainder = divmod(remainder, 3600)      # 3600 секунд в часе
    minutes, seconds = divmod(remainder, 60)        # 60 секунд в минуте

    parts = []
    if days:
        parts.append(f"{days} d.")
    if hours:
        parts.append(f"{hours} h.")
    if minutes:
        parts.append(f"{minutes} m.")

    return ' '.join(parts) if parts else "0 min."

@router.message(AddTask.reminder_count)
async def input_reminder_count(message: Message, state: FSMContext):
    try:
        reminder_count = int(message.text)
        if reminder_count <= 0:
            await message.answer("Please enter a positive number for the count.")
            return

        await state.update_data(reminder_count=reminder_count)
        data = await state.get_data()


        add_task(
            message.from_user.id,
            data["title"],
            data["description"],
            data["deadline"],
            reminder_time=data["reminder_time"],
            reminder_period=data["reminder_period"],
            reminder_count=data["reminder_count"]
        )

        await message.answer(
            "Task added successfully!\n"
            f"<b>Title</b>: {data['title']}\n"
            f"<b>Description</b>: {data['description']}\n"
            f"<b>Deadline</b>: {data['deadline'].strftime('%Y-%m-%d %H:%M')}\n"
            f"<b>Reminder set for</b>: {data['reminder_time'].strftime('%Y-%m-%d %H:%M')}\n"
            f"Reminder will repeat every {format_timedelta(data['reminder_period'])}, {data['reminder_count']} times."
        )
        await state.clear()

    except ValueError:
        await message.answer("Please enter a valid number for the count.")

# --- EDIT TASK CALLBACK (Initiates the edit process) ---
@router.callback_query(F.data.startswith("edit_task:"))
async def edit_task_callback(callback: CallbackQuery, state: FSMContext):
    task_id = callback.data.split(":")[1]
    task = Task.get_task_by_id(task_id)

    if not task:
        await callback.answer("Task not found.", show_alert=True)
        return

    await state.update_data(task_id=task_id)  # Store task_id for later use

    choose_field_keyboard = kb.create_choose_field_keyboard()

    await state.set_state(EditTask.choosing_field)
    await callback.message.answer("What do you want to edit?", reply_markup=choose_field_keyboard)
    await callback.answer()

# --- Choose Field to Edit Callback ---
@router.callback_query(EditTask.choosing_field)
async def choose_field_callback(callback: CallbackQuery, state: FSMContext):
    field_to_edit = callback.data.split(":")[1]
    await state.update_data(field_to_edit=field_to_edit)  # Store which field to edit
    data = await state.get_data()
    task_id = data.get("task_id")
    if task_id is None:
        await callback.message.answer("An error occurred. Please try again.")
        await state.clear()
        return

    await state.set_state(EditTask.editing_field)

    if field_to_edit == "title":
        await callback.message.answer("Enter new title for the task:")
    elif field_to_edit == "description":
        await callback.message.answer("Enter new description for the task:")
    elif field_to_edit == "deadline":
        await callback.message.answer("Enter new deadline for the task (YYYY-MM-DD HH:MM):")

    await callback.answer()

# --- Handlers for Editing Task Details (Title, Description, Deadline) ---
@router.message(EditTask.editing_field)
async def edit_task_value(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")
    field_to_edit = data.get("field_to_edit")

    task_db = Task.get_task_by_id(task_id)

    if task_id is None or field_to_edit is None or task_db is None:
        await message.answer("An error occurred. Please try again.")
        await state.clear()
        return


    if field_to_edit == "title":
        task_db.title = message.text
        task_db.commit()

    elif field_to_edit == "description":
        task_db.description = message.text
        task_db.commit()

    elif field_to_edit == "deadline":
        try:
            deadline = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
            if deadline < datetime.now():
                await message.answer("Deadline cannot be in the past. Please enter a future date.")
                return
            task_db.deadline = deadline
            task_db.commit()
            
        except ValueError:
            await message.answer("Invalid date format. Please use YYYY-MM-DD HH:MM")
            return  # Stop here if deadline is invalid.

    # --- After editing a field, ask if user wants to edit another one ---
    choose_another_keyboard = kb.create_choose_another_keyboard()


    deadline_str = task_db.deadline.strftime("%Y-%m-%d %H:%M")
    task_details = ( #Assign task_details
        f"<b>Title:</b> {task_db.title}\n"
        f"<b>Description:</b> {task_db.description}\n"
        f"<b>Deadline:</b> {deadline_str}\n"
    )

    await message.answer(
        f"Field updated successfully.\n\nHere's how the task looks now:\n\n{task_details}\nDo you want to edit another field?",
        reply_markup=choose_another_keyboard,
        parse_mode="HTML"
    )

    await state.set_state(EditTask.editing_field)

@router.callback_query(F.data == "edit_another_field")
async def edit_another_field_callback(callback: CallbackQuery, state: FSMContext):
    # Re-use the choose field keyboard
    choose_field_keyboard = kb.create_choose_field_keyboard()
    await state.set_state(EditTask.choosing_field)
    await callback.message.edit_text("What do you want to edit?", reply_markup=choose_field_keyboard)
    await callback.answer()

@router.callback_query(F.data == "finish_editing")
async def finish_editing_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")
    user_id = data.get("user_id")

    if task_id is None:
        await callback.message.answer("An error occurred. Please try again.")
        await state.clear()
        return

    await state.clear()

    #Confirmation Message
    updated_task = Task.get_task_by_id(task_id)
    title = updated_task.title
    description = updated_task.description
    deadline = updated_task.deadline

    if updated_task:
        await callback.message.answer(
            "Task updated successfully!\n"
            f"<b>Title</b>: {title}\n"
            f"<b>Description</b>: {description}\n"
            f"<b>Deadline</b>: {deadline.strftime('%Y-%m-%d %H:%M')}"
        )
    else:
        await callback.message.answer("Task not found after update.")

    await callback.answer()

# --- DELETE TASK CALLBACK ---
@router.callback_query(F.data.startswith("delete_task:"))
async def delete_task_callback(callback: CallbackQuery):
    task_id = callback.data.split(":")[1]
    task = Task.get_task_by_id(task_id)

    if task:
        title = task.title
        task.delete()

        await callback.message.edit_text(
            f"Task '{title}' completed.", reply_markup=None  # Remove the keyboard
        )
        await callback.answer()
    else:
        await callback.answer("Task not found.", show_alert=True)


# 3. Callback Handler for Search Button
@router.callback_query(F.data == "search_tasks_by_day")
async def search_tasks_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Please enter the date in <b>YYYY-MM-DD</b> format:", parse_mode="HTML")
    await state.set_state(SearchTask.waiting_for_date)

# 4. Message Handler for Date Input
@router.message(SearchTask.waiting_for_date)
async def ask_day(message: Message, state: FSMContext):
    try:
        day = datetime.strptime(message.text, "%Y-%m-%d")
        await state.update_data(search_date=day)  # Store the datetime object in state
        await message.answer("Searching tasks...")
        user_id = message.from_user.id
        tasks_by_day = Task.get_all_by_day(day, user_id)
        if tasks_by_day:
            # Here can add delete function as well
            reply_markup = kb.create_tasks_by_day_keyboard(tasks_by_day)
            await message.answer(f"Tasks for {message.text}:", reply_markup=reply_markup)
            await state.set_state(SearchTask.displaying_tasks) # Important
        else:
            await message.answer("No tasks found for that date.")
            await state.clear()  # Clear state after processing
    except ValueError:
        await message.answer("Invalid date format. Please use <b>YYYY-MM-DD</b>", parse_mode="HTML")
        await state.clear()  # Clear the state if there's an error


# 5. Corrected Callback Handler for Deleting Tasks
@router.callback_query(F.data == "delete_tasks_by_day", SearchTask.displaying_tasks) #Added state for security
async def delete_tasks_by_day_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()

    state_data = await state.get_data()
    day = state_data.get('search_date')  # Get the datetime object from state

    if day:
        user_id = callback_query.from_user.id
        Task.delete_all_by_day(day, user_id) #Delete operation goes here

        await callback_query.message.answer(f"All tasks for {day.strftime('%Y-%m-%d')} deleted successfully.")
    else:
        await callback_query.message.answer("Error: No date found in state.  Please start the search again.")

    await state.clear()
    