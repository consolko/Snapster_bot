import asyncio
from urllib.parse import unquote, quote
import urllib.parse

from random import randint

from datetime import datetime
from tzlocal import get_localzone
from time import time
import aiohttp
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestAppWebView, RequestWebView
from pyrogram.raw import types
from datetime import datetime, timedelta
from .agents import generate_random_user_agent

from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers, random_string
from bot.config import settings

yellow = "\x1b[33;20m"
green = "\x1b[1;32m"
blue = "\x1b[1;36m"
reset = "\x1b[0m"


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.bot_name = 'snapster_bot'
        self.app_url = 'https://prod.snapster.bot/'

        self.user = None
        self.token = None

        self.next_claim_dt = None

    def info(self, message):
        from bot.utils import info
        info(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def debug(self, message):
        from bot.utils import debug
        debug(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def warning(self, message):
        from bot.utils import warning
        warning(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def error(self, message):
        from bot.utils import error
        error(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def critical(self, message):
        from bot.utils import critical
        critical(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def success(self, message):
        from bot.utils import success
        success(f"<light-yellow>{self.session_name}</light-yellow> | {message}")

    def convert_to_local_and_unix(self, iso_time):
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        local_dt = dt.astimezone(get_localzone())
        unix_time = int(local_dt.timestamp())
        return unix_time

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer(self.bot_name)
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | FloodWait {fl}")
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            if settings.REF_ID == '':
                start_param = ''  # ref
                self.start_param = ''  # ref
            else:
                start_param = settings.REF_ID
                self.start_param = start_param

            InputBotApp = types.InputBotAppShortName(bot_id=peer, short_name="app")  # change app name

            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                app=InputBotApp,
                platform='android',
                write_allowed=True,
                start_param=start_param
            ))

            auth_url = web_view.url

            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            self.user = await self.tg_client.get_me()

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(
                f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def login(self, http_client: aiohttp.ClientSession, proxy: Proxy):
        try:
            tg_web_data = await self.get_tg_web_data(proxy=proxy)
            parsed_query = urllib.parse.parse_qs(tg_web_data)
            encoded_query = urllib.parse.urlencode(parsed_query, doseq=True)

            http_client.headers['User-Agent'] = generate_random_user_agent(device_type='android',
                                                                           browser_type='chrome')

            self.token = encoded_query
            http_client.headers["Telegram-Data"] = f"{self.token}"
            headers["Telegram-Data"] = f"{self.token}"
            logger.success(f"{self.session_name} | Success login.")

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting Access Token: {error}")
            await asyncio.sleep(delay=3)

    async def user_info(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(
                url=f'https://prod.snapster.bot/api/user/getUserByTelegramId?telegramId={self.user.id}')
            response.raise_for_status()
            response_json = await response.json()

            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting user info: {error}")
            await asyncio.sleep(delay=3)

    async def claim_mining(self, http_client: aiohttp.ClientSession):
        try:
            payload = {'telegramId': f'{self.user.id}'}
            response = await http_client.post(url='https://prod.snapster.bot/api/user/claimMiningBonus', json=payload)
            response.raise_for_status()
            response_json = await response.json()

            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting user info: {error}")
            await asyncio.sleep(delay=3)

    async def get_quests(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(
                url=f'https://prod.snapster.bot/api/quest/getQuests?telegramId={self.user.id}')
            response.raise_for_status()
            response_json = await response.json()

            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting quests: {error}")
            await asyncio.sleep(delay=3)

    async def start_quest(self, http_client: aiohttp.ClientSession, quest_id: int):
        try:
            payload = {'telegramId': f'{self.user.id}', 'questId': quest_id}
            response = await http_client.post(url='https://prod.snapster.bot/api/quest/startQuest', json=payload)
            response.raise_for_status()
            response_json = await response.json()

            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while starting quest: {error}")
            await asyncio.sleep(delay=3)

    async def claim_quest(self, http_client: aiohttp.ClientSession, quest_id: int):
        try:
            payload = {'telegramId': f'{self.user.id}', 'questId': quest_id}
            response = await http_client.post(url='https://prod.snapster.bot/api/quest/claimQuestBonus', json=payload)
            response.raise_for_status()
            response_json = await response.json()

            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while claiming quest: {error}")
            await asyncio.sleep(delay=3)

    async def get_referral_points(self, http_client: aiohttp.ClientSession):
        try:
            response = await http_client.get(
                url=f'https://prod.snapster.bot/api/referral/calculateReferralPoints?telegramId={self.user.id}')
            response.raise_for_status()
            response_json = await response.json()

            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting referral points: {error}")
            await asyncio.sleep(delay=3)

    async def claim_referrals(self, http_client: aiohttp.ClientSession):
        try:
            payload = {'telegramId': f'{self.user.id}'}
            response = await http_client.post(url='https://prod.snapster.bot/api/referral/claimReferralPoints',
                                              json=payload)
            response.raise_for_status()
            response_json = await response.json()

            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while claiming referrals: {error}")
            await asyncio.sleep(delay=3)

    async def start_daily(self, http_client: aiohttp.ClientSession):
        try:
            payload = {'telegramId': f'{self.user.id}'}
            response = await http_client.post(url='https://prod.snapster.bot/api/dailyQuest/startDailyBonusQuest',
                                              json=payload)
            response.raise_for_status()
            response_json = await response.json()

            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while starting daily bonus: {error}")
            await asyncio.sleep(delay=3)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            escaped_error = str(error).replace('<', '&lt;').replace('>', '&gt;')
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {escaped_error}")

    async def run(self, proxy: str | None) -> None:
        if settings.USE_RANDOM_DELAY_IN_RUN:
            random_delay = randint(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])
            logger.info(f"{self.tg_client.name} | Run for <lw>{random_delay}s</lw>")

            await asyncio.sleep(delay=random_delay)

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        while True:
            try:
                if http_client.closed:
                    if proxy_conn:
                        if not proxy_conn.closed:
                            proxy_conn.close()

                    proxy_conn = (ProxyConnector().from_url(proxy) if proxy else None)
                    http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

                if self.token is None:
                    await self.login(http_client=http_client, proxy=proxy)
                    user_data = await self.user_info(http_client)
                    user_points = user_data.get('data').get('pointsCount')
                    user_wallet = user_data.get('data').get('walletAddress')
                    wallet_signed = user_data.get('data').get('isWalletSigned')
                    self.info(f"Points: {user_points} Wallet: {user_wallet} Signed: {wallet_signed}")
                await asyncio.sleep(1.5)

                if settings.DAILY_BONUS:
                    try:
                        start_daily = await self.start_daily(http_client)
                        if start_daily.get('result') is True:
                            self.success(f"Daily bonus claimed!")

                    except Exception as error:
                        logger.error(f"{self.session_name} | Unknown error while daily bonus: {error}")
                        await asyncio.sleep(delay=3)

                if settings.AUTO_FARM:
                    try:
                        if self.next_claim_dt is None:
                            user_data = await self.user_info(http_client)
                            last_claim = self.convert_to_local_and_unix(
                                user_data.get('data').get('lastMiningBonusClaimDate')) + randint(
                                settings.CLAIM_RANGE[0], settings.CLAIM_RANGE[1])
                            self.next_claim_dt = last_claim
                            # print(self.next_claim_dt)
                            await asyncio.sleep(1)

                        if time() > self.next_claim_dt:
                            claim = await self.claim_mining(http_client)
                            # print(claim)
                            if claim.get('result'):
                                last_claim = self.convert_to_local_and_unix(
                                    claim.get('data').get('user').get('lastMiningBonusClaimDate')) + randint(
                                    settings.CLAIM_RANGE[0], settings.CLAIM_RANGE[1])
                                self.next_claim_dt = last_claim

                                self.success(f"Claimed {claim.get('data').get('pointsClaimed')} points.")
                                self.info(f"Next claim in {round((self.next_claim_dt - time()) / 60, 2)} min.")

                        else:
                            self.info(
                                f"Farming in progress, next claim in {round((self.next_claim_dt - time()) / 60, 2)} min.")

                        referrals = await self.get_referral_points(http_client=http_client)
                        ref_points = referrals.get('data').get('pointsToClaim')
                        if ref_points > 0:
                            claim_ref = await self.claim_referrals(http_client=http_client)
                            claimed_points = claim_ref.get('data').get('pointsClaimed')
                            self.success(f"Claimed {claimed_points} referral points.")

                    except Exception as error:
                        logger.error(f"{self.session_name} | Unknown error while claiming: {error}")
                        await asyncio.sleep(delay=3)

                if settings.AUTO_TASKS:
                    try:
                        quests = await self.get_quests(http_client=http_client)

                        if quests:
                            for quest in quests.get('data'):
                                if quest.get('type') != 'REFERRAL':
                                    if quest.get('status') == 'EARN':
                                        start = await self.start_quest(http_client=http_client,
                                                                       quest_id=quest.get('id'))
                                        if start.get('result') is True:
                                            self.info(f"Task {quest.get('title')} started.")
                                            await asyncio.sleep(delay=3)

                                    elif quest.get('status') == 'UNCLAIMED':
                                        claim = await self.claim_quest(http_client=http_client,
                                                                       quest_id=quest.get('id'))
                                        if claim.get('result') is True:
                                            self.success(f"Task {quest.get('title')} claimed.")
                                            await asyncio.sleep(delay=3)

                    except Exception as error:
                        logger.error(f"{self.session_name} | Unknown error while auto tasks: {error}")
                        await asyncio.sleep(delay=3)

                # Close connection & reset token
                await http_client.close()
                if proxy_conn:
                    if not proxy_conn.closed:
                        proxy_conn.close()

                self.token = None

                next_claim = self.next_claim_dt - time()
                logger.info(
                    f'<light-yellow>{self.session_name}</light-yellow> | sleep {round(next_claim / 60, 2)} min.')
                await asyncio.sleep(next_claim)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error: {error}")
                await asyncio.sleep(delay=3)


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
