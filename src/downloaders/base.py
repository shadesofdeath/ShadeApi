# src/downloaders/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class Release:
    """Uygulama sürüm detaylarını tutan sınıf"""
    # Temel bilgiler
    version: str
    url: str
    architecture: str
    type: str

    # Dosya bilgileri
    filename: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None
    hash_type: Optional[str] = None  # SHA256, MD5 vs.
    date: Optional[str] = None
    
    # İndirme/Yükleme bilgileri
    installerType: Optional[str] = None  # Setup, Portable, MSI vs.
    commandLine: Optional[str] = None  # Sessiz yükleme parametreleri
    productCode: Optional[str] = None  # MSI product code
    scope: Optional[str] = None  # User/Machine
    language: Optional[str] = "en-US"
    
    # Uygulama bilgileri
    publisher: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None
    category: Optional[str] = None
    minimumOS: Optional[str] = None
    
    # Ek bilgiler
    tags: List[str] = field(default_factory=list)
    releaseNotes: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

class BaseDownloader(ABC):
    """Temel indirici sınıfı"""
    
    def __init__(self):
        # Desteklenen dosya türleri ve açıklamaları
        self.file_types: Dict[str, str] = {
            'exe': 'Windows Executable',
            'msi': 'Windows Installer',
            'msix': 'Windows Package',
            'zip': 'Compressed Archive',
            'appx': 'Windows Store App',
            'pkg': 'Windows Package',
            'appxbundle': 'Windows App Bundle'
        }

        # Yükleyici türleri
        self.installer_types: Dict[str, str] = {
            'setup': 'Interactive Setup',
            'portable': 'Portable Application',
            'installer': 'Silent Installer',
            'standalone': 'Standalone Application',
            'msi': 'Windows Installer',
            'inno': 'Inno Setup',
            'nsis': 'NSIS Installer',
            'wix': 'WiX Installer'
        }

        # İşletim sistemi gereksinimleri
        self.os_requirements: Dict[str, str] = {
            'win7': 'Windows 7',
            'win8': 'Windows 8',
            'win10': 'Windows 10',
            'win11': 'Windows 11'
        }

        # Uygulama kategorileri
        self.categories: Dict[str, List[str]] = {
            'development': ['dev', 'developer', 'ide', 'programming'],
            'utility': ['tools', 'utilities', 'system'],
            'productivity': ['office', 'business', 'work'],
            'security': ['antivirus', 'firewall', 'protection'],
            'multimedia': ['audio', 'video', 'media', 'player'],
            'communication': ['chat', 'messaging', 'email'],
            'gaming': ['games', 'gaming'],
            'education': ['learning', 'educational', 'academic']
        }

    @abstractmethod
    async def get_releases(self) -> List[Release]:
        """
        Uygulama sürümlerini al
        Her alt sınıf bu metodu implement etmeli
        """
        pass

    def _format_size(self, size_bytes: int) -> str:
        """Byte cinsinden boyutu okunabilir formata çevir"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    def _detect_architecture(self, text: str) -> str:
        """Metin içinden mimariyi tespit et"""
        text = text.lower()
        
        # ARM mimarisi kontrolü
        if any(x in text for x in ['arm64', 'aarch64']):
            return 'arm64'
        
        # x64 kontrolü
        if any(x in text for x in ['x64', 'amd64', '64bit', 'win64', 'x86_64']):
            return 'x64'
        
        # x86 kontrolü
        if any(x in text for x in ['x86', 'win32', '32bit', 'i386']):
            return 'x86'
            
        return 'x86'  # Varsayılan değer

    def _detect_file_type(self, filename: str) -> str:
        """Dosya adından türünü tespit et"""
        ext = filename.split('.')[-1].lower()
        return self.file_types.get(ext, ext)

    def _detect_installer_type(self, filename: str, description: str = '') -> str:
        """Yükleyici türünü tespit et"""
        text = (filename + ' ' + description).lower()
        
        # Portable kontrol
        if 'portable' in text:
            return self.installer_types['portable']
            
        # Setup kontrol
        if any(x in text for x in ['setup', 'installer']):
            return self.installer_types['setup']
            
        # Standalone kontrol
        if 'standalone' in text:
            return self.installer_types['standalone']
            
        # MSI kontrol
        if filename.endswith('.msi'):
            return self.installer_types['msi']
            
        return 'Default'

    def _detect_category(self, text: str, tags: List[str] = None) -> str:
        """Uygulama kategorisini tespit et"""
        text = text.lower()
        tags = [t.lower() for t in (tags or [])]
        
        for category, keywords in self.categories.items():
            if any(keyword in text for keyword in keywords):
                return category
            if any(keyword in tag for tag in tags for keyword in keywords):
                return category
                
        return 'other'

    def _detect_minimum_os(self, text: str) -> str:
        """Minimum işletim sistemi gereksinimini tespit et"""
        text = text.lower()
        
        # En yüksek sürümden başlayarak kontrol et
        if 'windows 11' in text or 'win11' in text:
            return self.os_requirements['win11']
        if 'windows 10' in text or 'win10' in text:
            return self.os_requirements['win10']
        if 'windows 8' in text or 'win8' in text:
            return self.os_requirements['win8']
        if 'windows 7' in text or 'win7' in text:
            return self.os_requirements['win7']
            
        return 'Windows'  # Varsayılan değer

    def _clean_version(self, version: str) -> str:
        """Versiyon stringini temizle"""
        # v1.2.3 -> 1.2.3
        version = version.lower().strip()
        if version.startswith('v'):
            version = version[1:]
            
        # Sadece sayı ve noktaları bırak
        import re
        version = re.sub(r'[^\d.]', '', version)
        
        return version

    def _extract_command_line(self, text: str) -> Optional[str]:
        """Sessiz yükleme parametrelerini çıkar"""
        text = text.lower()
        
        # Yaygın sessiz yükleme parametreleri
        if '/s' in text or '/quiet' in text or '--silent' in text:
            params = []
            if '/s' in text: params.append('/S')
            if '/quiet' in text: params.append('/quiet')
            if '--silent' in text: params.append('--silent')
            return ' '.join(params)
            
        return None

    def _is_valid_release(self, release: Release) -> bool:
        """Release nesnesinin geçerli olup olmadığını kontrol et"""
        # Zorunlu alanları kontrol et
        if not all([release.version, release.url, release.architecture, release.type]):
            return False
            
        # URL formatını kontrol et
        if not release.url.startswith(('http://', 'https://')):
            return False
            
        return True

    def _normalize_filename(self, url: str) -> str:
        """URL'den dosya adını çıkar ve normalize et"""
        import urllib.parse
        return urllib.parse.unquote(url.split('/')[-1])

    def _extract_hash(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """Metin içinden hash değeri ve türünü çıkar"""
        hash_patterns = {
            'md5': r'MD5:\s*([a-fA-F0-9]{32})',
            'sha1': r'SHA1:\s*([a-fA-F0-9]{40})',
            'sha256': r'SHA256:\s*([a-fA-F0-9]{64})'
        }
        
        for hash_type, pattern in hash_patterns.items():
            import re
            match = re.search(pattern, text)
            if match:
                return match.group(1), hash_type
                
        return None, None