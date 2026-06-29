import os
import json
import glob
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import logging

load_dotenv()

# Setup logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "load_raw.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# DB Connection Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "medical_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def create_raw_table(conn):
    with conn.cursor() as cur:
        # Create schema raw if not exists
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
        # Create table raw.telegram_messages
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw.telegram_messages (
                message_id INT,
                channel_name VARCHAR(100),
                message_date TIMESTAMP WITH TIME ZONE,
                message_text TEXT,
                has_media BOOLEAN,
                image_path TEXT,
                views INT,
                forwards INT,
                PRIMARY KEY (channel_name, message_id)
            );
        """)
        conn.commit()
    logger.info("Raw schema and telegram_messages table verified/created.")

def load_json_files(conn):
    search_path = os.path.join("data", "raw", "telegram_messages", "**", "*.json")
    json_files = glob.glob(search_path, recursive=True)
    
    if not json_files:
        logger.warning("No JSON files found in data/raw/telegram_messages/")
        return

    logger.info(f"Found {len(json_files)} JSON files to load.")
    all_messages = []
    
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                messages = json.load(f)
                for msg in messages:
                    # Map to tuple for execute_values
                    all_messages.append((
                        msg.get("message_id"),
                        msg.get("channel_name"),
                        msg.get("message_date"),
                        msg.get("message_text"),
                        msg.get("has_media"),
                        msg.get("image_path"),
                        msg.get("views"),
                        msg.get("forwards")
                    ))
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")

    if not all_messages:
        logger.warning("No message records found inside JSON files.")
        return

    # Upsert data to avoid duplicates
    insert_query = """
        INSERT INTO raw.telegram_messages (
            message_id, channel_name, message_date, message_text, has_media, image_path, views, forwards
        ) VALUES %s
        ON CONFLICT (channel_name, message_id) DO UPDATE SET
            message_date = EXCLUDED.message_date,
            message_text = EXCLUDED.message_text,
            has_media = EXCLUDED.has_media,
            image_path = EXCLUDED.image_path,
            views = EXCLUDED.views,
            forwards = EXCLUDED.forwards;
    """
    
    with conn.cursor() as cur:
        execute_values(cur, insert_query, all_messages)
        conn.commit()
        
    logger.info(f"Successfully upserted {len(all_messages)} messages to raw.telegram_messages table.")

def main():
    try:
        conn = get_db_connection()
        create_raw_table(conn)
        load_json_files(conn)
        conn.close()
        logger.info("Raw data load process finished successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to database or execute query: {e}")
        raise e

if __name__ == "__main__":
    main()
