from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ReturnDocument
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
app = FastAPI()
api_router = APIRouter(prefix="/api")


class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: f"sat-{uuid.uuid4().hex[:10]}")
    name: str
    slug: str
    category: str
    price: int = Field(ge=0)
    compare: int = Field(ge=0)
    description: str = ""
    material: str = ""
    size: str = ""
    image: str = ""
    secondImage: str = ""
    badge: str = ""
    stock: int = Field(default=20, ge=0)
    bestseller: bool = False


class OrderItem(BaseModel):
    product_id: str
    name: str
    price: int = Field(ge=0)
    qty: int = Field(ge=1)
    image: str = ""


class OrderCreate(BaseModel):
    items: List[OrderItem]
    customer: dict = Field(default_factory=dict)
    payment_method: str = "upi"
    total: int = Field(ge=0)


class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    product_id: str
    name: str
    rating: int
    title: str
    body: str
    verified: bool = True


@api_router.get("/")
async def root():
    return {"message": "Sattva & Samagri API"}


@api_router.get("/products", response_model=List[Product])
async def list_products():
    return await db.products.find({}, {"_id": 0}).to_list(500)


@api_router.post("/products", response_model=Product)
async def create_product(product: Product):
    doc = product.model_dump()
    await db.products.insert_one(doc)
    return product


@api_router.post("/products/seed", response_model=List[Product])
async def seed_products(products: List[Product]):
    if await db.products.count_documents({}) == 0 and products:
        await db.products.insert_many([p.model_dump() for p in products])
    return await db.products.find({}, {"_id": 0}).to_list(500)


@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product: Product):
    updated = await db.products.find_one_and_update(
        {"id": product_id}, {"$set": product.model_dump(exclude={"id"})},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER
    )
    if not updated:
        await db.products.insert_one(product.model_dump())
        return product
    return updated


@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    result = await db.products.delete_one({"id": product_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True, "id": product_id}


@api_router.post("/orders", response_model=dict)
async def create_order(order: OrderCreate):
    order_id = f"SAT{datetime.now(timezone.utc).strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    doc = {"id": order_id, **order.model_dump(), "status": "confirmed", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.orders.insert_one(doc)
    return {"id": order_id, "status": "confirmed", "total": order.total, "created_at": doc["created_at"]}


@api_router.get("/orders", response_model=List[dict])
async def list_orders():
    return await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)


@api_router.get("/reviews/{product_id}", response_model=List[Review])
async def list_reviews(product_id: str):
    return [
        Review(id=f"review-{product_id}-1", product_id=product_id, name="Meera S.", rating=5, title="Beautifully made", body="The finish and packaging are both lovely. It has become part of our evening puja."),
        Review(id=f"review-{product_id}-2", product_id=product_id, name="Rohan K.", rating=5, title="Just as pictured", body="Arrived quickly and feels genuinely premium. Would happily gift this."),
        Review(id=f"review-{product_id}-3", product_id=product_id, name="Ananya P.", rating=4, title="A thoughtful purchase", body="A wonderful addition to our home altar and the quality is reassuring."),
    ]


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()