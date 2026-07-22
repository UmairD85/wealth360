---
name: scroll-world
description: >
  Build an immersive scroll-scrubbed “fly through the world” landing page for any
  industry or brand using Kie.ai. Generate cohesive scene images and frame-locked
  videos through Kie.ai, then wire them into a portable framework-agnostic scrub
  engine so scrolling drives one continuous cinematic journey with no visible cuts.
  Use when the user wants a 3D world, diorama landing page, scroll cinematic,
  browse-through-the-industry experience, or a business transformed into a scrollable
  visual world.
---

# Scroll World

Create a landing page where scrolling controls a pre-rendered camera flight. Generate
the media with Kie.ai; keep the browser layer deliberately simple. The page scrubs video
time—it does not render the 3D world in real time.

Produce:

1. `N` cohesive Kie.ai scene images.
2. A frame-locked video chain using one approved model.
3. Web-optimized MP4/WebP assets.
4. A responsive page powered by `references/scrub-engine.js`.

## Non-negotiable rules

- Make every seam frame-identical. The next clip must begin from the previous clip’s
  actual rendered last frame, or a connector must begin/end on frames extracted from
  the adjacent rendered clips.
- Maintain velocity as well as position. Never reverse camera direction across a seam.
- Use one video model for a complete chain. A provider/model change can shift colour,
  grain, motion, or geometry even when the boundary frames match.
- Generate a native 9:16 chain when the user buys a mobile version. Do not silently call
  a centre-crop “mobile optimized.”
- Never put `KIE_API_KEY` in chat, prompts, source code, frontend JavaScript, logs, or a
  committed `.env` file.
- Obtain approval after the calibrated cost estimate and before paid generation.

## Step 0 — Bootstrap and authenticate

Use the bundled client:

```bash
KIE=./scripts/kie_api.py
python3 "$KIE" self-test
python3 "$KIE" credits
```

Treat [Kie.ai's official documentation](https://docs.kie.ai/) and the linked
model-specific pages in `references/kie-api.md` as the API contract. Do not invent a
runner, endpoint, or model identifier from memory. In particular, use the unified
Market endpoints implemented by the bundled client; do not replace this workflow with
an unrelated Veo-only runner unless the user deliberately selects Veo and its current
model-specific schema has been implemented and tested.

The client reads the key only from `KIE_API_KEY`. Ask the user to configure the variable
outside the conversation. Safe interactive examples:

```bash
# macOS/Linux — input is hidden and not placed in the command itself
read -s KIE_API_KEY && export KIE_API_KEY

# PowerShell 7+
$env:KIE_API_KEY = Read-Host "Kie.ai API key" -MaskInput
```

Do not ask the user to paste the key. Do not test paid generation until `credits`
succeeds. Also require:

- Python 3.10+ for `scripts/kie_api.py`.
- `ffmpeg` and `ffprobe` for boundary-frame extraction and web encoding.
- PIL or `cwebp` only when background knockout or WebP conversion is needed.

Read `references/kie-api.md` when authentication, task states, uploads, model payloads,
or expiring URLs need diagnosis.

For Codex cloud, enable agent internet access and allow `api.kie.ai` and
`kieai.redpandaai.co` with GET, POST, HEAD, and OPTIONS. A CONNECT 403 is a cloud
network-policy failure before Kie.ai authentication, not evidence of a bad API key.

## Step 1 — Interview and define the world

Ask only for decisions that cannot be safely inferred.

1. **Subject:** Ask openly: “What should this world be about? A business, a client, or
   any idea—a word or sentence is enough.” Capture the subject and one-line pitch.
2. **Brand:** Use a supplied brand kit, inspect a public brand URL, or propose a system.
   Record the name, tone, 4–6 named colours, and one background colour. Kie.ai has no
   assumed brand-kit import in this workflow.
3. **Art direction:** Default to a soft matte clay diorama. Offer flat papercraft,
   glossy toy, claymation, neon miniature, or photoreal architectural. Freeze one style
   preamble and reuse it byte-for-byte in all still prompts.
4. **Journey:** Propose 5–7 ordered scenes derived from the subject’s real value chain.
   Each needs `id`, `subject`, `eyebrow`, `title`, `body`, and 0–3 proof tags. The last
   scene usually holds the payoff and CTA.
5. **Camera architecture:** Recommend A for realistic spaces and B for miniature worlds.
   See Step 4.
6. **Mobile:** Always ask “Desktop only” or “Desktop + native 9:16.” Explain that a
   second chain roughly doubles video generations.
7. **Render approval:** Calibrate credits with one image and one short preview clip,
   then estimate the total before starting the batch.

### Agreed Kie.ai model roster

| Purpose | Alias | Kie.ai model | Use |
|---|---|---|---|
| Final chain | `standard` | `bytedance/seedance-2` | Default final renders; first/last-frame capable |
| Fast preview | `fast` | `bytedance/seedance-2-fast` | Faster journey and prompt validation |
| Cheap previz | `preview` | `bytedance/seedance-2-mini` | Low-cost seam and pacing test |
| Continuation/fallback | `continuation` | `wan/2-7-image-to-video` | First/last frames, 1080p, and video continuation |
| Standard still | `standard` | `gpt-image-2-text-to-image` | Default scene images |
| Character still | `character` | `nano-banana-2` | Character-heavy or playful scenes |

Treat the aliases as payload adapters implemented in `scripts/kie_api.py`. Do not pass an
unlisted model until its current Kie.ai schema has been checked and a payload adapter has
been added. A model is eligible for a chain only if it can hold the required first/last
frames.

### Credit calibration

Do not guess from public pricing. Plans and model costs change.

1. Record `python3 "$KIE" credits`.
2. Generate one representative still and one 5-second preview video.
3. Read `creditsConsumed` from their metadata/task records.
4. Estimate:
   - Architecture A: `N images + N videos`.
   - Architecture B: `N images + N dives + (N-1) connectors`.
   - Native mobile: add another complete video chain.
   - Add 15–25% re-roll headroom.
5. Warn when the estimate would use more than 70% of the available balance.
6. Get explicit approval before the full batch.

## Step 2 — Generate scene images through Kie.ai

Write one prompt file per section using `references/prompts.md`. Reuse the identical
style preamble. Default to GPT Image 2; use Nano Banana 2 consistently for the whole set
when character continuity is central.

```bash
python3 "$KIE" image \
  --model standard \
  --prompt-file "$WORK/still_farm.txt" \
  --aspect 3:2 \
  --out "$WORK/still_farm.png" \
  --meta "$WORK/still_farm.json"
```

Generate no more than three stills concurrently. Kie.ai tasks are asynchronous; the
helper polls with backoff and downloads the result immediately because returned URLs are
temporary.

Review the full still set before video generation:

- Same camera height, lens feel, lighting, material language, palette, and background.
- No unwanted text, letters, numbers, logos, watermarks, or duplicate objects.
- Focal subjects remain centred and survive 16:9 composition.
- Re-roll only the off-style scene.

For floating islands, use `references/knockout.py` after approval. Preserve the original
solid-background PNG because it is the cleanest first frame for video generation.

## Step 3 — Select the camera architecture

### A. Continuous forward journey — recommended for realistic walkthroughs

Generate clips sequentially.

- Leg 0 starts from scene 0’s approved still.
- Extract the actual last frame of leg 0.
- Use that extracted frame as leg 1’s first frame.
- Repeat through the final scene.
- Do not provide a last frame unless a specific arrival must be locked. An unrelated
  wide destination frame can force the camera to pull backward and create stutter.
- End every leg with one second of slow forward drift; start the next by continuing that
  same drift.

Architecture A costs `N` video generations and usually feels most natural. Wan 2.7 video
continuation may be used only when the entire chain is intentionally built on Wan; do not
switch one middle leg casually.

### B. Dive plus aerial connector — for miniature/diorama worlds

- Generate every dive from its scene still.
- Extract the first and last frames from each rendered dive.
- Generate connector `i` from dive `i`’s actual last frame to dive `i+1`’s actual first
  frame.
- Keep the connector’s pull-out/fly-over motion intentional. This repeated direction
  change reads well for map-like islands but like rewind in grounded spaces.

Architecture B costs `2N-1` video generations but creates the signature “world map” feel.

## Step 4 — Generate frame-locked video

The helper uploads local frames to Kie.ai’s temporary file service, creates the task,
polls the unified task endpoint, downloads the result, and saves metadata.

First-frame leg/dive:

```bash
python3 "$KIE" video \
  --model standard \
  --prompt-file "$WORK/leg_farm.txt" \
  --first-frame "$WORK/still_farm.png" \
  --aspect 16:9 --resolution 720p --duration 5 \
  --out "$WORK/leg_farm.mp4" \
  --meta "$WORK/leg_farm.json"
```

Locked connector:

```bash
python3 "$KIE" video \
  --model standard \
  --prompt-file "$WORK/conn_1.txt" \
  --first-frame "$WORK/last_farm.png" \
  --last-frame "$WORK/first_kitchen.png" \
  --aspect 16:9 --resolution 720p --duration 5 \
  --out "$WORK/conn_1.mp4" \
  --meta "$WORK/conn_1.json"
```

Use `references/pipeline.md` for complete architecture A/B, mobile, resume, and encoding
commands.

### Paid-task safety

- The helper deliberately does not auto-retry task creation. A network timeout can be
  ambiguous; blindly retrying may create a second charged task.
- On a create timeout, inspect the Kie.ai dashboard or task history before resubmitting.
- Status checks, credit checks, and safe read operations do retry with exponential
  backoff on rate limits and transient server errors.
- Keep each task’s metadata JSON until the project is complete.

## Step 5 — Inspect every seam before continuing

Never generate downstream clips from an unreviewed boundary.

For each clip:

1. Confirm the opening frame matches the supplied first frame.
2. Extract a frame near the true end (`-sseof -0.12` to `-0.20`).
3. Confirm the camera has settled into the promised handoff motion.
4. Check geometry, lighting, colour, and grain for drift.
5. Re-roll the current clip before using its bad last frame downstream.

Exact coordinates without matching motion still look like a cut. Position continuity,
velocity continuity, and render-character continuity are all required.

## Step 6 — Encode for scroll scrubbing

Do not upscale the source. Encode native resolution with frequent keyframes; scrub
performance depends more on seek distance than on normal playback quality.

Desktop baseline:

```bash
ffmpeg -v error -y -i input.mp4 -an \
  -vf "unsharp=5:5:0.7:5:5:0.0" \
  -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p \
  -g 8 -keyint_min 8 -sc_threshold 0 -movflags +faststart output.mp4
```

Mobile baseline for the native 9:16 chain:

```bash
ffmpeg -v error -y -i input-portrait.mp4 -an \
  -vf "scale=720:-2,unsharp=5:5:0.5:5:5:0.0" \
  -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p \
  -g 4 -keyint_min 4 -sc_threshold 0 -movflags +faststart output-m.mp4
```

If phone scrubbing still stutters, try `-g 2`; use `-g 1` only when instant seeking is
worth the larger file. Keep audio disabled because scroll time is non-linear.

## Step 7 — Wire the portable engine

Copy `references/scrub-engine.js` into the project and initialize it with approved
assets. Example:

```js
createScrollWorld(document.querySelector('#world'), {
  sections: [
    {
      label: '01', eyebrow: 'ORIGIN', title: 'Where it begins',
      body: 'One sentence of visitor-facing copy.', tags: ['Proof'],
      still: 'assets/farm.webp', clip: 'assets/vid/farm.mp4',
      stillMobile: 'assets/farm-m.webp', clipMobile: 'assets/vid/farm-m.mp4',
      scroll: 1.1
    }
  ],
  connectors: ['assets/vid/conn1.mp4'],
  connectorsMobile: ['assets/vid/conn1-m.mp4'],
  crossfade: 0.08,
  brand: { name: 'Brand', accent: '#C88A5A', bg: '#F5EDE0', ink: '#27222B' }
});
```

Architecture A uses `connectors: []`. Architecture B requires exactly `N-1` connectors
in journey order.

## Step 8 — Native mobile chain

When approved, generate a complete parallel 9:16 chain:

1. Create portrait scene stills or portrait first-frame canvases; do not feed a 3:2
   canvas and hope the model composes it correctly.
2. Generate every portrait leg/dive and connector using `--aspect 9:16`.
3. Extract boundaries from portrait renders only.
4. Encode them to the `-m.mp4` variants and create matching `stillMobile` posters.
5. Never mix portrait and centre-cropped landscape clips in one chain.

A centre-cropped 16:9 fallback may be offered only after the user approves the quality
and cost compromise.

## Step 9 — Final QA

### Visual and narrative

- Play the whole journey normally once, then scrub slowly and aggressively.
- Check every seam for pops, direction reversals, subject morphing, brightness shifts,
  duplicated objects, and half-finished camera moves.
- Ensure copy stays brief and the CTA arrives at the narrative payoff.

### Performance and accessibility

- Test desktop and a real phone or equivalent constrained viewport.
- Keep the first poster local and small; lazy-load later clips.
- Confirm no horizontal overflow, console errors, or layout shift.
- Respect `prefers-reduced-motion` with a still-image narrative fallback.
- Provide keyboard-reachable navigation/CTA controls and readable contrast.
- Keep critical meaning outside the video; decorative video needs no redundant narration.

### API and asset hygiene

- Confirm no key appears in the project, metadata, shell output, or client bundle.
- Download all results immediately; do not treat Kie.ai temporary URLs as production
  assets.
- Store final media in the site/project, not in Kie.ai’s temporary upload service.
- Retain task IDs and `creditsConsumed` records for cost reconciliation.

## Failure handling

- **401:** Key missing, invalid, or expired. Reconfigure `KIE_API_KEY`; never reveal it.
- **402 / insufficient credits:** Stop the batch. Preserve completed files and resume
  after approval/top-up.
- **429:** Reduce concurrency to 2–3 and let safe polling retry with backoff.
- **Create timeout:** Do not blindly resubmit. Check task history first.
- **Task `fail`:** Read `failCode` and `failMsg`; re-run only that clip after correcting
  the cause.
- **Expired result:** Query the task again; if the source is no longer retrievable, re-run
  only after explaining the additional cost.
- **Visible seam:** Re-extract boundaries from rendered clips. Never use the original
  still as a substitute for a rendered boundary frame.
- **Model drift:** Re-render the affected chain segment using the chain’s original model.
- **Weak mobile:** Render the complete native 9:16 chain; do not conceal a crop compromise.

## Bundled resources

- `scripts/kie_api.py` — secure Kie.ai credits, upload, generation, polling, download,
  dry-run, and offline self-test helper.
- `references/kie-api.md` — endpoint/model/security notes and official documentation.
- `references/pipeline.md` — end-to-end commands for both camera architectures and mobile.
- `references/prompts.md` — intake, style, scene, leg, dive, connector, and copy templates.
- `references/scrub-engine.js` — framework-agnostic scroll-video engine.
- `references/index-template.html` — minimal integration shell.
- `references/knockout.py` — optional border-connected background knockout.
