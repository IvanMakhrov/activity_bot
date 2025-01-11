import os
from typing import Callable, Any, Dict, Awaitable

from utils import calculate_requirements, get_food_info, create_progress_chart,\
      setup_logging, log, ValueOutOfRangeError

from aiogram import Bot
from aiogram import Dispatcher
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import BaseMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import asyncio


# os.chdir('app')

load_dotenv()
setup_logging()

telegram_token = os.environ.get("ACTIVITY_BOT_TOKEN")
calories_token = os.environ.get("CALORIES_TOKEN")
bot = Bot(token=telegram_token)

dp = Dispatcher()
router = Router()

users = {}


class Form(StatesGroup):
    weight = State()
    height = State()
    sex = State()
    age = State()
    activity = State()
    calories = State()
    city = State()


class WorkoutState(StatesGroup):
    workout_type = State()
    duration = State()


class CounterMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.counter = 0

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        
        user_id = event.from_user.id
        message_text = event.text

        log('info', 'User: {}. Message: {}', user_id, message_text)

        return await handler(event, data)

dp.message.middleware(CounterMiddleware())


@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    text = f"""
👋 Привет, {user_name}! 💦🔥
    
Это ваш личный помощник по здоровью и питанию!
    
Давайте начнем! Для начала, вот список команд:

/set_profile 👤 - Создать профиль
/delete_profile ❌ - Удалить профиль
/log_water 💧 - Записать выпитую воду
/log_food 🍔 - Записать съеденную еду
/log_workout 🏃‍♂️ - Записать тренировку
/check_progress 📊 - Посмотреть текущий результат
    """
    
    await message.reply(text)


@dp.message(Command("help"))
async def help(message: Message):

    text = f"""
    Основные команды:

/set_profile 👤 - Создать профиль
/delete_profile ❌ - Удалить профиль
/log_water 💧 - Записать выпитую воду
/log_food 🍔 - Записать съеденную еду
/log_workout 🏃‍♂️ - Записать тренировку
/check_progress 📊 - Посмотреть текущий результат
    """

    await message.reply(text)


@dp.message(Command('delete_profile'))
async def delete_profile(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in users:
        del users[user_id]
        log('info', 'Profile deleted for user {}', user_id)
        await message.reply('Профиль был удален')
    else:
        log('info', 'Profile not found for user {}', user_id)
        await message.reply('Профиль не найден')


@dp.message(Command('set_profile'))
async def set_profile(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in users:
        await message.reply("Введите ваш вес (в кг):")
        await state.set_state(Form.weight)
    else:
        await message.reply('Профиль уже существует. Для удаления существующего '
                            'профиля используйте команду /delete_profile')
        return None


@dp.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    min_weight = 15
    max_weight = 200

    try:
        weight = int(message.text)

        if not min_weight <= weight <= max_weight:
            raise ValueOutOfRangeError(f"Значение веса некорректно",
                                       weight, min_weight, max_weight)
        
        await state.update_data(weight=weight)
        await message.reply("Введите ваш рост (в см):")
        await state.set_state(Form.height)

    except ValueError:
        await message.answer('Неверный ввод. Значение должно быть числом. '
                             'Попробуйте еще раз')
    except ValueOutOfRangeError as e:
        await message.answer(str(e))


@dp.message(Form.height)
async def process_height(message: Message, state: FSMContext):
    min_height = 140
    max_height = 250

    try:
        height = int(message.text)

        if not min_height <= height <= max_height:
            raise ValueOutOfRangeError(f"Значение роста некорректно",
                                       height, min_height, max_height)
        
        await state.update_data(height=height)
        await message.reply("Введите ваш пол:")
        await state.set_state(Form.sex)

    except ValueError:
        await message.answer('Неверный ввод. Значение должно быть числом. '
                             'Попробуйте еще раз')
    except ValueOutOfRangeError as e:
        await message.answer(str(e))


@dp.message(Form.sex)
async def process_sex(message: Message, state: FSMContext):
    sex = message.text.lower().strip()

    if sex != 'жен' and sex != 'муж':
        await message.reply("Неверный ввод. Пол может принимать значения 'муж' и 'жен'. "
                            "Попробуйте еще раз")
        return None
    else:
        await state.update_data(sex=sex)
        await message.reply("Введите ваш возраст:")
        await state.set_state(Form.age)


@dp.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    min_age = 18
    max_age = 120

    try:
        age = int(message.text)

        if not min_age <= age <= max_age:
            raise ValueOutOfRangeError(f"Значение возраста некорректно",
                                       age, min_age, max_age)

        await state.update_data(age=age)
        await message.reply("Сколько минут активности у вас в день?")
        await state.set_state(Form.activity)

    except ValueError:
        await message.answer('Неверный ввод. Значение должно быть числом. '
                             'Попробуйте еще раз')
    except ValueOutOfRangeError as e:
        await message.answer(str(e))


@dp.message(Form.activity)
async def process_activity(message: Message, state: FSMContext):
    min_activity = 0
    max_activity = 3600

    try:
        activity = int(message.text)

        if not min_activity <= activity <= max_activity:
            raise ValueOutOfRangeError(f"Значение времени тренировок некорректно",
                                       activity, min_activity, max_activity)

        await state.update_data(activity=activity)
        await message.reply("Какая у вас цель по калориям? Если хотите, чтобы она была рассчитана, то укажите 0")
        await state.set_state(Form.calories)
    except ValueError:
        await message.answer('Неверный ввод. Значение должно быть числом. '
                             'Попробуйте еще раз')
    except ValueOutOfRangeError as e:
        await message.answer(str(e))


@dp.message(Form.calories)
async def process_calories(message: Message, state: FSMContext):
    min_calories = 0
    max_calories = 10000

    try:
        calories = int(message.text)

        if not min_calories <= calories <= max_calories:
            raise ValueOutOfRangeError(f"Значение количества калорий некорректно",
                                       calories, min_calories, max_calories)

        await state.update_data(calories=calories)
        await message.reply("В каком городе вы находитесь?")
        await state.set_state(Form.city)
    except ValueError:
        await message.answer('Неверный ввод. Значение должно быть числом. '
                             'Попробуйте еще раз')
    except ValueOutOfRangeError as e:
        await message.answer(str(e))


@dp.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    user_id = message.from_user.id
    city = message.text
    await state.update_data(city=city)

    user_data = await state.get_data()
    users[user_id] = {**user_data}
    
    water_goal, calorie_goal, fat_goal, protein_goal, carbohydrates_goal = calculate_requirements(
        user_data['weight'], user_data['height'], user_data['age'],
        user_data['activity'], user_data['city'], user_data['sex']
        )
    
    calorie_goal = calorie_goal if user_data['calories'] == 0 else user_data['calories']
    
    users[user_id]['water_goal'] = water_goal
    users[user_id]['calorie_goal'] = calorie_goal
    users[user_id]['fat_goal'] = fat_goal
    users[user_id]['protein_goal'] = protein_goal
    users[user_id]['carbohydrates_goal'] = carbohydrates_goal
    
    await message.reply(f"Профиль установлен! Ваши цели:\n- Вода: {water_goal} мл"
                        f"\n- Калории: {calorie_goal} ккал\n- Белки: {protein_goal} г"
                        f"\n- Жиры: {fat_goal} г\n - Углеводы: {carbohydrates_goal} г"
                        )
    await state.clear()


@dp.message(Command('log_water'))
async def log_water(message: Message):
    user_id = message.from_user.id

    if user_id in users:
        try:
            amount = int(message.text.replace('/log_water ', '').strip())
        except ValueError:
            await message.reply("Используйте: /log_water <объем в мл>")
            return
            
        users[user_id]['logged_water'] = users.get(user_id, {}).get('logged_water', 0) + amount
        remaining = users[user_id]['water_goal'] - users[user_id]['logged_water']

        if remaining > 0:
            text = f"Выпито: {amount} мл.\nОсталось: {remaining} мл."
        else:
            text = f"Выпито: {amount} мл.\nЦель достигнута ✅"

        await message.reply(text)
    
    else:
        await message.reply('Профиль не создан. Для начала создайте профиль '
                            'с помощью команды /set_profile')


@dp.message(Command('log_food'))
async def log_food(message: Message):
    user_id = message.from_user.id

    if user_id in users:
        message_text = message.text.replace('/log_food ', '').split()

        if len(message_text) < 2:
            await message.reply("Используйте: /log_food <название продукта> <количество в граммах>")
            return
        
        food_gram = message_text[-1]
        food_name = ' '.join(message_text[:-1])

        try:
            food_gram = int(food_gram)
        except ValueError:
            await message.reply('Неверный ввод. Количество грамм должно быть числом. Попробуйте еще раз\n'
                                'Используйте: /log_food <название продукта> <количество в граммах>')
            return
        
        food_data = await get_food_info(food_name, calories_token)

        if food_data:
            food_data = food_data.get('items', [])
            
            calories_per_size = int(food_data[0].get('calories', 0) / 100 * food_gram)
            fat_per_size = int(food_data[0].get('fat_total_g', 0) / 100 * food_gram)
            protein_per_size = int(food_data[0].get('protein_g', 0) / 100 * food_gram)
            carbohydrates_per_size = int(food_data[0].get('carbohydrates_total_g', 0) / 100 * food_gram)
        else:
            await message.reply(f"Информация для '{food_name}' не найдена. Попробуйте другое написание")
            return

        users[user_id]['logged_calories'] = users.get(user_id, {}).get('logged_calories', 0) + calories_per_size
        users[user_id]['logged_fat'] = users.get(user_id, {}).get('logged_fat', 0) + fat_per_size
        users[user_id]['logged_protein'] = users.get(user_id, {}).get('logged_protein', 0) + protein_per_size
        users[user_id]['logged_carbohydrates'] = users.get(user_id, {}).get('logged_carbohydrates', 0) + carbohydrates_per_size
        
        remaining = users[user_id]['calorie_goal'] - users[user_id]['logged_calories']

        text = f"Еда: {food_name}\nКоличество: {food_gram} г.\n"\
        f"- {calories_per_size} ккал\n"\
        f"- {fat_per_size} г. жиров\n"\
        f"- {protein_per_size} г. белков\n"\
        f"- {carbohydrates_per_size} г. углеводов\n\n"

        text += f"Осталось {remaining} ккал" if remaining > 0 else "Цель достигнута ✅"

        await message.reply(text)
    
    else:
        await message.reply('Профиль не создан. Для начала создайте профиль с помощью команды /set_profile')


@dp.message(Command('log_workout'))
async def log_workout_keyboard(message: Message):
    user_id = message.from_user.id

    if user_id in users:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Бег", callback_data="Бег"),
             InlineKeyboardButton(text="Велосипед", callback_data="Велосипед")
             ],
             [InlineKeyboardButton(text="Йога", callback_data="Йога"),
              InlineKeyboardButton(text="Танцы", callback_data="Танцы")
              ],
             [InlineKeyboardButton(text="Плавание", callback_data="Плавание"),
              InlineKeyboardButton(text="Тренажерный зал", callback_data="Тренажерный зал")
              ],
              [InlineKeyboardButton(text="Фигурное катание", callback_data="Фигурное катание"),
              InlineKeyboardButton(text="Лыжи", callback_data="Лыжи")
              ],
              [InlineKeyboardButton(text="Бокс", callback_data="Бокс"),
              InlineKeyboardButton(text="Бадминтон", callback_data="Бадминтон")
              ],
              [InlineKeyboardButton(text="Боулинг", callback_data="Боулинг"),
              InlineKeyboardButton(text="Большой теннис", callback_data="Большой теннис")
              ],
              [InlineKeyboardButton(text="Футбол", callback_data="Футбол"),
              InlineKeyboardButton(text="Настольный теннис", callback_data="Настольный теннис")],
              [InlineKeyboardButton(text="Воллейбол", callback_data="Воллейбол")]
              ])
        
        await message.answer("Выберите тип тренировки:", reply_markup=keyboard)

    else:
        await message.reply('Профиль не создан. Для начала создайте профиль с помощью команды /set_profile')


@dp.callback_query(lambda c:c.data in ["Бег", "Велосипед", "Йога", "Танцы", "Плавание", "Тренажерный зал", "Фигурное катание", "Лыжи", "Бокс", "Бадминтон", "Боулинг", "Большой теннис", "Футбол", "Настольный теннис", "Воллейбол"])
async def log_workout(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.from_user.id in users:
        await callback_query.answer()
        await state.update_data(workout_type=callback_query.data)
        log('info', 'User {} chose {}', callback_query.from_user.id, callback_query.data)
        
        await callback_query.message.answer("Введите продолжительность тренировки в минутах:")
        await state.set_state(WorkoutState.duration)
    else:
        await callback_query.message.answer('Профиль не создан. Для начала создайте профиль с помощью команды /set_profile')


@dp.message(WorkoutState.duration)
async def process_duration(message: Message, state: FSMContext):
    workout_calories = {
        "Бег": 10,
        "Велосипед": 5.3,
        "Йога": 3.75,
        "Танцы": 6.7,
        "Плавание": 3.83,
        "Тренажерный зал": 11,
        "Фигурное катание": 5,
        "Лыжи": 8.1,
        "Бокс": 14.2,
        "Бадминтон": 6.75,
        "Боулинг": 4.5,
        "Большой теннис": 6.7,
        "Футбол": 7.5,
        "Настольный теннис": 5.25,
        "Воллейбол": 4.25
    }

    user_id = message.from_user.id

    min_duration = 0
    max_duration = 3600

    try:
        duration = int(message.text)

        if not min_duration <= duration <= max_duration:
            raise ValueOutOfRangeError(f"Значение времени тренировки некорректно",
                                       duration, min_duration, max_duration)

        await state.update_data(duration=duration)
        workout_data = await state.get_data()

        workout_type = workout_data['workout_type']
        training_min = workout_data['duration']

        calories_burned = int(training_min * workout_calories[workout_type])
        
        users[user_id]['burned_calories'] = users.get(user_id, {}).get('burned_calories', 0) + calories_burned
        users[user_id]['trained_time'] = users.get(user_id, {}).get('trained_time', 0) + training_min

        training_extra_time = users[user_id]['trained_time'] - users[user_id]['activity']
        text = f"{workout_type} {training_min} минут — {calories_burned} ккал"

        if training_extra_time > 0:
            additional_water = 7 * training_extra_time
            users[user_id]['additional_water'] = additional_water
            text += f". Дополнительно: выпейте {additional_water} мл воды."
        
        await message.reply(text)
        await state.clear()

    except ValueError:
        await message.answer('Неверный ввод. Значение должно быть числом. '
                             'Попробуйте еще раз')
    except ValueOutOfRangeError as e:
        await message.answer(str(e))


@dp.message(Command('check_progress'))
async def check_progress(message: Message):
    user_id = message.from_user.id
    
    if user_id in users:
        user_progress = users[user_id]

        water_left = user_progress['water_goal']+user_progress.get('additional_water', 0)-user_progress.get('logged_water', 0)
        water_left_title = 'Осталось:' if water_left > 0 else 'Перевыполнение:'

        calories_left  = user_progress['calorie_goal']+user_progress.get('burned_calories', 0)-user_progress.get('logged_calories', 0)
        calories_left_title = 'Осталось:' if calories_left > 0 else 'Перевыполнение:'

        progress_msg = (f"📊 Прогресс:\n\n"
                        "💧 Вода:"
                        f"\n- Выпито: {user_progress.get('logged_water', 0)} мл из {user_progress['water_goal']} мл\n"
                        f"- Баланс: {user_progress.get('logged_water', 0)} мл из {user_progress['water_goal'] + user_progress.get('additional_water', 0)} мл\n"
                        f"- {water_left_title} {abs(water_left)} мл\n\n"
                        "🔥 Калории:"
                        f"\n- Потреблено: {user_progress.get('logged_calories', 0)} ккал из {user_progress['calorie_goal']} ккал"
                        f"\n- Сожжено: {user_progress.get('burned_calories', 0)} ккал"
                        f"\n- Баланс: {user_progress.get('logged_calories', 0)} ккал из {user_progress['calorie_goal']+user_progress.get('burned_calories', 0)} ккал"
                        f"\n- {calories_left_title} {abs(calories_left)} ккал\n\n"
                        "🏃‍♂️ Активности:"
                        f"\n- {user_progress.get('trained_time', 0)} мин из {user_progress.get('activity', 0)} мин\n\n"
                        "🥗 БЖУ:"
                        f"\n- Белки: {user_progress.get('logged_protein', 0)} г из {user_progress.get('protein_goal', 0)} г"
                        f"\n- Жиры: {user_progress.get('logged_fat', 0)} г из {user_progress.get('fat_goal', 0)} г"
                        f"\n- Углеводы: {user_progress.get('logged_carbohydrates', 0)} г из {user_progress.get('carbohydrates_goal', 0)} г")
        await message.reply(progress_msg)
    
        create_progress_chart(user_id, users[user_id])

        await message.answer_photo(
            FSInputFile(path=f'plots/{user_id}_progress.png')
            )
    
    else:
        await message.reply('Профиль не создан. Для начала создайте профиль с помощью команды /set_profile')


async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
