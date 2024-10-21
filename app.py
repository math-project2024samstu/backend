from flask import Flask, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)
CORS(app)  # Добавляем CORS

@app.route('/conferences', methods=['GET'])
def get_conferences():
    url = "https://konferen.ru/tematic/filter/17?Event_page=8"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    conferences = []
    for conference in soup.find_all('div', class_='row-fluid event-head'):
        title_tag = conference.find('h4').find('a')
        date_tag = conference.find('span', class_='alert-info dates')
        sponsor_tag = conference.find('p', class_='sponsor')

        conferences.append({
            "title": title_tag.text.strip() if title_tag else "Название не найдено",
            "date": date_tag.text.strip() if date_tag else "Дата не найдена",
            "sponsor": sponsor_tag.text.strip() if sponsor_tag else "Организаторы не найдены"
        })

    return jsonify(conferences)

if __name__ == '__main__':
    app.run(debug=True)
