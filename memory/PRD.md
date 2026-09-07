# Sattva & Samagri — Product Requirements

## Original problem statement
Build a complete, production-quality, dynamic e-commerce website for a premium Indian Spiritual & Puja Samagri brand. It must be a real shopping platform rather than a landing page, with product discovery, search, filtering, product pages, wishlist, cart, checkout, order confirmation, account/order routes, responsive design, trust elements, and a future-ready product architecture.

## User choices
- Dummy Razorpay payment gateway for the first version; no real charges.
- Frontend-local product data for the first version.
- Premium warm ivory, deep maroon, muted saffron, and antique-gold visual direction.

## Architecture decisions
- React single-page storefront with React Router routes for connected shopping journeys.
- Reusable data-driven product cards, product grids, listing pages, category routing, detail pages, cart, wishlist, checkout, and account views.
- 36 generated catalog records sourced from 12 realistic product seeds, with product attributes ready to migrate to an API/admin catalog later.
- Cart and wishlist persist in browser localStorage.
- Payment is intentionally a **MOCKED** Razorpay-style UI flow; no external payment credentials or API calls are used.

## User personas
- Devotees buying daily puja essentials and festival supplies.
- Families looking for complete, convenient puja kits.
- Gift buyers seeking premium spiritual objects and curated sets.

## Core requirements
- Product discovery through home, shop, category, festival, search, best seller and new-style merchandising.
- Search, filters, sorting, load more, product details, related products and responsive product cards.
- Wishlist add/remove and cart add, quantity changes, removal, live totals, shipping threshold and checkout.
- Three-step checkout with contact, delivery and payment selections plus order confirmation.
- Account, order history, tracking, informational pages and sticky navigation.
- Responsive desktop/tablet/mobile layouts with mobile menu and no intentional horizontal overflow.

## What’s been implemented

### 2026-09-07
- Replaced the starter screen with Sattva & Samagri premium storefront experience.
- Added 36 local products, category tiles, hero merchandising, best sellers, puja kits, occasion navigation, trust strip, footer and newsletter UI.
- Added working routes for home, shop, categories, festival, search, product detail, wishlist, cart, checkout, order confirmation, account, order history, tracking and information pages.
- Added localStorage cart/wishlist persistence, live item counts, filters, sorting, load more, quantity controls, wishlist state and connected product navigation.
- Added dummy Razorpay payment choices (UPI, cards, cash on delivery) and checkout validation for required/valid contact and delivery fields.
- Verified production build, desktop and mobile smoke flows, and full shopping journey through confirmation.

## Prioritized backlog

### P0 — Remaining for a production commerce release
- Replace frontend-local catalog with a secured product/catalog API and admin CRUD.
- Add real authentication, saved addresses, persistent orders and server-side order creation.
- Replace the **MOCKED** Razorpay UI with verified server-created Razorpay orders and signature validation.

### P1
- Add real product review submission and moderation.
- Add product image upload and variants/weight selection.
- Add coupon engine, inventory updates and transactional order email/SMS.

### P2
- Add subscriptions for recurring incense/camphor essentials.
- Add richer ritual guides, content collections and social proof integrations.
- Add analytics dashboards for merchandising and conversion insights.

## Next tasks
1. Build the admin-ready catalog API and product editor.
2. Add persistent account and order services.
3. Connect Razorpay test orders with server-side verification.
4. Add real reviews, coupons and inventory.