import requests
from bs4 import BeautifulSoup
import sqlite3
import time

# Tor-Proxy-Einstellungen
proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

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

# Backlinks von einer .onion-Seite extrahieren
def extract_backlinks(url):
    try:
        response = requests.get(url, proxies=proxies, timeout=10)
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

# .onion-URLs
urls = [
    'http://p53lf57qovyuvwsc6xnrppyply3vtqm7l6pcobkmyqsiofyeznfu5uqd.onion',
    'http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion',
    'http://nytimesn7cgmftshazwhfgzm37qxb44r64ytbb2dj3x62d2lljsciiyd.onion',
    'http://sdolvtfhatvsysc6l34d65ymdwxcujausv7k5jk4cy5ttzhjoi6fzvyd.onion',
    'http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion',
    'http://keybase5wmilwokqirssclfnsqrjdsi7jdir5wy7y7iu3tanwmtp6oid.onion',
    'http://hctxrvjzfpvmzh2jllqhgvvkoepxb4kfzdjm6h7egcwlumggtktiftid.onion',
    'http://wasabiukrxmkdgve5kynjztuovbg43uxcbcxn6y2okcrsg7gb6jdmbad.onion',
    'http://portal.imprezareshna326gqgmbdzwmnad2wnjmeowh45bs2buxarh5qummjad.onion',
    'http://archiveiya74codqgiixo33q62qlrqtkgmcitqx5u2oeqnmn5bpcbiyd.onion',
    'http://facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd.onion',
    'http://ciadotgov4sjwlzihbbgxnqg3xiyrg7so2r2o3lt5wz5ypk4sxyjstad.onion',
    'http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxyd.onion',
    'http://darkfailenbsdla5mal2mxn2uz66od5vtzd5qozslagrfzachha3f3id.onion'
]

setup_database()
run_backlink_scraper(urls)
