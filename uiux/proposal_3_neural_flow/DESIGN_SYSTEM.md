# Proposal 3: Neural Flow

## Philosophy
"Neural Flow" visualizes the debate as a **directed graph of thought**. It moves away from the linear chat log entirely. Conversations branches, merge, and evolve visually. It borrows from modern unparalleled SaaS tools like Miro, Figma, and React Flow. It emphasizes **connection**, **context**, and **overview**.

## Design Tokens

### Colors
- **Background**: `bg-gray-50` via `bg-white` pattern dots.
- **Nodes**: Glassmorphism white panels with colorful borders.
- **Connectors**:
  - `stroke-slate-300` (Neutral)
  - `stroke-violet-400` (Argument)
  - `stroke-rose-400` (Counter-argument)
- **Status**:
  - Running: Pulse animations.
  - Complete: Solid lines.

### Typography
- **Primary**: `font-sans` (SF Pro / Inter).
- **Weights**: Heavy use of Medium (500) and Semibold (600).
- **Size**: Small, dense text (13px/14px) to fit content in nodes.

### Layout Principles
- **Infinite Canvas**: The main view is pan/zoom capable.
- **Node-Based**:
  - The System prompt is the Root Node.
  - Orthodox and Heretic are sibling nodes branching from the Root.
  - Skeptic is a child node connecting both.
  - Judge is the terminal node.
- **Minimap**: Bottom-right navigation aid.

## Key Components

### 1. The "Thought Graph" (Debate View)
Instead of scrolling down, the user sees a tree structure growing live.
- **Nodes**: Represent individual messages or argument blocks.
- **Edges**: Represent the flow of "Rebuttal" or "Support".
- **Interaction**: Clicking a node expands a side panel with full text, raw JSON, and metadata.

### 2. "Context Sidebar"
A collapsible right panel that holds the linear detail when a node is selected.
- Shows the full markdown content.
- Shows distinct "Evidence" chips extracted from the text.

### 3. "Live Pipeline" Status
Top bar shows the pipeline stages as a breadcrumb or stepper.
`[ Dataset ] -> [ Case 1/20 ] -> [ Debate ] -> [ Judging ] -> [ Scoring ]`
Active stage glows.

## UX Flow
1. **Overview**: User sees the whole dataset run as a grid of mini-graphs.
2. **Deep Dive**: User zooms into one Case Graph.
3. **Playback**: A "scrubber" at the bottom allows the user to replay the graph construction time-lapse style.
4. **Insight**: Critical failures or low scores highlight specific nodes in Red, instantly showing *where* the logic broke.

## Why this works for Galileo?
Complex debates are hard to follow linearly. A graph accurately represents the *structure* of a debate (claim -> counter-claim -> synthesis). It sets the tool apart as a "Debugging" platform, not just a chat viewer.
