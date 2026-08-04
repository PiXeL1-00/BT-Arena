# Proposal 7: Holo-Stratum

## Philosophy
"Holo-Stratum" treats the debate arena as a **3D Command Center**. Information is not flat; it exists in layers of depth. The user is an "Operator" overseeing a complex system. It leverages **spatial interfaces**, **depth of field**, and **holographic transparencies** to separate signal from noise.

## Design Tokens

### Colors
- **Void (Background)**: `bg-slate-950` (#020617) -> Deep space.
- **Grid Lines**: `border-cyan-500/20` -> Structural integrity.
- **Hologram Primary**: `text-cyan-400` (#22d3ee) -> Active data.
- **Alert/Critical**: `text-rose-500` (#f43f5e) -> System warnings.
- **Success/Stable**: `text-emerald-400` (#34d399) -> Optimal performance.

### Typography
- **Headings**: `font-rajdhani` (Rajdhani) -> Technical, squared, futuristic.
- **Data/UI**: `font-share-tech-mono` (Share Tech Mono) -> Terminal-like, monospaced.
- **Body**: `font-exo` (Exo 2) -> Readable but tech-forward.

### Visual Effects
- **Glassmorphism**: Heavy use of `backdrop-blur-md` with `bg-slate-900/40`.
- **Gliw**: `drop-shadow-[0_0_15px_rgba(34,211,238,0.5)]` for active elements.
- **Scanlines**: CSS overlay for CRT/Hologram texture.
- **Tilt**: UI cards respond to mouse movement (parallax).

## Interaction Model
- **3D Navigation**: The debate flow is a spiral or a z-axis tunnel.
- **Focus**: Clicking an argument brings it "forward" in Z-space, blurring the background.
- **Connections**: Visible laser lines connect related arguments across the 3D space.

## Key Components
1.  **The Holo-Deck**: Central view where arguments float as cards.
2.  **The HUD (Heads-Up Display)**: Peripheral vision data stats (System Load, Token Rate).
3.  **Depth Slider**: A control to "slice" through the debate timeline physically.
