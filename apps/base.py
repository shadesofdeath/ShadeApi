# apps/base.py
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict
import aiohttp
import logging
import json

@dataclass
class AppVersion:
    version: str
    architecture: str
    url: str
    hash: Optional[str] = None
    type: str = "exe"
    size: Optional[int] = None

    def to_dict(self):
        return {k: str(v) if isinstance(v, datetime) else v 
                for k, v in asdict(self).items() if v is not None}

@dataclass
class AppInfo:
    id: str
    name: str
    publisher: str
    versions: List[AppVersion]
    homepage: str
    last_updated: datetime

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'publisher': self.publisher,
            'versions': [v.to_dict() for v in self.versions],
            'homepage': self.homepage,
            'last_updated': self.last_updated.isoformat()
        }

class BaseAppTracker:
    def __init__(self):
        self.headers = {
            "User-Agent": "ShadeApi/1.0"
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_app_info(self) -> Optional[AppInfo]:
        """Her uygulama tracker'ı bu metodu implement etmeli"""
        raise NotImplementedError
    
    async def _make_request(self, url: str) -> Dict:
        """Genel HTTP istek fonksiyonu"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            self.logger.error(f"Error making request to {url}: {e}")
            raise