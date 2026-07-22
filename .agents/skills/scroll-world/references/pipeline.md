# Kie.ai production pipeline

Use this reference after the user approves the journey, art direction, mobile scope, and
calibrated credit estimate. All commands are Bash 3.2-safe unless marked PowerShell.

## 1. Setup

Run from the skill directory or set `SKILL_DIR` explicitly.

```bash
SKILL_DIR=/path/to/scroll-world
KIE="$SKILL_DIR/scripts/kie_api.py"
WORK=/tmp/scroll-world
ASSETS=./assets
NAMES="farm kitchen shop delivery plaza finale"

mkdir -p "$WORK" "$ASSETS/vid"
python3 "$KIE" self-test
python3 "$KIE" credits | tee "$WORK/credits-before.json"
```

`KIE_API_KEY` must already exist in the environment. Never put it in this file or the
project. The helper accepts these video aliases:

```text
standard     bytedance/seedance-2       final chain
fast         bytedance/seedance-2-fast  fast preview
preview      bytedance/seedance-2-mini  cheap previz
continuation wan/2-7-image-to-video     1080p continuation/fallback
```

Choose one model for a complete chain:

```bash
VMODEL=standard
```

## 2. Dry-run payloads first

Dry-run validates files and prints the Kie.ai request without reading a key or creating a
paid task.

```bash
python3 "$KIE" --dry-run image \
  --model standard --prompt-file "$WORK/still_farm.txt" \
  --aspect 3:2 --out "$WORK/still_farm.png"

python3 "$KIE" --dry-run video \
  --model "$VMODEL" --prompt-file "$WORK/leg_farm.txt" \
  --first-frame "$WORK/still_farm.png" \
  --aspect 16:9 --resolution 720p --duration 5 \
  --out "$WORK/leg_farm.mp4"
```

## 3. Calibrate cost

Generate one representative image and one short preview video before the full batch:

```bash
python3 "$KIE" image \
  --model standard --prompt-file "$WORK/still_farm.txt" \
  --aspect 3:2 --out "$WORK/still_farm.png" \
  --meta "$WORK/still_farm.json"

python3 "$KIE" video \
  --model preview --prompt-file "$WORK/leg_farm.txt" \
  --first-frame "$WORK/still_farm.png" \
  --aspect 16:9 --resolution 720p --duration 5 \
  --out "$WORK/preview_farm.mp4" \
  --meta "$WORK/preview_farm.json"

python3 "$KIE" credits | tee "$WORK/credits-after-calibration.json"
```

Read `creditsConsumed` from both metadata files. Extrapolate for the selected architecture,
mobile chain, and re-roll allowance. Continue only after approval.

## 4. Generate the scene stills

Create `$WORK/still_<name>.txt` files using `prompts.md`.

```bash
gen_still() {
  n="$1"
  [ -s "$WORK/still_$n.png" ] && { echo "still $n exists"; return; }
  python3 "$KIE" image \
    --model standard --prompt-file "$WORK/still_$n.txt" \
    --aspect 3:2 --out "$WORK/still_$n.png" \
    --meta "$WORK/still_$n.json"
}

# Batch at most three to avoid rate-limit pressure.
count=0
for n in $NAMES; do
  gen_still "$n" > "$WORK/still_$n.log" 2>&1 &
  count=$((count+1))
  [ $((count % 3)) -eq 0 ] && wait
done
wait
```

Review the full image set. Re-roll only off-style images. For character-heavy sets, use
`--model character` consistently for every scene.

Optional site poster conversion:

```bash
for n in $NAMES; do
  cwebp -quiet -q 84 -resize 1800 0 \
    "$WORK/still_$n.png" -o "$ASSETS/$n.webp"
done
```

## 5A. Architecture A — continuous forward chain

Write `$WORK/leg_<name>.txt` prompt files. Generate sequentially because each leg depends
on the previous leg’s rendered final frame.

```bash
prev_frame=""
for n in $NAMES; do
  if [ -z "$prev_frame" ]; then
    first="$WORK/still_$n.png"
  else
    first="$prev_frame"
  fi

  if [ ! -s "$WORK/leg_$n.mp4" ]; then
    python3 "$KIE" video \
      --model "$VMODEL" --prompt-file "$WORK/leg_$n.txt" \
      --first-frame "$first" \
      --aspect 16:9 --resolution 720p --duration 5 \
      --out "$WORK/leg_$n.mp4" \
      --meta "$WORK/leg_$n.json"
  fi

  ffmpeg -v error -y -sseof -0.15 -i "$WORK/leg_$n.mp4" \
    -frames:v 1 -q:v 2 "$WORK/last_$n.png"

  # Inspect this frame before continuing. Re-roll now if the camera did not settle.
  prev_frame="$WORK/last_$n.png"
done
```

Set `connectors: []` in the engine. The section clips are `leg_<name>.mp4`.

### Optional Wan 2.7 continuation chain

Use only when the whole chain is Wan-based. Video continuation is mutually exclusive
with first/last frames in one request.

```bash
python3 "$KIE" video \
  --model continuation --prompt-file "$WORK/continue_kitchen.txt" \
  --first-clip "$WORK/leg_farm.mp4" \
  --resolution 1080p --duration 5 \
  --out "$WORK/leg_kitchen.mp4" \
  --meta "$WORK/leg_kitchen.json"
```

Do not insert one Wan continuation clip into a Seedance chain without explicitly accepting
the possible render-character shift.

## 5B. Architecture B — dives and connectors

### Generate dives

Write `$WORK/dive_<name>.txt` prompt files.

```bash
gen_dive() {
  n="$1"
  [ -s "$WORK/dive_$n.mp4" ] && { echo "dive $n exists"; return; }
  python3 "$KIE" video \
    --model "$VMODEL" --prompt-file "$WORK/dive_$n.txt" \
    --first-frame "$WORK/still_$n.png" \
    --aspect 16:9 --resolution 720p --duration 5 \
    --out "$WORK/dive_$n.mp4" \
    --meta "$WORK/dive_$n.json"
}

count=0
for n in $NAMES; do
  gen_dive "$n" > "$WORK/dive_$n.log" 2>&1 &
  count=$((count+1))
  [ $((count % 3)) -eq 0 ] && wait
done
wait
```

### Extract real boundaries

```bash
for n in $NAMES; do
  ffmpeg -v error -y -ss 0 -i "$WORK/dive_$n.mp4" \
    -frames:v 1 -q:v 2 "$WORK/first_$n.png"
  ffmpeg -v error -y -sseof -0.15 -i "$WORK/dive_$n.mp4" \
    -frames:v 1 -q:v 2 "$WORK/last_$n.png"
done
```

### Generate locked connectors

Write `$WORK/conn_1.txt` through `$WORK/conn_<N-1>.txt`.

```bash
set -- $NAMES
prev=""
i=0
for n in "$@"; do
  if [ -n "$prev" ]; then
    i=$((i+1))
    if [ ! -s "$WORK/conn_$i.mp4" ]; then
      python3 "$KIE" video \
        --model "$VMODEL" --prompt-file "$WORK/conn_$i.txt" \
        --first-frame "$WORK/last_$prev.png" \
        --last-frame "$WORK/first_$n.png" \
        --aspect 16:9 --resolution 720p --duration 5 \
        --out "$WORK/conn_$i.mp4" \
        --meta "$WORK/conn_$i.json"
    fi
  fi
  prev="$n"
done
```

Generate connectors sequentially during final production so each can be reviewed before
moving on. Parallel connector generation is acceptable only during cheap previz.

## 6. Encode for scrubbing

```bash
enc() {
  ffmpeg -v error -y -i "$1" -an \
    -vf "unsharp=5:5:0.7:5:5:0.0" \
    -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p \
    -g 8 -keyint_min 8 -sc_threshold 0 -movflags +faststart "$2"
  echo "encoded $2"
}

for n in $NAMES; do
  src="$WORK/dive_$n.mp4"
  [ -s "$WORK/leg_$n.mp4" ] && src="$WORK/leg_$n.mp4"
  enc "$src" "$ASSETS/vid/$n.mp4"
done

i=0
for f in "$WORK"/conn_*.mp4; do
  [ -e "$f" ] || continue
  i=$((i+1))
  enc "$f" "$ASSETS/vid/conn$i.mp4"
done
```

Do not upscale. Confirm source dimensions with `ffprobe`.

## 7. Native 9:16 mobile chain

When approved, repeat the chosen architecture using portrait prompts/canvases and
`--aspect 9:16`. Never reuse landscape boundary frames.

Example portrait generation:

```bash
python3 "$KIE" video \
  --model "$VMODEL" --prompt-file "$WORK/portrait_leg_farm.txt" \
  --first-frame "$WORK/portrait_still_farm.png" \
  --aspect 9:16 --resolution 720p --duration 5 \
  --out "$WORK/portrait_leg_farm.mp4" \
  --meta "$WORK/portrait_leg_farm.json"
```

Encode portrait assets:

```bash
enc_mobile() {
  ffmpeg -v error -y -i "$1" -an \
    -vf "scale=720:-2,unsharp=5:5:0.5:5:5:0.0" \
    -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p \
    -g 4 -keyint_min 4 -sc_threshold 0 -movflags +faststart "$2"
}
```

Extract each portrait clip’s first frame as `stillMobile`; it must match frame zero to
avoid a landscape-to-portrait flash.

## 8. Resume and failure rules

- Existing non-empty output files are checkpoints; skip them unless the user asks to
  regenerate.
- Keep every task metadata JSON. It contains the task ID, model, result URLs, and credits.
- On a task-create timeout, inspect Kie.ai task history before resubmitting; the helper
  intentionally does not auto-retry paid creation.
- On `401`, fix `KIE_API_KEY` outside chat.
- On insufficient credits, stop while preserving completed assets.
- On `429`, reduce concurrency to two and resume individual failures.
- Download results immediately. Kie.ai generation and upload URLs are temporary.
- Re-run only the failed or visually rejected asset; never restart a successful batch.

## 9. Final accounting

```bash
python3 "$KIE" credits | tee "$WORK/credits-final.json"
```

Compare starting/final balances and sum `creditsConsumed` from task metadata. Report the
actual cost and list any re-rolls.
