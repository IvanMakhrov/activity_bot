# Activity bot

## Описание бота
Бот помогает рассчитывать дневную норму воды, калорий, белков, жиров и углеводов, а также отслеживать тренировки и питание

## Основные команды
* /start - Команда для начала работы с ботом
* /help - Выводит основные команды бота
* /set_profile - Создание профиля и расчет нормы воды, калорий, белков, жиров и углеводов
* /delete_profile - Удаление профиля
* /log_water <количество воды, мл> - Записать количество выпитой воды
* /log_food <Наименование еды> <Кол-во еды, г> - Записать количество съеденной еды
* /log_workout - Записать тренировку
* /check_progress - Посмотреть прогресс

## Методология расчета
На этапе формирования профиля бот заправшивает у пользователя следующие данные:
* Вес
* Рост
* Пол
* Возраст
* Длительность тренировок
* Цель по калориям
* Город

### Расчет цели по количеству воды
Кол-во воды - 30 мл на 1 кг веса + 500 мл за каждые 30 мин тренировок + дополнительная вода из-за высокой температуры + дополнительная вода из-за превышения времени плановой тренировки<br>
Дополнительная вода из-за температуры - Если температура больше 35 градусов, то добавляем 1000 мл, если больше 30 градусов, то добавляем 750 мл, если больше 25 градусов, то добавляем 500 мл<br>
Дополнительная вода из-за превышения времени плановой тренировки - Добавляем 7 мл за каждую минуту тренировки сверх плана<br>

### Расчет цели по количеству калорий
Количество калорий для женщин = 9.99 * Вес + 6.25 * Рост - 4.92 * Возраст - 161<br>
Количество калорий для мужчин = 9.99 * Вес + 6.25 * Рост - 4.92 * Возраст + 5<br>
Также добавляем сожженные калории на тренировке, которые считаются как длительность тренировки * расход калорий за минуту<br>

Расход калорий за минуту для каждого вида спорта различный:
* Бег - 10 ккал/мин
* Велосипед - 5.3 ккал/мин
* Йога - 3.75 ккал/мин
* Танцы - 6.7 ккал/мин
* Плавание - 3.83 ккал/мин
* Тренажерный зал - 11 ккал/мин
* Фигурное катание - 5 ккал/мин
* Лыжи - 8.1 ккал/мин
* Бокс - 14.2 ккал/мин
* Бадминтон - 6.75 ккал/мин
* Боулинг - 4.5 ккал/мин
* Большой теннис - 6.7 ккал/мин
* Футбол - 7.5 ккал/мин
* Настольный теннис - 5.25 ккал/мин
* Воллейбол - 4.25 ккал/мин

### Расчет цели по белкам, жирам и углеводам
Количество белков = Цель по калориям * 0.075<br>
Количество жиров = Цель по калориям * 0.022<br>
Количество углеводов = Цель по калориям * 0.125<br>

## Запуск бота
1. Клонировать репозиторий
```
git clone https://github.com/IvanMakhrov/activity_bot.git
```
2. Перейти в директорию app
```
cd app
```
3. Создать image 
```
docker build -t activity_bot .
```
4. Создать контейнер и запустить его в Docker указав токены для телеграм бота и для api с количеством калорий
```
docker run -e ACTIVITY_BOT_TOKEN="" -e CALORIES_TOKEN="" activity_bot
```

Для доступа к логам и изображениям в запущенном боте:<br>
```
docker exec -t -i container_name /bin/bash
```

## Демонстрация работы бота с логированием
![Alt text](https://github.com/IvanMakhrov/activity_bot/blob/main/images/docker_bot.gif?raw=true)

## Демонстрация деплоя на render.com
![Alt text](https://github.com/IvanMakhrov/activity_bot/blob/main/images/render_logs.png?raw=true)
