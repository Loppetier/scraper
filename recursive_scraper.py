import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller
import sqlite3
import time
from urllib.parse import urlparse

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

cursor.execute('''
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    level TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()

# Tor-IP erneuern
def renew_tor_ip():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password='your_tor_password')
            controller.signal(Signal.NEWNYM)
            time.sleep(10)
            log_event("INFO", "Tor-IP erfolgreich erneuert.")
    except Exception as e:
        log_event("ERROR", f"Fehler beim Erneuern der Tor-IP: {e}")

# Log-Ereignis speichern
def log_event(level, message, url=None):
    cursor.execute('''
        INSERT INTO logs (url, level, message)
        VALUES (?, ?, ?)
    ''', (url, level, message))
    conn.commit()

# Backlinks extrahieren und speichern
def scrape_backlinks(source_url, depth=2):
    """
    Scraped die Backlinks einer Seite rekursiv bis zur angegebenen Tiefe.
    :param source_url: URL der zu scrapenden Seite.
    :param depth: Rekursive Tiefe.
    """
    if depth == 0:
        return  # Rekursion endet hier

    try:
        response = requests.get(source_url, proxies=tor_proxy, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        log_event("INFO", f"Erfolgreich auf {source_url} zugegriffen.", source_url)

        cursor.execute("INSERT OR IGNORE INTO pages (url) VALUES (?)", (source_url,))
        source_id = cursor.execute("SELECT id FROM pages WHERE url = ?", (source_url,)).fetchone()[0]

        for link in soup.find_all('a', href=True):
            target_url = link['href'].strip()
            anchor_text = link.get_text(strip=True)

            # Relative URLs auflösen
            if target_url.startswith('/'):
                target_url = f"{urlparse(source_url).scheme}://{urlparse(source_url).netloc}{target_url}"

            # Nur valide HTTP/S-Links weiterverarbeiten
            if not target_url.startswith('http'):
                continue

            # Keine internen Links speichern
            if urlparse(source_url).netloc == urlparse(target_url).netloc:
                continue

            cursor.execute("INSERT OR IGNORE INTO pages (url) VALUES (?)", (target_url,))
            target_id = cursor.execute("SELECT id FROM pages WHERE url = ?", (target_url,)).fetchone()[0]

            # Backlink in die Datenbank einfügen
            cursor.execute('''
                INSERT INTO backlinks (source_id, target_id, anchor_text, timestamp)
                VALUES (?, ?, ?, datetime('now'))
            ''', (source_id, target_id, anchor_text))
            log_event("INFO", f"Backlink gespeichert: {source_url} -> {target_url}", source_url)

            # Rekursive Suche für das Ziel der aktuellen Backlink
            scrape_backlinks(target_url, depth=depth - 1)

        conn.commit()
    except requests.exceptions.RequestException as e:
        log_event("ERROR", f"HTTP-Fehler bei {source_url}: {e}", source_url)
    except Exception as e:
        log_event("ERROR", f"Allgemeiner Fehler bei {source_url}: {e}", source_url)

# Liste von .onion-URLs
urls = [
    'http://p53lf57qovyuvwsc6xnrppyply3vtqm7l6pcobkmyqsiofyeznfu5uqd.onion',
    'http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion',
    'http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxyd.onion',
    'http://p53lf57qovyuvwsc6xnrppyply3vtqm7l6pcobkmyqsiofyeznfu5uqd.onion',
    'http://zqktlwiuavvvqqt4ybvgvi7tyo4hjl5xgfuvpdf6otjiycgwqbym2qad.onion',
    'http://jaz45aabn5vkemy4jkg4mi4syheisqn2wn2n4fsuitpccdackjwxplad.onion',
    'http://bj5hp4onm4tvpdb5rzf4zsbwoons67jnastvuxefe4s3v7kupjhgh6qd.onion',
    'http://qrtitjevs5nxq6jvrnrjyz5dasi3nbzx24mzmfxnuk2dnzhpphcmgoyd.onion',
    'http://xsglq2kdl72b2wmtn5b2b7lodjmemnmcct37owlz5inrhzvyfdnryqid.onion',
    'http://zwf5i7hiwmffq2bl7euedg6y5ydzze3ljiyrjmm7o42vhe7ni56fm7qd.onion',
    'http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion',
    'http://torlinksge6enmcyyuxjpjkoouw4oorgdgeo7ftnq3zodj7g2zxi3kyd.onion',
    'http://xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion',
    'http://zqktlwi4fecvo6ri.onion/wiki/index.php/Main_Page',
    'http://vw5vzi62xqhihghvonatid7imut2rkgiudl3xomj4jftlmanuwh4r2qd.onion',
    'http://56dlutemceny6ncaxolpn6lety2cqfz5fd64nx4ohevj4a7ricixwzad.onion',
    'http://hbl6udan73w7qbjdey6chsu5gq5ehrfqbb73jq726kj3khnev2yarlid.onion',
    'http://netauthlixnkiat36qeh25w5t6ljyqwug3me6nprebo4s74lzvm3p3id.onion',
    'http://financo6ytrzaoqg.onion',
    'http://d46a7ehxj6d6f2cf4hi3b424uzywno24c7qtnvdvwsah5qpogewoeqid.onion',
    'http://hssza6r6fbui4x452ayv3dkeynvjlkzllezxf3aizxppmcfmz2mg7uad.onion',
    'http://n3irlpzwkcmfochhuswpcrg35z7bzqtaoffqecomrx57n3rd5jc72byd.onion'

	
]

# Scraping-Prozess starten
for url in urls:
    scrape_backlinks(url, depth=3)  # Rekursive Tiefe auf 3 setzen
    renew_tor_ip()

# Verbindung schließen
conn.close()