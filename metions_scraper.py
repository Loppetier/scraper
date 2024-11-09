import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import time

# Datenbank einrichten
def setup_mentions_database():
    conn = sqlite3.connect('mentions_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS mentions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT,
                        mention TEXT,
                        context TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')
    conn.commit()
    conn.close()

# Erwähnungen auf einer Webseite extrahieren
def extract_mentions(url, keyword):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text()
        
        mentions = []
        for match in re.finditer(rf'(.{{0,50}}{keyword}.{{0,50}})', text_content, re.IGNORECASE):
            context = match.group(0)
            mentions.append((url, keyword, context.strip()))
        
        return mentions
    except Exception as e:
        print(f"Fehler beim Zugriff auf {url}: {e}")
        return []

# Erwähnungen in die Datenbank speichern
def save_mentions(mentions):
    conn = sqlite3.connect('mentions_data.db')
    cursor = conn.cursor()
    cursor.executemany('''INSERT INTO mentions (url, mention, context)
                          VALUES (?, ?, ?)''', mentions)
    conn.commit()
    conn.close()

# Hauptprozess
def run_mentions_scraper(urls, keyword):
    for url in urls:
        print(f"Suche nach Erwähnungen von '{keyword}' auf {url}")
        mentions = extract_mentions(url, keyword)
        save_mentions(mentions)
        time.sleep(2)  # Wartezeit zwischen den Anfragen

# Beispiel-URLs und Keyword
urls = ['https://example.com', 'https://anotherexample.com']
keyword = 'Datenschutz'

setup_mentions_database()
run_mentions_scraper(urls, keyword)
