from flask import Flask, jsonify
from flask_cors import CORS
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Включаем CORS для всего приложения

# Функция для парсинга страницы с конференциями с сайта konferencii.ru
def parse_conference_page_konferencii(html):
    soup = BeautifulSoup(html, 'html.parser')
    conferences = soup.find_all('div', class_='index_cat_1st')

    conference_data = []

    for conference in conferences:
        title_tag = conference.find('div', class_='index_cat_tit')
        if title_tag:
            title = title_tag.a.text.strip()
            link = title_tag.a['href']
        else:
            title = None
            link = None

        date_tag = conference.find('div', class_='left')
        if date_tag:
            date = date_tag.text.strip().split('—')[0].strip()
        else:
            date = None

        organizers_tag = conference.find('p', class_='small_p')
        if organizers_tag:
            organizers = organizers_tag.text.strip().replace('Организаторы:', '').strip()
        else:
            organizers = None

        location_tag = conference.find('p', class_='ross_p')
        if location_tag:
            location = location_tag.b.text.strip()
        else:
            location = None

        if title and date and organizers and location and location.startswith('Россия'):
            conference_data.append({
                'title': title,
                'date': date,
                'organizers': organizers,
                'link': link,
                'location': location,
                'source': 'konferencii.ru'  # Добавляем поле источник
            })

    return conference_data

# Функция для парсинга страницы с конференциями с сайта konferen.ru
def parse_conference_page_konferen(html):
    soup = BeautifulSoup(html, 'html.parser')
    event_heads = soup.find_all('div', class_='event-head')

    conference_data = []

    for event in event_heads:
        image_div = event.find('div', class_='span2')
        image_url = image_div.find('img')['src'] if image_div else None

        title_div = event.find('div', class_='span10')
        title_link = title_div.find('a') if title_div else None
        title = title_link.text.strip() if title_link else None
        link = title_link['href'] if title_link else None

        dates_span = event.find('span', class_='alert-info dates')
        dates = dates_span.text.strip() if dates_span else None

        sponsor_p = event.find('p', class_='sponsor')
        sponsor = sponsor_p.text.strip() if sponsor_p else None

        location = dates.split(' ')[-1] if dates else None
        date = ' '.join(dates.split(' ')[:3]) if dates else None

        if title and date and sponsor and location:
            conference_data.append({
                'title': title,
                'date': date,
                'organizers': sponsor,
                'link': link,
                'location': location,
                'source': 'konferen.ru'  # Добавляем поле источник
            })

    return conference_data

# Функция для определения количества страниц на konferencii.ru
async def get_total_pages_konferencii(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            visible_links = soup.find('div', id='visibleLinks')
            if visible_links:
                pages = visible_links.find_all('a')
                if pages:
                    return int(pages[-1].text)
    return 1

# Функция для определения количества страниц на konferen.ru
async def get_total_pages_konferen(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            pager = soup.find('div', class_='pager')
            if pager:
                page_links = pager.find_all('li', class_='page')
                if page_links:
                    return len(page_links)
    return 1

# Асинхронная функция для загрузки и парсинга одной страницы с konferencii.ru
async def fetch_and_parse_page_konferencii(session, page_number):
    base_url = "https://konferencii.ru/year/2024/"
    url = f"{base_url}{page_number}"
    async with session.get(url) as response:
        if response.status == 200:
            html = await response.text()
            return parse_conference_page_konferencii(html)
        return []

# Асинхронная функция для загрузки и парсинга одной страницы с konferen.ru
async def fetch_and_parse_page_konferen(session, page_number):
    current_date = datetime.now().strftime("%d.%m.%Y")
    base_url = f"https://konferen.ru/date/{current_date}"
    url = f"{base_url}?Event_page={page_number}&ajax=yw0"
    async with session.get(url) as response:
        if response.status == 200:
            html = await response.text()
            return parse_conference_page_konferen(html)
        return []

# Асинхронная функция для загрузки и парсинга всех страниц с konferencii.ru
async def fetch_all_conferences_konferencii(total_pages):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_parse_page_konferencii(session, page_number) for page_number in range(1, total_pages + 1)]
        results = await asyncio.gather(*tasks)
        return results

# Асинхронная функция для загрузки и парсинга всех страниц с konferen.ru
async def fetch_all_conferences_konferen(total_pages):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_parse_page_konferen(session, page_number) for page_number in range(1, total_pages + 1)]
        results = await asyncio.gather(*tasks)
        return results

@app.route('/conferences', methods=['GET'])
def get_all_conferences():
    base_url_konferencii = "https://konferencii.ru/year/2024/"
    base_url_konferen = f"https://konferen.ru/date/{datetime.now().strftime('%d.%m.%Y')}"

    # Определяем количество страниц для обоих источников
    async def get_total_pages_and_fetch():
        async with aiohttp.ClientSession() as session:
            total_pages_konferencii = await get_total_pages_konferencii(session, base_url_konferencii + "1")
            total_pages_konferen = await get_total_pages_konferen(session, base_url_konferen)

            results_konferen = await fetch_all_conferences_konferen(total_pages_konferen)
            results_konferencii = await fetch_all_conferences_konferencii(total_pages_konferencii)

            return results_konferen, results_konferencii

    # Запускаем асинхронную функцию и получаем результаты
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results_konferen, results_konferencii = loop.run_until_complete(get_total_pages_and_fetch())
    loop.close()

    # Объединяем результаты, сначала konferen.ru, затем konferencii.ru
    all_conferences = []
    for conferences in results_konferen:
        all_conferences.extend(conferences)
    for conferences in results_konferencii:
        all_conferences.extend(conferences)

    return jsonify(all_conferences)

if __name__ == '__main__':
    app.run(host='localhost', port=5002)