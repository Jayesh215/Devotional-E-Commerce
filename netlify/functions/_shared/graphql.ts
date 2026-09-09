export const storefrontQueries: Record<string, string> = {
  CatalogProducts: `query CatalogProducts($first: Int!) {
  products(first: $first) {
    nodes {
      id
      handle
      title
      description
      productType
      tags
      featuredImage { url altText }
      images(first: 2) { nodes { url altText } }
      priceRange { minVariantPrice { amount } }
      compareAtPriceRange { minVariantPrice { amount } }
      variants(first: 1) {
        nodes {
          id
          sku
          availableForSale
          quantityAvailable
          price { amount }
          compareAtPrice { amount }
        }
      }
      material: metafield(namespace: "sattva", key: "material") { value }
      size: metafield(namespace: "sattva", key: "size") { value }
    }
  }
}`,
  ProductByHandle: `query ProductByHandle($handle: String!) {
  product(handle: $handle) {
    id
    handle
    title
    description
    productType
    tags
    featuredImage { url }
    images(first: 2) { nodes { url } }
    variants(first: 1) {
      nodes {
        id
        sku
        availableForSale
        quantityAvailable
        price { amount }
        compareAtPrice { amount }
      }
    }
    material: metafield(namespace: "sattva", key: "material") { value }
    size: metafield(namespace: "sattva", key: "size") { value }
  }
}`,
  SearchProducts: `query SearchProducts($query: String!, $first: Int!) {
  search(query: $query, first: $first, types: PRODUCT) {
    nodes {
      ... on Product {
        id
        handle
        title
        description
        productType
        tags
        featuredImage { url }
        images(first: 2) { nodes { url } }
        variants(first: 1) {
          nodes {
            id
            sku
            availableForSale
            quantityAvailable
            price { amount }
            compareAtPrice { amount }
          }
        }
      }
    }
  }
}`,
  CatalogCollections: `query CatalogCollections($first: Int!) {
  collections(first: $first) {
    nodes {
      id
      handle
      title
      description
      image { url altText }
    }
  }
}`,
  CollectionByHandle: `query CollectionByHandle($handle: String!, $first: Int!) {
  collection(handle: $handle) {
    id
    handle
    title
    description
    image { url altText }
    products(first: $first) {
      nodes {
        id
        handle
        title
        description
        productType
        tags
        featuredImage { url altText }
        images(first: 2) { nodes { url altText } }
        variants(first: 1) {
          nodes {
            id
            sku
            availableForSale
            quantityAvailable
            price { amount }
            compareAtPrice { amount }
          }
        }
        material: metafield(namespace: "sattva", key: "material") { value }
        size: metafield(namespace: "sattva", key: "size") { value }
      }
    }
  }
}`,
  CreateCheckoutCart: `mutation CreateCheckoutCart($input: CartInput!) {
  cartCreate(input: $input) {
    cart {
      id
      checkoutUrl
    }
    userErrors {
      field
      message
    }
  }
}`,
};

export const adminQueries: Record<string, string> = {
  AdminCatalog: `query AdminCatalog($first: Int!) {
  products(first: $first) {
    nodes {
      id
      handle
      title
      status
      productType
      tags
      descriptionHtml
      featuredMedia {
        ... on MediaImage {
          image { url }
        }
      }
      media(first: 2) {
        nodes {
          ... on MediaImage {
            image { url }
          }
        }
      }
      variants(first: 1) {
        nodes {
          id
          sku
          price
          compareAtPrice
          inventoryQuantity
        }
      }
      material: metafield(namespace: "sattva", key: "material") { value }
      size: metafield(namespace: "sattva", key: "size") { value }
    }
  }
}`,
  ShopPublications: `query ShopPublications {
  publications(first: 20) {
    nodes {
      id
      name
    }
  }
}`,
  ShopLocations: `query ShopLocations {
  locations(first: 5) {
    nodes {
      id
      name
    }
  }
}`,
  RecentOrders: `query RecentOrders($first: Int!) {
  orders(first: $first, sortKey: CREATED_AT, reverse: true) {
    nodes {
      id
      name
      createdAt
      displayFinancialStatus
      displayFulfillmentStatus
      totalPriceSet {
        shopMoney { amount }
      }
      lineItems(first: 5) {
        nodes {
          title
          quantity
        }
      }
    }
  }
}`,
  UpdateSattvaProduct: `mutation UpdateSattvaProduct($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product {
      id
      handle
      title
    }
    userErrors {
      field
      message
    }
  }
}`,
  DeleteSattvaProduct: `mutation DeleteSattvaProduct($id: ID!) {
  productDelete(input: { id: $id }) {
    deletedProductId
    userErrors {
      field
      message
    }
  }
}`,
  PublishSattvaProduct: `mutation PublishSattvaProduct($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors {
      field
      message
    }
  }
}`,
  CreateSattvaProduct: `mutation CreateSattvaProduct($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
  productCreate(product: $product, media: $media) {
    product { id handle title status productType }
    userErrors { field message }
  }
}`,
  SetSattvaVariantPricing: `mutation SetSattvaVariantPricing($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkCreate(productId: $productId, strategy: REMOVE_STANDALONE_VARIANT, variants: $variants) {
    product { id }
    productVariants { id price compareAtPrice inventoryItem { sku } }
    userErrors { field message }
  }
}`,
  CreateSattvaCollection: `mutation CreateSattvaCollection($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection { id handle title }
    userErrors { field message }
  }
}`,
  AddProductsToCollection: `mutation AddProductsToCollection($id: ID!, $productIds: [ID!]!) {
  collectionAddProducts(id: $id, productIds: $productIds) {
    collection { id handle }
    userErrors { field message }
  }
}`,
  PublishSattvaCollection: `mutation PublishSattvaCollection($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors {
      field
      message
    }
  }
}`,
};
