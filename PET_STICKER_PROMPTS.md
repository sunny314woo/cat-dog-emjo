# Cat & Dog Custom Sticker Prompt System

**Version:** v0.1  
**Status:** Prototype prompt baseline  
**Scope:** Cat + Dog only  
**Primary goal:** Identity consistency > cuteness > generation speed > cost  
**Output model:** two-stage generation: style preview sheet → selected-style 3×3 sticker sheet

> This document is the prompt source of truth for the local prototype stage. It intentionally does **not** define deployment, payment, account, database, or server architecture.

---

## 1. Product generation contract

### Stage 1 — Style Preview

Input: one original pet photo.  
Output: one **single large PNG** containing a **2×2 style preview sheet** of the same pet.

Four fixed style choices:

- **A — Soft Kawaii Chibi** (`soft_kawaii_chibi`)
- **B — Bold Cartoon Sticker** (`bold_cartoon_sticker`)
- **C — Cute Semi-Realistic** (`cute_semi_realistic`)
- **D — Storybook Watercolor** (`storybook_watercolor`)

Hard rules:

1. All four previews must depict the **same real pet** from the source photo.
2. Pose, viewing angle, crop, scale, and neutral cheerful expression must stay as similar as possible across A/B/C/D.
3. **STYLE is the only intended visual variable.**
4. Do not put A/B/C/D, style names, captions, watermarks, or any text inside the generated image.
5. The original uploaded pet photo remains the **identity source of truth**. A style preview is never allowed to replace the original photo as the sole identity reference for Stage 2.
6. Background must be **real alpha transparency**. A white background, checkerboard pattern drawn into the image, fake transparency, scene background, or near-white background is a failed output.

### Stage 2 — Final Sticker Sheet

Input:

- the same original pet photo;
- the style selected in Stage 1;
- one expression pack.

Output: one **single square PNG** containing a **3×3 grid / nine stickers**, intended to be programmatically cut into nine independent square sticker files later.

Hard rules:

1. Nine stickers must depict the **same pet**.
2. Identity must be derived from the original photo, not from a previously AI-generated preview alone.
3. Style must be consistent across all nine cells.
4. Each expression must be visually distinct.
5. Each cell must remain cut-safe: subject centered, comparable scale, no important anatomy crossing into neighboring cells.
6. The whole sheet must use **true transparent alpha** with no panel backgrounds.
7. No text in the image at this prototype stage.

---

## 2. Identity-locking rules

These rules are deliberately repeated in the prompts because identity drift is the highest-priority failure mode.

### 2.1 Cat identity anchors

Preserve, when visible in the reference photo:

- overall coat base color;
- exact major patch / stripe / point-color distribution;
- forehead markings and facial mask pattern;
- muzzle and chin color;
- white bib / white chest;
- white socks / glove markings and which paws have them;
- eye color and left/right symmetry or asymmetry;
- face width and muzzle proportion;
- ear size, ear angle, and ear tip shape;
- nose color;
- coat length and fluffiness;
- tail color pattern when visible;
- distinctive freckles, spots, scars, asymmetrical markings, or other identity cues.

Do **not** normalize the cat into a generic breed stereotype. A tuxedo cat must keep its actual white/black distribution; a tabby must keep recognizable stripe placement; a calico must keep its major color patches; a pointed cat must retain its real point pattern.

### 2.2 Dog identity anchors

Preserve, when visible in the reference photo:

- overall coat base color;
- exact major patch / mask / saddle distribution;
- eyebrow dots or facial points;
- muzzle length and width;
- muzzle color and blaze;
- eye color;
- ear type: upright / semi-upright / rose / folded / floppy;
- ear size and placement;
- nose size and color;
- forehead width and head silhouette;
- coat type: short / long / wiry / curly / fluffy / double coat;
- chest patch;
- white socks and which legs have them;
- tail shape, curl, plume, and color when visible;
- breed-defining proportions only insofar as they match the actual reference dog;
- distinctive asymmetrical markings.

Do **not** replace the dog with a generic breed icon. If breed is uncertain, preserve the visible individual rather than guessing a breed.

---

# PART A — CAT PROMPTS

## 3. Cat Stage 1 master prompt — 2×2 four-style preview sheet

Use this prompt when the model can generate all four style candidates in one image.

```text
Use the uploaded reference photo as the single identity source of truth for this real cat.

First, visually analyze and lock the cat’s identity before stylizing it. Preserve the same base coat color, major fur-pattern placement, forehead and facial markings, muzzle/chin color, eye color, face shape, ear size and angle, nose color, coat length, white bib/chest, white paws or glove markings, and any visible asymmetrical or distinctive markings. Do not simplify the cat into a generic breed stereotype. All four results must be immediately recognizable as the same individual cat from the reference photo.

Create ONE large PNG style-preview sheet with TRUE ALPHA TRANSPARENCY.

LAYOUT:
- exactly four isolated cat previews arranged as a clean 2×2 grid;
- top-left = Style A;
- top-right = Style B;
- bottom-left = Style C;
- bottom-right = Style D;
- equal visual scale in all four cells;
- same framing, same viewing angle, same body orientation, same cheerful-neutral expression, and as close as possible to the same pose in all four cells;
- each cat centered in its own quadrant with safe margins;
- no panel background, no box, no frame, no separator line.

STYLE A — SOFT KAWAII CHIBI:
2.5-head-tall chibi proportions, oversized rounded head, compact soft body, large but not identity-destroying eyes, rounded paws, gentle shapes, soft clean color blocks, highly adorable premium pet-sticker aesthetic. Preserve real fur markings rather than replacing them with generic cute patterns.

STYLE B — BOLD CARTOON STICKER:
thick smooth dark outline, expressive clean cartoon construction, strong readable silhouette, flat controlled colors, simplified but faithful fur pattern, crisp sticker-ready shapes, lively but not distorted facial features. Do not give the cat human fingers.

STYLE C — CUTE SEMI-REALISTIC:
retain the most faithful facial proportions, eye placement, ear geometry, muzzle, fur-color boundaries, and individual likeness while gently simplifying the cat into a polished cute digital illustration. Slightly enlarged expressive eyes are allowed, but the cat must still look unmistakably like the reference individual. No photorealistic rendering.

STYLE D — STORYBOOK WATERCOLOR:
warm premium children’s-book illustration feel, delicate watercolor-and-gouache texture contained inside the cat silhouette, soft hand-painted edges with enough contour clarity for a sticker, charming and artistic while preserving exact identity markings. Keep all paint texture on the subject only; the canvas behind the subject stays truly transparent.

TRANSPARENCY:
The canvas outside the four cat silhouettes must contain real alpha transparency. Do not draw a white background. Do not draw a gray or checkerboard transparency pattern. Do not create paper texture outside the subjects. Do not create environmental scenery, floor, shadow plate, halo rectangle, or colored cell background.

CONSISTENCY PRIORITY:
Identity consistency is more important than decorative detail. If a style would normally alter breed, coat pattern, face shape, eye color, or ear shape, preserve the real cat instead.

FORBIDDEN:
text, letters, numbers, labels A/B/C/D, watermark, logo, frame, border, panel backgrounds, scene background, extra animals, duplicated limbs, missing paws, human hands, human fingers, clothing, hats, random props, changed eye color, changed coat pattern, changed white-marking placement, different cats across cells, photorealism, 3D render.

FINAL CHECK:
The four previews must read as four art styles of ONE cat, not four similar cats.
```

---

## 4. Cat Style A — Soft Kawaii Chibi

```text
Transform the real cat in the reference photo into a premium Soft Kawaii Chibi pet sticker while preserving the cat’s identity with very high fidelity.

IDENTITY LOCK:
Preserve the exact base coat color, major stripe/patch distribution, forehead and facial markings, muzzle/chin color, eye color, face width, ear size and angle, nose color, coat length, white bib/chest, white glove/sock markings and their left/right placement, plus any asymmetrical identifying marks visible in the source photo. The result must look like this individual cat, not a generic cat of the same breed or color.

STYLE:
- 2.5-head-tall chibi proportions;
- oversized rounded head and compact body;
- large expressive round eyes, but keep original eye color and overall eye placement;
- rounded paws with simplified feline paw anatomy;
- soft, clean, polished color blocks;
- gentle curves and highly adorable expression;
- premium kawaii sticker aesthetic;
- minimal fur-detail lines only where useful;
- preserve recognizable fur markings as stable graphic shapes.

COMPOSITION:
Single cat, centered, isolated, clear silhouette, half-body or full-body depending on the source, with enough transparent margin for sticker cutting.

BACKGROUND:
TRUE transparent alpha only. No white background, no checkerboard pattern, no scene, no floor, no paper texture, no rectangular panel, no cast-shadow plate.

FORBIDDEN:
identity drift, different coat pattern, different eye color, different ear shape, extra cat, text, watermark, human fingers, clothing, props, photorealism, 3D render, overly detailed individual fur strands.
```

---

## 5. Cat Style B — Bold Cartoon Sticker

```text
Create a Bold Cartoon Sticker version of the real cat in the reference photo while keeping the same individual identity unmistakable.

IDENTITY LOCK:
Preserve base coat color, exact major pattern placement, facial mask/forehead markings, muzzle and chin color, eye color, face shape, ear geometry, nose color, coat length, white bib, white paws and their exact distribution, and visible asymmetrical markings. Do not standardize the cat into a generic breed template.

STYLE:
- bold smooth dark outline with consistent stroke weight;
- strong readable silhouette at small messaging-sticker size;
- flat, clean, saturated but faithful color blocks;
- expressive cartoon facial design without changing identity;
- simplified fur texture, using only a few controlled lines;
- rounded feline paws, no human fingers;
- energetic, polished, high-clarity sticker aesthetic;
- suitable for WhatsApp / messaging-scale viewing.

COMPOSITION:
Single isolated cat, centered, balanced margins, no important feature near the canvas edge.

BACKGROUND:
TRUE alpha transparency outside the cat. No white fill, no faux-checkerboard transparency, no environment, no floor, no panel.

FORBIDDEN:
identity drift, breed substitution, altered markings, altered eye color, human hands, extra limbs, text, logo, watermark, props, clothing, photorealistic fur, 3D render, gradients that muddy the silhouette.
```

---

## 6. Cat Style C — Cute Semi-Realistic

```text
Create a Cute Semi-Realistic illustrated sticker of the real cat in the reference photo. Likeness is the primary objective.

IDENTITY LOCK:
Match the reference cat’s real face width, muzzle proportion, eye placement and color, ear size and angle, nose color, coat base color, exact major patch/stripe boundaries, forehead/facial markings, chin/muzzle color, white bib/chest, white socks/gloves, and other distinctive asymmetrical details. Preserve the individual first; stylize second.

STYLE:
- polished cute digital illustration;
- slightly simplified anatomy with natural feline structure;
- gentle controlled stylization, not extreme chibi;
- eyes may be subtly enlarged for warmth but must preserve color, spacing and identity;
- fur rendered as clean grouped masses with a few soft texture accents, not thousands of strands;
- soft facial modeling with clear sticker silhouette;
- warm, premium, emotionally appealing;
- more likeness-focused than Styles A or B;
- no photorealism.

COMPOSITION:
One cat only, centered, isolated, clean outer contour, sticker-safe margins.

BACKGROUND:
True alpha transparency. No white background, no backdrop, no furniture, no floor, no painted paper outside the cat.

FORBIDDEN:
generic breed replacement, face-shape drift, eye-color drift, marking drift, age drift, extra animals, human features, text, watermark, props, photorealistic photo look, 3D render.
```

---

## 7. Cat Style D — Storybook Watercolor

```text
Create a premium Storybook Watercolor sticker illustration of the real cat in the reference photo while preserving the cat’s identity precisely.

IDENTITY LOCK:
Keep the actual base coat color, recognizable major markings, facial pattern, muzzle/chin color, eye color, ear shape and angle, face proportion, nose color, coat length, white chest/bib, white paws, and distinctive asymmetrical marks. Watercolor texture must never obscure or redesign the identity markings.

STYLE:
- charming hand-painted children’s-book illustration;
- watercolor + light gouache feel;
- soft pigment variation inside the subject;
- selective fine ink or painted contour where needed for readability;
- warm, gentle, premium handmade feeling;
- expressive and cute but not babyish;
- maintain a clear sticker silhouette;
- preserve enough color separation to remain readable after downscaling.

COMPOSITION:
Single isolated cat, centered, balanced transparent margins.

BACKGROUND:
The entire area outside the cat must be genuine alpha transparency. Watercolor paper grain must NOT fill the background. No painted wash behind the cat, no vignette, no white rectangle, no checkerboard pattern.

FORBIDDEN:
background wash, paper background, identity drift, altered markings, extra cat, scene, furniture, text, signature, watermark, photorealism, 3D render.
```

---

## 8. Cat Stage 2 master prompt — final 3×3 sticker sheet

Replace `{{STYLE_BLOCK}}` with the selected Style A/B/C/D definition.

```text
Use the uploaded ORIGINAL cat photo as the identity source of truth.

Create ONE square PNG containing exactly NINE distinct stickers of the SAME real cat, arranged as a precise 3×3 grid suitable for later programmatic cutting into nine equal square images.

IDENTITY FIRST:
Before drawing expressions, lock the cat’s identity from the original photo. Preserve the same base coat color, exact major stripe/patch placement, facial and forehead markings, muzzle/chin color, eye color, face shape, ear size and angle, nose color, coat length, white bib/chest, white paws or glove markings and their left/right placement, and any distinctive asymmetrical marks. Every cell must depict the same individual cat. Do not allow identity drift between expressions.

SELECTED STYLE:
{{STYLE_BLOCK}}

GRID / CUT-SAFETY:
- one square master canvas;
- exactly 3 rows × 3 columns;
- nine equal invisible cells;
- no visible grid lines or cell backgrounds;
- one cat sticker centered in each cell;
- comparable head size and overall visual scale across all cells;
- keep ears, paws, tail, hearts, tears, stars, and motion marks safely inside their own cell;
- no overlap across cell boundaries;
- no important detail touching the outer canvas edge;
- spacing must support clean equal-size programmatic cutting.

GLOBAL CHARACTER CONSISTENCY:
- same cat identity in every cell;
- same art style in every cell;
- same coat pattern geometry and colors;
- same eye color;
- same ear shape;
- same face proportion;
- same outline / rendering language;
- expression and pose may change, identity may not.

EXPRESSIONS — left to right, top to bottom:

1. HELLO / WAVE
Raise one front paw in a friendly feline waving gesture. Eyes curve into a cheerful smile, mouth open in a happy expression, subtle pink cheek blush allowed. Keep the paw anatomically paw-like; do not create human fingers.

2. APPROVAL / LIKE
Show a clear enthusiastic approval gesture using one raised paw and proud, pleased facial expression. Suggest the visual meaning of “thumbs up” without turning the paw into a human hand or adding human fingers. Confident upward mouth curve.

3. THANK YOU
Both front paws brought together politely in front of the chest, eyes closed in a warm grateful expression. One small heart above the head is allowed, fully contained within the cell.

4. ANGRY / PUFFED
Fur and tail visibly puffed, tense compact posture, narrowed or vertical pupils where stylistically appropriate, furrowed brow, small angry mouth. Up to three simple red anger marks allowed. Still cute, not violent or frightening.

5. SAD / CRYING
Large expressive eyes with two clear tear streams, downturned mouth, small paws near the eyes as if wiping tears. Subtle trembling motion marks allowed. Do not distort the face identity.

6. EXCITED / JUMPING
Body lifted in a joyful jump, both front paws raised, delighted open-mouth smile, bright excited eyes. Up to three small star accents allowed and must remain inside the cell.

7. SPEECHLESS / EYE ROLL
Eyes rolled upward showing a clear “speechless” emotion, mouth a short flat line, unimpressed posture. A few simple sweat / awkward marks allowed, but no text or punctuation characters.

8. SLEEPING
Cat curled naturally into a compact sleeping pose, eyes fully closed, peaceful facial expression, tail wrapped naturally if visible. Do NOT include letter “Z” or any written sleep symbol because the full sheet must remain text-free.

9. HUG / CUDDLE REQUEST
Both front paws extended forward in an inviting cuddle gesture, wide gentle watery eyes, tiny open mouth, affectionate pleading expression. Up to two small pink hearts allowed above the head, fully contained in the cell.

TRUE TRANSPARENCY:
The entire canvas outside every sticker subject and allowed decorative accent must be genuine alpha transparency. Do not create white cell backgrounds. Do not draw a checkerboard transparency pattern. Do not add scene backgrounds, colored circles, floor shadows, rectangular cards, paper texture, gradients behind the subjects, or any opaque sheet background.

NO TEXT:
No words, letters, numbers, punctuation, labels, captions, signatures, logos, watermarks, or “Z” symbols anywhere in the image.

NEGATIVE / FAILURE CONDITIONS:
- different-looking cats across cells;
- changed coat pattern or white-mark placement;
- changed eye color;
- changed ear geometry;
- changed breed appearance;
- accidental extra cat;
- duplicated or missing limbs;
- human hands or human fingers;
- anatomically impossible paw shapes;
- expression repetition;
- inconsistent scale;
- cell overlap;
- text of any kind;
- white or colored background;
- fake checkerboard transparency;
- photorealistic rendering;
- 3D render;
- excessive detailed fur that destroys sticker clarity;
- extra props unrelated to the expression.

QUALITY ORDER:
1. same-cat identity consistency;
2. expression clarity;
3. cut-safe 3×3 layout;
4. cuteness and polish;
5. decorative detail.

FINAL SELF-CHECK:
This must look like nine expressions performed by ONE recognizable cat character derived from the original pet photo, not nine loosely similar cats.
```

---

# PART B — DOG PROMPTS

## 9. Dog Stage 1 master prompt — 2×2 four-style preview sheet

```text
Use the uploaded reference photo as the single identity source of truth for this real dog.

First, visually analyze and lock the dog’s identity before stylizing it. Preserve the actual base coat color, major patch/mask/saddle distribution, facial blaze, eyebrow points if present, muzzle length and width, muzzle color, eye color, forehead width, ear type and exact placement, nose size and color, coat length/texture, chest patch, white socks and which legs have them, visible tail shape, and any asymmetrical or distinctive markings. If breed is uncertain, preserve the visible individual rather than inventing a breed. All four results must be immediately recognizable as the same dog.

Create ONE large PNG style-preview sheet with TRUE ALPHA TRANSPARENCY.

LAYOUT:
- exactly four isolated dog previews arranged as a clean 2×2 grid;
- top-left = Style A;
- top-right = Style B;
- bottom-left = Style C;
- bottom-right = Style D;
- equal visual scale in all four cells;
- same framing, same viewing angle, same body orientation, same cheerful-neutral expression, and as close as possible to the same pose in all four cells;
- each dog centered in its own quadrant with safe margins;
- no panel background, no box, no frame, no separator line.

STYLE A — SOFT KAWAII CHIBI:
2.5-head-tall chibi proportions, oversized rounded head, compact soft body, expressive eyes, rounded paws, cute simplified silhouette, gentle clean colors, premium adorable sticker aesthetic. Preserve breed-defining muzzle, ears, coat type, and real markings.

STYLE B — BOLD CARTOON STICKER:
thick smooth dark outline, strong readable silhouette, flat controlled colors, expressive cartoon construction, clean sticker-ready shape. Keep the dog’s real ear type, muzzle geometry, head shape, and identifying coat pattern. Do not give the dog human hands or fingers.

STYLE C — CUTE SEMI-REALISTIC:
prioritize faithful likeness: real head shape, muzzle length, ear geometry, eye placement, coat pattern and breed feel, gently simplified into a polished cute digital illustration. No photorealism.

STYLE D — STORYBOOK WATERCOLOR:
warm premium children’s-book illustration feel, watercolor-and-gouache texture contained inside the dog silhouette, soft artistic rendering while preserving the exact dog identity and readable sticker contour. Keep the canvas behind the dog truly transparent.

TRANSPARENCY:
The canvas outside the four dog silhouettes must contain real alpha transparency. Do not draw a white background. Do not draw a gray or checkerboard transparency pattern. Do not create paper texture outside the subjects. Do not create scenery, floor, shadow plate, halo rectangle, or colored cell background.

CONSISTENCY PRIORITY:
Identity consistency is more important than decorative detail. If a style would normally alter breed, muzzle length, ear shape, coat pattern, face proportions, or eye color, preserve the real dog instead.

FORBIDDEN:
text, letters, numbers, labels A/B/C/D, watermark, logo, frame, border, panel backgrounds, scene background, extra animals, duplicated limbs, missing paws, human hands, human fingers, clothing, hats, random props, changed eye color, changed coat pattern, changed ear type, changed muzzle length, different dogs across cells, photorealism, 3D render.

FINAL CHECK:
The four previews must read as four art styles of ONE dog, not four dogs of a similar breed.
```

---

## 10. Dog Style A — Soft Kawaii Chibi

```text
Transform the real dog in the reference photo into a premium Soft Kawaii Chibi pet sticker while preserving individual identity with very high fidelity.

IDENTITY LOCK:
Preserve exact base coat color, major mask/patch/saddle distribution, facial blaze, eyebrow points if present, muzzle length and width, muzzle color, eye color, head shape, ear type/size/placement, nose size and color, coat length and texture, chest patch, white socks and their leg placement, tail shape when visible, and any asymmetrical identifying marks. Do not turn the dog into a generic breed mascot.

STYLE:
- 2.5-head-tall chibi proportions;
- oversized rounded head with compact body;
- expressive larger eyes while preserving eye color and placement;
- soft rounded paws with canine anatomy;
- gentle, clean, premium color blocks;
- highly adorable but still recognizably the same dog;
- breed-defining muzzle and ear structure must remain visible;
- minimal fur-detail lines;
- stable graphic rendering of real coat markings.

COMPOSITION:
Single dog, centered, isolated, half-body or full-body depending on reference, transparent sticker-safe margin.

BACKGROUND:
TRUE transparent alpha only. No white background, no checkerboard, no environment, no floor, no panel, no paper texture.

FORBIDDEN:
identity drift, breed drift, shortened/lengthened muzzle that changes identity, changed ears, changed coat pattern, changed eye color, extra dog, text, watermark, human fingers, clothing, random props, photorealism, 3D render.
```

---

## 11. Dog Style B — Bold Cartoon Sticker

```text
Create a Bold Cartoon Sticker version of the real dog in the reference photo while keeping the same individual dog unmistakable.

IDENTITY LOCK:
Preserve base coat color, actual mask/patch/saddle geometry, facial blaze, eyebrow points, muzzle length and width, eye color, head shape, ear type and placement, nose size/color, coat type, chest patch, white socks, tail characteristics, and visible asymmetrical markings. Do not replace the dog with a generic breed caricature.

STYLE:
- thick smooth dark outline with consistent stroke weight;
- strong silhouette that remains readable at messaging-sticker size;
- flat clean colors faithful to the real dog;
- expressive cartoon face without changing muzzle/head identity;
- simplified coat texture;
- clear canine paws, no human fingers;
- energetic, polished, sticker-ready design;
- preserve breed feel and individual facial geometry.

COMPOSITION:
One dog only, centered, balanced transparent margins, no feature touching the canvas edge.

BACKGROUND:
Genuine alpha transparency outside the dog. No white fill, no fake checkerboard, no environment, no floor, no panel.

FORBIDDEN:
breed substitution, muzzle drift, ear drift, coat-pattern drift, human hands, extra limbs, text, logo, watermark, props, clothes, photorealistic fur, 3D render.
```

---

## 12. Dog Style C — Cute Semi-Realistic

```text
Create a Cute Semi-Realistic illustrated sticker of the real dog in the reference photo. Individual likeness is the primary objective.

IDENTITY LOCK:
Match the real head silhouette, forehead width, muzzle length/width, eye placement and color, ear type/size/placement, nose size/color, base coat color, facial mask or blaze, major body markings, eyebrow points, chest patch, white socks, coat length/texture, and distinctive asymmetry. If breed is uncertain, do not guess; follow the visible dog.

STYLE:
- polished cute digital illustration;
- natural canine anatomy with gentle simplification;
- restrained stylization, not extreme chibi;
- eyes may be subtly enlarged for warmth but must preserve identity;
- coat rendered as grouped soft masses with limited texture accents;
- breed feel remains recognizable;
- clean sticker silhouette;
- premium emotional portrait quality;
- no photorealism.

COMPOSITION:
One dog only, centered, isolated, clean contour, sticker-safe transparent margins.

BACKGROUND:
True alpha transparency. No white background, no furniture, no scenery, no floor, no paper field behind the dog.

FORBIDDEN:
generic breed replacement, head-shape drift, muzzle drift, ear drift, eye-color drift, marking drift, age drift, extra animals, human features, text, watermark, props, photorealistic photo look, 3D render.
```

---

## 13. Dog Style D — Storybook Watercolor

```text
Create a premium Storybook Watercolor sticker illustration of the real dog in the reference photo while preserving the dog’s identity precisely.

IDENTITY LOCK:
Keep the real base coat color, exact major markings, face mask/blaze, eyebrow points, eye color, ear type and placement, muzzle geometry, head proportion, nose color, coat type, chest patch, white socks, and distinctive asymmetrical marks. Watercolor texture must never redesign the dog’s breed feel or individual identity.

STYLE:
- warm hand-painted children’s-book illustration;
- watercolor + light gouache feel;
- soft pigment variation only within the dog silhouette;
- selective fine contour for sticker readability;
- premium handmade warmth;
- expressive and cute without turning the dog into a generic puppy icon;
- preserve small-size readability and strong outer silhouette.

COMPOSITION:
Single isolated dog, centered, balanced transparent margin.

BACKGROUND:
The whole area outside the dog must be real alpha transparency. Do not fill the canvas with watercolor paper grain. No wash, vignette, white rectangle, checkerboard, or scene behind the subject.

FORBIDDEN:
background wash, paper background, identity drift, breed drift, changed muzzle/ears/markings, extra dog, scenery, text, signature, watermark, photorealism, 3D render.
```

---

## 14. Dog Stage 2 master prompt — final 3×3 sticker sheet

Replace `{{STYLE_BLOCK}}` with the selected Style A/B/C/D definition.

```text
Use the uploaded ORIGINAL dog photo as the identity source of truth.

Create ONE square PNG containing exactly NINE distinct stickers of the SAME real dog, arranged as a precise 3×3 grid suitable for later programmatic cutting into nine equal square images.

IDENTITY FIRST:
Before drawing expressions, lock the dog’s identity from the original photo. Preserve the same base coat color, exact major patch/mask/saddle placement, facial blaze, eyebrow points if present, muzzle length and width, muzzle color, eye color, head shape, ear type/size/placement, nose size and color, coat length/texture, chest patch, white socks and which legs have them, visible tail shape, and any distinctive asymmetrical markings. If breed is uncertain, follow the visible individual instead of inventing a breed. Every cell must depict the same dog.

SELECTED STYLE:
{{STYLE_BLOCK}}

GRID / CUT-SAFETY:
- one square master canvas;
- exactly 3 rows × 3 columns;
- nine equal invisible cells;
- no visible grid lines or cell backgrounds;
- one dog sticker centered in each cell;
- comparable head size and overall visual scale across all cells;
- keep ears, paws, tail, hearts, tears, stars, and motion marks safely inside their own cell;
- no overlap across cell boundaries;
- no important detail touching the outer canvas edge;
- spacing must support clean equal-size programmatic cutting.

GLOBAL CHARACTER CONSISTENCY:
- same dog identity in every cell;
- same art style in every cell;
- same muzzle length and head geometry;
- same ear type and placement;
- same coat pattern and colors;
- same eye color;
- same coat texture language;
- expression and pose may change, identity may not.

EXPRESSIONS — left to right, top to bottom:

1. HELLO / WAVE
Raise one front paw in a friendly canine waving gesture, cheerful eyes and happy open-mouth expression. Keep the paw canine; no human fingers.

2. APPROVAL / LIKE
Show a clear enthusiastic approval gesture with one raised front paw and a proud pleased face. Communicate the meaning of “thumbs up” through pose and expression without turning the paw into a human hand.

3. THANK YOU
Both front paws brought together politely in front of the chest, warm grateful expression, eyes gently closed or softened. One small heart allowed above the head, inside the cell.

4. ANGRY / GRUMPY
Clear grumpy emotion using ears, brows, eyes, mouth and body tension appropriate to this dog’s natural ear type. Keep it cute and non-threatening. Do not force upright ears on a floppy-eared dog. Up to three small anger marks allowed.

5. SAD / CRYING
Large expressive watery eyes, clear tears, downturned mouth, lowered or softened ears as appropriate to the actual ear anatomy, small paw near face if natural. Preserve muzzle and face identity.

6. EXCITED / JUMPING
Joyful jump with both front paws raised, excited open-mouth smile; tongue may appear only if natural and not identity-distorting. Up to three small star accents allowed, contained within the cell.

7. SPEECHLESS / EYE ROLL
Clear unimpressed / speechless expression, upward eye roll or sideways skeptical look, simple flat mouth. Ear position should remain anatomically consistent with the real dog. A few simple awkward/sweat marks allowed, but no text.

8. SLEEPING
Dog curled or lying naturally in a peaceful sleeping pose, eyes fully closed, relaxed ears and paws, tail resting naturally if visible. No letter “Z” or written sleep symbol.

9. HUG / CUDDLE REQUEST
Both front paws extended forward in an inviting cuddle gesture, soft pleading eyes, affectionate expression, slightly open mouth if appropriate. Up to two small pink hearts allowed, fully inside the cell.

TRUE TRANSPARENCY:
The entire canvas outside every sticker subject and allowed decorative accent must be genuine alpha transparency. No white cell backgrounds, no checkerboard transparency pattern, no environmental scene, no colored circles, no floor shadows, no rectangular cards, no paper texture, no opaque master-sheet background.

NO TEXT:
No words, letters, numbers, punctuation, labels, captions, signatures, logos, watermarks, or “Z” symbols anywhere.

NEGATIVE / FAILURE CONDITIONS:
- different dogs across cells;
- breed drift;
- changed muzzle length or width;
- changed ear type;
- changed coat pattern or white-sock placement;
- changed eye color;
- accidental extra dog;
- duplicated or missing limbs;
- human hands or fingers;
- expression repetition;
- inconsistent scale;
- cell overlap;
- text;
- white or colored background;
- fake checkerboard transparency;
- photorealistic render;
- 3D render;
- excessive fur detail that destroys sticker readability;
- unrelated props.

QUALITY ORDER:
1. same-dog identity consistency;
2. expression clarity;
3. cut-safe 3×3 layout;
4. cuteness and polish;
5. decorative detail.

FINAL SELF-CHECK:
This must look like nine expressions performed by ONE recognizable dog character derived from the original pet photo, not nine dogs from the same breed.
```

---

# PART C — STYLE BLOCKS FOR STAGE 2 INJECTION

These compact blocks are intended to be injected into the Stage 2 master prompt after the user selects A/B/C/D.

## 15. Style A block — `soft_kawaii_chibi`

```text
SOFT KAWAII CHIBI: 2.5-head-tall proportions, oversized rounded head, compact soft body, expressive large eyes without changing eye color or identity, rounded species-correct paws, gentle clean color blocks, minimal fur lines, highly adorable premium sticker aesthetic. Preserve all identity-defining markings exactly. No photorealism, no 3D.
```

## 16. Style B block — `bold_cartoon_sticker`

```text
BOLD CARTOON STICKER: thick smooth dark outline, consistent stroke weight, strong readable silhouette, clean flat colors, expressive cartoon construction, simplified fur texture, crisp sticker-ready shapes, high readability at small messaging size. Preserve exact identity markings and species anatomy. No human fingers, no photorealism, no 3D.
```

## 17. Style C block — `cute_semi_realistic`

```text
CUTE SEMI-REALISTIC: prioritize individual likeness, preserve real facial/head proportions, eye placement and color, ear geometry, muzzle structure, and exact coat-marking boundaries; gently simplify into a polished cute digital illustration with restrained stylization, subtle eye enlargement only if identity remains intact, grouped soft fur masses, clear sticker silhouette. No photorealistic photo look, no 3D.
```

## 18. Style D block — `storybook_watercolor`

```text
STORYBOOK WATERCOLOR: premium children’s-book watercolor + light gouache feel, pigment and paper-like texture contained only inside the subject silhouette, warm handmade character, soft but readable contour, preserved exact identity markings, clear sticker silhouette and small-size readability. The canvas outside the subject remains true alpha transparency; no background wash, no paper field, no 3D.
```

---

# PART D — PROTOTYPE TEST PROTOCOL

## 19. Recommended test order

To avoid confusing model problems with prompt problems, change only one variable at a time.

1. Test **Cat Stage 1 master prompt** with 5–10 visually different cats.
2. Check whether A/B/C/D are visibly different while still being the same cat.
3. Select one style and run **Cat Stage 2**.
4. Repeat the same cat with all four styles only after identity consistency is acceptable.
5. Then test **Dog Stage 1** with dogs covering at least:
   - upright ears;
   - floppy ears;
   - short muzzle;
   - long muzzle;
   - short coat;
   - long / curly coat;
   - high-contrast markings.
6. Then test **Dog Stage 2**.

## 20. Failure labels

Use these labels when recording prototype results:

- `IDENTITY_DRIFT` — no longer clearly the same individual pet.
- `MARKING_DRIFT` — key coat markings moved, disappeared, or changed.
- `EYE_DRIFT` — eye color / placement changed materially.
- `EAR_DRIFT` — ear type or geometry changed materially.
- `MUZZLE_DRIFT` — dog muzzle changed enough to alter identity.
- `STYLE_COLLAPSE` — A/B/C/D look too similar.
- `STYLE_OVERPOWERED_IDENTITY` — style changed identity-defining features.
- `GRID_LEAK` — limbs / decorations cross into neighboring cells.
- `SCALE_DRIFT` — character size varies too much across cells.
- `EXPRESSION_COLLAPSE` — several expressions look effectively the same.
- `FAKE_TRANSPARENCY` — white / checkerboard / opaque background instead of alpha.
- `TEXT_LEAK` — model generated letters, labels, numbers, or symbols.
- `ANATOMY_ERROR` — duplicated/missing limbs or human fingers.

## 21. Prototype acceptance priorities

Evaluate outputs in this order:

1. **Identity consistency** — must still be the same pet.
2. **Cuteness / willingness to buy** — should feel emotionally appealing.
3. **Sticker readability** — must still work when reduced to chat-sticker size.
4. **Layout / cut safety** — later processing must be reliable.
5. **Transparency correctness** — real alpha, not fake transparency.
6. **Speed and generation cost** — optimize only after the above are acceptable.

---

# 22. Prompt inventory

This document contains:

- 4 cat style-specific prompts;
- 4 dog style-specific prompts;
- 1 cat 2×2 four-style preview master prompt;
- 1 dog 2×2 four-style preview master prompt;
- 1 cat final 3×3 master prompt;
- 1 dog final 3×3 master prompt;
- 4 compact reusable Stage-2 style blocks.

The core “4 + 4” style prompts are the eight species/style variants. The master prompts are included so the prototype can be tested directly without manually assembling prompt fragments.

---

## 23. Non-goals for this version

Not defined in this prompt baseline:

- baby / human sticker generation;
- dynamic GIF stickers;
- user-defined expression packs;
- 18 / 27 expression pack contents;
- server deployment;
- payment pricing;
- account reuse;
- order workflow;
- WeChat / WhatsApp final export dimensions;
- model/API vendor choice.

Those should be frozen separately after image-generation quality is validated.
