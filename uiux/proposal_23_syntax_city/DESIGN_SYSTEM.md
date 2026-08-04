# Proposal 23: Syntax City (Pixel Symposium)

## Philosophy
"Syntax City" uses **Pixel Art** to create a charming, approachable, yet data-rich environment. It visualizes the debate as a "GameDev" office or a retro computer lab. It feels like an RPG game.

## Design Tokens

### Aesthetic
- **Theme**: 16-bit RPG / Stardew Valley / Isometric.
- **Vibe**: Cozy, retro, geeky.

### Colors
- **Palette**: Earth tones + vibrant terminal greens/ambers.
- **Font Color**: `text-green-400` (Terminal vibes) on dark backgrounds.

### Typography
- **Font**: `Press Start 2P` or `VT323`.
- **Style**: Aliased, blocky.

## Key Components

### 1. The Room
An isometric CSS grid representing a room.
- Orthodox sits at a blue terminal.
- Heretic sits at a red terminal.
- Skeptic walks between them.

### 2. Speech Bubbles
Pixel-perfect speech bubbles pop up over the characters' heads.
- Typing animations are character-by-character.

### 3. Inventory (Evidence)
Citations are stored in an "Inventory" bar at the bottom, looking like items (Scrolls, Books, Disks).

## UX Flow
1.  **Exploration**: The user sees the room. The little robots have idle animations (bobbing up/down).
2.  **Action**: When a message comes in, the robot raises its hand and a bubble appears.
3.  **Verdict**: The Judge (a giant Mainframe Computer on the wall) flashes its screen.

## Why this works?
It’s disarming. AI debate can feel cold and scary. Making it "cute" and "retro" makes it accessible while still conveying complex logic.
