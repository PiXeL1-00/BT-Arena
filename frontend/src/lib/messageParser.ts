import type {
  MessageType,
  ParsedMessage,
  StructuredMessage,
} from "./types";

/**
 * Extract TOML from code blocks
 */
function extractTomlFromText(text: string): string | null {
  // Check for ```toml code blocks (with or without newline after toml)
  const tomlBlockMatch = text.match(/```toml\s*([\s\S]*?)```/i);
  if (tomlBlockMatch) {
    return tomlBlockMatch[1].trim();
  }

  // Check for ``` code blocks (might be TOML)
  const codeBlockMatch = text.match(/```\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    const content = codeBlockMatch[1].trim();
    // Check if it looks like TOML (has key = value patterns)
    if (/^\w+\s*=/.test(content)) {
      return content;
    }
  }

  // Check if entire content is TOML (no code blocks)
  const trimmed = text.trim();
  if (/^\w+\s*=/.test(trimmed) && !trimmed.startsWith("{")) {
    return trimmed;
  }

  return null;
}

/**
 * Simple TOML to object converter (handles basic TOML syntax)
 * Handles quoted strings, arrays, numbers, and booleans
 */
function parseTomlToObject(toml: string): Record<string, unknown> | null {
  const result: Record<string, unknown> = {};
  let pos = 0;

  // Parse key = value pairs, handling quoted strings properly
  while (pos < toml.length) {
    // Skip whitespace
    while (pos < toml.length && /\s/.test(toml[pos])) pos++;
    if (pos >= toml.length) break;

    // Skip comments
    if (toml[pos] === '#') {
      while (pos < toml.length && toml[pos] !== '\n') pos++;
      continue;
    }

    // Match key
    const keyMatch = toml.slice(pos).match(/^(\w+)\s*=\s*/);
    if (!keyMatch) {
      pos++;
      continue;
    }

    const key = keyMatch[1];
    pos += keyMatch[0].length;

    // Parse value
    let value: unknown = null;

    // Check for quoted string
    if (toml[pos] === '"' || toml[pos] === "'") {
      const quote = toml[pos];
      pos++; // Skip opening quote
      const start = pos;

      // Find closing quote (handle escaped quotes)
      while (pos < toml.length) {
        if (toml[pos] === quote && toml[pos - 1] !== '\\') {
          break;
        }
        pos++;
      }

      value = toml.slice(start, pos);
      // Unescape
      value = (value as string).replace(/\\"/g, '"').replace(/\\'/g, "'").replace(/\\n/g, '\n');
      pos++; // Skip closing quote
    }
    // Check for array
    else if (toml[pos] === '[') {
      pos++; // Skip [
      const start = pos;
      let depth = 1;

      // Find matching ]
      while (pos < toml.length && depth > 0) {
        if (toml[pos] === '[') depth++;
        if (toml[pos] === ']') depth--;
        if (depth > 0) pos++;
      }

      const arrayStr = toml.slice(start, pos);
      try {
        value = JSON.parse('[' + arrayStr + ']');
      } catch {
        // Fallback: simple parsing
        value = arrayStr
          .split(',')
          .map(item => {
            const trimmed = item.trim();
            if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
              (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
              return trimmed.slice(1, -1);
            }
            return trimmed;
          });
      }
      pos++; // Skip ]
    }
    // Check for number or boolean
    else {
      // Find end of value (next newline or end of string)
      let end = pos;
      while (end < toml.length && toml[end] !== '\n' && toml[end] !== '#') {
        end++;
      }

      const valueStr = toml.slice(pos, end).trim();

      // Try parsing as number
      if (/^-?\d+\.?\d*$/.test(valueStr)) {
        value = valueStr.includes('.') ? parseFloat(valueStr) : parseInt(valueStr, 10);
      }
      // Try parsing as boolean
      else if (valueStr === 'true') {
        value = true;
      } else if (valueStr === 'false') {
        value = false;
      } else {
        // Default to string
        value = valueStr;
      }

      pos = end;
    }

    if (value !== null) {
      result[key] = value;
    }
  }

  return Object.keys(result).length > 0 ? result : null;
}

/**
 * Quick check if content looks like JSON or TOML
 */
function looksLikeJson(content: string): boolean {
  const trimmed = content.trim();
  // Check for JSON
  if (trimmed.startsWith("{")) return true;
  // Check for TOML (in code blocks or raw)
  if (extractTomlFromText(content)) return true;
  return false;
}

/**
 * Extract JSON from text (finds first { to matching })
 * Also handles truncated JSON by finding the best partial match
 */
function extractJsonFromText(text: string): string | null {
  const start = text.indexOf("{");
  if (start === -1) return null;

  // Find matching closing brace
  let depth = 0;
  let lastValidEnd = -1;
  for (let i = start; i < text.length; i++) {
    if (text[i] === "{") depth++;
    if (text[i] === "}") {
      depth--;
      if (depth === 0) {
        return text.substring(start, i + 1);
      }
      // Track the last position where we had a valid closing brace
      if (depth > 0) {
        lastValidEnd = i;
      }
    }
  }

  // If we have unclosed braces but found some structure, try to extract partial
  if (depth > 0 && lastValidEnd > start) {
    // Try to find a reasonable cutoff point
    // Look for the last complete field before truncation
    const partial = text.substring(start);
    // Try to find last complete key-value pair
    const lastComma = partial.lastIndexOf(',');
    const lastColon = partial.lastIndexOf(':');
    if (lastComma > lastColon && lastComma > 0) {
      // We have a complete field, try to close it
      const candidate = partial.substring(0, lastComma + 1) + '}';
      try {
        // Quick validation - does it have at least one complete field?
        if (candidate.includes(':') && candidate.split(':').length >= 2) {
          return candidate;
        }
      } catch {
        // Ignore
      }
    }
  }

  return null; // Unclosed object
}

/**
 * Check if JSON appears truncated (improved detection)
 */
function isTruncatedJson(content: string): boolean {
  const trimmed = content.trim();

  // If content is exactly 2000 chars, it's almost certainly truncated (backend limit)
  if (trimmed.length === 2000) return true;

  // If it parses successfully, it's not truncated
  try {
    JSON.parse(trimmed);
    return false;
  } catch {
    // Check if ends mid-structure
    const endsWithQuote = trimmed.endsWith('"') && !trimmed.endsWith('\\"');
    const endsWithComma = trimmed.endsWith(",");
    const endsWithBracket = trimmed.endsWith("[") || trimmed.endsWith("{");
    const hasUnclosedBrace =
      (trimmed.match(/\{/g) || []).length >
      (trimmed.match(/\}/g) || []).length;
    const hasUnclosedBracket =
      (trimmed.match(/\[/g) || []).length >
      (trimmed.match(/\]/g) || []).length;

    return (
      (endsWithQuote || endsWithComma || endsWithBracket || hasUnclosedBrace || hasUnclosedBracket) &&
      trimmed.length > 0 &&
      (trimmed.includes('"') || trimmed.includes("[") || trimmed.includes("{"))
    );
  }
}

/**
 * Detect message type using phase + field presence
 */
function detectMessageType(
  data: Record<string, unknown>,
  phase?: string
): MessageType {
  // Use phase to help disambiguate
  if (phase === "judge") {
    if (data.verdict && data.reasoning !== undefined) return "judge_decision";
  }

  if (phase === "dispute") {
    if (Array.isArray(data.questions) && data.questions.length > 0) {
      // Dispute questions don't have 'to' field
      const firstQ = data.questions[0] as Record<string, unknown>;
      if (!firstQ.to) return "dispute_questions";
    }
    if (Array.isArray(data.answers) && data.answers.length > 0) {
      return "dispute_answers";
    }
  }

  // JudgeDecision: has 'verdict' and 'reasoning' (check first as most specific)
  if (data.verdict && typeof data.reasoning === "string") {
    return "judge_decision";
  }

  // Revision: has 'final_proposed_verdict' and 'what_i_changed'
  if (
    data.final_proposed_verdict &&
    Array.isArray(data.what_i_changed)
  ) {
    return "revision";
  }

  // Proposal: has 'proposed_verdict' and 'key_points'
  if (data.proposed_verdict && Array.isArray(data.key_points)) {
    return "proposal";
  }

  // QuestionsMessage: has 'questions' array with 'to' field
  if (Array.isArray(data.questions) && data.questions.length > 0) {
    const firstQ = data.questions[0] as Record<string, unknown>;
    if (firstQ.to) return "questions";
    // Otherwise might be dispute_questions (handled above if phase is dispute)
  }

  // AnswersMessage: has 'answers' array
  if (Array.isArray(data.answers) && data.answers.length > 0) {
    return "answers";
  }

  return "unknown";
}

/**
 * Basic validation of parsed data structure
 */
function validateParsedData(
  data: Record<string, unknown>,
  type: MessageType
): boolean {
  switch (type) {
    case "proposal":
      return (
        typeof data.proposed_verdict === "string" &&
        Array.isArray(data.key_points)
      );
    case "judge_decision":
      return (
        typeof data.verdict === "string" &&
        typeof data.reasoning === "string"
      );
    case "revision":
      return (
        typeof data.final_proposed_verdict === "string" &&
        Array.isArray(data.what_i_changed)
      );
    case "questions":
    case "dispute_questions":
      return (
        Array.isArray(data.questions) && data.questions.length > 0
      );
    case "answers":
    case "dispute_answers":
      return Array.isArray(data.answers) && data.answers.length > 0;
    default:
      return false;
  }
}

/**
 * Find the last complete field in JSON (for truncation repair)
 */
function findLastCompleteField(content: string): number {
  let depth = 0;
  let inString = false;
  let escapeNext = false;
  let lastCompleteField = -1;

  for (let i = 0; i < content.length; i++) {
    const char = content[i];

    if (escapeNext) {
      escapeNext = false;
      continue;
    }

    if (char === '\\') {
      escapeNext = true;
      continue;
    }

    if (char === '"' && !escapeNext) {
      inString = !inString;
      continue;
    }

    if (!inString) {
      if (char === '{') depth++;
      if (char === '}') depth--;
      if (char === '[') depth++;
      if (char === ']') depth--;

      // If we're at the root object level (depth === 1) and find a comma,
      // that's the end of a complete field
      if (char === ',' && depth === 1) {
        lastCompleteField = i;
      }

      // If we find a closing brace at root level, we have complete JSON
      if (char === '}' && depth === 0) {
        return content.length; // Complete JSON
      }
    }
  }

  return lastCompleteField;
}

/**
 * Improved repair: remove incomplete fields instead of trying to close them
 */
function repairTruncatedJson(content: string): string | null {
  const trimmed = content.trim();
  if (!trimmed.startsWith("{")) return null;

  // Strategy 1: Find the last complete field and remove everything after
  const lastCompleteField = findLastCompleteField(trimmed);

  if (lastCompleteField > 0) {
    // We found a complete field, cut there and close the object
    const repaired = trimmed.substring(0, lastCompleteField + 1) + '}';
    // Validate it's parseable
    try {
      JSON.parse(repaired);
      return repaired;
    } catch {
      // Continue to fallback strategy
    }
  }

  // Strategy 2: Try to close incomplete structures (fallback)
  // Count open/close braces and brackets
  const openBraces = (trimmed.match(/\{/g) || []).length;
  const closeBraces = (trimmed.match(/\}/g) || []).length;
  const openBrackets = (trimmed.match(/\[/g) || []).length;
  const closeBrackets = (trimmed.match(/\]/g) || []).length;

  // If we have unclosed structures, try to close them
  let repaired = trimmed;

  // Close unclosed strings (find last quote and close it if needed)
  // Count quotes, but ignore escaped quotes
  let quoteCount = 0;
  let inEscape = false;
  for (let i = 0; i < repaired.length; i++) {
    if (inEscape) {
      inEscape = false;
      continue;
    }
    if (repaired[i] === '\\') {
      inEscape = true;
      continue;
    }
    if (repaired[i] === '"') {
      quoteCount++;
    }
  }

  if (quoteCount % 2 !== 0) {
    // Unclosed string - close it
    repaired = repaired + '"';
  }

  // Close unclosed arrays first (they're inside objects)
  for (let i = 0; i < openBrackets - closeBrackets; i++) {
    repaired += ']';
  }

  // Close unclosed objects
  for (let i = 0; i < openBraces - closeBraces; i++) {
    repaired += '}';
  }

  return repaired;
}

/**
 * Try to repair truncated JSON (wrapper for improved repair)
 */
function tryRepairTruncatedJson(content: string): string | null {
  return repairTruncatedJson(content);
}

/**
 * Main parser function with fixed logic
 */
export function parseStructuredMessage(
  content: string,
  phase?: string
): ParsedMessage | null {
  // Early exit: only parse if looks like JSON or TOML
  if (!looksLikeJson(content)) {
    return null;
  }

  let parsedData: Record<string, unknown> | null = null;
  let isTruncated = false;

  // 0. Try TOML parsing first (for judge output)
  const tomlContent = extractTomlFromText(content);
  if (tomlContent) {
    const tomlData = parseTomlToObject(tomlContent);
    if (tomlData) {
      parsedData = tomlData;
      isTruncated = false;
      // Continue to type detection and validation
    }
  }

  // 1. Try direct JSON parsing (if TOML didn't work)
  if (!parsedData) {
    try {
      parsedData = JSON.parse(content) as Record<string, unknown>;
      isTruncated = false;
    } catch {
      // 2. Try extracting JSON from text
      const extracted = extractJsonFromText(content);
      if (extracted) {
        try {
          parsedData = JSON.parse(extracted) as Record<string, unknown>;
          // Check if original was truncated
          isTruncated = isTruncatedJson(content);
        } catch {
          // 3. Try to repair truncated JSON
          const repaired = tryRepairTruncatedJson(content);
          if (repaired) {
            try {
              parsedData = JSON.parse(repaired) as Record<string, unknown>;
              isTruncated = true;
            } catch {
              // Repair failed, check if truncated
              isTruncated = isTruncatedJson(content);
              return null; // Can't parse at all
            }
          } else {
            // Extraction failed, check if truncated
            isTruncated = isTruncatedJson(content);
            return null; // Can't parse at all
          }
        }
      } else {
        // 4. Try to repair directly
        const repaired = tryRepairTruncatedJson(content);
        if (repaired) {
          try {
            parsedData = JSON.parse(repaired) as Record<string, unknown>;
            isTruncated = true;
          } catch {
            // Check if truncated (before giving up)
            isTruncated = isTruncatedJson(content);
            return null; // Can't extract or parse
          }
        } else {
          // Check if truncated (before giving up)
          isTruncated = isTruncatedJson(content);
          return null; // Can't extract or parse
        }
      }
    }
  }

  if (!parsedData) return null;

  // 5. Detect type using phase + data
  const type = detectMessageType(parsedData, phase);
  if (type === "unknown") return null;

  // 6. Validate structure (relaxed for truncated content)
  if (!validateParsedData(parsedData, type)) {
    // If truncated, be more lenient - just check we have the main identifying field
    if (isTruncated) {
      // For truncated content, just verify we have at least one key field that identifies the type
      let hasAnyKey = false;
      if (type === "proposal") {
        hasAnyKey = typeof parsedData.proposed_verdict === "string";
      } else if (type === "judge_decision") {
        hasAnyKey = typeof parsedData.verdict === "string";
      } else if (type === "revision") {
        hasAnyKey = typeof parsedData.final_proposed_verdict === "string";
      } else if (type === "questions" || type === "dispute_questions") {
        hasAnyKey = Array.isArray(parsedData.questions) && parsedData.questions.length > 0;
      } else if (type === "answers" || type === "dispute_answers") {
        hasAnyKey = Array.isArray(parsedData.answers) && parsedData.answers.length > 0;
      }
      if (!hasAnyKey) return null;
    } else {
      return null;
    }
  }

  return {
    type,
    data: parsedData as unknown as StructuredMessage,
    isTruncated,
  };
}
