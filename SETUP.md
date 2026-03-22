# 🚀 Инструкция по запуску GoodBooks

## Требования

- Python 3.8+
- Docker и Docker Compose (или MongoDB установленная локально)
- Git

## Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/AslanAbishev/BookMagaz.git
cd BookMagaz
```

## Шаг 2: Подготовка окружения

### Вариант A: С Docker (Рекомендуется)

1. Запустите MongoDB в Docker:
```bash
docker-compose up -d
```

Это запустит MongoDB на `mongodb://localhost:27017/`

### Вариант B: Без Docker (Локально установленная MongoDB)

Убедитесь, что MongoDB запущена:
```bash
# Windows
mongod

# Linux/Mac
brew services start mongodb-community
```

## Шаг 3: Создание виртуального окружения

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

## Шаг 4: Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

## Шаг 5: Инициализация базы данных

```bash
python db_setup.py
```

Это загрузит данные книг и рейтингов в MongoDB.

## Шаг 6: Запуск приложения

```bash
python app.py
```

Приложение будет доступно по адресу: **http://localhost:5000**

## 🎯 Функции приложения

✅ Регистрация и вход пользователя  
✅ Поиск и просмотр книг  
✅ Катеаория товаров  
✅ История покупок  
✅ Рейтинги и отзывы  
✅ Персональные рекомендации (AI)  

## 📁 Структура проекта

```
backend/
├── app.py              # Flask приложение
├── models.py           # Функции работы с БД
├── recommend.py        # Алгоритм рекомендаций
├── db_setup.py         # Инициализация БД
├── requirements.txt    # Зависимости Python
└── templates/          # HTML шаблоны
```

## ⚙️ Переменные окружения

Создайте файл `.env` в папке `backend/` (опционально):

```env
MONGO_URI=mongodb://localhost:27017/
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
```

## 🐛 Решение проблем

**Проблема:** "Connection refused" для MongoDB
- Убедитесь что MongoDB запущена (docker-compose up или mongod)

**Проблема:** "Module not found"
- Проверьте что виртуальное окружение активировано
- Переинсталируйте зависимости: `pip install -r requirements.txt`

**Проблема:** Порт 5000 уже занят
- Измените порт в `app.py` строка 139: `app.run(debug=True, port=5001)`

## 📝 Заметки

- CSV файлы (books.csv, ratings.csv) должны быть в папке `data/`
- Используйте `db_setup.py` только один раз для инициализации
- Для разработки используется `FLASK_ENV=development`

## 🤝 Контакты

Если есть вопросы - свяжитесь с автором проекта!
