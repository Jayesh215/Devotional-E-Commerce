from pathlib import Path
from typing import List, Optional
import logging
import os

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware

from shopify_client import ShopifyClient, ShopifyError

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

app = FastAPI(title="Sattva & Samagri API", description="Shopify-backed storefront API")
api_router = APIRouter(prefix="/api")
shopify = ShopifyClient()


class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    shopifyProductId: str = ""
    variantId: str = ""
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
    stock: int = Field(default=0, ge=0)
    bestseller: bool = False
    available: bool = True


class ProductWrite(BaseModel):
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


class CheckoutLine(BaseModel):
    variantId: str
    qty: int = Field(ge=1)


class CheckoutCreate(BaseModel):
    items: List[CheckoutLine]


@api_router.get("/")
async def root():
    return {
        "message": "Sattva & Samagri API",
        "catalog": "shopify",
        "store": os.environ.get("SHOPIFY_STORE_DOMAIN"),
    }


@api_router.get("/health")
async def health():
    return {"ok": True, "shopify": True}


@api_router.get("/collections", response_model=List[dict])
async def list_collections(first: int = Query(default=20, ge=1, le=50)):
    try:
        return await shopify.list_collections(first=first)
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@api_router.get("/collections/{handle}")
async def get_collection(handle: str, first: int = Query(default=50, ge=1, le=50)):
    try:
        collection = await shopify.get_collection_by_handle(handle, first=first)
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@api_router.post("/seed")
async def seed_catalog():
    try:
        return await shopify.seed_dummy_catalog()
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": str(exc), "details": exc.details}) from exc


@api_router.get("/products", response_model=List[Product])
async def list_products(first: int = Query(default=250, ge=1, le=250)):
    try:
        return await shopify.list_products(first=first)
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@api_router.get("/products/{handle}", response_model=Product)
async def get_product(handle: str):
    try:
        product = await shopify.get_product_by_handle(handle)
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@api_router.get("/search", response_model=List[Product])
async def search_products(q: str = Query(min_length=1), first: int = Query(default=50, ge=1, le=50)):
    try:
        return await shopify.search_products(query=q, first=first)
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@api_router.post("/products", response_model=Product)
async def create_product(product: ProductWrite):
    try:
        return await shopify.admin_create_product(product.model_dump())
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": str(exc), "details": exc.details}) from exc


@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product: ProductWrite):
    try:
        return await shopify.admin_update_product(product_id, product.model_dump())
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": str(exc), "details": exc.details}) from exc


@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    try:
        return await shopify.admin_delete_product(product_id)
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@api_router.post("/checkout")
async def create_checkout(payload: CheckoutCreate):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    try:
        return await shopify.create_checkout([item.model_dump() for item in payload.items])
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": str(exc), "details": exc.details}) from exc


@api_router.get("/orders", response_model=List[dict])
async def list_orders(first: int = Query(default=50, ge=1, le=50)):
    try:
        return await shopify.list_orders(first=first)
    except ShopifyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@api_router.get("/reviews/{product_id}", response_model=List[dict])
async def list_reviews(product_id: str):
    # Product reviews are managed in Shopify via a reviews app (Judge.me, Loox, etc.).
    return []


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
