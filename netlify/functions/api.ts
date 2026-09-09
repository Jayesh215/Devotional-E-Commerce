import type { Config, Context } from "@netlify/functions";
import { ShopifyClient, ShopifyError } from "./_shared/shopify";

function json(data: unknown, status = 200) {
  return Response.json(data, {
    status,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}

function errorResponse(error: unknown) {
  if (error instanceof ShopifyError) {
    const body =
      error.details && typeof error.details === "object"
        ? { message: error.message, details: error.details }
        : { detail: error.message };
    return json(body, error.statusCode);
  }
  const message = error instanceof Error ? error.message : "Unexpected error";
  return json({ detail: message }, 500);
}

function shopify() {
  const domain = typeof Netlify !== "undefined" ? Netlify.env.get("SHOPIFY_STORE_DOMAIN") : process.env.SHOPIFY_STORE_DOMAIN;
  if (!domain) {
    throw new ShopifyError("Shopify is not configured", 500);
  }
  return new ShopifyClient();
}

function intParam(url: URL, name: string, fallback: number, min: number, max: number) {
  const raw = Number(url.searchParams.get(name) || fallback);
  if (Number.isNaN(raw)) return fallback;
  return Math.min(max, Math.max(min, raw));
}

function apiPath(pathname: string) {
  const cleaned = pathname.replace(/\/$/, "") || "/";
  if (cleaned.startsWith("/.netlify/functions/api")) {
    const rest = cleaned.replace("/.netlify/functions/api", "") || "/";
    return rest.startsWith("/") ? rest : `/${rest}`;
  }
  if (cleaned.startsWith("/api")) {
    const rest = cleaned.slice(4) || "/";
    return rest.startsWith("/") ? rest : `/${rest}`;
  }
  return cleaned;
}

export default async (req: Request, context: Context) => {
  if (req.method === "OPTIONS") {
    return json({ ok: true });
  }

  const url = new URL(req.url);
  const path = apiPath(url.pathname);
  const parts = path.split("/").filter(Boolean);

  try {
    const client = shopify();

    if (req.method === "GET" && (path === "/" || path === "")) {
      return json({
        message: "Sattva & Samagri API",
        catalog: "shopify",
        store: Netlify.env.get("SHOPIFY_STORE_DOMAIN") || process.env.SHOPIFY_STORE_DOMAIN,
      });
    }

    if (req.method === "GET" && path === "/health") {
      return json({ ok: true, shopify: true });
    }

    if (req.method === "GET" && path === "/collections") {
      return json(await client.listCollections(intParam(url, "first", 20, 1, 50)));
    }

    if (req.method === "GET" && parts[0] === "collections" && parts[1]) {
      const collection = await client.getCollectionByHandle(parts[1], intParam(url, "first", 50, 1, 50));
      if (!collection) return json({ detail: "Collection not found" }, 404);
      return json(collection);
    }

    if (req.method === "POST" && path === "/seed") {
      return json(await client.seedDummyCatalog());
    }

    if (req.method === "GET" && path === "/products") {
      return json(await client.listProducts(intParam(url, "first", 250, 1, 250)));
    }

    if (req.method === "GET" && parts[0] === "products" && parts[1]) {
      const product = await client.getProductByHandle(parts[1]);
      if (!product) return json({ detail: "Product not found" }, 404);
      return json(product);
    }

    if (req.method === "GET" && path === "/search") {
      const q = (url.searchParams.get("q") || "").trim();
      if (!q) return json({ detail: "q is required" }, 400);
      return json(await client.searchProducts(q, intParam(url, "first", 50, 1, 50)));
    }

    if (req.method === "POST" && path === "/products") {
      return json(await client.adminCreateProduct(await req.json()));
    }

    if (req.method === "PUT" && parts[0] === "products" && parts[1]) {
      return json(await client.adminUpdateProduct(parts[1], await req.json()));
    }

    if (req.method === "DELETE" && parts[0] === "products" && parts[1]) {
      return json(await client.adminDeleteProduct(parts[1]));
    }

    if (req.method === "POST" && path === "/checkout") {
      const payload = await req.json();
      if (!payload?.items?.length) return json({ detail: "Cart is empty" }, 400);
      return json(await client.createCheckout(payload.items));
    }

    if (req.method === "GET" && path === "/orders") {
      return json(await client.listOrders(intParam(url, "first", 50, 1, 50)));
    }

    if (req.method === "GET" && parts[0] === "reviews" && parts[1]) {
      return json([]);
    }

    return json({ detail: "Not found" }, 404);
  } catch (error) {
    return errorResponse(error);
  }
};

export const config: Config = {
  path: ["/api", "/api/*"],
};
