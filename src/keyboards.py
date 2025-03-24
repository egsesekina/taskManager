from aiogram.types import (KeyboardButton, ReplyKeyboardMarkup,
                           InlineKeyboardButton,InlineKeyboardMarkup)
from aiogram.utils.keyboard import ReplyKeyboardBuilder



def create_task_keyboard(user_tasks: list) -> InlineKeyboardMarkup:
    keyboard = []

    # Add the search button as the first button
    search_button = InlineKeyboardButton(text="🔍", callback_data="search_tasks_by_day")
    keyboard.append([search_button])  # Add as a row

    for task in user_tasks:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=task.title, callback_data=f"task:{task._id}"
                )
            ]
        )
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    return reply_markup

def create_tasks_by_day_keyboard(user_tasks: list) -> InlineKeyboardMarkup:
    keyboard = []

    search_button = InlineKeyboardButton(text="🗑", callback_data="delete_tasks_by_day")
    keyboard.append([search_button])  # Add as a row

    for task in user_tasks:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=task.title, callback_data=f"task:{task._id}"
                )
            ]
        )
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    return reply_markup

def create_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Creates an inline keyboard with Edit and Delete buttons for a specific task."""
    edit_button = InlineKeyboardButton(text="✏️", callback_data=f"edit_task:{task_id}")
    delete_button = InlineKeyboardButton(text="✔️", callback_data=f"delete_task:{task_id}")
    task_actions_keyboard = InlineKeyboardMarkup(inline_keyboard=[[edit_button, delete_button]])
    return task_actions_keyboard

def create_choose_field_keyboard() -> InlineKeyboardMarkup:
    """Creates an inline keyboard allowing the user to choose which task field to edit."""
    title_button = InlineKeyboardButton(text="Title", callback_data="edit_field:title")
    description_button = InlineKeyboardButton(text="Description", callback_data="edit_field:description")
    deadline_button = InlineKeyboardButton(text="Deadline", callback_data="edit_field:deadline")
    choose_field_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [title_button],
        [description_button],
        [deadline_button]
    ])
    return choose_field_keyboard

def create_choose_another_keyboard() -> InlineKeyboardMarkup:
    """Creates a keyboard to ask if user wants to edit more fields."""
    choose_another_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Edit another field", callback_data="edit_another_field")],
        [InlineKeyboardButton(text="Finish editing", callback_data="finish_editing")],
    ])
    return choose_another_keyboard