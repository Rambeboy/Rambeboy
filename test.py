import uuid
import aiohttp
import asyncio
import time
import cloudscraper
import logging
from InquirerPy import inquirer
from colorama import Fore, Style, init

show_errors = True
init(autoreset=True)
print(f"{Fore.CYAN}" + """

██████╗  █████╗ ███╗   ███╗██████╗ ██████╗ ██████╗  ██████╗ ██╗   ██╗
██╔══██╗██╔══██╗████╗ ████║██╔══██╗╚════██╗██╔══██╗██╔═████╗╚██╗ ██╔╝
██████╔╝███████║██╔████╔██║██████╔╝ █████╔╝██████╔╝██║██╔██║ ╚████╔╝ 
██╔══██╗██╔══██║██║╚██╔╝██║██╔══██╗ ╚═══██╗██╔══██╗████╔╝██║  ╚██╔╝  
██║  ██║██║  ██║██║ ╚═╝ ██║██████╔╝██████╔╝██████╔╝╚██████╔╝   ██║   
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═════╝ ╚═════╝ ╚═════╝  ╚═════╝    ╚═╝   
                                                                     
""" + Style.RESET_ALL)
print("\n" + " " * 35 + f"{Fore.YELLOW}NODEPAY NETWORK BOT{Style.RESET_ALL}")
print(" " * 32 + f"{Fore.GREEN}Welcome & Enjoy Sir!{Style.RESET_ALL}")
print(" " * 30 + f"{Fore.WHITE}Author : Nofan Rambe{Style.RESET_ALL}" + "\n")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():

    console_handler = logging.StreamHandler()
    
    logger.addHandler(console_handler)

    console_handler.setFormatter(logging.Formatter(f'{Fore.CYAN}[%(asctime)s] {Style.RESET_ALL}%(message)s', datefmt='%Y-%m-%d/%H:%M:%S'))



apiurl, status = {

    "session": "http://18.136.143.169/api/auth/session", 

    "ping": "http://54.255.192.166/api/network/ping"

}, {

    "connected": 1, 

    "disconnected": 2, 

    "no_connection": 3

}



current_status, browser_identifier, user_account_info, last_ping_timestamp, pingdelay, retry = status["no_connection"], None, {}, {}, 60, 60



def gen_uuid(): return str(uuid.uuid4())



def validate_resp(resp):

    if not resp or "code" not in resp or resp["code"] < 0: raise ValueError("Invalid response")

    return resp



def load_file(filename):

    try:

        with open(filename, 'r') as file: return [line.strip() for line in file if line.strip()]

    except FileNotFoundError: logger.error(f"File {filename} not found.") if show_errors else None

    except Exception as e: logger.error(f"An error occurred: {e}") if show_errors else None

    return []



def proxy_operations(op, proxy=None, data=None): return op == 'is_valid_proxy'



async def fetch_profile(proxy, token):

    global browser_identifier, user_account_info

    try:

        session_info = proxy_operations('load_session', proxy)

        if not session_info:

            browser_identifier = gen_uuid()

            response = await call_api(apiurl["session"], {}, proxy, token)

            validate_resp(response)

            user_account_info = response["data"]

            if user_account_info.get("uid"):

                proxy_operations('save_session', proxy, user_account_info)

                await initiate_ping(proxy, token)

            else:

                proxy_operations('remove_proxy', proxy)

        else:

            user_account_info = session_info

            await initiate_ping(proxy, token)

    except Exception as e:

        if show_errors:

            logger.error(f"Error occurred in fetch_profile: {e}")



async def call_api(url, data, proxy, token):

    headers = {

        "Authorization": f"Bearer {token}", "Content-Type": "application/json",

        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",

        "Accept": "application/json", "Accept-Language": "en-US,en;q=0.5", "Referer": "https://app.nodepay.ai"

    }

    try:

        scraper = cloudscraper.create_scraper()

        response = scraper.post(url, json=data, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=30)

        response.raise_for_status()

        return validate_resp(response.json())

    except Exception as e:

        logger.error(f"An error occurred in call_api: {e}") if show_errors else None



async def initiate_ping(proxy, token):

    try:

        while True:

            await send_ping(proxy, token)

            await asyncio.sleep(pingdelay)

    except asyncio.CancelledError:

        logger.info(f"Ping for proxy {proxy} cancelled")

    except Exception as e:

        logger.error(f"An error occurred in initiate_ping: {e}") if show_errors else None



async def send_ping(proxy, token):

    global last_ping_timestamp, retry, current_status

    current_time = time.time()

    logger.info(f"{Fore.BLUE}Attempting to send ping from {Fore.YELLOW}{proxy}{Style.RESET_ALL}")

    if proxy in last_ping_timestamp and (current_time - last_ping_timestamp[proxy]) < pingdelay:

        logger.info(f"Woah there! Not enough time has elapsed for proxy {proxy}")

        return

    last_ping_timestamp[proxy] = current_time

    try:

        data = {"id": user_account_info.get("uid"), "browser_id": browser_identifier, "timestamp": int(time.time())}

        response = await call_api(apiurl["ping"], data, proxy, token)

        ping_result, network_quality = "success" if response["code"] == 0 else "failed", response["data"].get("ip_score", "N/A")

        if ping_result == "success":

            logger.info(f"Ping {Fore.GREEN}{ping_result}{Fore.WHITE} from {Fore.YELLOW}{proxy}{Fore.WHITE}, Network Quality: {Fore.GREEN}{network_quality}")

            retry, current_status = 0, status["connected"]

        else:

            ping_fail(proxy, response)

    except Exception as e:

        logger.error(f"An error occurred in send_ping: {e}") if show_errors else None



def ping_fail(proxy, response):

    global retry, current_status

    retry += 1

    if response and response.get("code") == 403: proxy_operations('remove_proxy', proxy)

    else: current_status = status["disconnected"]



async def main():

    use_proxy_option = inquirer.select(message="Do you want to use or run with proxy?", choices=["Use Proxy", "Without Proxy/Local network"]).execute()

    show_errors_option = inquirer.select(message="Do you want to show error in console?", choices=["Show Errors", "Hide Errors"]).execute()

    global show_errors

    show_errors = (show_errors_option == "Show Errors")

    all_proxies, tokens = load_file('proxy.txt') if use_proxy_option == "Use Proxy" else [None], load_file('user.txt')

    total_accounts = len(tokens)

    logger.info(f"{Fore.YELLOW}Total user accounts loaded: {Fore.GREEN}{total_accounts}{Style.RESET_ALL}")

    if use_proxy_option == "Use Proxy":

        total_proxies = len(all_proxies)

        logger.info(f"{Fore.WHITE}Processing with {Fore.YELLOW}{total_proxies}{Fore.WHITE} proxies, {Fore.YELLOW}trying to filter the proxy and only connect with active proxy...{Style.RESET_ALL}")

    

    while True:

        tasks = []

        for i, token in enumerate(tokens):

            active_proxies = [proxy for proxy in all_proxies if proxy_operations('is_valid_proxy', proxy)]

            token_proxies = active_proxies[i*10:(i+1)*10]

            for proxy in token_proxies:

                tasks.append(asyncio.create_task(fetch_profile(proxy, token)))

        await asyncio.gather(*tasks)

        await asyncio.sleep(10)



def run_application():

    import nest_asyncio

    nest_asyncio.apply()

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info("Application stopped by user")

    finally:

        logger.info("Goodbye!")



if __name__ == '__main__':

    run_application()
