from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from api.database import get_db, engine
from api import schemas

app = FastAPI(
    title="Ethiopian Medical Business Analytics API",
    description="REST API for insights on scraped medical channels in Ethiopia, transformed via dbt.",
    version="1.0.0"
)

# Endpoint 1: Top Products
@app.get("/api/reports/top-products", response_model=schemas.TopProductsResponse)
def get_top_products(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """
    Returns the most frequently mentioned medical/pharmaceutical products or cosmetic brands in message texts.
    Performs text search frequency analysis in the fct_messages table.
    """
    # Common products to search for dynamically
    products_to_track = [
        "paracetamol", "amoxicillin", "ibuprofen", "metformin", "omeprazole", 
        "vitamin c", "aspirin", "insulin", "ciprofloxacin", "azithromycin", 
        "sunscreen", "moisturizer", "serum", "shampoo", "panadol", "asthalin", "augmentin"
    ]
    
    # We will build a dynamic SQL query to count occurrences of each product keyword in message_text
    case_statements = []
    for prod in products_to_track:
        # Match case-insensitively
        case_statements.append(f"SUM(CASE WHEN LOWER(message_text) LIKE '%{prod}%' THEN 1 ELSE 0 END) as \"{prod}\"")
        
    select_clause = ", ".join(case_statements)
    query = f"SELECT {select_clause} FROM public_marts.fct_messages"
    
    try:
        result = db.execute(text(query)).fetchone()
        if not result:
            return {"products": []}
            
        product_counts = []
        # Get results
        keys = result.keys()
        for key in keys:
            count = result._mapping[key] or 0
            if count > 0:
                product_counts.append({"product_name": key.capitalize(), "mention_count": count})
                
        # Sort by count descending
        product_counts.sort(key=lambda x: x["mention_count"], reverse=True)
        return {"products": product_counts[:limit]}
    except Exception as e:
        # Fallback to local schema if public_marts is not found
        try:
            query_fallback = query.replace("public_marts.fct_messages", "fct_messages")
            result = db.execute(text(query_fallback)).fetchone()
            product_counts = []
            if result:
                for key in result.keys():
                    count = result._mapping[key] or 0
                    product_counts.append({"product_name": key.capitalize(), "mention_count": count})
                product_counts.sort(key=lambda x: x["mention_count"], reverse=True)
                return {"products": product_counts[:limit]}
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

# Endpoint 2: Channel Activity
@app.get("/api/channels/{channel_name}/activity", response_model=schemas.ChannelActivity)
def get_channel_activity(channel_name: str, db: Session = Depends(get_db)):
    """
    Returns posting activity and aggregated metrics for a specific channel.
    """
    query = text("""
        SELECT channel_name, total_posts, avg_views, first_post_date, last_post_date
        FROM public_marts.dim_channels
        WHERE LOWER(channel_name) LIKE :name
    """)
    
    try:
        row = db.execute(query, {"name": f"%{channel_name.lower()}%"}).fetchone()
        if not row:
            # Fallback schema check
            query_fallback = text("""
                SELECT channel_name, total_posts, avg_views, first_post_date, last_post_date
                FROM dim_channels
                WHERE LOWER(channel_name) LIKE :name
            """)
            row = db.execute(query_fallback, {"name": f"%{channel_name.lower()}%"}).fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="Channel not found")
            
        return schemas.ChannelActivity(
            channel_name=row.channel_name,
            total_posts=row.total_posts,
            avg_views=row.avg_views,
            first_post_date=row.first_post_date,
            last_post_date=row.last_post_date
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

# Endpoint 3: Message Search
@app.get("/api/search/messages", response_model=List[schemas.MessageSearchItem])
def search_messages(query: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """
    Searches for messages containing a specific keyword (e.g., 'paracetamol').
    """
    sql = text("""
        SELECT f.message_id, c.channel_name, f.message_text, f.view_count as views, f.forward_count as forwards, d.full_date as message_date
        FROM public_marts.fct_messages f
        JOIN public_marts.dim_channels c ON f.channel_key = c.channel_key
        JOIN public_marts.dim_dates d ON f.date_key = d.date_key
        WHERE LOWER(f.message_text) LIKE :query
        ORDER BY f.view_count DESC
        LIMIT :limit
    """)
    
    try:
        result = db.execute(sql, {"query": f"%{query.lower()}%", "limit": limit}).fetchall()
        if not result:
            # Fallback schema check
            sql_fallback = text("""
                SELECT f.message_id, c.channel_name, f.message_text, f.view_count as views, f.forward_count as forwards, d.full_date as message_date
                FROM fct_messages f
                JOIN dim_channels c ON f.channel_key = c.channel_key
                JOIN dim_dates d ON f.date_key = d.date_key
                WHERE LOWER(f.message_text) LIKE :query
                ORDER BY f.view_count DESC
                LIMIT :limit
            """)
            result = db.execute(sql_fallback, {"query": f"%{query.lower()}%", "limit": limit}).fetchall()
            
        return [
            schemas.MessageSearchItem(
                message_id=row.message_id,
                channel_name=row.channel_name,
                message_text=row.message_text,
                views=row.views,
                forwards=row.forwards,
                message_date=row.message_date
            )
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

# Endpoint 4: Visual Content Stats
@app.get("/api/reports/visual-content", response_model=List[schemas.VisualContentStats])
def get_visual_content_stats(db: Session = Depends(get_db)):
    """
    Returns image classification categories count across channels.
    """
    sql = text("""
        SELECT 
            c.channel_name,
            COUNT(d.message_id) AS total_images,
            SUM(CASE WHEN d.image_category = 'promotional' THEN 1 ELSE 0 END) AS promotional_count,
            SUM(CASE WHEN d.image_category = 'product_display' THEN 1 ELSE 0 END) AS product_display_count,
            SUM(CASE WHEN d.image_category = 'lifestyle' THEN 1 ELSE 0 END) AS lifestyle_count,
            SUM(CASE WHEN d.image_category = 'other' THEN 1 ELSE 0 END) AS other_count
        FROM public_marts.fct_image_detections d
        JOIN public_marts.dim_channels c ON d.channel_key = c.channel_key
        GROUP BY c.channel_name
    """)
    
    try:
        result = db.execute(sql).fetchall()
        if not result:
            # Fallback schema check
            sql_fallback = text("""
                SELECT 
                    c.channel_name,
                    COUNT(d.message_id) AS total_images,
                    SUM(CASE WHEN d.image_category = 'promotional' THEN 1 ELSE 0 END) AS promotional_count,
                    SUM(CASE WHEN d.image_category = 'product_display' THEN 1 ELSE 0 END) AS product_display_count,
                    SUM(CASE WHEN d.image_category = 'lifestyle' THEN 1 ELSE 0 END) AS lifestyle_count,
                    SUM(CASE WHEN d.image_category = 'other' THEN 1 ELSE 0 END) AS other_count
                FROM fct_image_detections d
                JOIN dim_channels c ON d.channel_key = c.channel_key
                GROUP BY c.channel_name
            """)
            result = db.execute(sql_fallback).fetchall()
            
        return [
            schemas.VisualContentStats(
                channel_name=row.channel_name,
                total_images=row.total_images,
                promotional_count=row.promotional_count,
                product_display_count=row.product_display_count,
                lifestyle_count=row.lifestyle_count,
                other_count=row.other_count
            )
            for row in result
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

@app.get("/")
def read_root():
    return {"message": "Welcome to Kara Solutions Ethiopian Medical Business Data Warehouse API. Visit /docs for documentation."}
