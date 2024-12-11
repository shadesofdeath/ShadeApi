# src/app_tracker.py
import os
import yaml
import json
import aiohttp
import asyncio
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import re
from jsonpath_ng import parse
from typing import Dict, List, Optional

class AppTracker:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.github_token = os.environ.get('GITHUB_TOKEN')

    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def scrape_info(self, config: Dict) -> Dict:
        """Website scraping ile bilgi çekme"""
        url = config['info']['url']
        async with self.session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            info = {}
            selectors = config['info']['selectors']
            
            # Versiyon için regex
            if 'version' in selectors:
                match = re.search(selectors['version'], html)
                if match:
                    info['version'] = match.group(1)
            
            # Diğer bilgiler için CSS selectors
            for key, selector in selectors.items():
                if key != 'version':
                    elem = soup.select_one(selector)
                    if elem:
                        info[key] = elem.get('content', elem.text.strip())
            
            return info

    async def fetch_api_info(self, config: Dict) -> Dict:
        """API endpoint'inden bilgi çekme"""
        url = config['info']['url']
        params = config['info'].get('params', {})
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            
            # JSONPath ile versiyon çıkarma
            version_expr = parse(config['info']['version_path'])
            version_matches = version_expr.find(data)
            if version_matches:
                return {'version': version_matches[0].value}
            
            return {}

    async def fetch_github_info(self, config: Dict) -> Dict:
        """GitHub'dan bilgi çekme"""
        headers = {'Authorization': f'token {self.github_token}'} if self.github_token else {}
        repo = config['repo']
        
        # Release bilgisi
        async with self.session.get(
            f'https://api.github.com/repos/{repo}/releases/latest',
            headers=headers
        ) as response:
            if response.status != 200:
                return {}
            
            release = await response.json()
            return {
                'version': release['tag_name'].strip('v'),
                'assets': release['assets']
            }

    async def process_app(self, yaml_path: Path) -> Optional[Dict]:
        """YAML'da tanımlı mantığa göre uygulama bilgilerini işle"""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            detect = config['detect']
            info = {}
            variants = []

            # Bilgi toplama
            if detect['type'] == 'scrape':
                info = await self.scrape_info(detect)
            elif detect['type'] == 'api':
                info = await self.fetch_api_info(detect)
            elif detect['type'] == 'github':
                info = await self.fetch_github_info(detect)

            # Dosya bilgilerini oluştur
            version = info.get('version')
            if version:
                version_clean = version.replace('.', '')
                
                if detect['type'] == 'scrape':
                    for pattern in detect['downloads']['patterns']:
                        url = detect['downloads']['base_url'] + pattern['pattern'].format(
                            version=version,
                            version_clean=version_clean
                        )
                        variants.append({
                            'version': version,
                            'architecture': pattern['arch'],
                            'type': pattern['type'],
                            'url': url
                        })
                
                elif detect['type'] == 'api':
                    for download in detect['downloads']:
                        variants.append({
                            'version': version,
                            'architecture': download['arch'],
                            'type': download['type'],
                            'url': download['url']
                        })
                
                elif detect['type'] == 'github':
                    for asset in info['assets']:
                        for pattern in detect['assets']:
                            if re.match(pattern['pattern'], asset['name']):
                                variants.append({
                                    'version': version,
                                    'architecture': pattern['arch'],
                                    'type': pattern['type'],
                                    'url': asset['browser_download_url']
                                })

            return {
                'name': config['name'],
                'variants': variants,
                'updated_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error processing {yaml_path}: {str(e)}")
            return None

    async def update_all_apps(self):
        """Tüm uygulamaları güncelle"""
        await self.init_session()
        try:
            apps_data = {}
            apps_dir = Path('apps')

            for category in apps_dir.iterdir():
                if category.is_dir():
                    for app_file in category.glob('*.yml'):
                        result = await self.process_app(app_file)
                        if result:
                            app_name = app_file.stem
                            apps_data[app_name] = result

            # Sonuçları kaydet
            data_dir = Path('data')
            data_dir.mkdir(exist_ok=True)
            
            output = {
                'last_updated': datetime.utcnow().isoformat(),
                'apps_count': len(apps_data),
                'apps': apps_data
            }

            with open(data_dir / 'apps.json', 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2)

        finally:
            await self.close_session()

if __name__ == '__main__':
    tracker = AppTracker()
    asyncio.run(tracker.update_all_apps())