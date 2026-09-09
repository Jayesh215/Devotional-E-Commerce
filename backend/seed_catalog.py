"""Dummy Sattva catalog — collections and products for Shopify seeding."""

IMG = lambda photo_id, w=900: f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w={w}&q=84"

DUMMY_COLLECTIONS = [
    {
        "title": "Puja Samagri",
        "handle": "puja-samagri",
        "description": "Pure ingredients and essentials for daily rituals.",
        "image": IMG("photo-1603006905003-be475563bc59"),
    },
    {
        "title": "Diyas & Lamps",
        "handle": "diyas",
        "description": "Brass diyas and lamps for illuminating sacred moments.",
        "image": IMG("photo-1587223757288-85e8402baf60"),
    },
    {
        "title": "Puja Kits",
        "handle": "puja-kits",
        "description": "Complete, thoughtfully assembled kits for home puja.",
        "image": IMG("photo-1518709268805-4e9042af9f23"),
    },
    {
        "title": "Incense & Dhoop",
        "handle": "incense",
        "description": "Temple-grade incense, dhoop and agarbatti.",
        "image": IMG("photo-1552014359-e81c947ca502"),
    },
    {
        "title": "Idols & Murtis",
        "handle": "idols",
        "description": "Hand-crafted murtis for your home altar.",
        "image": IMG("photo-1577083552431-6e5fd01aa342"),
    },
    {
        "title": "Rudraksha & Mala",
        "handle": "rudraksha",
        "description": "Malas and rudraksha for meditation and devotion.",
        "image": IMG("photo-1612704057720-e8f66bade6ca"),
    },
    {
        "title": "Festival Essentials",
        "handle": "festival",
        "description": "Curated edits for Diwali, Navratri and sacred celebrations.",
        "image": IMG("photo-1603006905003-be475563bc59"),
    },
]

IMAGE_POOL = [
    "photo-1587223757288-85e8402baf60",
    "photo-1552014359-e81c947ca502",
    "photo-1612704057720-e8f66bade6ca",
    "photo-1518709268805-4e9042af9f23",
    "photo-1603006905003-be475563bc59",
]

COLLECTION_HANDLE_BY_CATEGORY = {
    "Puja Samagri": "puja-samagri",
    "Diyas & Lamps": "diyas",
    "Puja Kits": "puja-kits",
    "Incense & Dhoop": "incense",
    "Idols & Murtis": "idols",
    "Rudraksha & Mala": "rudraksha",
    "Festival Essentials": "festival",
    "Brass Accessories": "puja-samagri",
    "Havan & Wicks": "puja-samagri",
}

PRODUCT_SEEDS = [
    ["Brass Surya Diya", "Diyas & Lamps", 849, 1099, "A hand-finished brass lamp for an illuminating daily ritual.", "Brass", "250 g", "Bestseller"],
    ["Sandalwood Dhoop Cones", "Incense & Dhoop", 399, 499, "Slow-burning, temple-grade sandalwood fragrance.", "Natural herbs", "100 g", "New"],
    ["Shubh Labh Puja Kit", "Puja Kits", 1299, 1599, "A complete, thoughtfully assembled kit for your home puja.", "Natural ingredients", "1 complete set", "Bestseller"],
    ["Pure Camphor Tablets", "Puja Samagri", 249, 299, "Bright, clean-burning camphor for a pure aarti.", "Edible-grade camphor", "50 g", "Popular"],
    ["Kumkum & Chandan Set", "Puja Samagri", 299, 399, "Hand-ground powders in a beautiful reusable brass tin.", "Sandalwood, turmeric", "30 g each", "New"],
    ["Lotus Puja Thali", "Brass Accessories", 1899, 2299, "A sculptural brass thali made for meaningful offerings.", "Solid brass", "32 cm", "Featured"],
    ["Sacred Rudraksha Mala", "Rudraksha & Mala", 1199, 1499, "108 naturally faceted beads, strung for meditation.", "5 mukhi Rudraksha", "42 cm", "Bestseller"],
    ["Mogra Agarbatti", "Incense & Dhoop", 349, 449, "Soft mogra notes that bring calm to your prayer space.", "Herbal blend", "100 sticks", "Popular"],
    ["Ganesha Brass Murti", "Idols & Murtis", 2499, 2999, "A serene hand-cast Ganesha for a welcoming altar.", "Brass", "18 cm", "Featured"],
    ["Havan Samagri Blend", "Havan & Wicks", 449, 549, "A fragrant, balanced blend for sacred fire ceremonies.", "31 herbs", "250 g", "New"],
    ["Cotton Puja Wicks", "Havan & Wicks", 149, 199, "Pure cotton wicks, evenly spun for a steady flame.", "100% cotton", "100 wicks", "Popular"],
    ["Diwali Light Gift Box", "Festival Essentials", 1599, 1899, "A festive edit of diyas, incense and auspicious essentials.", "Brass & botanicals", "1 gift box", "Bestseller"],
]


def slugify(name: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-").replace("--", "-")


def build_dummy_products() -> list[dict]:
    products = []
    for i, seed in enumerate(PRODUCT_SEEDS):
        name, category, price, compare, description, material, size, badge = seed
        slug = f"{slugify(name)}-{i + 1}"
        products.append(
            {
                "name": name,
                "slug": slug,
                "category": category,
                "price": price,
                "compare": compare,
                "description": description,
                "material": material,
                "size": size,
                "badge": badge,
                "bestseller": badge.lower() == "bestseller",
                "stock": 25,
                "image": IMG(IMAGE_POOL[i % len(IMAGE_POOL)]),
                "secondImage": IMG(IMAGE_POOL[(i + 1) % len(IMAGE_POOL)]),
                "collectionHandle": COLLECTION_HANDLE_BY_CATEGORY.get(category, "puja-samagri"),
            }
        )
    return products
