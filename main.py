import os
import asyncio
import random
import imaplib
import requests
import names
import email
import time
import re
import win32gui
import win32api
import win32con
import numpy as np
from typing import Optional, Dict, Any

from playwright.async_api import (
    async_playwright,
    expect,
    Page,
    Locator,
)

from playwright_recaptcha import recaptchav2

from nstbrowser import NstbrowserClient
from dotenv import load_dotenv

from mouse_utils import move_mouse_in_window

load_dotenv()

global_playwright_timeout = 20000

nst_api_key = os.environ.get("NST_API_KEY")
nst_private_auth_token = os.environ.get("NST_PRIVATE_AUTH_TOKEN")
capsolver_api_key = os.environ.get("CAPSOLVER_API_KEY")
address = os.environ.get("ADDRESS")
catchall = os.environ.get("CATCHALL")

browser_profile_name = "instacart_profile_" + str(np.random.randint(1, 10000))


def find_maximize_and_focus_window(
    title_substring: str, timeout: int = 10
) -> Optional[int]:
    start_time = time.time()
    hwnd = None

    while not hwnd and time.time() - start_time < timeout:
        hwnd = win32gui.FindWindow(None, title_substring)
        if not hwnd:
            try:
                win32gui.EnumWindows(
                    lambda handle, L: (
                        L.append(handle)
                        if title_substring.lower()
                        in win32gui.GetWindowText(handle).lower()
                        else None
                    ),
                    hwnd_list := [],
                )
                hwnd = hwnd_list[0] if hwnd_list else None
            except Exception:
                pass

        if not hwnd:
            time.sleep(0.5)

    if hwnd:
        try:
            win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)

            win32gui.SetForegroundWindow(hwnd)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

            print(f"Successfully focused and maximized window with handle {hwnd}")
        except Exception as e:
            print(f"Error while trying to focus window: {e}")
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    else:
        print(
            f"Error: Could not find window with title containing '{title_substring}' within {timeout} seconds."
        )

    return hwnd


def simulate_human_movement(hwnd, duration_seconds=3) -> None:
    if not win32gui.IsWindow(hwnd):
        raise ValueError(f"Invalid window handle: {hwnd}")

    print(f"Simulating human-like idle movement for {duration_seconds} seconds...")
    start_time = time.time()

    try:
        _, _, width, height = win32gui.GetClientRect(hwnd)
        if width <= 1 or height <= 1:
            print("Window is too small to move within.")
            return
    except Exception as e:
        print(f"Could not get window dimensions: {e}")
        return

    while time.time() - start_time < duration_seconds:
        margin = 5
        dest_x = np.random.randint(margin, width - margin)
        dest_y = np.random.randint(margin, height - margin)

        move_mouse_in_window(hwnd, dest_x, dest_y, verbose=False)

        if time.time() - start_time >= duration_seconds:
            break

        pause_duration = np.random.uniform(0.1, 0.8)
        remaining_time = duration_seconds - (time.time() - start_time)
        time.sleep(min(pause_duration, max(0, remaining_time)))

    print("Simulation finished.")


async def get_code(mail: imaplib.IMAP4_SSL, email_address: str) -> Optional[str]:
    mail.select("INBOX")

    search_criteria = (
        'FROM "no-reply@instacart.com"' ' SUBJECT "is your Instacart verification code"'
    )
    _, data = mail.search(None, search_criteria)

    code_pattern = re.compile(r"(\d{6}) is your Instacart verification code")
    email_ids = data[0].split()[::-1][:1]  # Only get the last email

    for num in email_ids:
        _, email_data = mail.fetch(num, "(RFC822)")
        email_message = email.message_from_bytes(email_data[0][1])

        subject = email_message["Subject"]
        to_address = email_message["To"]

        if to_address == email_address:
            code_match = code_pattern.search(subject)
            return code_match.group(1) if code_match else "Unknown"

    return None


async def search_emails(email_address: str, timeout: int = 30) -> Optional[str]:
    result = None

    imap_server = "imap.gmail.com"
    imap_port = 993

    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(os.environ.get("IMAP_EMAIL"), os.environ.get("IMAP_PASSWORD"))

    start_time = asyncio.get_event_loop().time()
    try:
        while result is None:
            print("Waiting for code...")

            remaining_time = timeout - (asyncio.get_event_loop().time() - start_time)
            if remaining_time <= 0:
                break

            result = await get_code(mail, email_address)

            elapsed_time = asyncio.get_event_loop().time() - start_time
            if elapsed_time > timeout:
                break

            await asyncio.sleep(1)

    finally:
        mail.close()
        mail.logout()

    return result


async def wait_for_code(email: str, timeout: int = 30) -> str:
    start_time = asyncio.get_event_loop().time()

    while True:
        remaining_time = timeout - (asyncio.get_event_loop().time() - start_time)
        if remaining_time <= 0:
            raise TimeoutError("Timed out waiting for code (outer loop).")

        code = await search_emails(email, timeout=int(remaining_time))
        if code:
            return code

        elapsed_time = asyncio.get_event_loop().time() - start_time
        if elapsed_time > timeout:
            raise TimeoutError("Timed out waiting for code.")

        await asyncio.sleep(1)


def generate_fingerprint(
    auth_token: str,
    kernel: int,
    kernel_milestone: str,
    platform: int,
    platform_milestone: str,
) -> Optional[dict]:
    url = "https://api.nstbrowser.io/api/fpb/rand/fingerprint"
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {auth_token}",
        "content-type": "application/json",
    }
    payload = {
        "kernel": kernel,
        "KernelMilestone": kernel_milestone,
        "platform": platform,
        "platformMilestone": platform_milestone,
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(
            f"HTTP error occurred during fingerprint generation: {http_err} - {response.text}"
        )
    except Exception as err:
        print(f"An error occurred during fingerprint generation: {err}")
    return None


def mark_proxy_as_used(proxy_string: str, filename: str = "used_proxies.txt") -> None:
    if not proxy_string:
        print("No proxy string provided to mark as used.")
        return
    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(proxy_string + "\n")
        print(f"Marked proxy {proxy_string} as used in {filename}.")
    except IOError as e:
        print(f"Error writing to used proxies file '{filename}': {e}")


def get_random_proxy(
    filename: str = "proxies.txt", used_proxies_filename: str = "used_proxies.txt"
) -> Optional[str]:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            all_proxies_lines = [line.strip() for line in f if line.strip()]
        if not all_proxies_lines:
            print(f"Proxy file '{filename}' is empty.")
            return None
    except FileNotFoundError:
        print(f"Proxy file '{filename}' not found. Proceeding without proxy.")
        return None
    except Exception as e:
        print(f"Error reading proxy file '{filename}': {e}")
        return None

    used_proxies = set()
    try:
        with open(used_proxies_filename, "r", encoding="utf-8") as f:
            used_proxies = {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        print(
            f"Used proxies file '{used_proxies_filename}' not found. Assuming no proxies are used yet."
        )
        try:
            with open(used_proxies_filename, "w", encoding="utf-8") as f:
                pass
        except IOError as e:
            print(f"Could not create used_proxies file '{used_proxies_filename}': {e}")
    except Exception as e:
        print(f"Error reading used proxies file '{used_proxies_filename}': {e}")

    parsed_proxies_map = {}
    for line in all_proxies_lines:
        parts = line.split(":")
        proxy_str = None
        if len(parts) == 2:  # host:port
            host, port = parts[0], parts[1]
            proxy_str = f"http://{host}:{port}"
        elif len(parts) == 4:  # host:port:user:pass
            host, port, username, password = parts[0], parts[1], parts[2], parts[3]
            proxy_str = f"http://{username}:{password}@{host}:{port}"

        if proxy_str:
            parsed_proxies_map[line] = proxy_str

    available_proxy_lines = [
        original_line
        for original_line, http_form in parsed_proxies_map.items()
        if http_form not in used_proxies
    ]

    if not available_proxy_lines:
        print("All proxies from the list have been used or no valid proxies found.")
        return None

    selected_proxy_line = random.choice(available_proxy_lines)

    parts = selected_proxy_line.split(":")
    host = parts[0]
    port = parts[1]
    final_proxy_string = f"http://{host}:{port}"
    if len(parts) == 4:
        username = parts[2]
        password = parts[3]
        final_proxy_string = f"http://{username}:{password}@{host}:{port}"

    print(
        f"Selected available proxy: {final_proxy_string} (from line: {selected_proxy_line})"
    )
    return final_proxy_string


def generate_profile_data() -> Optional[Dict[str, Any]]:
    fp = generate_fingerprint(
        auth_token=nst_private_auth_token,
        kernel=0,
        kernel_milestone="135",
        platform=0,
        platform_milestone="11",
    )

    if not fp:
        print("Failed to generate fingerprint data or API call returned None.")
        return None

    data_from_api = fp.get("data", {})
    profile_from_api = data_from_api.get("profile", {})
    parameters_from_profile = profile_from_api.get("parameters", {})
    fingerprint_details = parameters_from_profile.get("fingerprint", {})
    navigator_details = fingerprint_details.get("navigator", {})

    user_agent = navigator_details.get("userAgent")
    user_agent_full_version = navigator_details.get("uaFullVersion")
    user_agent = user_agent.replace("135.0.0.0", user_agent_full_version)

    memory_cpu_combinations = [
        {"cpu": 8, "ram": 16},
        {"cpu": 4, "ram": 8},
        {"cpu": 12, "ram": 32},
        {"cpu": 4, "ram": 16},
        {"cpu": 6, "ram": 12},
    ]

    random_hardware = random.choice(memory_cpu_combinations)

    proxy_str = get_random_proxy()

    profile_data = {
        "name": browser_profile_name,
        "platform": "Windows",
        "kernel": "Chrome",
        "kernelMilestone": "135",
        "clearCacheOnClose": True,
        "groupName": "Default",
        "note": "Generated profile using private API fingerprint",
        "skipProxyChecking": False,
        "proxy": proxy_str,
        "fingerprint": {
            "flags": {
                "audio": "Noise",
                "battery": "Masked",
                "canvas": "Noise",
                "clientRect": "Noise",
                "fonts": "Masked",
                "geolocation": "Real",
                "geolocationPopup": "Prompt",
                "gpu": "Allow",
                "localization": "Real",
                "screen": "Custom",
                "speech": "Masked",
                "timezone": "Real",
                "webgl": "Noise",
                "webrtc": "Masked",
            },
        },
        "userAgent": user_agent,
        "screen": {"width": 1920, "height": 1080},
        "deviceMemory": random_hardware["ram"],
        "hardwareConcurrency": random_hardware["cpu"],
        "disableImageLoading": True,
        "doNotTrack": True,
        "args": {
            "--remote-debugging-port": random.randint(20000, 50000),
            "--disable-backgrounding-occluded-windows": True,
        },
    }

    return profile_data


def get_cdp_websocket_url(max_retries: int = 3) -> Optional[str]:
    client = NstbrowserClient(api_key=nst_api_key)

    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1}/{max_retries} to get CDP WebSocket URL.")
        profile = generate_profile_data()

        if not profile:
            print("Failed to generate browser profile. Cannot connect.")
            return None

        current_proxy = profile.get("proxy")
        log_proxy_info = current_proxy if current_proxy else "N/A (direct connection)"
        print(f"Using proxy for this attempt: {log_proxy_info}")

        try:
            response = client.cdp_endpoints.connect_once_browser(config=profile)

            if (
                response
                and isinstance(response, dict)
                and "data" in response
                and isinstance(response["data"], dict)
                and response["data"].get("webSocketDebuggerUrl")
            ):
                ws_endpoint = response["data"]["webSocketDebuggerUrl"]
                print(f"Successfully connected. WebSocket endpoint: {ws_endpoint}")
                if current_proxy:
                    mark_proxy_as_used(current_proxy)
                return ws_endpoint
            else:
                print(
                    "Connection attempt failed: WebSocket endpoint not found or unexpected response structure."
                )
                if response and isinstance(response, dict):
                    error_info = response.get(
                        "error", response.get("message", str(response))
                    )
                    print(f"NSTBrowser response snapshot: {str(error_info)[:500]}...")
                elif response:
                    print(f"NSTBrowser raw response: {str(response)[:500]}...")

                if current_proxy:
                    print(f"Proxy {log_proxy_info} might be bad.")
                    if attempt < max_retries - 1:
                        print("Retrying with a new proxy...")
                        time.sleep(random.uniform(1, 3))
                        continue
                    else:
                        print(
                            "Max retries reached with different proxies after bad response structure."
                        )
                        return None
                else:
                    print(
                        "Failed on a direct connection (no proxy) with bad response structure. Not retrying."
                    )
                    return None

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error during connection: {http_err}")
            if http_err.response is not None:
                print(
                    f"Response status: {http_err.response.status_code}, Body: {str(http_err.response.text)[:200]}..."
                )
                if http_err.response.status_code == 500 and current_proxy:
                    print(f"Proxy {log_proxy_info} likely caused HTTP 500 error.")
                    if attempt < max_retries - 1:
                        print("Retrying with a new proxy...")
                        time.sleep(random.uniform(1, 3))
                        continue
                    else:
                        print("Max retries reached after HTTP 500 with proxy.")
                        return None
                elif http_err.response.status_code == 500 and not current_proxy:
                    print(
                        "HTTP 500 error on a direct connection (no proxy). Not retriable for this issue."
                    )
                    return None
                else:
                    print(
                        "Non-500 HTTP error, or 500 without proxy being the primary suspect for retry. Not retrying this error."
                    )
                    return None
            else:
                print("HTTPError occurred without a response object. Not retrying.")
                return None

        except Exception as e:
            print(f"An unexpected error occurred during connect_once_browser: {e}")
            if current_proxy:
                if attempt < max_retries - 1:
                    print("Retrying with a new proxy due to unexpected error...")
                    time.sleep(random.uniform(1, 3))
                    continue
                else:
                    print("Max retries reached after unexpected error with proxy.")
                    return None
            else:
                print("Unexpected error on direct connection. Not retrying.")
                return None

    print(f"Failed to obtain WebSocket endpoint after {max_retries} attempts.")
    return None


async def click_element(locator: Locator) -> None:
    await expect(locator).to_be_visible(timeout=global_playwright_timeout)
    await locator.click()


async def solve_captcha_task(page: Page) -> None:
    try:
        async with recaptchav2.AsyncSolver(
            page, capsolver_api_key=capsolver_api_key
        ) as solver:
            await solver.solve_recaptcha(wait=True, image_challenge=True)
            print("Solver task completed without error.")
    except Exception:
        pass


async def fill_input(
    page: Page,
    locator: Locator,
    text: str,
    delay_range: tuple = (50, 300),
) -> None:
    await expect(locator).to_be_editable(timeout=global_playwright_timeout)
    await locator.focus()
    await page.keyboard.type(text, delay=random.uniform(*delay_range))


async def human_like_pause(min_seconds: int = 1, max_seconds: int = 2) -> None:
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))


async def start_signup_flow(page: Page) -> None:
    print("Navigating to Instacart and starting signup...")
    await page.goto("https://instacart.com/")
    await human_like_pause()
    await click_element(page.get_by_test_id("auth-buttons-signup"))


async def enter_email_and_continue(page: Page, email: str) -> None:
    print(f"Entering email: {email}")
    email_input = page.get_by_role("textbox", name="Email")
    await fill_input(page, email_input, email)

    await human_like_pause()

    continue_button = page.get_by_role("button", name="Continue", exact=True)
    await click_element(continue_button)
    await human_like_pause()


async def submit_verification_code(page: Page, email: str, wait_for_code_func) -> None:
    print("Waiting for verification code...")
    code = await wait_for_code_func(email)
    print(f"Submitting code: {code}")

    code_input = page.get_by_role("textbox", name="Enter code")
    await code_input.wait_for(state="visible", timeout=global_playwright_timeout)
    await human_like_pause()
    await fill_input(page, code_input, code, delay_range=(250, 1000))


async def save_address(page: Page) -> None:
    print(f"Adding address: {address}")
    await asyncio.sleep(5)

    await page.goto("https://www.instacart.com/store/account/addresses")
    add_address_button = page.get_by_role(
        "menuitem", name="Add a new address", exact=True
    )
    await click_element(add_address_button)
    await human_like_pause()
    add_address_input = page.get_by_role("textbox", name="Add a new address")
    await click_element(add_address_input)
    await fill_input(page, add_address_input, address)

    await human_like_pause()

    print("Attempting to select address suggestion by tabindex='-1'.")
    suggestion_button_locator = page.locator('button[tabindex="-1"]').first

    try:
        await expect(suggestion_button_locator).to_be_visible(
            timeout=global_playwright_timeout
        )
        await click_element(suggestion_button_locator)
    except Exception as e:
        print(f"Could not find or click suggestion with tabindex='-1': {e}")
        print("Proceeding to click 'Save Address' anyway. This might fail.")

    save_button = page.get_by_role("button", name="Save Address")
    await click_element(save_button)
    await human_like_pause()
    print(f"Address saving process for '{address}' initiated.")


async def is_captcha_present(page: Page) -> bool:
    try:
        captcha_frame_locator = page.frame_locator('iframe[title="reCAPTCHA"]')
        await captcha_frame_locator.wait_for(
            state="visible", timeout=global_playwright_timeout
        )
        return True
    except TimeoutError as e:
        print(f"Timed out waiting for captcha. {e}")
        return False


async def main_signup_process(
    page: Page,
    browser,
) -> None:
    try:
        await start_signup_flow(page)

        hwnd = find_maximize_and_focus_window(browser_profile_name)
        simulate_human_movement(hwnd, 5)

        first_name = names.get_first_name().lower()
        last_name = names.get_last_name().lower()
        random_number = np.random.randint(1, 10000)
        email_address = f"{first_name}{last_name}{random_number}@{catchall}"

        await enter_email_and_continue(page, email_address.lower())
        asyncio.create_task(solve_captcha_task(page))

        simulate_human_movement(hwnd, 5)

        await submit_verification_code(page, email_address, wait_for_code)
        asyncio.create_task(solve_captcha_task(page))

        await save_address(page)

        print("Signup complete. Navigating back to homepage.")
        await page.goto("https://instacart.com/")
        await asyncio.sleep(5)

    except Exception as e:
        print(f"An error occurred during the signup process: {e}")
    finally:
        print("Closing browser.")
        await page.close()
        await browser.close()


async def control_browser_with_playwright(websocket_url) -> None:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(websocket_url)
            default_context = browser.contexts[0]

            await default_context.add_init_script(
                """
                delete window.__playwright__binding__;
                delete window.__pwInitScripts;
                """
            )

            pages = default_context.pages
            page = pages[0] if pages else await default_context.new_page()

            await main_signup_process(page, browser)

    except Exception as e:
        print(f"Error during Playwright automation: {e}")


def main():
    while True:
        try:
            websocket_url = get_cdp_websocket_url()
            if websocket_url:
                asyncio.run(control_browser_with_playwright(websocket_url))
            else:
                print(
                    "Cannot proceed with Playwright automation: WebSocket URL not available"
                )
        except Exception as e:
            print(f"Exception occured: {e}")
            pass


if __name__ == "__main__":
    main()
