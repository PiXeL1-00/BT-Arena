# Proposal 1: Quantum Nexus

## Philosophy
"Quantum Nexus" is designed for the **high-frequency power user**. It visualizes the debate as a high-stakes, real-time data stream. The interface borrows from financial terminals, sci-fi HUDs, and cyberpunk aesthetics. It emphasizes **density**, **immediacy**, and **machine precision**.

## Design Tokens

### Colors
- **Background**: `bg-black` (#000000) or `bg-slate-950`
- **Surface**: `bg-slate-900/80` (Glass)
- **Primary (Orthodox)**: `text-cyan-400` (#00f3ff) -> Reliable, cold logic.
- **Secondary (Heretic)**: `text-fuchsia-500` (#d946ef) -> Disruptive, creative.
- **Tertiary (Skeptic)**: `text-amber-400` (#fbbf24) -> Caution, warning.
- **Quaternary (Judge)**: `text-emerald-400` (#34d399) -> Verdict, truth.
- **Borders**: `border-slate-800` with glow effects `shadow-[0_0_10px_rgba(0,243,255,0.2)]`

### Typography
- **Headers**: `font-orbitron` (Orbitron) -> Futuristic, angular.
- **Body**: `font-inter` (Inter) -> Clean readability.
- **Code/Data**: `font-mono` (JetBrains Mono) -> Technical precision.

### Layout Principles
- **Grid-Heavy**: Strict bento-box grid layout.
- **Sticky HUD**: Critical metrics (Pass Rate, Tokens/Sec) always visible in a top or side ticker.
- **Terminal Aesthetics**: Scanlines, typing effects, blinking cursors.

## Key Components

### 1. The "Stream Deck" (Debate View)
Instead of a simple chat bubble list, the debate is a **waterfall log**.
- **Orthodox**: Aligned Left, Cyan borders.
- **Heretic**: Aligned Right, Fuchsia borders.
- **Skeptic**: Centered, Amber warning alerts.
- **Judge**: Modal overlay or bottom pinned "Verdict" panel.

### 2. "Holographic" Evidence Cards
Evidence cited by agents appears as floating "cards" in a dedicated right-hand sidebar.
- Hovering an evidence key `[E1]` in the chat draws a connection line to the card in the sidebar.

### 3. "Synapse" Score Visualization
A radar chart (spider web) for the 4 scoring axes:
- Correctness
- Grounding
- Calibration
- Falsifiability
Animated and updating in real-time as the Judge evaluates.

## UX Flow
1. **Command Center**: User selects a dataset and models via a "Mission Config" panel.
2. **Launch**: The view shifts to "Tactical Mode" (The Debate).
3. **Execution**: Text streams in with typewriter effects.
4. **Debrief**: Post-run summary looks like a mission report (Stats, Medals, Efficiency).
