# apps/chrome.py
from datetime import datetime
from typing import Optional
from .base import BaseAppTracker, AppInfo, AppVersion

class ChromeTracker(BaseAppTracker):
    async def get_app_info(self) -> Optional[AppInfo]:
        try:
            # Chrome versiyonunu Win64 için al
            data = await self._make_request("https://chromiumdash.appspot.com/fetch_releases?channel=Stable&platform=Win64")
            if not data or not data[0]:
                return None

            latest_version = data[0].get('version')
            
            if not latest_version:
                return None

            versions = [
                AppVersion(
                    version=latest_version,
                    architecture="x64",
                    url="https://dl.google.com/chrome/install/ChromeStandaloneSetup64.exe",
                    type="exe",
                    size=85000000  # Yaklaşık boyut
                ),
                AppVersion(
                    version=latest_version,
                    architecture="x86",
                    url="https://dl.google.com/chrome/install/ChromeStandaloneSetup.exe",
                    type="exe",
                    size=75000000  # Yaklaşık boyut
                )
            ]

            return AppInfo(
                id="chrome",
                name="Google Chrome",
                publisher="Google LLC",
                versions=versions,
                homepage="https://www.google.com/chrome",
                last_updated=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"Error tracking Chrome: {e}")
            return None