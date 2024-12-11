# apps/vscode.py
from datetime import datetime
from typing import Optional
from .base import BaseAppTracker, AppInfo, AppVersion

class VSCodeTracker(BaseAppTracker):
    async def get_app_info(self) -> Optional[AppInfo]:
        try:
            data = await self._make_request("https://update.code.visualstudio.com/api/releases/stable")
            latest = data[0]
            
            versions = []
            for arch in ["win32-x64", "win32-arm64"]:
                if arch in latest["downloads"]:
                    versions.append(
                        AppVersion(
                            version=latest["version"],
                            architecture=arch.split("-")[1],
                            url=latest["downloads"][arch]["url"],
                            hash=latest["downloads"][arch].get("sha256"),
                            type="exe",
                            size=latest["downloads"][arch].get("size")
                        )
                    )

            return AppInfo(
                id="vscode",
                name="Visual Studio Code",
                publisher="Microsoft Corporation",
                versions=versions,
                homepage="https://code.visualstudio.com",
                last_updated=datetime.fromisoformat(latest["timestamp"].replace("Z", "+00:00"))
            )

        except Exception as e:
            self.logger.error(f"Error tracking VSCode: {e}")
            return None