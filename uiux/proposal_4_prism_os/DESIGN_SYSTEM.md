# Proposal 4: Prism OS

## Philosophy
"Prism OS" is inspired by **Spatial Computing** (Apple Vision Pro) and modern high-end glassmorphism. It feels weightless, ethereal, and extremely polished. It relies on **translucency**, **depth**, and **vibrant background blurs** to create hierarchy.

## Design Tokens

### Colors
- **Background**: Complex, animated mesh gradients (Auroras) moving slowly.
- **Surface**: `bg-white/10` to `bg-white/40` with differing `backdrop-blur` levels (Glass).
- **Text**: `text-white` (primary) and `text-white/60` (secondary).
- **Accents**: 
  - Vivid gradients rather than solid colors.
  - Orthodox: Blue-Cyan gradient.
  - Heretic: Pink-Purple gradient.
- **Borders**: `border-white/20` (Subtle 1px rim light).

### Typography
- **Font**: `font-sans` (SF Pro Display / System UI).
- **Weights**: Light (300) to Medium (500). Avoid Bold heavy blocks.
- **Spacing**: Generous tracking and leading.

### Layout Principles
- **Floating Windows**: Panels float in space with soft diffuse shadows.
- **Micro-Interactions**: Hover states glow and lift (z-index shift).
- **Rounded Corners**: Heavy rounding (`rounded-3xl`).

## Key Components

### 1. The "Glass Slate" (Debate View)
The debate container is a large sheet of frosted glass.
- Agents are represented by glowing orbs or soft avatars.
- Messages are bubbles with a lighter glass tint.

### 2. "Floating" Controls
Buttons and toggles look like physical glass lozenges.

### 3. "Aurora" Visualization
The background isn't static. It shifts colors based on the debate sentiment.
- Conflict -> Red/Orange hues.
- Consensus -> Blue/Teal hues.

## UX Flow
1.  **Immersion**: The user feels like they are looking *through* a lens at the data.
2.  **Focus**: The background blurs out when a specific case is active.
3.  **Fluidity**: Transitions are slow, smooth curves.

## Why this works for Galileo?
It presents the AI as a "clean", advanced intelligence. It feels premium and futuristic without being "sci-fi/hacker" (unlike Quantum Nexus).
