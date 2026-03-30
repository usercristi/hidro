"""API client pentru Hidroelectrica SEW platform."""

import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

_LOGGER = logging.getLogger(__name__)


class HidroelectricaApiClient:
    """Client pentru API-ul Hidroelectrica."""

    def __init__(self, username: str, password: str, session: requests.Session = None):
        """Inițializează clientul API."""
        self.username = username
        self.password = password
        self.session = session or requests.Session()
        self.token = None
        self._accounts_cache = None

    def _login(self) -> bool:
        """Autentificare și obținere token."""
        try:
            login_url = "https://portal.hidroelectrica.ro/SEW/rest/login"
            payload = {"username": self.username, "password": self.password}
            
            response = self.session.post(login_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.token = data.get("token")
            
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            })
            
            _LOGGER.debug("Autentificare reușită pentru %s", self.username)
            return True
            
        except Exception as e:
            _LOGGER.error("Eroare la autentificare: %s", e)
            return False

    def _ensure_auth(self) -> bool:
        """Verifică și reînnoiește autentificarea dacă e necesar."""
        if not self.token:
            return self._login()
        return True

    def _get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Cerere GET cu autentificare."""
        if not self._ensure_auth():
            return None
        
        try:
            url = f"https://portal.hidroelectrica.ro/SEW/rest/{endpoint}"
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 401:
                _LOGGER.debug("Token expirat, reautentificare...")
                if self._login():
                    response = self.session.get(url, params=params, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            _LOGGER.error("Eroare la cererea %s: %s", endpoint, e)
            return None

    def _post(self, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Cerere POST cu autentificare."""
        if not self._ensure_auth():
            return None
        
        try:
            url = f"https://portal.hidroelectrica.ro/SEW/rest/{endpoint}"
            response = self.session.post(url, json=data, timeout=30)
            
            if response.status_code == 401:
                if self._login():
                    response = self.session.post(url, json=data, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            _LOGGER.error("Eroare la cererea POST %s: %s", endpoint, e)
            return None

    def get_accounts(self) -> List[Dict]:
        """Obține lista conturilor utilizatorului."""
        if self._accounts_cache is not None:
            return self._accounts_cache
        
        data = self._get("GetAccounts")
        if data:
            self._accounts_cache = data.get("accounts", [])
            return self._accounts_cache
        return []

    def get_multi_meter(self, uan: str) -> Dict:
        """Obține detalii contor."""
        return self._get("GetMultiMeter", {"uan": uan}) or {}

    def get_bill(self, uan: str) -> Dict:
        """Obține detalii factură curentă."""
        return self._get("GetBill", {"uan": uan}) or {}

    def get_previous_meter_read(self, uan: str) -> Dict:
        """Obține indexul curent."""
        return self._get("GetPreviousMeterRead", {"uan": uan}) or {}

    def get_window_dates(self, uan: str) -> Dict:
        """Obține fereastra de autocitire."""
        return self._get("GetWindowDates", {"uan": uan}) or {}

    def get_meter_read_history(self, uan: str, year: int = None) -> Dict:
        """Obține istoricul citirilor."""
        params = {"uan": uan}
        if year:
            params["year"] = year
        return self._get("GetMeterReadHistory", params) or {}

    def get_usage_generation(self, uan: str, year: int = None) -> Dict:
        """Obține consumul lunar."""
        params = {"uan": uan}
        if year:
            params["year"] = year
        return self._get("GetUsageGeneration", params) or {}

    def get_billing_history(self, uan: str, year: int = None) -> Dict:
        """Obține istoricul plăților."""
        params = {"uan": uan}
        if year:
            params["year"] = year
        return self._get("GetBillingHistoryList", params) or {}

    def submit_self_read(self, uan: str, index: float) -> bool:
        """Trimite autocitire."""
        data = {
            "uan": uan,
            "index": index,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        result = self._post("SubmitSelfRead", data)
        return result is not None

    def is_prosumer(self, uan: str) -> bool:
        """Detectează dacă contul este prosumator."""
        history = self.get_meter_read_history(uan)
        if not history:
            return False
        
        reads = history.get("reads", [])
        for read in reads:
            if read.get("register") == "1.8.0_P":
                return True
        return False