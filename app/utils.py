import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Tuple, Dict, Union

import requests
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import matplotlib.pyplot as plt
from googletrans import Translator
import aiohttp


class ValueOutOfRangeError(Exception):
    def __init__(self, message, value, min_value, max_value):
        super().__init__(message)
        self.message = message
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
    
    def __str__(self):
        return f"{self.message}. Значение {self.value} выходит из диапазона [{self.min_value}, {self.max_value}]"


def get_coordinates(city: str) -> Union[Tuple[float, float], None]:
    """
    Get coordinates by city name
    """

    url = f'https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ru&format=json'
    response = requests.get(url)

    if response.status_code == 200:
        log('info', 'Coordinates received for {}. Response code {}', city, response.status_code)
        data = response.json().get('results', [])
        
        if data:
            lat = data[0]['latitude']
            lon = data[0]['longitude']
            log('info', 'City: {}, latitude: {}, longitude: {}', city, lat, lon)
            return (lat, lon)
        else:
            log('info', 'Coordinates for city {} not found', city)
            return None
    else:
        log('info', 'Error: {}', response.status_code)
        return None

def get_weather(city: str) -> Union[float, None]:
    """
    Get geather by coordinates
    """

    coord = get_coordinates(city)
    if not coord:
        return None
    
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": coord[0],
        "longitude": coord[1],
        "hourly": "temperature_2m",
        "forecast_days": 1
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

    if list(hourly_temperature_2m):
        log('info', 'Max temperature for {} is {}', city, max(hourly_temperature_2m))

        hourly_data = {"date": pd.date_range(
            start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
            end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
            freq = pd.Timedelta(seconds = hourly.Interval()),
            inclusive = "left"
        )}
        hourly_data["temperature_2m"] = hourly_temperature_2m
        hourly_dataframe = pd.DataFrame(data = hourly_data)
        max_temp = max(hourly_dataframe['temperature_2m'])

        return max_temp
    
    else:
        log('info', 'Weather not found for {} with latitude {} and longitude {}', city, coord[0], coord[1])
        return None

def calculate_requirements(weight: float, height: float, age: int, activity: int, city: str, sex: str) -> Tuple[float, float]:
    """
    Calculating water goal and calories goal
    """

    # calculating water goal
    temp = get_weather(city)
    temp = temp if temp else 0
    high_temp_water = 0

    match temp:
        case _ if temp >= 35:
            high_temp_water = 1000
        case _ if temp >= 30:
            high_temp_water = 750
        case _ if temp >= 25:
            high_temp_water = 500

    water_goal = weight * 30 + (500 * (activity // 30)) + high_temp_water

    # calculating calorie goal
    if sex == 'жен':
        calorie_goal = int((9.99 * weight + 6.25 * height - 4.92 * age - 161))
    else:
        calorie_goal = int((9.99 * weight + 6.25 * height - 4.92 * age + 5))
    
    # calculating protein, fat and carbohydrates goal
    fat_goal = int(calorie_goal * 0.022)
    protein_goal = int(calorie_goal * 0.075)
    carbohydrates_goal = int(calorie_goal * 0.125)

    return (water_goal, calorie_goal, fat_goal, protein_goal, carbohydrates_goal)

async def get_food_info(food_name: str, calories_token: str) -> Dict:
    """
    Getting calories info by food name
    """

    api_url = 'https://api.calorieninjas.com/v1/nutrition?query='
    food_name = await translate_text(food_name)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url + food_name, headers={'X-Api-Key': calories_token}) as response:
                if response.status == 200:
                    data = await response.json()
                    log('info', 'Api successful request. {} response code: {}',api_url+food_name, response.status)

                    if data.get('items', []):
                        log('info', "Data received for {}", food_name)
                        return data
                    else:
                        log('info', 'No data was found for {}', food_name)
                        return None
                else:
                    log('info', 'Api error. Response code: {}',response.status)
                    return None
        except Exception as e:
            log('info', 'Error: {}', e)
            return None

async def translate_text(food_name: str) -> str:
    async with Translator() as translator:
        try:
            result = await translator.translate(food_name)

            if result.text:
                log('info', "Translated '{}' to '{}'", food_name, result.text)
                return result.text
            else:
                log('info', 'Failed to translate {}', food_name)
                return None

        except Exception as e:
            log('info', 'Error: {}', e)

def format_func(pct, allvals, performance):
    absolute = int(pct / 100. * sum(allvals))
    performance = performance * 100
    value = performance if performance > 100 else pct
    return '{:.1f}%\n({:d})'.format(value, absolute)

def get_pie_size(target, actual):
    if actual >= target:
        size = [actual]
        labels = ['Выполнено']
        colors_water = [(0.95, 0.7, 0.27)]
        colors_calories = [(0.86, 0.4, 0.31)]
        colors_activities = [(0.45, 0.84, 0.52)]
        performance = actual/target
    elif actual == 0:
        size = [target]
        labels = ['Осталось']
        colors_water = [(0.8, 0.8, 0.8)]
        colors_calories = [(0.8, 0.8, 0.8)]
        colors_activities = [(0.8, 0.8, 0.8)]
        performance = actual/target
    else:
        target = target - actual
        size = [target, actual]
        labels = ['Осталось', 'Выполнено']
        colors_water = [(0.8, 0.8, 0.8), (0.95, 0.7, 0.27)]
        colors_calories = [(0.8, 0.8, 0.8), (0.86, 0.4, 0.31)]
        colors_activities = [(0.8, 0.8, 0.8), (0.45, 0.84, 0.52)]
        performance = actual/target

    return (size, labels, (colors_water, colors_calories, colors_activities), performance)

def create_progress_chart(user_id, user_data):
    """
    Create progress plot
    """

    plot_dir = 'plots'
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)

    water_actual = user_data.get('logged_water', 0)
    water_target = user_data.get('water_goal', 0) + user_data.get('additional_water', 0)

    calories_actual = user_data.get('logged_calories', 0)
    calories_target = user_data.get('calorie_goal', 0) + user_data.get('burned_calories', 0)

    activities_actual = user_data.get('trained_time', 0)
    activities_target = user_data.get('activity', 0)
    
    fat_actual = user_data.get('logged_fat', 0)
    fat_target = user_data.get('fat_goal', 0)

    protein_actual = user_data.get('logged_protein', 0)
    protein_target = user_data.get('protein_goal', 0)

    carbohydrates_actual = user_data.get('logged_carbohydrates', 0)
    carbohydrates_target = user_data.get('carbohydrates_goal', 0)

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    data = [[get_pie_size(water_target, water_actual), get_pie_size(calories_target, calories_actual), get_pie_size(activities_target, activities_actual)],
            [get_pie_size(fat_target, fat_actual), get_pie_size(protein_target, protein_actual), get_pie_size(carbohydrates_target, carbohydrates_actual)]
            ]
    titles = [['Выполнение плана по воде, мл.', 'Выполнение плана по калориям, ккал.', 'Выполнение плана по спорту, мин.'],
              ['Выполнение плана по жирам, г.', 'Выполнение плана по белкам, г.', 'Выполнение плана по углеводам, г.']
              ]
    
    for j, group in enumerate(data):
        for i, elem in enumerate(group):
            axes[j][i].pie(elem[0], autopct=lambda pct: format_func(pct, elem[0], elem[3]), startangle=90, colors=elem[2][i])
            axes[j][i].axis('equal')
            axes[j][i].set_title(titles[j][i])
            axes[j][i].legend(elem[1])

    plt.tight_layout()
    plt.savefig(f'plots/{user_id}_progress.png', format='png')
    plt.close()

def setup_logging() -> None:
    '''
    logging settings
    '''

    log_dir = 'logs'
    log_file_path = os.path.join(log_dir, 'log_file.log')

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    if not os.path.isfile(log_file_path):
        open(log_file_path, 'a').close()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[RotatingFileHandler(log_file_path,
                                                      maxBytes=10*1024*1024,
                                                      backupCount=10),
                                  logging.StreamHandler()]
                                  )

def log(level: str, message: str, *args) -> None:
    '''
    Logging messages
    '''

    if level == 'info':
        logging.info(message.format(*args))
    elif level == 'error':
        logging.error(message.format(*args))
    elif level == 'warning':
        logging.warning(message.format(*args))
