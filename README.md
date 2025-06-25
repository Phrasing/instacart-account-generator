# Instacart Account Creator

## Overview

This Python script automates the process of creating accounts on Instacart.com. It leverages various techniques to simulate human-like behavior and manage browser profiles for potentially creating multiple accounts.

**Note:** This script is designed to run on **Windows only** due to its reliance on Windows-specific libraries (`win32gui`, `win32api`) for certain automation tasks like window focusing and simulated mouse movements.

## Features

- **Browser Automation**: Uses Playwright for robust browser control and interaction.
- **Advanced Browser Profiling**: Integrates with Nstbrowser to generate unique browser fingerprints and manage browser profiles, aiming to reduce detection.
- **Proxy Management**: 
    - Supports the use of proxies listed in `proxies.txt`.
    - Tracks successfully used proxies in `used_proxies.txt` to avoid re-using them in subsequent runs until the list is cleared or all proxies are exhausted.
- **Human-like Interaction**:
    - Simulates human-like mouse movements using the `mouse_utils.py` module.
    - Introduces random delays and pauses throughout the automation process.
- **CAPTCHA Solving**: Integrates with Capsolver to automatically solve reCAPTCHA challenges encountered during signup.
- **Email Verification**: Automatically fetches verification codes from a GMail account (via IMAP) to complete the signup process.
- **Configuration**: Sensitive data and operational parameters (API keys, email credentials, target address, catchall domain) are managed through an `.env` file.

## Prerequisites

- Python 3.7+
- **Operating System**: Windows (due to the use of `win32gui` and `win32api` libraries).
- A Gmail account with IMAP enabled (for fetching verification codes).
- API Keys:
    - Nstbrowser API Key (`NST_API_KEY`)
    - Nstbrowser Private Auth Token (`NST_PRIVATE_AUTH_TOKEN`) (ctrl+shift+i in nstbrowser, grab from any request with auth) (optional just remove usage of 'generate_fingerprint')
    - Capsolver API Key (`CAPSOLVER_API_KEY`)
- A `.env` file in the project root directory. See the `.env.example` (you'll need to create this manually if it's not provided) or the "Setup" section for required variables.
- (Optional) A `proxies.txt` file if you intend to use proxies.

## Setup

1.  **Clone the Repository** (if you have it in a Git repository):
    ```bash
    git clone <repository-url>
    cd instacart-account-generator
    ```

2.  **Create a Virtual Environment** (recommended):
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create and Populate the `.env` File**:
    Create a file named `.env` in the root of the project and add the following variables with your actual credentials and settings:
    ```env
    NST_API_KEY="YOUR_NSTBROWSER_API_KEY"
    NST_PRIVATE_AUTH_TOKEN="YOUR_NSTBROWSER_PRIVATE_AUTH_TOKEN"
    CAPSOLVER_API_KEY="YOUR_CAPSOLVER_API_KEY"
    IMAP_EMAIL="your_gmail_address@gmail.com"
    IMAP_PASSWORD="your_gmail_app_password" # Use an App Password if 2FA is enabled
    CATCHALL="yourcatchalldomain.com"
    ADDRESS="123 Main St, Anytown, USA" 
    ```
    *Note on `IMAP_PASSWORD`: If you have 2-Factor Authentication enabled on your Gmail account, you'll need to generate an "App Password" to use here.*

5.  **Create `proxies.txt` (Optional)**:
    If you want to use proxies, create a file named `proxies.txt` in the project root. Add one proxy per line in either of the following formats:
    - `host:port`
    - `host:port:username:password`

## Running the Script

Once the setup is complete, you can run the script from the project's root directory:

```bash
python main.py
```

The script will run in a loop, attempting to create an account in each iteration. It will use a new proxy from `proxies.txt` (that hasn't been marked as used in `used_proxies.txt`) for each attempt if proxies are configured.
