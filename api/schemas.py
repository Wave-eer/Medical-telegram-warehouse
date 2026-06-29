from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProductMention(BaseModel):
    product_name: str
    mention_count: int

class TopProductsResponse(BaseModel):
    products: List[ProductMention]

class ChannelActivity(BaseModel):
    channel_name: str
    total_posts: int
    avg_views: float
    first_post_date: Optional[datetime]
    last_post_date: Optional[datetime]

class MessageSearchItem(BaseModel):
    message_id: int
    channel_name: str
    message_text: str
    views: int
    forwards: int
    message_date: Optional[datetime]

class VisualContentStats(BaseModel):
    channel_name: str
    total_images: int
    promotional_count: int
    product_display_count: int
    lifestyle_count: int
    other_count: int
