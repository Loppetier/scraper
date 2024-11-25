import requests
from bs4 import BeautifulSoup
from stem import Signal
from stem.control import Controller
import sqlite3
import time
from urllib.parse import urljoin, urlparse
import datetime

# Tor-Proxyeinstellungen
tor_proxy = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

# Verbindung zur Datenbank
conn = sqlite3.connect('tor_backlinks.db')
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
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
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

# Fortschrittsanzeige
processed_urls = set()
start_time = time.time()

def show_progress(current, total):
    elapsed_time = time.time() - start_time
    avg_time_per_url = elapsed_time / current if current > 0 else 0
    remaining_time = avg_time_per_url * (total - current)

    elapsed_str = str(datetime.timedelta(seconds=int(elapsed_time)))
    remaining_str = str(datetime.timedelta(seconds=int(remaining_time)))

    progress = (current / total) * 100 if total > 0 else 0
    print(f"Fortschritt: {current}/{total} URLs ({progress:.2f}%)")
    print(f"Vergangene Zeit: {elapsed_str}, Verbleibende Zeit: {remaining_str}")

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

# URLs validieren
def is_valid_onion_url(url):
    return url.endswith('.onion')

# Backlinks extrahieren und speichern
def scrape_backlinks(source_url):
    if source_url in processed_urls:
        return
    processed_urls.add(source_url)

    try:
        response = requests.get(source_url, proxies=tor_proxy, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        log_event("INFO", f"Erfolgreich auf {source_url} zugegriffen.", source_url)

        # Quellseite speichern
        if is_valid_onion_url(source_url):
            cursor.execute("INSERT OR IGNORE INTO pages (url) VALUES (?)", (source_url,))
            source_id = cursor.execute("SELECT id FROM pages WHERE url = ?", (source_url,)).fetchone()[0]
        else:
            log_event("WARNING", f"Ungültige Quelle ignoriert: {source_url}")
            return

        for link in soup.find_all('a', href=True):
            target_url = link['href'].strip()

            # Relative URLs in absolute URLs umwandeln
            if target_url.startswith('/'):
                target_url = urljoin(source_url, target_url)

            # Nur `.onion`-Adressen speichern
            if not is_valid_onion_url(target_url):
                continue

            # Zielseite speichern
            cursor.execute("INSERT OR IGNORE INTO pages (url) VALUES (?)", (target_url,))
            target_id = cursor.execute("SELECT id FROM pages WHERE url = ?", (target_url,)).fetchone()[0]

            # Backlink speichern
            cursor.execute('''
                INSERT INTO backlinks (source_id, target_id, timestamp)
                VALUES (?, ?, datetime('now'))
            ''', (source_id, target_id))

            log_event("INFO", f"Backlink gespeichert: {source_url} -> {target_url}", source_url)

        conn.commit()
        show_progress(len(processed_urls), len(urls_to_process) + len(processed_urls))

    except requests.exceptions.RequestException as e:
        log_event("ERROR", f"HTTP-Fehler bei {source_url}: {e}", source_url)
    except Exception as e:
        log_event("ERROR", f"Allgemeiner Fehler bei {source_url}: {e}", source_url)

# Rückwärts-Suche von Backlinks
def find_referring_pages(target_url):
    search_engines = [
        'http://6pxxjp7iwjbvtrfv3qqgz36zm6nnovi3xujepycve3n4jirg5vpmorad.onion',
        'http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion',
        'http://darknetlidvrsli6iso7my54rjayjursyw637aypb6qambkoepmyq2yd.onion'
    
    ]

    for engine in search_engines:
        try:
            search_url = f"{engine}/search?q={target_url}"
            response = requests.get(search_url, proxies=tor_proxy, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            for link in soup.find_all('a', href=True):
                referring_url = link['href'].strip()
                if referring_url.startswith('/'):
                    referring_url = urljoin(engine, referring_url)

                if is_valid_onion_url(referring_url):
                    urls_to_process.append(referring_url)
        except Exception as e:
            log_event("ERROR", f"Fehler bei der Rückwärtssuche für {target_url}: {e}")

# Liste von `.onion`-Startseiten
urls_to_process = [
'http://2356uhnbpv5nk3bni5bv6jg2cd6lgj664kwx3lhyelstpttpyv4kk2qd.onion',
'http://2bcbla34hrkp6shb4myzb2wntl2fxdbrroc2t4t7c3shckvhvk4fw6qd.onion',
'http://2ezyofc26j73hv3xxvsrnbc23dqxhgxqtk5ogcc7y6j5t6rlqquvhzid.onion',
'http://2gzyxa5ihm7nsggfxnu52rck2vv4rvmdlkiu3zzui5du4xyclen53wid.onion',
'http://2jwcnprqbugvyi6ok2h2h7u26qc6j5wxm7feh3znlh2qu3h6hjld4kyd.onion',
'http://2ln3x7ru6psileh7il7jot2ufhol4o7nd54z663xonnnmmku4dgkx3ad.onion',
'http://3bp7szl6ehbrnitmbyxzvcm3ieu7ba2kys64oecf4g2b65mcgbafzgqd.onion',
'http://3xeiol2bnhrsqhcsaifwtnlqkylrerdspzua7bcjrh26qlrrrctfobid.onion',
'http://45tbhx5prlejzjgn36nqaxqb6qnm73pbohuvqkpxz2zowh57bxqawkid.onion',
'http://4p6i33oqj6wgvzgzczyqlueav3tz456rdu632xzyxbnhq4gpsriirtqd.onion',
'http://4usoivrpy52lmc4mgn2h34cmfiltslesthr56yttv2pxudd3dapqciyd.onion',
'http://4wbwa6vcpvcr3vvf4qkhppgy56urmjcj2vagu2iqgp3z656xcmfdbiqd.onion',
'http://55niksbd22qqaedkw36qw4cpofmbxdtbwonxam7ov2ga62zqbhgty3yd.onion',
'http://5kpq325ecpcncl4o2xksvaso5tuydwj2kuqmpgtmu3vzfxkpiwsqpfid.onion',
'http://5wvugn3zqfbianszhldcqz2u7ulj3xex6i3ha3c5znpgdcnqzn24nnid.onion',
'http://6hasakffvppilxgehrswmffqurlcjjjhd76jgvaqmsg6ul25s7t3rzyd.onion',
'http://6hzbfxpnsdo4bkplp5uojidkibswevsz3cfpdynih3qvfr24t5qlkcyd.onion',
'http://6nhmgdpnyoljh5uzr5kwlatx2u3diou4ldeommfxjz3wkhalzgjqxzqd.onion',
'http://6o2ewykepkp7k65bvxjqhoqmh3osksxrhpd3e6oyhiw5yl3skbyvzuad.onion',
'http://74ck36pbaxz7ra6n7v5pbpm5n2tsdaiy4f6p775qvjmowxged65n3cid.onion',
'http://7bw24ll47y7aohhkrfdq2wydg3zvuecvjo63muycjzlbaqlihuogqvyd.onion',
'http://7mejofwihleuugda5kfnr7tupvfbaqntjqnfxc4hwmozlcmj2cey3hqd.onion',
'http://7sk2kov2xwx6cbc32phynrifegg6pklmzs7luwcggtzrnlsolxxuyfyd.onion',
'http://7wsvq2aw5ypduujgcn2zauq7sor2kqrqidguwwtersivfa6xcmdtaayd.onion',
'http://abrx6wcpzkfpwxb5eb2wsra2wnkrv2macdtkpnrepswodz5jxd4schyd.onion',
'http://ajlu6mrc7lwulwakojrgvvtarotvkvxqosb4psxljgobjhureve4kdqd.onion',
'http://answerszuvs3gg2l64e6hmnryudl5zgrmwm3vh65hzszdghblddvfiqd.onion',
'http://archivebyd3rzt3ehjpm4c3bjkyxv3hjleiytnvxcn7x32psn2kxcuid.onion',
'http://awsvrc7occzj2yeyqevyrw7ji5ejuyofhfomidhh5qnuxpvwsucno7id.onion',
'http://bepig5bcjdhtlwpgeh3w42hffftcqmg7b77vzu7ponty52kiey5ec4ad.onion',
'http://bible4u2lvhacg4b3to2e2veqpwmrc2c3tjf2wuuqiz332vlwmr4xbad.onion',
'http://bj5hp4onm4tvpdb5rzf4zsbwoons67jnastvuxefe4s3v7kupjhgh6qd.onion',
'http://blkchairbknpn73cfjhevhla7rkp4ed5gg2knctvv7it4lioy22defid.onion',
'http://bombsjy5lsgehdyuevxu5kt3zdw22bfqrhbanc32evab3o3j3dvc7cid.onion',
'http://c5xoy22aadb2rqgw3jh2m2irmu563evukqqddu5zjandunaimzaye5id.onion',
'http://cathug2kyi4ilneggumrenayhuhsvrgn6qv2y47bgeet42iivkpynqad.onion',
'http://cct5wy6mzgmft24xzw6zeaf55aaqmo6324gjlsghdhbiw5gdaaf4pkad.onion',
'http://cgjzkysxa4ru5rhrtr6rafckhexbisbtxwg2fg743cjumioysmirhdad.onion',
'http://ciadotgov4sjwlzihbbgxnqg3xiyrg7so2r2o3lt5wz5ypk4sxyjstad.onion',
'http://cr32aykujaxqkfqyrjvt7lxovnadpgmghtb3y4g6jmx6oomr572kbuqd.onion',
'http://ctemplarpizuduxk3fkwrieizstx33kg5chlvrh37nz73pv5smsvl6ad.onion',
'http://danielas3rtn54uwmofdo3x2bsdifr47huasnmbgqzfrec5ubupvtpid.onion',
'http://darkzzx4avcsuofgfez5zq75cqc4mprjvfqywo45dfcaxrwqg6qrlfid.onion',
'http://dds6qkxpwdeubwucdiaord2xgbbeyds25rbsgr73tbfpqpt4a6vjwsyd.onion',
'http://dhosting4xxoydyaivckq7tsmtgi4wfs3flpeyitekkmqwu4v4r46syd.onion',
'http://digdeep4orxw6psc33yxa2dgmuycj74zi6334xhxjlgppw6odvkzkiad.onion',
'http://dngtk6iydmpokbyyk3irqznceft3hze6q6rasrqlz46v7pq4klxnl4yd.onion',
'http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion',
'http://dumlq77rikgevyimsj6e2cwfsueo7ooynno2rrvwmppngmntboe2hbyd.onion',
'http://eludemailxhnqzfmxehy3bk5guyhlxbunfyhkcksv4gvx6d3wcf6smad.onion',
'http://endchancxfbnrfgauuxlztwlckytq7rgeo5v6pc2zd4nyqo3khfam4ad.onion',
'http://endtovmbc5vokdpnxrhajcwgkfbkfz4wbyhbj6ueisai4prtvencheyd.onion',
'http://enxx3byspwsdo446jujc52ucy2pf5urdbhqw3kbsfhlfjwmbpj5smdad.onion',
'http://explorerzydxu5ecjrkwceayqybizmpjjznk5izmitf2modhcusuqlid.onion',
'http://ez37hmhem2gh3ixctfeaqn7kylal2vyjqsedkzhu4ebkcgikrigr5gid.onion',
'http://f6wqhy6ii7metm45m4mg6yg76yytik5kxe6h7sestyvm6gnlcw3n4qad.onion',
'http://dds6qkxpwdeubwucdiaord2xgbbeyds25rbsgr73tbfpqpt4a6vjwsyd.onion',
'http://fwfwqtpi2ofmehzdxe3e2htqfmhwfciwivpnsztv7dvpuamhr72ktlqd.onion',
'http://g7ejphhubv5idbbu3hb3wawrs5adw7tkx7yjabnf65xtzztgg4hcsqqd.onion',
'http://gch3dyxo5zuqbrrtd64zlvzwxden4jkikyqk3ikjhggqzoxixcmq2fid.onion',
'http://gd5x24pjoan2pddc2fs6jlmnqbawq562d2qyk6ym4peu5ihzy6gd4jad.onion',
'http://fwfwqtpi2ofmehzdxe3e2htqfmhwfciwivpnsztv7dvpuamhr72ktlqd.onion',
'http://gkcns4d3453llqjrksxdijfmmdjpqsykt6misgojxlhsnpivtl3uwhqd.onion',
'http://gn74rz534aeyfxqf33hqg6iuspizulmvpd7zoyz7ybjq4jo3whkykryd.onion',
'http://guzjgkpodzshso2nohspxijzk5jgoaxzqioa7vzy6qdmwpz3hq4mwfid.onion',
'http://he5dybnt7sr6cm32xt77pazmtm65flqy6irivtflruqfc5ep7eiodiad.onion',
'http://hqfld5smkr4b4xrjcco7zotvoqhuuoehjdvoin755iytmpk4sm7cbwad.onion',
'http://hyjgsnkanan2wsrksd53na4xigtxhlz57estwqtptzhpa53rxz53pqad.onion',
'http://hyxme2arc5jnevzlou547w2aaxubjm7mxhbhtk73boiwjxewawmrz6qd.onion',
'http://hzwjmjimhr7bdmfv2doll4upibt5ojjmpo3pbp5ctwcg37n3hyk7qzid.onion',
'http://fwfwqtpi2ofmehzdxe3e2htqfmhwfciwivpnsztv7dvpuamhr72ktlqd.onion',
'http://iwggpyxn6qv3b2twpwtyhi2sfvgnby2albbcotcysd5f7obrlwbdbkyd.onion',
'http://jaz45aabn5vkemy4jkg4mi4syheisqn2wn2n4fsuitpccdackjwxplad.onion',
'http://jbtb75gqlr57qurikzy2bxxjftzkmanynesmoxbzzcp7qf5t46u7ekqd.onion',
'http://jgwe5cjqdbyvudjqskaajbfibfewew4pndx52dye7ug3mt3jimmktkid.onion',
'http://jhi4v5rjly75ggha26cu2eeyfhwvgbde4w6d75vepwxt2zht5sqfhuqd.onion',
'http://jn6weomv6klvnwdwcgu55miabpwklsmmyaf5qrkt4miif4shrqmvdhqd.onion',
'http://jptvwdeyknkv6oiwjtr2kxzehfnmcujl7rf7vytaikmwlvze773uiyyd.onion',
'http://k6m3fagp4w4wspmdt23fldnwrmknse74gmxosswvaxf3ciasficpenad.onion',
'http://kaizushih5iec2mxohpvbt5uaapqdnbluaasa2cmsrrjtwrbx46cnaid.onion',
'http://kallist4mcluuxbjnr5p2asdlmdhaos3pcrvhk3fbzmiiiftwg6zncid.onion',
'http://keybase5wmilwokqirssclfnsqrjdsi7jdir5wy7y7iu3tanwmtp6oid.onion',
'http://kfahv6wfkbezjyg4r6mlhpmieydbebr5vkok5r34ya464gqz6c44bnyd.onion',
'http://killnod2s77o3axkktdu52aqmmy4acisz2gicbhjm4xbvxa2zfftteyd.onion',
'http://kl4gp72mdxp3uelicjjslqnpomqfr5cbdd3wzo5klo3rjlqjtzhaymqd.onion',
'http://ko5enel7ogpruey25y3pcfmobcwrjiwwhyjp3t5nqsuqoytpsjrls2qd.onion',
'http://kq4okz5kf4xosbsnvdr45uukjhbm4oameb6k6agjjsydycvflcewl4qd.onion',
'http://kx5thpx2olielkihfyo4jgjqfb7zx7wxr3sd4xzt26ochei4m6f7tayd.onion',
'http://lainwir3s4y5r7mqm3kurzpljyf77vty2hrrfkps6wm4nnnqzest4lqd.onion',
'http://libraryfyuybp7oyidyya3ah5xvwgyx6weauoini7zyz555litmmumad.onion',
'http://lkqx6qn7whctpdjhcoohpoyi6ahtrveuii7kq2m647ssvo5skqp7ioad.onion',
'http://lldan5gahapx5k7iafb3s4ikijc4ni7gx5iywdflkba5y2ezyg6sjgyd.onion',
'http://lpiyu33yusoalp5kh3f4hak2so2sjjvjw5ykyvu2dulzosgvuffq6sad.onion',
'http://lqcjo7esbfog5t4r4gyy7jurpzf6cavpfmc4vkal4k2g4ie66ao5mryd.onion',
'http://meynethaffeecapsvfphrcnfrx44w2nskgls2juwitibvqctk2plvhqd.onion',
'http://mp3fpv6xbrwka4skqliiifoizghfbjy5uyu77wwnfruwub5s4hly2oid.onion',
'http://n6qisfgjauj365pxccpr5vizmtb5iavqaug7m7e4ewkxuygk5iim6yyd.onion',
'http://nanochanqzaytwlydykbg5nxkgyjxk3zsrctxuoxdmbx5jbh2ydyprid.onion',
'http://ncidetfs7banpz2d7vpndev5somwoki5vwdpfty2k7javniujekit6ad.onion',
'http://nehdddktmhvqklsnkjqcbpmb63htee2iznpcbs5tgzctipxykpj6yrid.onion',
'http://nv3x2jozywh63fkohn5mwp2d73vasusjixn3im3ueof52fmbjsigw6ad.onion',
'http://odahix2ysdtqp4lgak4h2rsnd35dmkdx3ndzjbdhk3jiviqkljfjmnqd.onion',
'http://okayd5ljzdv4gzrtiqlhtzjbflymfny2bxc2eacej3tamu2nyka7bxad.onion',
'http://onili244aue7jkvzn2bgaszcb7nznkpyihdhh7evflp3iskfq7vhlzid.onion',
'http://ovai7wvp4yj6jl3wbzihypbq657vpape7lggrlah4pl34utwjrpetwid.onion',
'http://ozmh2zkwx5cjuzopui64csb5ertcooi5vya6c2gm4e3vcvf2c2qvjiyd.onion',
'http://p2qzxkca42e3wccvqgby7jrcbzlf6g7pnkvybnau4szl5ykdydzmvbid.onion',
'http://p53lf57qovyuvwsc6xnrppyply3vtqm7l6pcobkmyqsiofyeznfu5uqd.onion',
'http://paavlaytlfsqyvkg3yqj7hflfg5jw2jdg2fgkza5ruf6lplwseeqtvyd.onion',
'http://picochanwvqfa2xsrfzlul4x4aqtog2eljll5qnj5iagpbhx2vmfqnid.onion',
'http://pliy7tiq6jf77gkg2sezlx7ljynkysxq6ptmfbfcdyrvihp7i6imyyqd.onion',
'http://porf65zpwy2yo4sjvynrl4eylj27ibrmo5s2bozrhffie63c7cxqawid.onion',
'http://potatoynwcg34xyodol6p6hvi5e4xelxdeowsl5t2daxywepub32y7yd.onion',
'http://privacy2zbidut4m4jyj3ksdqidzkw3uoip2vhvhbvwxbqux5xy5obyd.onion',
'http://prjd5pmbug2cnfs67s3y65ods27vamswdaw2lnwf45ys3pjl55h2gwqd.onion',
'http://pz5uprzhnzeotviraa2fogkua5nlnmu75pbnnqu4fnwgfffldwxog7ad.onion',
'http://qazkxav4zzmt5xwfw6my362jdwhzrcafz7qpd5kugfgx7z7il5lyb6ad.onion',
'http://qrtitjevs5nxq6jvrnrjyz5dasi3nbzx24mzmfxnuk2dnzhpphcmgoyd.onion',
'http://qubesosfasa4zl44o4tws22di6kepyzfeqv3tg4e3ztknltfxqrymdad.onion',
'http://rbcxodz4socx3rupvmhan2d7pvik4dpqmf4kexz6acyxbucf36a6ggid.onion',
'http://reycdxyc24gf7jrnwutzdn3smmweizedy7uojsa7ols6sflwu25ijoyd.onion',
'http://rfyb5tlhiqtiavwhikdlvb3fumxgqwtg2naanxtiqibidqlox5vispqd.onion',
'http://rxmyl3izgquew65nicavsk6loyyblztng6puq42firpvbe32sefvnbad.onion',
'http://s4k4ceiapwwgcm3mkb6e4diqecpo7kvdnfr5gg7sph7jjppqkvwwqtyd.onion',
'http://s57divisqlcjtsyutxjz2ww77vlbwpxgodtijcsrgsuts4js5hnxkhqd.onion',
'http://sa3ut5u4qdw7yiunpdieypzsrdylhbtafyhymd75syjcn46yb5ulttid.onion',
'http://sabladem4rxv5p34qcpz6sxitmftvmzmlzi4cjmmh5a3phcvdi3k2wad.onion',
'http://sazyr2ntihjqpjtruxbn2z7kingj6hfgysiy5lzgo2aqduqpa3gfgmyd.onion',
'http://secmail63sex4dfw6h2nsrbmfz2z6alwxe4e3adtkpd4pcvkhht4jdad.onion',
'http://sga5n7zx6qjty7uwvkxpwstyoh73shst6mx3okouv53uks7ks47msayd.onion',
'http://sidignlwz2odjhgcfhbueinmr23v5bubq2x43dskcebh5sbd2qrxtkid.onion',
'http://sik5nlgfc5qylnnsr57qrbm64zbdx6t4lreyhpon3ychmxmiem7tioad.onion',
'http://sonarmsng5vzwqezlvtu2iiwwdn3dxkhotftikhowpfjuzg7p3ca5eid.onion',
'http://spore64i5sofqlfz5gq2ju4msgzojjwifls7rok2cti624zyq3fcelad.onion',
'http://spywaredrcdg5krvjnukp3vbdwiqcv3zwbrcg6qh27kiwecm4qyfphid.onion',
'http://stormu36id5e62n2i7kq3v7batuy34dimpijx5euklgl5bwi65eaycyd.onion',
'http://stormwayszuh4juycoy4kwoww5gvcu2c4tdtpkup667pdwe4qenzwayd.onion',
'http://sukamuzgxigntu7issqf3y5bfsskwg5zzrzbuqjaxxmhkfoxbgiy77qd.onion',
'http://t43fsf65omvf7grt46wlt2eo5jbj3hafyvbdb7jtr2biyre5v24pebad.onion',
'http://theendgtso35ir6ngdtyhgtjhhbbprmkzl74gt5nyeu3ocr34sfa67yd.onion',
'http://titanxsu7bfd7vlyyffilprauwngr4acbnz27ulfhyxrqutu7atyptad.onion',
'http://torpastezr7464pevuvdjisbvaf4yqi4n7sgz7lkwgqwxznwy5duj4ad.onion',
'http://us3xsdrhmhk4h3bkuq7ttkp6pocs4726esycpgwtogrpu3nfjj6eroqd.onion',
'http://us63bgjkxwpyrpvsqom6kw3jcy2yujbplkhtzt64yykt42ne2ms7p4yd.onion',
'http://usmost4cbpesx552s2s4ti3c4nk2xgiu763vhcs3b4uc4ppp3zwnscyd.onion',
'http://vhlehwexxmbnvecbmsk4ormttdvhlhbnyabai4cithvizzaduf3gmayd.onion',
'http://vu3miq3vhxljfclehmvy7ezclvsb3vksmug5vuivbpw4zovyszbemvqd.onion',
'http://vww6ybal4bd7szmgncyruucpgfkqahzddi37ktceo3ah7ngmcopnpyyd.onion',
'http://w27irt6ldaydjoacyovepuzlethuoypazhhbot6tljuywy52emetn7qd.onion',
'http://wasabiukrxmkdgve5kynjztuovbg43uxcbcxn6y2okcrsg7gb6jdmbad.onion',
'http://wbz2lrxhw4dd7h5t2wnoczmcz5snjpym4pr7dzjmah4vi6yywn37bdyd.onion',
'http://wges3aohuplu6he5tv4pn7sg2qaummlokimim6oaauqo2l7lbx4ufyyd.onion',
'http://wk3mtlvp2ej64nuytqm3mjrm6gpulix623abum6ewp64444oreysz7qd.onion',
'http://wms5y25kttgihs4rt2sifsbwsjqjrx3vtc42tsu2obksqkj7y666fgid.onion',
'http://wnrgozz3bmm33em4aln3lrbewf3ikxj7fwglqgla2tpdji4znjp7viqd.onion',
'http://wosc4noitfscyywccasl3c4yu3lftpl2adxuvprp6sbg4fud6mkrwqqd.onion',
'http://kj2aybibqqcwt5nrskmv2qzdbq2gfgimpyshcnerbxkhkbyqz64kgcyd.onion',
'http://qubesosfasa4zl44o4tws22di6kepyzfeqv3tg4e3ztknltfxqrymdad.onion',
'http://xdkriz6cn2avvcr2vks5lvvtmfojz2ohjzj4fhyuka55mvljeso2ztqd.onion',
'http://xf2gry25d3tyxkiu2xlvczd3q7jl6yyhtpodevjugnxia2u665asozad.onion',
'http://xjfbpuj56rdazx4iolylxplbvyft2onuerjeimlcqwaihp3s6r4xebqd.onion',
'http://xsglq2kdl72b2wmtn5b2b7lodjmemnmcct37owlz5inrhzvyfdnryqid.onion',
'http://xykxv6fmblogxgmzjm5wt6akdhm4wewiarjzcngev4tupgjlyugmc7qd.onion',
'http://y22arit74fqnnc2pbieq3wqqvkfub6gnlegx3cl6thclos4f7ya7rvad.onion',
'http://ymvhtqya23wqpez63gyc3ke4svju3mqsby2awnhd3bk2e65izt7baqad.onion',
'http://z7s2w5vruxbp2wzts3snxs24yggbtdcdj5kp2f6z5gimouyh3wiaf7id.onion',
'http://zgeajoabenj2nac6k5cei5qy62iu5yun5gm2vjnxy65r3p3amzykwxqd.onion',
'http://zkdppoahhqu5ihjqd4qqvyfd2bm4wejrhjosim67t6yopl77jitg2nad.onion',
'http://zkj7mzglnrbvu3elepazau7ol26cmq7acryvsqxvh4sreoydhzin7zid.onion',
'http://zqktlwiuavvvqqt4ybvgvi7tyo4hjl5xgfuvpdf6otjiycgwqbym2qad.onion',
'http://zsxjtsgzborzdllyp64c6pwnjz5eic76bsksbxzqefzogwcydnkjy3yd.onion',
'http://zwf5i7hiwmffq2bl7euedg6y5ydzze3ljiyrjmm7o42vhe7ni56fm7qd.onion',
'https://5gdvpfoh6kb2iqbizb37lzk2ddzrwa47m6rpdueg2m656fovmbhoptqd.onion',
'https://protonmailrmez3lotccipshtkleegetolb73fuirgj7r4o4vfu7ozyd.onion',
'https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion',
'https://kcmykvkkt3umiyx4xouu3sjo6odz3rolqphy2i2bbdan33g3zrjfjgqd.onion',
'https://protonmailrmez3lotccipshtkleegetolb73fuirgj7r4o4vfu7ozyd.onion',
'https://facebookwkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd.onion'

]

# Scraping-Prozess starten
while urls_to_process:
    current_url = urls_to_process.pop(0)
    scrape_backlinks(current_url)
    renew_tor_ip()
    find_referring_pages(current_url)

# Verbindung schließen
conn.close()

# Beliebteste Webseite abrufen
cursor.execute('''
SELECT p.url, COUNT(b.target_id) AS backlink_count
FROM backlinks b
JOIN pages p ON b.target_id = p.id
GROUP BY p.url
ORDER BY backlink_count DESC
LIMIT 1
''')
popular_page = cursor.fetchone()
if popular_page:
    print(f"Beliebteste Webseite: {popular_page[0]} mit {popular_page[1]} Backlinks.")
else:
    print("Keine Daten gefunden.")
