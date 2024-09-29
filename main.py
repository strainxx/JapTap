import re
import requests
from datetime import datetime, timezone
import asyncio
import aiohttp
from colorama import Fore, Style, init
import time
import shutil
import os

headers = { # Enter your headers
    'sec-ch-ua-platform': '""',
    'Authorization': '',
    'Referer': 'https://jabka.skin/ru/jab-tap',
    'Accept-Language': '',
    'sec-ch-ua': '""',
    'sec-ch-ua-mobile': '',
    'User-Agent': '',
    'Accept': '',
}

init(autoreset=True)

os.system('cls' if os.name == 'nt' else 'clear')

def strip_ansi_codes(text):
    ansi_escape = re.compile(r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def format_time():
    return time.strftime("%H:%M:%S", time.localtime())

def print_status(energy, max_energy, click_count, taps_count):
    os.system('cls' if os.name == 'nt' else 'clear')

    energy_percentage = (energy / max_energy) * 100
    terminal_width = min(80, shutil.get_terminal_size().columns)
    bar_width = min(50, terminal_width - 10)
    energy_bar = '█' * int(energy_percentage / 100 * bar_width) + '░' * (bar_width - int(energy_percentage / 100 * bar_width))
    
    status = [
        f"{Fore.MAGENTA}╔{'═' * (terminal_width - 2)}╗{Style.RESET_ALL}",
        f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.YELLOW}[{format_time()}] {Fore.GREEN}Frog Tap Status{' ' * (terminal_width - len(strip_ansi_codes(f'[Frog Tap Status]')) - 12)}{Fore.MAGENTA}║{Style.RESET_ALL}",
        f"{Fore.MAGENTA}╠{'═' * (terminal_width - 2)}╣{Style.RESET_ALL}",
        f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.WHITE}Energy: {energy}/{max_energy} ({energy_percentage:.2f}%){' ' * (terminal_width - len(strip_ansi_codes(f'Energy: {energy}/{max_energy} ({energy_percentage:.2f}%)')) - 3)}{Fore.MAGENTA}║{Style.RESET_ALL}",
        f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.WHITE}{energy_bar}{' ' * (terminal_width - bar_width - 3)}{Fore.MAGENTA}║{Style.RESET_ALL}",
        f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.WHITE}Total Clicks: {click_count}{' ' * (terminal_width - len(strip_ansi_codes(f'Total Clicks: {click_count}')) - 3)}{Fore.MAGENTA}║{Style.RESET_ALL}",
        f"{Fore.MAGENTA}║{Style.RESET_ALL} {Fore.WHITE}Current Tap Mode: {Fore.YELLOW}{taps_count} taps{' ' * (terminal_width - len(strip_ansi_codes(f'Current Tap Mode: {taps_count} taps')) - 3)}{Fore.MAGENTA}║{Style.RESET_ALL}",
        f"{Fore.MAGENTA}╚{'═' * (terminal_width - 2)}╝{Style.RESET_ALL}"
    ]
    
    padded_status = [line.ljust(terminal_width) for line in status]
    
    print('\n' + '\n'.join(padded_status) + '\n')

async def check_energy():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://jabka.skin/api/jab-tap/frog', headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    remaining_energy = data['data']['frog']['remainingEnergy']
                    max_energy = data['data']['frog']['energyLevel']['energy']
                    next_recharge = data['data']['frog']['nextRechargeAt']
                    return remaining_energy, max_energy, next_recharge
                else:
                    print(Fore.RED + f"Failed to check energy. Status code: {response.status}")
                    return 0, 0, None
    except Exception as e:
        print(Fore.RED + f"Error checking energy: {e}")
        return 0, 0, None

async def perform_tap(taps_count):
    try:
        json_data = {
            'tapsCount': taps_count,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post('https://jabka.skin/api/jab-tap/frog/tap', headers=headers, json=json_data) as response:
                return response.status
    except Exception as e:
        print(Fore.RED + f"Error performing tap: {e}")
        return 500

async def wait_until_recharge(next_recharge):
    next_recharge_time = datetime.strptime(next_recharge, "%Y-%m-%dT%H:%M:%S.%f%z")
    now = datetime.now(timezone.utc)
    wait_time = (next_recharge_time - now).total_seconds()
    if wait_time > 0:
        print(Fore.YELLOW + f'Waiting for {wait_time:.2f} seconds until next recharge...')
        await asyncio.sleep(wait_time)

async def main():
    click_count = 0
    energy, max_energy, next_recharge = await check_energy()
    
    while True:
        try:
            if click_count % 20 == 0 or energy <= 1:
                energy, max_energy, next_recharge = await check_energy()
                if energy <= 1:
                    print(f"{Fore.YELLOW}[{format_time()}] No energy left. Waiting for recharge...")
                    await wait_until_recharge(next_recharge)
                    continue
            
            energy_percentage = (energy / max_energy) * 100
            
            if 99 <= energy_percentage <= 100:
                taps_count = 1
                delay = 1.0
            else:
                taps_count = 7
                delay = 0.1
            
            status_code = await perform_tap(taps_count)
            
            if status_code == 200:
                click_count += 1
                energy -= taps_count
                if click_count % 10 == 0:  
                    print_status(energy, max_energy, click_count, taps_count)
                await asyncio.sleep(delay)
            elif status_code == 429:
                print(f"{Fore.YELLOW}[{format_time()}] Too many requests, retrying in 60 seconds...")
                await asyncio.sleep(61)
            elif status_code == 400:
                print(f"{Fore.RED}[{format_time()}] Bad request, retrying in 60 seconds...")
                await asyncio.sleep(61)
            else:
                print(f"{Fore.RED}[{format_time()}] Error (Status code: {status_code}), retrying in 60 seconds...")
                await asyncio.sleep(61)
        
        except asyncio.CancelledError:
            print(f"{Fore.WHITE}[{format_time()}] Program terminated by user.")
            break
        except Exception as e:
            print(f"{Fore.RED}[{format_time()}] Unexpected error: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(Style.RESET_ALL + "Program terminated by user.")
