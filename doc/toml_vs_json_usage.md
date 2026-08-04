
This handles cases where LLMs wrap JSON in markdown code fences or add preamble text.

#### 3. **Stored Content in `DebateMessage.content`**

AutoGen controller stores **clean JSON** in `DebateMessage.content`:

- **Proposals**: `json.dumps(parsed)` (line 52)
- **Revisions**: `json.dumps(parsed)` (line 75)
- **Judge**: Stores raw LLM text (may include markdown fences), then uses `parse_judge_output()` which tries TOML first, then JSON (line 493)

**Note**: Cross-examination and Dispute phases are conversational (no structured format), so they store raw text.

### TOML Usage

**None**. AutoGen controller does not use TOML for prompts or parsing.

---

## Comparison Table

| Phase | FSM Controller | AutoGen Controller |
|-------|----------------|-------------------|
| **Proposals** | Prompt: **TOML**<br>Stored: **JSON** | Prompt: **JSON**<br>Stored: **JSON** |
| **Cross-exam** | Prompt: **TOML**<br>Stored: **JSON** | Prompt: **Conversational**<br>Stored: **Raw text** |
| **Revisions** | Prompt: **TOML**<br>Stored: **JSON** | Prompt: **JSON**<br>Stored: **JSON** |
| **Dispute** | Prompt: **TOML**<br>Stored: **JSON** | Prompt: **Conversational**<br>Stored: **Raw text** |
| **Judge** | Prompt: **TOML**<br>Stored: **Raw text**<br>Parse: TOML→JSON | Prompt: **JSON**<br>Stored: **Raw text**<br>Parse: TOML→JSON |

---

## Key Design Decisions

### 1. **Why FSM Stores JSON Despite Requesting TOML?**

The frontend's `messageParser.ts` expects JSON for structured messages. The `detectMessageType()` function parses JSON to identify:
- Proposals: checks for `proposed_verdict` + `key_points`
- Revisions: checks for `final_proposed_verdict` + `confidence`

Storing JSON ensures consistent frontend rendering regardless of which controller generated the debate.

### 2. **Why Judge Uses Dual Parsing (TOML→JSON)?**

The `parse_judge_output()` function in `toml_serde.py` tries TOML first, then JSON:

def parse_judge_output(text: str) -> dict[str, Any]:
    """Parse judge output from TOML or JSON, with fallback."""
    # try TOML first
    try:
        return toml_to_dict(text)
    except ValueError:
        pass
    
    # JSON fallback
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # ... extraction and fallback logic
