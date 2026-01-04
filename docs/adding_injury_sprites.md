# Adding Injury Sprites

Quick reference for adding new injury overlays to the sprite system.

## The Basics

When a cat has an injury, the game can overlay a sprite on top of their normal appearance. This is controlled by the gore setting (players can turn it off if they want).

**Three files you care about:**
- `sprites/injuries.png` - the actual sprite sheet
- `scripts/cat/sprites.py` - the `injuries_data` list that maps names to grid positions
- `scripts/utility.py` - rendering code (shouldn't need to touch this)

## How It Works

The game looks at a cat's injuries (stored as dictionary keys like `"broken bone"` or `"severe burn"`), then checks if there's a matching sprite name in `injuries_data`. If found, it overlays the sprite from the corresponding position in `injuries.png`.

**Important:** The injury name must match EXACTLY - spaces, hyphens, capitalization all matter.

## Adding a New Injury Sprite

### Step 1: Find the injury name

Check what the game actually calls the injury. You can:
- Look in `resources/dicts/conditions/injuries.json` or `illnesses.json`
- Enable the ID display setting and check a cat's profile in-game
- Add a debug print in the code: `print(cat.injuries.keys())`

### Step 2: Pick a spot in the grid

Edit `injuries_data` in `scripts/cat/sprites.py`:

```python
injuries_data = [
    ["pregnant"],                    # Row 0, Col 0
    ["broken bone", "claw-wound"],   # Row 1, Col 0 and Col 1
    ["torn pelt"],                   # Row 2, Col 0
]
```

The position in this list determines where in `injuries.png` the system will look. Each row is a list, each item in that list is a column.

### Step 3: Draw the sprites

Open `sprites/injuries.png`. It's currently 1800×2450 pixels (3 columns × 7 rows, expanded to handle lots of injuries).

**Grid math:**
- Each column: 600 pixels wide
- Each row: 350 pixels tall (standard sprite strip height)
- Each row contains 21 poses side-by-side (50px each + 10px padding)

If you put `"broken bone"` at Row 1, Col 0, draw your sprites starting at:
- X: 0 pixels (column 0)
- Y: 350 pixels (row 1)

Draw all 21 cat poses horizontally. The system auto-splits them.

### Step 4: Test it

Run the game, give a cat that injury (or wait for it naturally), and check if the overlay appears.

## Location-Specific Injuries

Some injuries can occur in different body locations. Example: burns can be on paws, tail, belly, etc.

**The predetermined scar system handles this.** When an injury is applied and it maps to a scar (like "BURNTAIL"), the game stores that specific scar name. Later, when rendering the injury overlay, it uses that stored value instead of the generic injury name.

So you can do this:

```python
injuries_data = [
    ["BURNPAWS", "BURNTAIL", "BURNBELLY", "BRIGHTHEART"],
]
```

Each gets its own sprite in the grid. When a cat gets a "severe burn" injury that's on their tail, the code looks for the "BURNTAIL" sprite instead of "severe burn".

**Setting up the mapping:** This happens in `scripts/events_module/short/scar_events.py` - the injury-to-scar connection is already there, you just need to draw the sprites.

## Special Cases

### Aliasing

Some conditions share sprites to save space. Example: "pregnant" and "recovering from birth" use the same sprite.

This is handled in `utility.py` with an alias map - you don't need to draw duplicates.

### Missing Sprites

If a sprite isn't found, the system just skips it (no crash). This means you can add injury names to `injuries_data` as placeholders and draw them later.

### Generic vs Specific

You can mix approaches:
- Draw location-specific sprites for important stuff (burns, major wounds)
- Draw one generic sprite for simple conditions (blood loss, shock)

Just add what you want to `injuries_data` and the system will use whatever you've drawn.

## Current Sheet Layout

As of now, `injuries.png` has capacity for 84 injury types (3 cols × 28 rows, though we've only allocated 3×7 so far). Row 0 Col 0 has the pregnancy sprite.

If you need more space, just expand the PNG height and update the grid math above.

## Quick Checklist

- [ ] Find exact injury name from game files
- [ ] Add name to `injuries_data` at desired row/col
- [ ] Calculate pixel position (col × 600, row × 350)
- [ ] Draw 21 poses horizontally starting at that position
- [ ] Save injuries.png
- [ ] Test in-game

That's it. The system handles everything else automatically.
