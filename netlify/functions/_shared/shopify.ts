import { adminQueries, storefrontQueries } from "./graphql";
import { buildDummyProducts, DUMMY_COLLECTIONS } from "./seed";

export class ShopifyError extends Error {
  statusCode: number;
  details: unknown;

  constructor(message: string, statusCode = 502, details: unknown = null) {
    super(message);
    this.statusCode = statusCode;
    this.details = details;
  }
}

type ProductWrite = {
  name: string;
  slug: string;
  category: string;
  price: number;
  compare: number;
  description?: string;
  material?: string;
  size?: string;
  image?: string;
  secondImage?: string;
  badge?: string;
  stock?: number;
  bestseller?: boolean;
};

function env(name: string, fallback = "") {
  const fromNetlify = typeof Netlify !== "undefined" ? Netlify.env.get(name) : undefined;
  return (fromNetlify || process.env[name] || fallback).trim();
}

function money(value?: string | null) {
  if (!value) return 0;
  return Math.round(Number(value));
}

export class ShopifyClient {
  storeDomain = env("SHOPIFY_STORE_DOMAIN").replace(/^https?:\/\//, "").replace(/\/$/, "");
  apiVersion = env("SHOPIFY_API_VERSION", "2026-07");
  storefrontToken = env("SHOPIFY_STOREFRONT_ACCESS_TOKEN");
  adminToken = env("SHOPIFY_ADMIN_ACCESS_TOKEN");
  clientId = env("SHOPIFY_CLIENT_ID");
  clientSecret = env("SHOPIFY_CLIENT_SECRET");
  oauthAdminToken: string | null = null;

  private async request(url: string, token: string, query: string, variables: Record<string, unknown> = {}) {
    const headers: Record<string, string> = url.includes("/admin/")
      ? { "Content-Type": "application/json", "X-Shopify-Access-Token": token }
      : { "Content-Type": "application/json", "X-Shopify-Storefront-Access-Token": token };
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({ query, variables }),
    });
    if (response.status >= 400) {
      throw new ShopifyError(`Shopify HTTP ${response.status}`, response.status, await response.text());
    }
    const body = await response.json();
    if (body.errors) {
      throw new ShopifyError("Shopify GraphQL error", 502, body.errors);
    }
    return body.data;
  }

  private storefront(operation: string, variables?: Record<string, unknown>) {
    const query = storefrontQueries[operation];
    if (!query) throw new ShopifyError(`Unknown Storefront operation: ${operation}`, 500);
    const url = `https://${this.storeDomain}/api/${this.apiVersion}/graphql.json`;
    return this.request(url, this.storefrontToken, query, variables);
  }

  private usesOauthAdmin() {
    const token = this.adminToken;
    return (!token || token.startsWith("PASTE_")) && Boolean(this.clientId && this.clientSecret);
  }

  private async getAdminToken() {
    if (!this.usesOauthAdmin()) return this.adminToken;
    if (this.oauthAdminToken) return this.oauthAdminToken;
    const response = await fetch(`https://${this.storeDomain}/admin/oauth/access_token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "client_credentials",
        client_id: this.clientId,
        client_secret: this.clientSecret,
      }),
    });
    if (response.status >= 400) {
      throw new ShopifyError("Could not fetch Shopify admin OAuth token", response.status, await response.text());
    }
    const body = await response.json();
    if (!body.access_token) {
      throw new ShopifyError("Shopify OAuth response missing access_token", 502, body);
    }
    this.oauthAdminToken = body.access_token;
    return body.access_token as string;
  }

  private async admin(operation: string, variables?: Record<string, unknown>) {
    const query = adminQueries[operation];
    if (!query) throw new ShopifyError(`Unknown Admin operation: ${operation}`, 500);
    const url = `https://${this.storeDomain}/admin/api/${this.apiVersion}/graphql.json`;
    return this.request(url, await this.getAdminToken(), query, variables);
  }

  private mapCollection(node: any) {
    if (!node) return {};
    return {
      id: node.handle,
      handle: node.handle,
      name: node.title,
      title: node.title,
      description: node.description || "",
      image: node.image?.url || "",
    };
  }

  private mapStorefrontProduct(node: any) {
    if (!node) return {};
    const variants = node.variants?.nodes || [{}];
    const variant = variants[0] || {};
    const images = node.images?.nodes || [];
    const image = node.featuredImage?.url || images[0]?.url || "";
    const second = images[1]?.url || image;
    const tags = (node.tags || []).map((tag: string) => tag.toLowerCase());
    const badge = (node.tags || []).find((tag: string) => tag.toLowerCase() !== "bestseller") || "";
    const price = money(variant.price?.amount);
    const compare = money(variant.compareAtPrice?.amount);
    return {
      id: node.handle,
      shopifyProductId: node.id,
      variantId: variant.id || "",
      name: node.title,
      slug: node.handle,
      category: node.productType || "General",
      price,
      compare: compare || price,
      description: node.description || "",
      material: node.material?.value || "",
      size: node.size?.value || "",
      image,
      secondImage: second,
      badge,
      stock: variant.quantityAvailable || 0,
      bestseller: tags.includes("bestseller"),
      available: Boolean(variant.availableForSale),
    };
  }

  private mapAdminProduct(node: any) {
    const variants = node.variants?.nodes || [{}];
    const variant = variants[0] || {};
    const mediaNodes = node.media?.nodes || [];
    let image = node.featuredMedia?.image?.url || "";
    let second = "";
    mediaNodes.forEach((media: any, idx: number) => {
      const url = media.image?.url;
      if (!url) return;
      if (idx === 0 && !image) image = url;
      else if (idx === 1) second = url;
    });
    if (!second) second = image;
    const tags = (node.tags || []).map((tag: string) => tag.toLowerCase());
    const badge = (node.tags || []).find((tag: string) => tag.toLowerCase() !== "bestseller") || "";
    return {
      id: node.handle,
      shopifyProductId: node.id,
      variantId: variant.id || "",
      name: node.title,
      slug: node.handle,
      category: node.productType || "General",
      price: money(variant.price),
      compare: money(variant.compareAtPrice) || money(variant.price),
      description: node.descriptionHtml || "",
      material: node.material?.value || "",
      size: node.size?.value || "",
      image,
      secondImage: second,
      badge,
      stock: variant.inventoryQuantity || 0,
      bestseller: tags.includes("bestseller"),
      status: node.status,
    };
  }

  async listProducts(first = 250) {
    const data = await this.storefront("CatalogProducts", { first });
    return data.products.nodes.map((node: any) => this.mapStorefrontProduct(node));
  }

  async getProductByHandle(handle: string) {
    const data = await this.storefront("ProductByHandle", { handle });
    return data.product ? this.mapStorefrontProduct(data.product) : null;
  }

  async searchProducts(query: string, first = 50) {
    const data = await this.storefront("SearchProducts", { query, first });
    return data.search.nodes
      .filter((node: any) => node?.handle)
      .map((node: any) => this.mapStorefrontProduct(node));
  }

  async createCheckout(lines: { variantId: string; qty: number }[]) {
    const data = await this.storefront("CreateCheckoutCart", {
      input: {
        lines: lines.map((line) => ({ merchandiseId: line.variantId, quantity: line.qty })),
      },
    });
    if (data.cartCreate.userErrors?.length) {
      throw new ShopifyError("Could not create Shopify cart", 502, data.cartCreate.userErrors);
    }
    return { cartId: data.cartCreate.cart.id, checkoutUrl: data.cartCreate.cart.checkoutUrl };
  }

  async listCollections(first = 20) {
    const data = await this.storefront("CatalogCollections", { first });
    return data.collections.nodes.map((node: any) => this.mapCollection(node));
  }

  async getCollectionByHandle(handle: string, first = 50) {
    const data = await this.storefront("CollectionByHandle", { handle, first });
    if (!data.collection) return null;
    return {
      ...this.mapCollection(data.collection),
      shopifyCollectionId: data.collection.id,
      products: data.collection.products.nodes.map((node: any) => this.mapStorefrontProduct(node)),
    };
  }

  private async resolveProductGid(productId: string) {
    if (productId.startsWith("gid://")) return productId;
    const product = await this.getProductByHandle(productId);
    if (!product) throw new ShopifyError("Product not found", 404);
    return product.shopifyProductId;
  }

  private async primaryLocationId() {
    const data = await this.admin("ShopLocations");
    const nodes = data.locations.nodes;
    if (!nodes.length) throw new ShopifyError("No Shopify locations configured", 500);
    return nodes[0].id;
  }

  private async publishResource(resourceGid: string) {
    const pubs = await this.admin("ShopPublications");
    const publicationInputs = pubs.publications.nodes.map((node: any) => ({ publicationId: node.id }));
    if (!publicationInputs.length) return;
    if (resourceGid.startsWith("gid://shopify/Product")) {
      await this.admin("PublishSattvaProduct", { id: resourceGid, input: publicationInputs });
    } else {
      await this.admin("PublishSattvaCollection", { id: resourceGid, input: publicationInputs });
    }
  }

  async adminCreateProduct(product: ProductWrite) {
    const tags = [product.badge?.trim()].filter(Boolean) as string[];
    if (product.bestseller) tags.push("bestseller");
    const media = [];
    if (product.image) media.push({ originalSource: product.image, mediaContentType: "IMAGE", alt: product.name });
    if (product.secondImage) {
      media.push({ originalSource: product.secondImage, mediaContentType: "IMAGE", alt: product.name });
    }
    const metafields = [];
    if (product.material) {
      metafields.push({ namespace: "sattva", key: "material", type: "single_line_text_field", value: product.material });
    }
    if (product.size) {
      metafields.push({ namespace: "sattva", key: "size", type: "single_line_text_field", value: product.size });
    }
    const created = await this.admin("CreateSattvaProduct", {
      product: {
        title: product.name,
        handle: product.slug,
        productType: product.category,
        descriptionHtml: product.description || "",
        status: "ACTIVE",
        tags,
        metafields,
      },
      media: media.length ? media : null,
    });
    if (created.productCreate.userErrors?.length) {
      throw new ShopifyError("Could not create product", 502, created.productCreate.userErrors);
    }
    const shopifyProduct = created.productCreate.product;
    const locationId = await this.primaryLocationId();
    const variantPayload: Record<string, unknown> = {
      optionValues: [{ name: "Default Title", optionName: "Title" }],
      price: Number(product.price),
      compareAtPrice: product.compare ? Number(product.compare) : null,
      inventoryItem: { sku: product.slug },
    };
    if (product.stock != null) {
      variantPayload.inventoryQuantities = [{ availableQuantity: Number(product.stock), locationId }];
    }
    const variantData = await this.admin("SetSattvaVariantPricing", {
      productId: shopifyProduct.id,
      variants: [variantPayload],
    });
    if (variantData.productVariantsBulkCreate.userErrors?.length) {
      throw new ShopifyError("Product created but variant pricing failed", 502, variantData.productVariantsBulkCreate.userErrors);
    }
    await this.publishResource(shopifyProduct.id);
    return (
      (await this.getProductByHandle(shopifyProduct.handle)) ||
      this.mapAdminProduct({
        ...shopifyProduct,
        variants: { nodes: variantData.productVariantsBulkCreate.productVariants },
      })
    );
  }

  async adminUpdateProduct(productId: string, product: ProductWrite) {
    const gid = await this.resolveProductGid(productId);
    const tags = [product.badge?.trim()].filter(Boolean) as string[];
    if (product.bestseller) tags.push("bestseller");
    const data = await this.admin("UpdateSattvaProduct", {
      product: {
        id: gid,
        title: product.name,
        handle: product.slug,
        productType: product.category,
        descriptionHtml: product.description || "",
        tags,
      },
    });
    if (data.productUpdate.userErrors?.length) {
      throw new ShopifyError("Could not update product", 502, data.productUpdate.userErrors);
    }
    return (await this.getProductByHandle(data.productUpdate.product.handle)) || { id: gid, ...product };
  }

  async adminDeleteProduct(productId: string) {
    const gid = await this.resolveProductGid(productId);
    const data = await this.admin("DeleteSattvaProduct", { id: gid });
    if (data.productDelete.userErrors?.length) {
      throw new ShopifyError("Could not delete product", 502, data.productDelete.userErrors);
    }
    return { ok: true, id: data.productDelete.deletedProductId || gid };
  }

  async seedDummyCatalog() {
    const productIdsByCollection: Record<string, string[]> = {};
    const createdProducts: any[] = [];
    for (const product of buildDummyProducts()) {
      const { collectionHandle, ...payload } = product;
      let saved;
      try {
        saved = await this.adminCreateProduct(payload);
      } catch (error) {
        saved = await this.getProductByHandle(product.slug);
        if (!saved) throw error;
      }
      createdProducts.push(saved);
      if (saved.shopifyProductId) {
        productIdsByCollection[collectionHandle] ||= [];
        productIdsByCollection[collectionHandle].push(saved.shopifyProductId);
      }
    }

    const createdCollections = [];
    for (const coll of DUMMY_COLLECTIONS) {
      const existing = await this.getCollectionByHandle(coll.handle, 1);
      let collectionGid: string;
      let collectionHandle: string;
      if (existing) {
        collectionGid = existing.shopifyCollectionId;
        collectionHandle = existing.handle;
      } else {
        const created = await this.admin("CreateSattvaCollection", {
          input: {
            title: coll.title,
            handle: coll.handle,
            descriptionHtml: coll.description,
            image: { src: coll.image },
          },
        });
        if (created.collectionCreate.userErrors?.length) {
          throw new ShopifyError("Could not create collection", 502, created.collectionCreate.userErrors);
        }
        collectionGid = created.collectionCreate.collection.id;
        collectionHandle = created.collectionCreate.collection.handle;
        await this.publishResource(collectionGid);
      }
      const productIds = productIdsByCollection[coll.handle] || [];
      if (productIds.length) {
        const added = await this.admin("AddProductsToCollection", { id: collectionGid, productIds });
        if (added.collectionAddProducts.userErrors?.length) {
          throw new ShopifyError("Could not add products to collection", 502, added.collectionAddProducts.userErrors);
        }
      }
      createdCollections.push({ handle: collectionHandle, title: coll.title, productCount: productIds.length });
    }

    return { ok: true, products: createdProducts.length, collections: createdCollections };
  }

  async listOrders(first = 50) {
    const data = await this.admin("RecentOrders", { first });
    return data.orders.nodes.map((node: any) => ({
      id: node.name,
      shopifyId: node.id,
      status: (node.displayFulfillmentStatus || "UNFULFILLED").toLowerCase(),
      payment_method: (node.displayFinancialStatus || "pending").toLowerCase(),
      total: Math.trunc(Number(node.totalPriceSet.shopMoney.amount)),
      created_at: node.createdAt,
      items: node.lineItems.nodes.map((item: any) => ({ name: item.title, qty: item.quantity })),
    }));
  }
}
