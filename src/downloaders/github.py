# src/downloaders/github.py
from .base import BaseDownloader, Release
import aiohttp
import os
from datetime import datetime
import re

class GithubDownloader(BaseDownloader):
    async def get_releases(self, repo: str) -> List[Release]:
        headers = {
            'Authorization': f"token {os.environ.get('GITHUB_TOKEN')}",
            'Accept': 'application/vnd.github.v3+json'
        }
        
        async with aiohttp.ClientSession() as session:
            # Repo bilgilerini al
            async with session.get(
                f'https://api.github.com/repos/{repo}',
                headers=headers
            ) as response:
                if response.status != 200:
                    return []
                repo_info = await response.json()

            # Release bilgilerini al
            async with session.get(
                f'https://api.github.com/repos/{repo}/releases/latest',
                headers=headers
            ) as response:
                if response.status != 200:
                    return []
                release_info = await response.json()

            # README dosyasını al (daha detaylı açıklama için)
            async with session.get(
                f'https://api.github.com/repos/{repo}/readme',
                headers=headers
            ) as response:
                readme_content = ""
                if response.status == 200:
                    readme_info = await response.json()
                    import base64
                    readme_content = base64.b64decode(readme_info['content']).decode('utf-8')

            releases = []
            version = release_info['tag_name'].strip('v')
            
            for asset in release_info['assets']:
                filename = asset['name']
                arch = self._detect_architecture(filename)
                file_type = self._detect_file_type(filename)
                installer_type = self._detect_installer_type(filename, asset.get('label', ''))
                
                releases.append(Release(
                    version=version,
                    url=asset['browser_download_url'],
                    architecture=arch,
                    type=file_type,
                    date=release_info['published_at'],
                    size=asset['size'],
                    installerType=installer_type,
                    publisher=repo_info['owner']['login'],
                    description=repo_info['description'] or self._extract_description(readme_content),
                    homepage=repo_info['homepage'] or repo_info['html_url'],
                    license=repo_info.get('license', {}).get('name', 'Unknown'),
                    filename=filename,
                    minimumOS=self._detect_minimum_os(filename, readme_content),
                    category=self._detect_category(repo_info['topics'] if 'topics' in repo_info else []),
                    tags=repo_info.get('topics', [])
                ))

            return releases

    def _detect_architecture(self, filename: str) -> str:
        filename = filename.lower()
        if any(x in filename for x in ['x64', 'amd64', '64bit', 'win64']):
            return 'x64'
        elif any(x in filename for x in ['arm64', 'aarch64']):
            return 'arm64'
        elif any(x in filename for x in ['x86', 'win32', '32bit']):
            return 'x86'
        return 'x86'

    def _detect_file_type(self, filename: str) -> str:
        ext = filename.split('.')[-1].lower()
        return self.file_types.get(ext, ext)

    def _detect_minimum_os(self, filename: str, readme: str) -> str:
        # Windows sürümünü tespit etmeye çalış
        if 'windows 11' in readme.lower():
            return 'Windows 11'
        elif 'windows 10' in readme.lower():
            return 'Windows 10'
        elif 'windows 7' in readme.lower():
            return 'Windows 7'
        return 'Windows'

    def _detect_category(self, topics: List[str]) -> str:
        categories = {
            'dev': ['developer', 'development', 'programming', 'code'],
            'utility': ['utility', 'tool', 'system'],
            'multimedia': ['audio', 'video', 'media', 'player'],
            'productivity': ['office', 'document', 'productivity'],
            'security': ['security', 'encryption', 'antivirus'],
            'communication': ['chat', 'messaging', 'communication']
        }
        
        for topic in topics:
            for category, keywords in categories.items():
                if any(keyword in topic.lower() for keyword in keywords):
                    return category
        return 'other'

    def _extract_description(self, readme: str) -> str:
        if not readme:
            return ""
        
        # İlk anlamlı paragrafı bul
        paragraphs = readme.split('\n\n')
        for p in paragraphs:
            clean_p = re.sub(r'[#*`]', '', p).strip()
            if len(clean_p) > 20:  # Anlamlı bir açıklama olmalı
                return clean_p[:200]  # İlk 200 karakter
        return ""