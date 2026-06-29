import os
import json
import logging
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "scraper.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
CHANNELS = {
    "chemed_telegram": "CheMed Telegram Channel",
    "lobelia_cosmetics": "Lobelia Cosmetics",
    "tikvah_pharma": "Tikvah Pharma"
}

def generate_mock_data():
    """Generates realistic mock raw data for Telegram messages to ensure downstream pipeline runs without live credentials."""
    logger.info("Generating mock Telegram data (no API credentials provided or connection failed)...")
    
    # Simple products for realistic message text
    medical_products = ["Paracetamol 500mg", "Amoxicillin 250mg", "Ibuprofen 400mg", "Metformin 850mg", "Omeprazole 20mg", "Vitamin C", "Aspirin", "Insulin", "Ciprofloxacin", "Azithromycin"]
    cosmetic_products = ["Sunscreen SPF 50", "Moisturizer", "Anti-aging Serum", "Vitamin C Face Wash", "Shampoo Sulfate-free", "Lip Balm", "Aloe Vera Gel", "Cleanser"]
    pharma_products = ["Asthalin Inhaler", "Augmentin 625mg", "Panadol Extra", "Cetirizine 10mg", "Atorvastatin 10mg", "Loratadine", "Multivitamin Tablets"]

    start_date = datetime.now() - timedelta(days=5)
    
    for i in range(6):  # Generate data for the past 6 days
        date_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        dest_dir = os.path.join("data", "raw", "telegram_messages", date_str)
        os.makedirs(dest_dir, exist_ok=True)
        
        for ch_slug, ch_name in CHANNELS.items():
            messages = []
            num_messages = random.randint(3, 8)
            
            for msg_idx in range(num_messages):
                msg_id = 1000 + i * 100 + msg_idx
                has_media = random.choice([True, False])
                
                # Pick product name and generate text
                if "chemed" in ch_slug:
                    prod = random.choice(medical_products)
                    text = f"New arrival: {prod}. Price: {random.randint(100, 1500)} ETB. Available at all branches. Call us for delivery!"
                elif "lobelia" in ch_slug:
                    prod = random.choice(cosmetic_products)
                    text = f"Special promo on {prod}! Order now and get 10% discount. Price: {random.randint(200, 3000)} ETB. #LobeliaBeauty"
                else:
                    prod = random.choice(pharma_products)
                    text = f"Prescription drug: {prod} is now back in stock. Check with our pharmacists. Views and orders welcome."
                
                image_path = None
                if has_media:
                    # Create mock image file directory
                    img_dir = os.path.join("data", "raw", "images", ch_slug)
                    os.makedirs(img_dir, exist_ok=True)
                    image_path = os.path.join(img_dir, f"{msg_id}.jpg")
                    # Create a blank text file acting as image placeholder for YOLO
                    with open(image_path, "w") as img_f:
                        img_f.write(f"Mock image content for {ch_name} message {msg_id}")
                
                messages.append({
                    "message_id": msg_id,
                    "channel_name": ch_name,
                    "message_date": f"{date_str}T{random.randint(8, 20):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}+03:00",
                    "message_text": text,
                    "has_media": has_media,
                    "image_path": image_path,
                    "views": random.randint(50, 5000),
                    "forwards": random.randint(0, 50)
                })
            
            # Write JSON file
            filepath = os.path.join(dest_dir, f"{ch_slug}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(messages, f, indent=4, ensure_ascii=False)
                
    logger.info("Mock Telegram data generated successfully.")

async def scrape_live():
    """Live scraper using Telethon. Attempts to scrape if credentials exist."""
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        logger.warning("No API credentials in environment. Falling back to mock generator.")
        generate_mock_data()
        return

    from telethon import TelegramClient
    
    logger.info("Initializing TelegramClient...")
    client = TelegramClient('session_name', int(api_id), api_hash)
    
    try:
        await client.start()
        logger.info("Telegram Client connected successfully.")
        
        # Mapping channel nicknames
        channel_entities = {
            "chemed_telegram": "CheMed19",  # typical channel username
            "lobelia_cosmetics": "lobelia4cosmetics",
            "tikvah_pharma": "tikvahpharma"
        }
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        dest_dir = os.path.join("data", "raw", "telegram_messages", date_str)
        os.makedirs(dest_dir, exist_ok=True)
        
        for ch_slug, entity in channel_entities.items():
            logger.info(f"Scraping channel: {entity}")
            messages = []
            
            async for message in client.iter_messages(entity, limit=20):
                msg_id = message.id
                has_media = message.photo is not None
                image_path = None
                
                if has_media:
                    img_dir = os.path.join("data", "raw", "images", ch_slug)
                    os.makedirs(img_dir, exist_ok=True)
                    image_path = await message.download_media(file=os.path.join(img_dir, f"{msg_id}.jpg"))
                
                messages.append({
                    "message_id": msg_id,
                    "channel_name": CHANNELS[ch_slug],
                    "message_date": message.date.isoformat(),
                    "message_text": message.text or "",
                    "has_media": has_media,
                    "image_path": image_path,
                    "views": message.views or 0,
                    "forwards": message.forwards or 0
                })
            
            filepath = os.path.join(dest_dir, f"{ch_slug}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(messages, f, indent=4, ensure_ascii=False)
                
    except Exception as e:
        logger.error(f"Error during live scraping: {e}. Falling back to mock data.")
        generate_mock_data()
    finally:
        await client.disconnect()

def main():
    api_id = os.getenv("TELEGRAM_API_ID")
    if not api_id:
        generate_mock_data()
    else:
        import asyncio
        asyncio.run(scrape_live())

if __name__ == "__main__":
    main()
