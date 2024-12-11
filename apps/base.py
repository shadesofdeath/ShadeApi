# apps/base.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
import aiohttp
import logging

@dataclass
class AppVersion:
    version: str
    architecture: str
    url: str
    hash: Optional[str] = None
    type: str = "exe"
    size: Optional[int] = None

@dataclass
class AppInfo:
    id: str
    name: str
    publisher: str
    versions: List[AppVersion]
    homepage: str
    last_updated: datetime

class BaseAppTracker:
    def __init__(self):
        self.headers = {
            "User-Agent": "App-Tracker/1.0"
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_app_info(self) -> Optional[AppInfo]:
        """Her uygulama tracker'ı bu metodu implement etmeli"""
        raise NotImplementedError
    
    async def _make_request(self, url: str) -> Dict:
        """Genel HTTP istek fonksiyonu"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                return await response.json()

    def _format_bytes(self, size_bytes: int) -> str:
        """Byte değerini insan okunabilir formata çevirir"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f}TB"