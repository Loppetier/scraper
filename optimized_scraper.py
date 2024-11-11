import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller
import sqlite3
import time

# Tor-Proxyeinstellungen
tor_proxy = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

# Verbindung zur Datenbank
conn = sqlite3.connect('optimized_backlinks.db')
cursor = conn.cursor()

# Tabellen erstellen
cursor.execute('''
CREATE TABLE IF NOT EXISTS pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS backlinks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    target_id INTEGER,
    anchor_text TEXT,
    timestamp DATETIME,
    FOREIGN KEY (source_id) REFERENCES pages (id),
    FOREIGN KEY (target_id) REFERENCES pages (id)
)
''')

conn.commit()

# Tor-IP erneuern
def renew_tor_ip():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password='your_tor_password')  # Passwort anpassen
        controller.signal(Signal.NEWNYM)
        time.sleep(10)  # Wartezeit nach IP-Wechsel

# Backlinks extrahieren und Navigationslinks filtern
def scrape_backlinks(source_url):
    # Liste der Navigationsankertexte
    navigation_keywords = ['Home', 'Über uns', 'Kontakt', 'Impressum', 'Datenschutz']
    # Liste typischer Navigationspfade
    navigation_paths = ['/home', '/about', '/contact', '/privacy', '/terms']

    try:
        response = requests.get(source_url, proxies=tor_proxy, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')

        for link in soup.find_all('a', href=True):
            target_url = link['href'].strip()
            anchor_text = link.get_text(strip=True)

            # Filterung von Navigationslinks basierend auf Ankertext und URL-Pfaden
            if anchor_text in navigation_keywords or any(nav_path in target_url for nav_path in navigation_paths):
                continue  # Ignoriere Navigationslinks

            # Nur valide und relevante Links weiterverarbeiten
            if not (target_url.startswith('/') or target_url.startswith('.')):
                print(f"Valid URL: {target_url}, Anchor: {anchor_text}")

                # URLs in die Tabelle "pages" einfügen
                cursor.execute("INSERT OR IGNORE INTO pages (url) VALUES (?)", (source_url,))
                cursor.execute("INSERT OR IGNORE INTO pages (url) VALUES (?)", (target_url,))

                source_id = cursor.execute("SELECT id FROM pages WHERE url = ?", (source_url,)).fetchone()[0]
                target_id = cursor.execute("SELECT id FROM pages WHERE url = ?", (target_url,)).fetchone()[0]

                # Backlink in die Tabelle "backlinks" einfügen
                cursor.execute('''
                    INSERT INTO backlinks (source_id, target_id, anchor_text, timestamp)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (source_id, target_id, anchor_text))

        conn.commit()
    except Exception as e:
        print(f"Fehler beim Abrufen von {source_url}: {e}")

# Liste von .onion-URLs
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

# Scraping-Prozess starten
for url in urls:
    scrape_backlinks(url)
    renew_tor_ip()  # Tor-IP regelmäßig erneuern

# Verbindung schließen
conn.close()
