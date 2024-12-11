# src/utils.py
import os
import yaml
import json
import hashlib
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

class AppUtils:
    @staticmethod
    def load_yaml(file_path: Path) -> Dict[str, Any]:
        """YAML dosyasını yükle"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading YAML {file_path}: {str(e)}")
            return {}

    @staticmethod
    def save_json(data: Dict[str, Any], file_path: Path) -> bool:
        """JSON dosyasına kaydet"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving JSON {file_path}: {str(e)}")
            return False

    @staticmethod
    def clean_version(version: str) -> str:
        """Versiyon string'ini temizle"""
        # v1.2.3 -> 1.2.3
        version = version.lower().strip()
        if version.startswith('v'):
            version = version[1:]
        return version

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Byte cinsinden boyutu okunabilir formata çevir"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    @staticmethod
    async def calculate_file_hash(session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Dosyanın SHA256 hash'ini hesapla"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    hasher = hashlib.sha256()
                    async for chunk in response.content.iter_chunked(8192):
                        hasher.update(chunk)
                    return hasher.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {url}: {str(e)}")
        return None

    @staticmethod
    def detect_architecture(filename: str) -> str:
        """Dosya adından mimariyi tespit et"""
        filename = filename.lower()
        if any(x in filename for x in ['x64', 'amd64', '64bit', 'win64']):
            return 'x64'
        elif any(x in filename for x in ['arm64', 'aarch64']):
            return 'arm64'
        return 'x86'

    @staticmethod
    def detect_file_type(filename: str) -> str:
        """Dosya adından dosya türünü tespit et"""
        extensions = {
            'exe': 'exe',
            'msi': 'msi',
            'zip': 'zip',
            'msix': 'msix',
            'appx': 'appx'
        }
        ext = filename.split('.')[-1].lower()
        return extensions.get(ext, ext)

    @staticmethod
    def normalize_app_name(name: str) -> str:
        """Uygulama adını normalize et"""
        # Özel karakterleri kaldır, boşlukları tire ile değiştir
        return re.sub(r'[^a-zA-Z0-9-]', '', name.lower().replace(' ', '-'))

    @staticmethod
    def get_category_folder(app_name: str) -> str:
        """Uygulama adına göre kategori klasörünü belirle"""
        first_char = app_name[0].lower()
        if first_char.isdigit():
            return first_char
        return first_char if first_char.isalpha() else 'other'

    @staticmethod
    def validate_app_data(app_data: Dict[str, Any]) -> List[str]:
        """App verilerini doğrula ve hataları döndür"""
        errors = []
        required_fields = ['name', 'variants']
        
        for field in required_fields:
            if field not in app_data:
                errors.append(f"Missing required field: {field}")

        if 'variants' in app_data:
            for idx, variant in enumerate(app_data['variants']):
                if 'version' not in variant:
                    errors.append(f"Missing version in variant {idx}")
                if 'url' not in variant:
                    errors.append(f"Missing url in variant {idx}")

        return errors

    @staticmethod
    def load_cached_data() -> Dict[str, Any]:
        """Önbellekteki app verilerini yükle"""
        cache_file = Path('data/apps.json')
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cache: {str(e)}")
        return {'apps': {}, 'last_updated': None}

    @staticmethod
    def compare_versions(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Eski ve yeni veriler arasındaki değişiklikleri bul"""
        changes = {
            'updated': [],
            'added': [],
            'removed': []
        }

        old_apps = old_data.get('apps', {})
        new_apps = new_data.get('apps', {})

        # Güncellenen ve yeni eklenen uygulamalar
        for app_id, app_data in new_apps.items():
            if app_id in old_apps:
                old_version = old_apps[app_id].get('variants', [{}])[0].get('version')
                new_version = app_data.get('variants', [{}])[0].get('version')
                if old_version != new_version:
                    changes['updated'].append(app_id)
            else:
                changes['added'].append(app_id)

        # Silinen uygulamalar
        for app_id in old_apps:
            if app_id not in new_apps:
                changes['removed'].append(app_id)

        return changes