# My Pet Stickers

English pet sticker storefront, isolated in `apps/emjo`.

## Preview

Run `python3 -m http.server 4173 --bind 127.0.0.1` in this directory, then open http://127.0.0.1:4173. Opening index.html directly is also supported.

## Implemented

- Rebuilt brand, responsive storefront, original-photo / sticker-sheet gallery, four visual styles, pack details and FAQ.
- Six user-provided assets stored locally in assets/. Two genuine supplied sample sets; no invented customer testimonials.
- Cat/dog style browsing, validated local photo preview, sample style selection and watermarked sample pack walkthrough.
- Uploaded photos stay local. Sample packs are labeled and never presented as output generated from a new upload.
- Paddle product and price identifiers configured. Checkout stays disabled until a real generated order and server-verified payment flow are available.

## Deployment target

- Public site: https://pet.wisteriasoftware.uk
- Origin server supplied by owner: 5.78.185.116 (Cloudflare DNS configured by owner).
- Recommended isolated root: /opt/my-pet-stickers. This source change does not deploy or alter existing server services.
- Public API path: /api on the same domain, reserved for the independent FastAPI service.
- Never serve .env, source server files or private order assets from the public web root. Only index.html, styles.css, app.js, config.js and assets/ belong in it.

## Server integrations still required

Volcano image generation, order persistence, Paddle webhook verification, protected downloads, background removal / image delivery processing, retention jobs and delivery email remain backend work. Public samples are marketing assets, not private paid order files.

.env.example contains server-only placeholders, the supplied Paddle IDs and the production domain. Confirm Paddle environment before enabling checkout; product IDs do not identify sandbox versus live.

Email uses Resend, following services/account-server/app/services/mail.py: POST https://api.resend.com/emails, Bearer authentication, RESEND_API_KEY and MAIL_FROM. Set MAIL_PROVIDER=resend. The configured sender must be verified in Resend. Paid delivery should attach one ZIP and include a protected backup download link. Never send before the backend has verified payment.

## Design references

West & Willow: product-focused presentation and space. FurEver Stickers: preview-first buying flow. Pop Your Pup and Poster & Paw: pet-led merchandising. MooPortraits was requested as a style-selection reference but could not be accessed during this pass. All site artwork here comes from the owner’s supplied assets, not reference-site artwork.
