import string
import random

def random_string():
                return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Host': 'prod.snapster.bot',
    'Origin': 'https://prod.snapster.bot',
    'Pragma': 'no-cache',
    'Referer': 'https://prod.snapster.bot/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
}
