from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Release:
    version: str
    url: str
    architecture: str
    type: str
    size: Optional[int] = None
    date: Optional[datetime] = None

class BaseDownloader(ABC):
    @abstractmethod
    async def get_releases(self) -> List[Release]:
        pass

# src/downloaders/github.py
from .base import BaseDownloader, Release
import aiohttp
import os

class GithubDownloader(BaseDownloader):
    async def get_releases(self, repo: str) -> List[Release]:
        headers = {
            'Authorization': f"token {os.environ.get('GITHUB_TOKEN')}",
            'Accept': 'application/vnd.github.v3+json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'https://api.github.com/repos/{repo}/releases/latest',
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    releases = []
                    version = data['tag_name'].strip('v')
                    
                    for asset in data['assets']:
                        arch = self._detect_architecture(asset['name'])
                        type = asset['name'].split('.')[-1]
                        releases.append(Release(
                            version=version,
                            url=asset['browser_download_url'],
                            architecture=arch,
                            type=type,
                            size=asset['size'],
                            date=datetime.fromisoformat(data['published_at'].replace('Z', '+00:00'))
                        ))
                    return releases
                return []

    def _detect_architecture(self, filename: str) -> str:
        filename = filename.lower()
        if any(x in filename for x in ['x64', 'amd64', '64bit', 'win64']):
            return 'x64'
        elif any(x in filename for x in ['arm64', 'aarch64']):
            return 'arm64'
        return 'x86'

# src/downloaders/direct.py
from .base import BaseDownloader, Release

class DirectDownloader(BaseDownloader):
    async def get_releases(self, downloads: list) -> List[Release]:
        return [
            Release(
                version='latest',
                url=download['url'],
                architecture=download['arch'],
                type=download.get('type', 'exe')
            )
            for download in downloads
        ]

# src/downloaders/website.py
from .base import BaseDownloader, Release
import aiohttp
from bs4 import BeautifulSoup

class WebsiteDownloader(BaseDownloader):
    def __init__(self):
        self.download_keywords = ['download', 'setup', 'install', 'get', 'latest']
        self.file_types = ['.exe', '.msi', '.zip', '.msix']
        self.arch_indicators = {
            'x64': ['x64', '64-bit', 'win64', 'x86_64', 'amd64', '64bit'],
            'x86': ['x86', '32-bit', 'win32', 'i386', '32bit'],
            'arm64': ['arm64', 'aarch64', 'arm']
        }

    async def get_releases(self, url: str) -> List[Release]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    return self._find_downloads(soup, url)
                return []

    def _find_downloads(self, soup: BeautifulSoup, base_url: str) -> List[Release]:
        releases = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.text.lower()
            
            if any(ext in href.lower() for ext in self.file_types) or \
               any(kw in text for kw in self.download_keywords):
                
                if not href.startswith(('http://', 'https://')):
                    href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                
                arch = self._detect_architecture(href + ' ' + text)
                file_type = self._detect_file_type(href)
                
                if arch and file_type:
                    releases.append(Release(
                        version='latest',
                        url=href,
                        architecture=arch,
                        type=file_type
                    ))
        
        return releases

    def _detect_architecture(self, text: str) -> str:
        text = text.lower()
        for arch, indicators in self.arch_indicators.items():
            if any(ind in text for ind in indicators):
                return arch
        return 'x86'

    def _detect_file_type(self, url: str) -> str:
        for ext in self.file_types:
            if url.lower().endswith(ext):
                return ext.lstrip('.')
        return 'exe'

# src/app_tracker.py
import asyncio
import yaml
import json
from pathlib import Path
from datetime import datetime
from .downloaders.github import GithubDownloader
from .downloaders.direct import DirectDownloader
from .downloaders.website import WebsiteDownloader

class AppTracker:
    def __init__(self):
        self.github_downloader = GithubDownloader()
        self.direct_downloader = DirectDownloader()
        self.website_downloader = WebsiteDownloader()

    async def process_app(self, yaml_path: Path) -> dict:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        detect = config['detect']
        releases = []

        try:
            if detect['type'] == 'github':
                releases = await self.github_downloader.get_releases(detect['repo'])
            elif detect['type'] == 'direct':
                releases = await self.direct_downloader.get_releases(detect['downloads'])
            elif detect['type'] == 'website':
                releases = await self.website_downloader.get_releases(detect['base_url'])

            if releases:
                return {
                    'name': config['name'],
                    'variants': [vars(r) for r in releases],
                    'updated_at': datetime.utcnow().isoformat()
                }
        except Exception as e:
            print(f"Error processing {yaml_path}: {str(e)}")
        
        return None

    async def update_all_apps(self):
        apps_data = {}
        apps_dir = Path('apps')

        for category in apps_dir.iterdir():
            if category.is_dir():
                for app_file in category.glob('*.yml'):
                    result = await self.process_app(app_file)
                    if result:
                        app_name = app_file.stem
                        apps_data[app_name] = result

        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        output = {
            'last_updated': datetime.utcnow().isoformat(),
            'apps_count': len(apps_data),
            'apps': apps_data
        }

        with open(data_dir / 'apps.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

async def main():
    tracker = AppTracker()
    await tracker.update_all_apps()

if __name__ == '__main__':
    asyncio.run(main())