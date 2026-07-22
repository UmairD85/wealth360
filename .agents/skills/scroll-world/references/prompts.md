# Prompt templates and intake

Keep the style preamble byte-for-byte identical across every scene still. Consistency is
more important than adding fresh adjectives to each prompt.

## Intake record

Capture:

- `SUBJECT`: business/idea plus one-line pitch.
- `BRAND_NAME`: public display name.
- `PALETTE`: 4–6 named hex values; identify background, accent, and ink.
- `TONE`: one or two words.
- `STYLE`: one frozen art-direction preamble.
- `SECTIONS[]`: `id`, `subject`, `focal_point`, `next_direction`, `eyebrow`, `title`,
  `body`, `tags[]`.
- `ARCHITECTURE`: A continuous journey or B dives/connectors.
- `VIDEO_TIER`: `preview`, `fast`, or `standard`.
- `IMAGE_MODEL`: `standard` or `character`.
- `MOBILE`: desktop only or desktop + native 9:16.
- `COST_APPROVED`: calibrated estimate and explicit approval.

## Default style preamble — clay diorama

```text
Isometric low-poly 3D diorama floating as a small rounded island on a plain solid
[BG_HEX] background with a soft contact shadow beneath it. Soft matte clay render,
rounded toy-model shapes, gentle warm studio lighting, long soft shadows, and a
tilt-shift miniature lens. Cohesive palette of [PALETTE]. Highly detailed, centred
composition. Absolutely no text, letters, numbers, logos, signatures, or watermarks.
```

Alternate openings; retain the palette and no-text tail:

- **Flat papercraft:** Isometric layered paper-craft diorama, matte cardstock, clean
  die-cut edges, subtle shadows between layers.
- **Glossy toy:** Isometric collectible vinyl-toy world, smooth plastic shading, soft
  rim light, premium product-render finish.
- **Claymation:** Isometric stop-motion clay set, handmade plasticine texture, visible
  thumbprints, soft studio light.
- **Neon miniature:** Isometric miniature at night, warm interiors, restrained neon,
  wet reflective ground, moody rim light.
- **Photoreal architectural:** Ultra-photorealistic architectural photography of one
  cohesive [SUBJECT], cinematic wide lens, natural materials, restrained furniture,
  golden-hour light, editorial magazine quality, no people, no text. Use full-bleed
  scenes, not floating islands.

## Scene-still prompt

```text
[STYLE PREAMBLE]

Scene: [SECTION.subject]. Include [3–6 concrete props or actions that prove this stage of
the journey]. The primary focal point is [FOCAL_POINT]. Preserve generous negative space
around the island and keep the focal subject near the visual centre. Wide 3:2 composition.
```

Prompting rules:

- Concrete props anchor meaning: tanks, ledgers, conveyors, crates, glass walls,
  dashboards, workbenches, delivery vehicles, control rooms, gardens.
- Do not ask the model to render interface text. Add live HTML copy later.
- The final scene may shift from an island to one oversized hero object, using the same
  background, materials, and lighting.
- Generate one source model consistently across all scenes.
- For native mobile, write a separate 9:16 version with the focal point around 45% of
  canvas height and meaningful negative space above/below.

## Architecture A — continuous leg

The first input is the previous leg’s actual rendered last frame. Leg 0 uses the approved
first scene still. Do not provide a last frame by default.

```text
One continuous cinematic camera move with no cuts. Continue the same slow, steady
forward glide from the opening frame. Move into [SCENE] toward [FOCAL_POINT].

[OPTIONAL MID-LEG MOVE]

Maintain coherent geometry, materials, lighting, and palette: [STYLE TAIL + PALETTE].
Use graceful slow movement and subtle parallax. In the final second, settle into a calm,
steady forward drift toward [NEXT_DIRECTION], ready for the next shot to continue the
same movement. No text, captions, logos, watermarks, cuts, flicker, or sudden speed change.
```

Optional mid-leg moves:

- Product/luxury: slow half-orbit around the hero object, then continue past it.
- Real estate/hospitality: steadicam glide through a doorway, with a gentle atrium
  crane-up before returning to forward drift.
- Industrial/process: low lateral track beside the line with foreground parallax.
- Travel/outdoors: gentle rise-and-reveal followed by a descending forward swoop.
- Food/craft: push close to the craft moment, ease back inside the same shot, then
  continue forward.

Reversal is acceptable inside one rendered leg; it is unacceptable across the seam.

## Architecture B — dive

The first frame is the solid-background approved scene still.

```text
One continuous cinematic camera move with no cuts. Begin high and far, looking down at
the entire [SECTION.subject] like a miniature world. Glide forward and descend toward
[FOCAL_POINT], flying inside the scene. If it is a building, let the roof or upper
structure open naturally as the camera approaches; otherwise fly low across the terrain.
Preserve [STYLE TAIL + PALETTE]. Smooth, slow motion with subtle parallax. Finish on an
intimate interior/detail view. No text, captions, logos, watermarks, flicker, or cuts.
```

## Architecture B — connector

The first frame is the previous dive’s actual rendered last frame. The last frame is the
next dive’s actual rendered first frame.

```text
One continuous cinematic camera move with no cuts. Starting exactly from the supplied
interior/detail frame of [SCENE A], pull smoothly upward and outward into the connected
miniature world. Glide forward across the landscape toward [SCENE B], then descend and
arrive exactly on the supplied final frame. Keep one coherent world, palette, lighting,
materials, and lens character. Smooth slow motion, no pause, no sudden acceleration, no
text, no captions, no logos, no watermarks, and no flicker.
```

For a product finale:

```text
As the camera leaves [SCENE A], the connected world dissolves gently into open [BG_HEX]
space and reveals one oversized [PRODUCT] ahead, arriving exactly on the supplied hero
frame without a cut.
```

## Wan 2.7 negative prompt

Use with the helper’s `--negative-prompt` option:

```text
flicker, jitter, abrupt camera movement, reverse motion at the cut, blur, compression
artifacts, distorted architecture, warped objects, duplicated subjects, text, captions,
logo, signature, watermark
```

## Native 9:16 additions

Prepend to each portrait prompt:

```text
Vertical 9:16 portrait composition designed natively for a phone. Keep the focal subject
centred horizontally around 45% of frame height, with intentional background space above
and below. Do not crop a landscape composition.
```

The portrait chain must use its own portrait stills, rendered boundary frames, and
connectors. Do not mix desktop boundaries into portrait requests.

## Section copy

- `eyebrow`: 2–4 words; signals the stage or value.
- `title`: 3–7 words; one strong narrative beat.
- `body`: one plain-spoken sentence from the visitor’s perspective.
- `tags`: 0–3 proof chips, not generic adjectives.
- Final scene: payoff plus one clear CTA.

Keep important claims and CTAs in live HTML, never baked into generated media.
