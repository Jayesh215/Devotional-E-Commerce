from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).parent
GRAPHQL_DIR = ROOT / "graphql"


class ShopifyError(Exception):
    def __init__(self, message: str, *, status_code: int = 502, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class ShopifyClient:
    def __init__(self) -> None:
        self.store_domain = os.environ["SHOPIFY_STORE_DOMAIN"].strip().removeprefix("https://").rstrip("/")
        self.api_version = os.environ.get("SHOPIFY_API_VERSION", "2026-07")
        self.storefront_token = os.environ.get("SHOPIFY_STOREFRONT_ACCESS_TOKEN", "")
        self.admin_token = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "")
        self.client_id = os.environ.get("SHOPIFY_CLIENT_ID", "")
        self.client_secret = os.environ.get("SHOPIFY_CLIENT_SECRET", "")
        self._oauth_admin_token: str | None = None
        self._storefront_queries = self._load("storefront.graphql")
        self._admin_queries = self._load("admin.graphql")
        self._admin_extra = self._load("admin_extra.graphql")

    @staticmethod
    def _load(name: str) -> dict[str, str]:
        text = (GRAPHQL_DIR / name).read_text(encoding="utf-8")
        queries: dict[str, str] = {}
        current_name: str | None = None
        current_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("query ") or stripped.startswith("mutation "):
                if current_name and current_lines:
                    queries[current_name] = "\n".join(current_lines).strip()
                token = stripped.split()[1]
                current_name = token.split("(")[0]
                current_lines = [line]
            elif current_name is not None:
                current_lines.append(line)
        if current_name and current_lines:
            queries[current_name] = "\n".join(current_lines).strip()
        return queries

    async def _request(self, *, url: str, token: str, query: str, variables: dict | None = None) -> dict:
        headers = {"Content-Type": "application/json", "X-Shopify-Storefront-Access-Token": token}
        if "admin" in url:
            headers = {"Content-Type": "application/json", "X-Shopify-Access-Token": token}
        payload = {"query": query, "variables": variables or {}}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ShopifyError(
                f"Shopify HTTP {response.status_code}",
                status_code=response.status_code,
                details=response.text,
            )
        body = response.json()
        if body.get("errors"):
            raise ShopifyError("Shopify GraphQL error", details=body["errors"])
        return body["data"]

    async def storefront(self, operation: str, variables: dict | None = None) -> dict:
        query = self._storefront_queries.get(operation)
        if not query:
            raise ShopifyError(f"Unknown Storefront operation: {operation}", status_code=500)
        url = f"https://{self.store_domain}/api/{self.api_version}/graphql.json"
        return await self._request(url=url, token=self.storefront_token, query=query, variables=variables)

    def _uses_oauth_admin(self) -> bool:
        token = (self.admin_token or "").strip()
        return (not token or token.startswith("PASTE_")) and bool(self.client_id and self.client_secret)

    async def _get_admin_token(self) -> str:
        if not self._uses_oauth_admin():
            return self.admin_token
        if self._oauth_admin_token:
            return self._oauth_admin_token
        url = f"https://{self.store_domain}/admin/oauth/access_token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if response.status_code >= 400:
            raise ShopifyError("Could not fetch Shopify admin OAuth token", status_code=response.status_code, details=response.text)
        body = response.json()
        token = body.get("access_token")
        if not token:
            raise ShopifyError("Shopify OAuth response missing access_token", details=body)
        self._oauth_admin_token = token
        return token

    async def admin(self, operation: str, variables: dict | None = None) -> dict:
        query = self._admin_queries.get(operation) or self._admin_extra.get(operation)
        if not query:
            raise ShopifyError(f"Unknown Admin operation: {operation}", status_code=500)
        url = f"https://{self.store_domain}/admin/api/{self.api_version}/graphql.json"
        token = await self._get_admin_token()
        return await self._request(url=url, token=token, query=query, variables=variables)

    async def list_products(self, *, first: int = 250) -> list[dict]:
        data = await self.storefront("CatalogProducts", {"first": first})
        return [self._map_storefront_product(node) for node in data["products"]["nodes"]]

    async def get_product_by_handle(self, handle: str) -> dict | None:
        data = await self.storefront("ProductByHandle", {"handle": handle})
        node = data.get("product")
        return self._map_storefront_product(node) if node else None

    async def search_products(self, *, query: str, first: int = 50) -> list[dict]:
        data = await self.storefront("SearchProducts", {"query": query, "first": first})
        products = []
        for node in data["search"]["nodes"]:
            if node.get("handle"):
                products.append(self._map_storefront_product(node))
        return products

    async def create_checkout(self, lines: list[dict]) -> dict:
        cart_lines = [
            {"merchandiseId": line["variantId"], "quantity": line["qty"]}
            for line in lines
        ]
        data = await self.storefront("CreateCheckoutCart", {"input": {"lines": cart_lines}})
        payload = data["cartCreate"]
        if payload.get("userErrors"):
            raise ShopifyError("Could not create Shopify cart", details=payload["userErrors"])
        cart = payload["cart"]
        return {"cartId": cart["id"], "checkoutUrl": cart["checkoutUrl"]}

    async def admin_list_products(self, *, first: int = 250) -> list[dict]:
        data = await self.admin("AdminCatalog", {"first": first})
        return [self._map_admin_product(node) for node in data["products"]["nodes"]]

    async def admin_create_product(self, product: dict) -> dict:
        tags = [t for t in [product.get("badge", "").strip()] if t]
        if product.get("bestseller"):
            tags.append("bestseller")
        media = []
        if product.get("image"):
            media.append({"originalSource": product["image"], "mediaContentType": "IMAGE", "alt": product["name"]})
        if product.get("secondImage"):
            media.append(
                {"originalSource": product["secondImage"], "mediaContentType": "IMAGE", "alt": product["name"]}
            )
        metafields = []
        if product.get("material"):
            metafields.append(
                {"namespace": "sattva", "key": "material", "type": "single_line_text_field", "value": product["material"]}
            )
        if product.get("size"):
            metafields.append(
                {"namespace": "sattva", "key": "size", "type": "single_line_text_field", "value": product["size"]}
            )
        create_input = {
            "title": product["name"],
            "handle": product["slug"],
            "productType": product["category"],
            "descriptionHtml": product.get("description") or "",
            "status": "ACTIVE",
            "tags": tags,
            "metafields": metafields,
        }
        created = await self.admin(
            "CreateSattvaProduct",
            {"product": create_input, "media": media or None},
        )
        result = created["productCreate"]
        if result.get("userErrors"):
            raise ShopifyError("Could not create product", details=result["userErrors"])
        shopify_product = result["product"]
        location_id = await self._primary_location_id()
        variant_payload: dict[str, Any] = {
            "optionValues": [{"name": "Default Title", "optionName": "Title"}],
            "price": float(product["price"]),
            "compareAtPrice": float(product["compare"]) if product.get("compare") else None,
            "inventoryItem": {"sku": product.get("slug")},
        }
        if product.get("stock") is not None:
            variant_payload["inventoryQuantities"] = [
                {"availableQuantity": int(product["stock"]), "locationId": location_id}
            ]
        variant_data = await self.admin(
            "SetSattvaVariantPricing",
            {"productId": shopify_product["id"], "variants": [variant_payload]},
        )
        if variant_data["productVariantsBulkCreate"].get("userErrors"):
            raise ShopifyError(
                "Product created but variant pricing failed",
                details=variant_data["productVariantsBulkCreate"]["userErrors"],
            )
        await self._publish_product(shopify_product["id"])
        return await self.get_product_by_handle(shopify_product["handle"]) or self._map_admin_product(
            {**shopify_product, "variants": {"nodes": variant_data["productVariantsBulkCreate"]["productVariants"]}}
        )

    async def admin_update_product(self, product_id: str, product: dict) -> dict:
        gid = product_id if product_id.startswith("gid://") else await self._resolve_product_gid(product_id)
        tags = [t for t in [product.get("badge", "").strip()] if t]
        if product.get("bestseller"):
            tags.append("bestseller")
        update_input: dict[str, Any] = {
            "id": gid,
            "title": product["name"],
            "handle": product["slug"],
            "productType": product["category"],
            "descriptionHtml": product.get("description") or "",
            "tags": tags,
        }
        data = await self.admin("UpdateSattvaProduct", {"product": update_input})
        if data["productUpdate"].get("userErrors"):
            raise ShopifyError("Could not update product", details=data["productUpdate"]["userErrors"])
        handle = data["productUpdate"]["product"]["handle"]
        return await self.get_product_by_handle(handle) or {"id": gid, **product}

    async def admin_delete_product(self, product_id: str) -> dict:
        gid = product_id if product_id.startswith("gid://") else await self._resolve_product_gid(product_id)
        data = await self.admin("DeleteSattvaProduct", {"id": gid})
        if data["productDelete"].get("userErrors"):
            raise ShopifyError("Could not delete product", details=data["productDelete"]["userErrors"])
        return {"ok": True, "id": data["productDelete"].get("deletedProductId") or gid}

    async def list_collections(self, *, first: int = 20) -> list[dict]:
        data = await self.storefront("CatalogCollections", {"first": first})
        return [self._map_collection(node) for node in data["collections"]["nodes"]]

    async def get_collection_by_handle(self, handle: str, *, first: int = 50) -> dict | None:
        data = await self.storefront("CollectionByHandle", {"handle": handle, "first": first})
        node = data.get("collection")
        if not node:
            return None
        return {
            **self._map_collection(node),
            "shopifyCollectionId": node["id"],
            "products": [self._map_storefront_product(p) for p in node["products"]["nodes"]],
        }

    async def seed_dummy_catalog(self) -> dict:
        from seed_catalog import DUMMY_COLLECTIONS, build_dummy_products

        product_ids_by_collection: dict[str, list[str]] = {}
        created_products: list[dict] = []

        for product in build_dummy_products():
            collection_handle = product["collectionHandle"]
            payload = {k: v for k, v in product.items() if k != "collectionHandle"}
            try:
                saved = await self.admin_create_product(payload)
            except ShopifyError:
                saved = await self.get_product_by_handle(product["slug"])
                if not saved:
                    raise
            created_products.append(saved)
            gid = saved.get("shopifyProductId")
            if gid:
                product_ids_by_collection.setdefault(collection_handle, []).append(gid)

        created_collections: list[dict] = []
        for coll in DUMMY_COLLECTIONS:
            existing = await self.get_collection_by_handle(coll["handle"], first=1)
            if existing:
                collection_gid = existing["shopifyCollectionId"]
                collection_handle = existing["handle"]
            else:
                created = await self.admin(
                    "CreateSattvaCollection",
                    {
                        "input": {
                            "title": coll["title"],
                            "handle": coll["handle"],
                            "descriptionHtml": coll["description"],
                            "image": {"src": coll["image"]},
                        }
                    },
                )
                result = created["collectionCreate"]
                if result.get("userErrors"):
                    raise ShopifyError("Could not create collection", details=result["userErrors"])
                collection_gid = result["collection"]["id"]
                collection_handle = result["collection"]["handle"]
                await self._publish_resource(collection_gid)

            product_ids = product_ids_by_collection.get(coll["handle"], [])
            if product_ids:
                added = await self.admin(
                    "AddProductsToCollection",
                    {"id": collection_gid, "productIds": product_ids},
                )
                if added["collectionAddProducts"].get("userErrors"):
                    raise ShopifyError(
                        "Could not add products to collection",
                        details=added["collectionAddProducts"]["userErrors"],
                    )
            created_collections.append({"handle": collection_handle, "title": coll["title"], "productCount": len(product_ids)})

        return {
            "ok": True,
            "products": len(created_products),
            "collections": created_collections,
        }

    async def list_orders(self, *, first: int = 50) -> list[dict]:
        data = await self.admin("RecentOrders", {"first": first})
        orders = []
        for node in data["orders"]["nodes"]:
            total = node["totalPriceSet"]["shopMoney"]["amount"]
            orders.append(
                {
                    "id": node["name"],
                    "shopifyId": node["id"],
                    "status": (node.get("displayFulfillmentStatus") or "UNFULFILLED").lower(),
                    "payment_method": (node.get("displayFinancialStatus") or "pending").lower(),
                    "total": int(float(total)),
                    "created_at": node["createdAt"],
                    "items": [
                        {"name": item["title"], "qty": item["quantity"]}
                        for item in node["lineItems"]["nodes"]
                    ],
                }
            )
        return orders

    async def _resolve_product_gid(self, product_id: str) -> str:
        if product_id.startswith("gid://"):
            return product_id
        product = await self.get_product_by_handle(product_id)
        if not product:
            raise ShopifyError("Product not found", status_code=404)
        return product["shopifyProductId"]

    async def _primary_location_id(self) -> str:
        data = await self.admin("ShopLocations")
        nodes = data["locations"]["nodes"]
        if not nodes:
            raise ShopifyError("No Shopify locations configured", status_code=500)
        return nodes[0]["id"]

    async def _publish_resource(self, resource_gid: str) -> None:
        pubs = await self.admin("ShopPublications")
        publication_inputs = [{"publicationId": node["id"]} for node in pubs["publications"]["nodes"]]
        if not publication_inputs:
            return
        if resource_gid.startswith("gid://shopify/Product"):
            await self.admin("PublishSattvaProduct", {"id": resource_gid, "input": publication_inputs})
        else:
            await self.admin("PublishSattvaCollection", {"id": resource_gid, "input": publication_inputs})

    async def _publish_product(self, product_gid: str) -> None:
        await self._publish_resource(product_gid)

    @staticmethod
    def _map_collection(node: dict | None) -> dict:
        if not node:
            return {}
        return {
            "id": node["handle"],
            "handle": node["handle"],
            "name": node["title"],
            "title": node["title"],
            "description": node.get("description") or "",
            "image": (node.get("image") or {}).get("url") or "",
        }

    @staticmethod
    def _money(value: str | None) -> int:
        if not value:
            return 0
        return int(round(float(value)))

    def _map_storefront_product(self, node: dict | None) -> dict:
        if not node:
            return {}
        variant = (node.get("variants") or {}).get("nodes") or [{}]
        variant = variant[0] if variant else {}
        images = (node.get("images") or {}).get("nodes") or []
        image = (node.get("featuredImage") or {}).get("url") or (images[0]["url"] if images else "")
        second = images[1]["url"] if len(images) > 1 else image
        tags = [t.lower() for t in (node.get("tags") or [])]
        badge = next((t for t in node.get("tags") or [] if t.lower() not in {"bestseller"}), "")
        price = self._money((variant.get("price") or {}).get("amount"))
        compare = self._money((variant.get("compareAtPrice") or {}).get("amount"))
        material = ((node.get("material") or {}).get("value")) or ""
        size = ((node.get("size") or {}).get("value")) or ""
        return {
            "id": node["handle"],
            "shopifyProductId": node["id"],
            "variantId": variant.get("id", ""),
            "name": node["title"],
            "slug": node["handle"],
            "category": node.get("productType") or "General",
            "price": price,
            "compare": compare or price,
            "description": node.get("description") or "",
            "material": material,
            "size": size,
            "image": image,
            "secondImage": second,
            "badge": badge,
            "stock": variant.get("quantityAvailable") or 0,
            "bestseller": "bestseller" in tags,
            "available": variant.get("availableForSale", False),
        }

    def _map_admin_product(self, node: dict) -> dict:
        variant = (node.get("variants") or {}).get("nodes") or [{}]
        variant = variant[0] if variant else {}
        media_nodes = (node.get("media") or {}).get("nodes") or []
        image = ""
        second = ""
        if node.get("featuredMedia", {}).get("image"):
            image = node["featuredMedia"]["image"]["url"]
        for idx, media in enumerate(media_nodes):
            url = (media.get("image") or {}).get("url")
            if not url:
                continue
            if idx == 0 and not image:
                image = url
            elif idx == 1:
                second = url
        if not second:
            second = image
        tags = [t.lower() for t in (node.get("tags") or [])]
        badge = next((t for t in node.get("tags") or [] if t.lower() not in {"bestseller"}), "")
        return {
            "id": node["handle"],
            "shopifyProductId": node["id"],
            "variantId": variant.get("id", ""),
            "name": node["title"],
            "slug": node["handle"],
            "category": node.get("productType") or "General",
            "price": self._money(variant.get("price")),
            "compare": self._money(variant.get("compareAtPrice")) or self._money(variant.get("price")),
            "description": node.get("descriptionHtml") or "",
            "material": ((node.get("material") or {}).get("value")) or "",
            "size": ((node.get("size") or {}).get("value")) or "",
            "image": image,
            "secondImage": second,
            "badge": badge,
            "stock": variant.get("inventoryQuantity") or 0,
            "bestseller": "bestseller" in tags,
            "status": node.get("status"),
        }
