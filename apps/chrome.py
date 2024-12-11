# apps/chrome.py
from datetime import datetime
from typing import Optional
from .base import BaseAppTracker, AppInfo, AppVersion

class ChromeTracker(BaseAppTracker):
    async def get_app_info(self) -> Optional[AppInfo]:
        try:
            data = await self._make_request("https://omahaproxy.appspot.com/json")
            
            win_stable = next(
                (item for item in data if item["os"] == "win" and item["channel"] == "stable"),
                None
            )
            
            if not win_stable:
                return None

            versions = [
                AppVersion(
                    version=win_stable["version"],
                    architecture="x64",
                    url="https://dl.google.com/chrome/install/ChromeStandaloneSetup64.exe",
                    type="exe"
                ),
                AppVersion(
                    version=win_stable["version"],
                    architecture="x86",
                    url="https://dl.google.com/chrome/install/ChromeStandaloneSetup.exe",
                    type="exe"
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