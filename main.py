# main.py
import asyncio
import json
import logging
import importlib
import pkgutil
import inspect
from datetime import datetime
from pathlib import Path
from typing import List, Type
import apps
from apps.base import BaseAppTracker, AppInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_all_trackers() -> List[Type[BaseAppTracker]]:
    """apps dizinindeki tüm tracker'ları otomatik olarak bulur"""
    trackers = []
    
    for _, name, _ in pkgutil.iter_modules(apps.__path__):
        if name != "base":
            module = importlib.import_module(f"apps.{name}")
            for _, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseAppTracker) and 
                    obj != BaseAppTracker):
                    trackers.append(obj)
    
    return trackers

async def update_app_data():
    """Tüm tracker'ları çalıştırır ve sonuçları kaydeder"""
    output_dir = Path("docs/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    trackers = await get_all_trackers()
    results: List[AppInfo] = []
    
    for tracker_class in trackers:
        try:
            tracker = tracker_class()
            logger.info(f"Running {tracker_class.__name__}")
            result = await tracker.get_app_info()
            
            if result:
                results.append(result)
                
                # Her uygulama için ayrı JSON
                app_file = output_dir / f"{result.id}.json"
                with open(app_file, "w", encoding="utf-8") as f:
                    json.dump(result.__dict__, f, indent=2, default=str)
        
        except Exception as e:
            logger.error(f"Error with {tracker_class.__name__}: {e}")
    
    # Index dosyasını oluştur
    index = {
        "last_updated": datetime.now().isoformat(),
        "total_apps": len(results),
        "apps": [
            {
                "id": app.id,
                "name": app.name,
                "publisher": app.publisher,
                "version": app.versions[0].version if app.versions else None,
                "last_updated": app.last_updated.isoformat()
            }
            for app in results
        ]
    }
    
    with open(output_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

if __name__ == "__main__":
    asyncio.run(update_app_data())