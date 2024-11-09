import requests
from bs4 import BeautifulSoup
import sqlite3
import time

# Datenbank einrichten
def setup_database():
    conn = sqlite3.connect('backlinks_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS backlinks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_url TEXT,
                        target_url TEXT,
                        anchor_text TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')
    conn.commit()
    conn.close()

# Backlinks von einer Webseite extrahieren
def extract_backlinks(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        backlinks = []
        for link in links:
            anchor_text = link.text.strip()
            target_url = link['href']
            backlinks.append((url, target_url, anchor_text))
        
        return backlinks
    except Exception as e:
        print(f"Fehler beim Zugriff auf {url}: {e}")
        return []

# Backlinks in die Datenbank speichern
def save_backlinks(backlinks):
    conn = sqlite3.connect('backlinks_data.db')
    cursor = conn.cursor()
    cursor.executemany('''INSERT INTO backlinks (source_url, target_url, anchor_text)
                          VALUES (?, ?, ?)''', backlinks)
    conn.commit()
    conn.close()

# Hauptprozess
def run_backlink_scraper(urls):
    for url in urls:
        print(f"Scraping Backlinks von {url}")
        backlinks = extract_backlinks(url)
        save_backlinks(backlinks)
        time.sleep(2)  # Wartezeit zwischen den Anfragen

# Beispiel-URLs
urls = ['https://example.com', 'https://anotherexample.com']

setup_database()
run_backlink_scraper(urls)
