# main.py
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from apps import ChromeTracker, VSCodeTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_app_data():
    """Tüm trackerları çalıştır ve sonuçları kaydet"""
    output_dir = Path("docs/data")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Tracker listesi
    trackers = [
        ChromeTracker(),
        VSCodeTracker()
    ]
    
    results = []
    
    # Her tracker'ı çalıştır
    for tracker in trackers:
        try:
            logger.info(f"Running {tracker.__class__.__name__}")
            result = await tracker.get_app_info()
            
            if result:
                results.append(result)
                
                # Her uygulama için ayrı JSON dosyası oluştur
                app_file = output_dir / f"{result.id}.json"
                with open(app_file, "w", encoding="utf-8") as f:
                    json.dump(result.to_dict(), f, indent=2)
                logger.info(f"Saved data for {result.id}")
        
        except Exception as e:
            logger.error(f"Error with {tracker.__class__.__name__}: {e}")
    
    # Index dosyasını oluştur
    index = {
        "last_updated": datetime.now().isoformat(),
        "total_apps": len(results),
        "apps": [app.to_dict() for app in results]
    }
    
    index_file = output_dir / "index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    
    logger.info(f"Updated index.json with {len(results)} apps")

if __name__ == "__main__":
    asyncio.run(update_app_data())