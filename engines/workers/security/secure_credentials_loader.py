"""
FULL PATH: engines/workers/security/secure_keystorage_worker.py
(Security Monitor content, merged into File 01 per the locked blueprint —
placed here because Market Data Monitor's real WS/REST connection needs it.)

Loads CoinDCX API key/secret from the OS keyring (preferred) or a local,
git-ignored .env file (fallback for dev). NEVER hardcode a key/secret in any
.py or .json file in this project -- that is a non-negotiable rule in
QuantumTrade19_Project_Instructions_v2.md.

Setup (one-time, run once locally, never commit the values anywhere):
    pip install keyring python-dotenv
    python -c "import keyring; keyring.set_password('quantumtrade19','coindcx_api_key','YOUR_NEW_KEY')"
    python -c "import keyring; keyring.set_password('quantumtrade19','coindcx_secret_key','YOUR_NEW_SECRET')"

If you'd rather use a .env file for local dev, create a file literally named
`.env` in the project root (already covered by .gitignore) containing:
    COINDCX_API_KEY=your_new_key
    COINDCX_SECRET_KEY=your_new_secret
"""
from __future__ import annotations

import os
from typing import Optional

try:
    import keyring
except ImportError:
    keyring = None

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads .env into os.environ if present, no-op otherwise
except ImportError:
    pass

_SERVICE_NAME = "quantumtrade19"


class SecureKeyStorageWorker:
    """Single point of truth for reading CoinDCX credentials. Every other Worker
    (WS_Feed_Worker, REST fallback, Historical loader for private endpoints, future
    Execution Monitor) must obtain credentials only through this Worker -- never
    read os.environ or keyring directly themselves."""

    @staticmethod
    def get_api_key() -> Optional[str]:
        if keyring:
            value = keyring.get_password(_SERVICE_NAME, "coindcx_api_key")
            if value:
                return value
        return os.environ.get("COINDCX_API_KEY")

    @staticmethod
    def get_secret_key() -> Optional[str]:
        if keyring:
            value = keyring.get_password(_SERVICE_NAME, "coindcx_secret_key")
            if value:
                return value
        return os.environ.get("COINDCX_SECRET_KEY")

    @staticmethod
    def has_credentials() -> bool:
        return bool(SecureKeyStorageWorker.get_api_key() and SecureKeyStorageWorker.get_secret_key())

    @staticmethod
    def sign_request(secret_key: str, payload_body: str) -> str:
        """HMAC-SHA256 signature CoinDCX requires on every private REST/WS auth call."""
        import hashlib
        import hmac
        return hmac.new(secret_key.encode(), payload_body.encode(), hashlib.sha256).hexdigest()
