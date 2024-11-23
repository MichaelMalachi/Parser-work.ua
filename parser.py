import requests
from bs4 import BeautifulSoup
import time
import re
import json
import csv
import sqlite3

try:
    # Инициализация списка для JSON
    data = []

    # Создаем или перезаписываем CSV-файл
    csv_file = open('jobs.csv', mode='w', newline='', encoding='utf-8-sig')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Название вакансии', 'Компания', 'Описание вакансии', 'Зарплата', 'Ссылка'])

    # Подключение к SQLite
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()

    # Создаем таблицу, если она не существует
    cursor.execute('DROP TABLE IF EXISTS jobs')
    cursor.execute('''
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            description TEXT,
            salary TEXT,
            link TEXT
        )
    ''')

    page = 1
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/115.0.0.0 Safari/537.36'
        )
    }

    while True:
        url = f'https://www.work.ua/jobs-python/?page={page}'
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(
                f"Ошибка доступа к странице {url}: статус "
                f"{response.status_code}"
            )
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        job_cards = soup.find_all('div', class_='card-hover')

        print(f"Найдено {len(job_cards)} вакансий на странице {page}")

        if not job_cards:
            break

        for job in job_cards:
            # Поиск названия вакансии
            title_tag = job.find('h2')
            link_tag = title_tag.find('a') if title_tag else None
            title = (
                link_tag.get_text(strip=True)
                if link_tag else 'Нет названия'
            )

            # Поиск ссылки
            link = (
                'https://www.work.ua' + link_tag['href']
                if link_tag else 'Нет ссылки'
            )

            # Поиск названия компании
            company = 'Нет компании'
            company_div = job.find('div', class_='mt-xs')
            if company_div:
                # Первый вариант: <span class="mr-xs"><span class="strong-600">
                first_span = company_div.find('span', class_='mr-xs')
                if first_span:
                    company_span = first_span.find('span', class_='strong-600')
                    if company_span:
                        company = company_span.get_text(strip=True)
                else:
                    # Второй вариант: <span class=""><span class="strong-600">
                    second_span = company_div.find('span', class_='')
                    if second_span:
                        company_span = second_span.find('span', class_='strong-600')
                        if company_span:
                            company = company_span.get_text(strip=True)

            # Поиск зарплаты
            salary = 'Не указана'
            salary_span = job.find('span', class_='strong-600')
            if salary_span:
                salary_text = salary_span.get_text(strip=True)
                # Проверяем, содержит ли текст символы валюты
                if any(c in salary_text for c in ['грн', '$', '€']):
                    salary = salary_text
                    # Очистка зарплаты от специальных символов
                    salary = re.sub(r'[\u00A0\u202F\u2009\u200A]', '', salary)
                    salary = ''.join(c for c in salary if c.isprintable())

            # Поиск описания вакансии
            description_tag = job.find('p')
            description = (
                description_tag.get_text(strip=True)
                if description_tag else 'Нет описания'
            )

            # Вывод данных
            print(
                f"Страница {page} - Вакансия: {title}, "
                f"Компания: {company}, Зарплата: {salary}"
            )
            print(f"Описание: {description}\n")

            # Формирование словаря с данными вакансии
            job_data = {
                'title': title,
                'company': company,
                'description': description,
                'salary': salary,
                'link': link
            }

            # Добавление в список для JSON
            data.append(job_data)

            # Запись в CSV
            csv_writer.writerow([title, company, description, salary, link])

            # Запись в базу данных SQLite
            cursor.execute('''
                INSERT INTO jobs (title, company, description, salary, link)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, company, description, salary, link))
            conn.commit()

        page += 1
        time.sleep(1)

except Exception as e:
    print(f"Произошла ошибка: {e}")

finally:
    # Закрытие CSV-файла
    csv_file.close()

    # Закрытие подключения к SQLite
    conn.close()

    # Сохранение в JSON-файл
    with open('jobs.json', 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

    print("Данные сохранены в файлы jobs.csv, jobs.db и jobs.json")
