# Proposal 2: Agora Classic

## Philosophy
"Agora Classic" treats the debate as an **intellectual pursuit**. The design inspiration comes from academia, legal manuscripts, and classical forums. It emphasizes **readability**, **structure**, and **calmness**. It removes the "tech" noise to focus purely on the arguments.

## Design Tokens

### Colors
- **Background**: `bg-[#F9F7F1]` (Warm Parchment) or White.
- **Surface**: `bg-white` with subtle warmth.
- **Text**: `text-slate-900` (Charcoal) for high contrast.
- **Accents**: 
  - `text-blue-900` (Navy) -> Orthodox/Authority.
  - `text-red-900` (Crimson) -> Heretic/Challenge.
  - `text-amber-700` (Gold) -> Skeptic/Query.
- **Borders**: `border-stone-200` (Double borders for elegance).

### Typography
- **Headings**: `font-serif` (Playfair Display, Merriweather) -> Editorial authority.
- **Body**: `font-sans` (Source Sans Pro, Lato) -> Clean legibility.
- **Quotes**: `font-serif-italic` -> For evidence and citations.

### Layout Principles
- **Document-Centric**: The debate view looks like a generated paper or transcript.
- **Skeuomorphism lite**: Subtle paper textures, shadow depth that feels like cardstock.
- **Margin Notes**: Evidence and comments appear in the margins (like a textbook) rather than a separate tech sidebar.

## Key Components

### 1. The "Transcript" (Debate View)
A single, centered document column.
- **Agent Avatars**: Classical busts or engraved icons instead of robots.
- **Bubbles**: No "chat bubbles". Instead, distinct paragraphs with hanging indents and clear attribution headers.
- **Typography**: Heavy use of italics, bold, and small caps for hierarchy.

### 2. "Margin" Evidence
When an agent cites `[1]`, the reference appears partly in the comfortable right margin, expandable on click. This mimics academic footnotes/sidenotes.

### 3. "The Gavel" (Scoring)
A sliding scale UI that looks like a physical slider or balance scale. 
- "Correctness" is a balance beam.
- "Confidence" is a filled fountain pen ink meter.

## UX Flow
1. **Library**: Users browse datasets visually like book covers on a shelf.
2. **Session**: The debate unfolds page-by-page. No "autoscroll" jitter; smooth paging.
3. **Verdict**: The final judgment is presented as a stamped, sealed document.

## Why this works for Galileo?
Galileo is about **truth** and **logic**. This aesthetic reinforces the seriousness of the evaluation, separating it from "just another chatbot" interface.
