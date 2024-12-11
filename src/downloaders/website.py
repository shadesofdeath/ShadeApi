# src/downloaders/website.py
from .base import BaseDownloader, Release
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import re
from typing import Optional, Dict

class WebsiteDownloader(BaseDownloader):
    def __init__(self):
        super().__init__()
        self.download_keywords = ['download', 'setup', 'install', 'get', 'latest']
        self.size_pattern = r'(\d+(?:\.\d+)?)\s*(MB|GB|KB)'
        self.date_pattern = r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
        self.version_pattern = r'(?:version|v)?[\s-]*(\d+\.\d+(?:\.\d+)?)'

    async def get_releases(self, url: str) -> List[Release]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Sayfa meta bilgilerini al
                    meta_info = self._extract_meta_info(soup)
                    
                    # İndirme linklerini bul
                    return self._find_downloads(soup, url, meta_info)

    def _extract_meta_info(self, soup: BeautifulSoup) -> Dict:
        meta = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            meta['title'] = title_tag.text.strip()
        
        # Description
        desc_tag = soup.find('meta', {'name': 'description'})
        if desc_tag:
            meta['description'] = desc_tag.get('content', '')
        
        # Publisher
        publisher_tag = soup.find('meta', {'name': ['publisher', 'author']})
        if publisher_tag:
            meta['publisher'] = publisher_tag.get('content', '')
        
        return meta

    def _find_downloads(self, soup: BeautifulSoup, base_url: str, meta_info: Dict) -> List[Release]:
        releases = []
        version = self._extract_version(soup)
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.text.lower()
            parent_text = link.parent.text.lower() if link.parent else ''
            
            if self._is_download_link(href, text):
                if not href.startswith(('http://', 'https://')):
                    href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                
                size = self._extract_size(parent_text)
                date = self._extract_date(parent_text)
                arch = self._detect_architecture(href + ' ' + text)
                file_type = self._detect_file_type(href)
                installer_type = self._detect_installer_type(href, text)
                
                releases.append(Release(
                    version=version,
                    url=href,
                    architecture=arch,
                    type=file_type,
                    date=date,
                    size=size,
                    installerType=installer_type,
                    publisher=meta_info.get('publisher', ''),
                    description=meta_info.get('description', ''),
                    homepage=base_url,
                    filename=href.split('/')[-1]
                ))
        
        return releases

    def _is_download_link(self, href: str, text: str) -> bool:
        return (
            any(ext in href.lower() for ext in self.file_types.keys()) or
            any(kw in text.lower() for kw in self.download_keywords)
        )

    def _extract_version(self, soup: BeautifulSoup) -> str:
        # Sayfa içeriğinde versiyon numarası ara
        text = soup.get_text()
        version_matches = re.findall(self.version_pattern, text)
        return version_matches[0] if version_matches else 'latest'

    def _extract_size(self, text: str) -> Optional[int]:
        size_match = re.search(self.size_pattern, text)
        if size_match:
            value, unit = size_match.groups()
            multiplier = {
                'KB': 1024,
                'MB': 1024 * 1024,
                'GB': 1024 * 1024 * 1024
            }
            return int(float(value) * multiplier[unit])
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        date_match = re.search(self.date_pattern, text)
        if date_match:
            return date_match.group(1)
        return None