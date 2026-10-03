# 本地新版 H5（2026-10-03）

运行 `python3 tools/run_local.py`，打开 http://127.0.0.1:4173/sticker/ 。默认固定样例模式，不调用真实 AI、不收款、不发邮件。

实现范围、已确认需求和上线缺口见 [增量决策](docs/product/IMPLEMENTATION_2026-10-03.md)。测试：`python3 -m pytest tests -q`。需要 Python 依赖见 `server/requirements.txt`。

---

# My Pet Stickers

## 项目最新方向（2026-10-02）

请先阅读 [V2.3 首版需求整理稿](docs/PROJECT_OVERVIEW.md)和[负责人原稿](docs/product/MVP_DRAFT_V2.3_SOURCE.md)。首版每次九张：匿名上传一张宝宝／宠物照片，选主题和风格，一次生成九宫格、揭晓、任选两张正式贴纸免费领取；完整解锁时验证邮箱，Paddle 付款后下载同一套九张和 ZIP，并由 Resend 邮件交付。后续新生成使用 1／3／5 Pack 余额。后端按 Python／FastAPI／MySQL／pymysql、原生 SQL 独立实现，图片短期保存；价格和新 Price ID 留配置占位。

[上传与成本历史讨论](docs/product/UPLOAD_PREVIEW_PAYMENT.md)保留多图、裁切和技术依据；其中两阶段调用、每日免费、赠送重做及 30 天保留已经被 V2.3 更新，不作为当前商业合同。

支付商品参数已配置，但本地结账仍禁用，真实订单、支付验证与交付尚需实现。下文保留当前版本的运行与部署背景；其中既有设计方向需结合新说明重新评估。`doubao/` 与 `UI/` 是被 Git 忽略的本地参考，克隆仓库不会自动包含这些目录。目录迁移方案目前仅为建议，尚未执行。

English pet sticker storefront, isolated in `apps/emjo`.

## Repository and prompts

This directory is an independent Git checkout of [sunny314woo/cat-dog-emjo](https://github.com/sunny314woo/cat-dog-emjo), located inside the Wisteria Suite workspace. Run this project's Git commands here. The outer repository ignores `apps/emjo/` locally via `.git/info/exclude`.

[PET_STICKER_PROMPTS.md](PET_STICKER_PROMPTS.md) contains the active v0.5 prompt draft: thirteen candidate styles, four preview slots, 9/18/27 expressions generated in pages of nine, optional small accessories, and one selected subject per request. Final generation uses 1–2 original subject photos, the selected style crop, and user requirements. Existing styles are preserved; the final four UI styles are undecided. Its v0.1 appendix is historical reference. The static storefront does not yet send these prompts to a generation API.

V2.3 requires an implementation adapter for this library: one uploaded photo, fixed example style selection, one nine-cell generation, and program-rendered text. The earlier personalized four-style generation, free-form user prompt and per-cell AI fallback are outside the new MVP. Preserve the library; follow the requirements document when building the new flow.

`doubao/`, `UI/`, `.local-backups/` and real environment/credential files stay local and must never be committed or published. See [the prompt comparison and Git handoff](docs/ai-handoff/prompt-sync-2026-10-02.md) for the imported revision, local prototype differences and update workflow.

## Preview

Run `python3 -m http.server 4173 --bind 127.0.0.1` in this directory, then open http://127.0.0.1:4173. Opening index.html directly is also supported.

## Implemented

- Rebuilt brand, responsive storefront, original-photo / sticker-sheet gallery, four visual styles, pack details and FAQ.
- Six user-provided assets stored locally in assets/. Two genuine supplied sample sets; no invented customer testimonials.
- Cat/dog style browsing, validated local photo preview, sample style selection and watermarked sample pack walkthrough.
- Uploaded photos stay local. Sample packs are labeled and never presented as output generated from a new upload.
- Paddle product and price identifiers configured. Checkout stays disabled until a real generated order and server-verified payment flow are available.

## Deployment target

- New target: https://wisteriasoftware.uk/sticker/ — the same hostname as the Outline website. Confirm the new path before deployment.
- Checkout and order pages belong under this product path; the Outline page and its existing payment flow remain separate.
- Proposed API prefix: /sticker/api, served by an isolated backend.
- Existing pet.wisteriasoftware.uk and CNAME are historical deployment files; production routing has not been changed.
- Use an independent process/container, database and private data directory. services/account-server and services/api-server are read-only references; do not modify or restart those services as part of this project.
- Never serve .env, source server files or private order assets from the public web root. Only index.html, styles.css, app.js, config.js and assets/ belong in it.

## Server integrations still required

Volcano image generation, order persistence, Paddle webhook verification, protected downloads, background removal / image delivery processing, retention jobs and delivery email remain backend work. Public samples are marketing assets, not private paid order files.

.env.example is the target configuration template with blank credentials, model IDs, payment IDs and business limits for the owner to complete. Runtime integration is not implemented yet. Confirm the Paddle environment and product before enabling checkout; old public IDs in config.js are reference only.

Email uses Resend, following services/account-server/app/services/mail.py: POST https://api.resend.com/emails, Bearer authentication, RESEND_API_KEY and MAIL_FROM. Set MAIL_PROVIDER=resend. The configured sender must be verified in Resend. Paid delivery should attach one ZIP and include a protected backup download link. Never send before the backend has verified payment.

## Design references

West & Willow: product-focused presentation and space. FurEver Stickers: preview-first buying flow. Pop Your Pup and Poster & Paw: pet-led merchandising. MooPortraits was requested as a style-selection reference but could not be accessed during this pass. All site artwork here comes from the owner’s supplied assets, not reference-site artwork.
