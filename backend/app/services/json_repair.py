"""
JSON Repair Module for Local LLM Output

Fixes common JSON errors from local models:
1. Missing commas between array/object elements
2. Trailing commas before } or ]
3. Single quotes instead of double quotes
4. Unquoted keys
5. Missing closing braces/brackets
6. Truncated JSON (attempt to close)
7. Control characters in strings
8. Markdown code blocks
"""

import re
import json
import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger("gamed_ai.json_repair")


class JSONRepairError(Exception):
    """Raised when JSON cannot be repaired"""
    def __init__(self, message: str, original_error: str, position: int = -1):
        self.message = message
        self.original_error = original_error
        self.position = position
        super().__init__(message)


def repair_json(raw_content: str, max_attempts: int = 3) -> Tuple[Dict[str, Any], bool, str]:
    """
    Attempt to repair malformed JSON from LLM output.

    Args:
        raw_content: The raw string that should be JSON
        max_attempts: Maximum repair iterations

    Returns:
        Tuple of (parsed_dict, was_repaired, repair_log)

    Raises:
        JSONRepairError: If JSON cannot be repaired
    """
    repair_log = []
    content = raw_content.strip()

    if not content:
        raise JSONRepairError(
            message="Empty content",
            original_error="Empty string received",
            position=0
        )

    # Stage 0: Try parsing as-is first
    try:
        result = json.loads(content)
        return result, False, "Parsed successfully without repair"
    except json.JSONDecodeError as e:
        repair_log.append(f"Initial parse failed at position {e.pos}: {e.msg}")

    # Stage 1: Extract JSON from surrounding text/markdown
    content = _extract_json_block(content)
    repair_log.append("Extracted JSON block from content")

    # Try again after extraction
    try:
        result = json.loads(content)
        return result, True, "Fixed by extracting JSON block"
    except json.JSONDecodeError:
        pass

    # Stage 2: Apply repair transformations
    repairs_applied = []

    # Fix 0: Escape literal newlines/tabs inside JSON strings
    content, fixed = _escape_newlines_in_strings(content)
    if fixed:
        repairs_applied.append("escaped_newlines_in_strings")

    # Try again after newline escape
    try:
        result = json.loads(content)
        return result, True, " | ".join(repair_log + [f"Applied repairs: {repairs_applied}"])
    except json.JSONDecodeError:
        pass

    # Fix 1: Remove control characters
    content, fixed = _remove_control_characters(content)
    if fixed:
        repairs_applied.append("removed_control_chars")

    # Fix 2: Replace single quotes with double quotes (carefully)
    content, fixed = _fix_quotes(content)
    if fixed:
        repairs_applied.append("fixed_quotes")

    # Fix 3: Add quotes to unquoted keys
    content, fixed = _quote_unquoted_keys(content)
    if fixed:
        repairs_applied.append("quoted_keys")

    # Fix 4: Remove trailing commas
    content, fixed = _remove_trailing_commas(content)
    if fixed:
        repairs_applied.append("removed_trailing_commas")

    # Fix 5: Add missing commas
    content, fixed = _add_missing_commas(content)
    if fixed:
        repairs_applied.append("added_missing_commas")

    # Fix 6: Close unclosed brackets/braces
    content, fixed = _close_unclosed_brackets(content)
    if fixed:
        repairs_applied.append("closed_brackets")

    repair_log.append(f"Applied repairs: {repairs_applied}")

    # Try parsing after repairs
    try:
        result = json.loads(content)
        return result, True, " | ".join(repair_log)
    except json.JSONDecodeError as e:
        repair_log.append(f"Parse still failed after repairs at position {e.pos}: {e.msg}")

        # Stage 3: Aggressive truncation repair (try to salvage partial JSON)
        content_truncated, fixed = _truncate_to_valid_json(content)
        if fixed:
            repair_log.append("Applied truncation repair")
            try:
                result = json.loads(content_truncated)
                return result, True, " | ".join(repair_log)
            except json.JSONDecodeError as e2:
                repair_log.append(f"Truncation repair also failed: {e2.msg}")

        raise JSONRepairError(
            message=f"Could not repair JSON after {len(repairs_applied)} fixes: {e.msg}",
            original_error=str(e),
            position=e.pos
        )


def _extract_json_block(content: str) -> str:
    """Extract JSON from markdown code blocks or surrounding text"""
    content = content.strip()

    # Remove markdown code blocks
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```JSON"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    # Remove leading text before first {
    first_brace = content.find("{")
    first_bracket = content.find("[")

    # Determine which comes first (object or array)
    if first_brace == -1 and first_bracket == -1:
        return content  # No JSON-like structure found

    if first_brace == -1:
        start = first_bracket
    elif first_bracket == -1:
        start = first_brace
    else:
        start = min(first_brace, first_bracket)

    # Find matching end
    if content[start] == "{":
        end = content.rfind("}")
        if end > start:
            content = content[start:end + 1]
    elif content[start] == "[":
        end = content.rfind("]")
        if end > start:
            content = content[start:end + 1]

    return content


def _escape_newlines_in_strings(content: str) -> Tuple[str, bool]:
    """Escape literal newlines and tabs inside JSON string values.

    LLMs often produce JSON with literal newlines in code strings:
      "code": "def foo():
          return 1"
    This should be:
      "code": "def foo():\\n    return 1"

    Uses a state machine to track when we're inside a JSON string.
    """
    result = []
    in_string = False
    escaped = False
    changed = False

    for ch in content:
        if escaped:
            result.append(ch)
            escaped = False
            continue

        if ch == '\\' and in_string:
            result.append(ch)
            escaped = True
            continue

        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue

        if in_string:
            if ch == '\n':
                result.append('\\n')
                changed = True
                continue
            elif ch == '\r':
                result.append('\\r')
                changed = True
                continue
            elif ch == '\t':
                result.append('\\t')
                changed = True
                continue

        result.append(ch)

    return ''.join(result), changed


def _remove_control_characters(content: str) -> Tuple[str, bool]:
    """Remove non-printable control characters except newlines/tabs"""
    original = content
    # Keep newlines (\n), tabs (\t), and carriage returns (\r)
    # Remove other control chars (0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f, 0x7f)
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
    return content, content != original


def _fix_quotes(content: str) -> Tuple[str, bool]:
    """Replace single quotes with double quotes for JSON strings"""
    original = content

    # Strategy: Replace single-quoted strings carefully
    # Pattern 1: Single-quoted keys: 'key':
    content = re.sub(r"'([^']*?)'\s*:", r'"\1":', content)

    # Pattern 2: Single-quoted string values after colon: : 'value'
    # Be careful not to replace apostrophes within double-quoted strings
    content = re.sub(r":\s*'([^']*?)'(\s*[,}\]])", r': "\1"\2', content)

    # Pattern 3: Single-quoted strings in arrays: ['item1', 'item2']
    content = re.sub(r"\[\s*'([^']*?)'", r'["\1"', content)
    content = re.sub(r",\s*'([^']*?)'(\s*[,\]])", r', "\1"\2', content)

    return content, content != original


def _quote_unquoted_keys(content: str) -> Tuple[str, bool]:
    """Add quotes to unquoted object keys"""
    original = content

    # Match unquoted keys: word characters before colon, not already quoted
    # Pattern: { key: or , key: where key is not quoted
    content = re.sub(
        r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:',
        r'\1"\2":',
        content
    )

    return content, content != original


def _remove_trailing_commas(content: str) -> Tuple[str, bool]:
    """Remove trailing commas before closing brackets/braces"""
    original = content

    # Remove comma followed by whitespace and closing bracket/brace
    # Handle multiple trailing commas
    while True:
        new_content = re.sub(r',(\s*[}\]])', r'\1', content)
        if new_content == content:
            break
        content = new_content

    return content, content != original


def _add_missing_commas(content: str) -> Tuple[str, bool]:
    """Add missing commas between array/object elements"""
    original = content

    # Pattern 1: "value" "nextKey": -> "value", "nextKey":
    # String value followed by string key
    content = re.sub(r'"\s*\n\s*"([^"]*)":', r'",\n"\1":', content)
    content = re.sub(r'"\s+"([^"]*)":', r'", "\1":', content)

    # Pattern 2: "value" { -> "value", {
    # String value followed by object
    content = re.sub(r'"\s+\{', '", {', content)
    content = re.sub(r'"\s*\n\s*\{', '",\n{', content)

    # Pattern 3: } "key": -> }, "key":
    # Object end followed by string key
    content = re.sub(r'\}\s*\n\s*"([^"]*)":', r'},\n"\1":', content)
    content = re.sub(r'\}\s+"([^"]*)":', r'}, "\1":', content)

    # Pattern 4: } { -> }, {
    # Object end followed by object start
    content = re.sub(r'\}\s+\{', '}, {', content)
    content = re.sub(r'\}\s*\n\s*\{', '},\n{', content)

    # Pattern 5: ] [ -> ], [
    # Array end followed by array start
    content = re.sub(r'\]\s+\[', '], [', content)
    content = re.sub(r'\]\s*\n\s*\[', '],\n[', content)

    # Pattern 6: } ] -> }] (this is valid, but handle ] "key" case)
    content = re.sub(r'\]\s*\n\s*"([^"]*)":', r'],\n"\1":', content)

    # Pattern 7: number followed by "key": (missing comma after number)
    content = re.sub(r'(\d)\s*\n\s*"([^"]*)":', r'\1,\n"\2":', content)
    content = re.sub(r'(\d)\s+"([^"]*)":', r'\1, "\2":', content)

    # Pattern 8: true/false/null followed by "key":
    content = re.sub(r'(true|false|null)\s*\n\s*"([^"]*)":', r'\1,\n"\2":', content)
    content = re.sub(r'(true|false|null)\s+"([^"]*)":', r'\1, "\2":', content)

    return content, content != original


def _close_unclosed_brackets(content: str) -> Tuple[str, bool]:
    """Close unclosed brackets and braces"""
    original = content

    # Count open vs close brackets (simple approach)
    # Note: This doesn't account for brackets inside strings properly,
    # but it's a reasonable heuristic for LLM output
    open_braces = content.count('{')
    close_braces = content.count('}')
    open_brackets = content.count('[')
    close_brackets = content.count(']')

    # Add missing closing brackets/braces
    missing_braces = open_braces - close_braces
    missing_brackets = open_brackets - close_brackets

    if missing_braces > 0 or missing_brackets > 0:
        # Try to close in the right order by scanning the content
        # For simplicity, add closing brackets then braces
        if missing_brackets > 0:
            content += ']' * missing_brackets
        if missing_braces > 0:
            content += '}' * missing_braces

    return content, content != original


def _truncate_to_valid_json(content: str) -> Tuple[str, bool]:
    """
    Attempt to truncate content to produce valid JSON.

    Tries removing characters from the end until we get valid JSON.
    This handles cases where the LLM output was cut off mid-way.
    """
    # Don't try truncation on very short content
    if len(content) < 10:
        return content, False

    # Try progressively shorter prefixes
    # Start from 10 chars before end to avoid tiny truncations
    for i in range(len(content), max(10, len(content) - 500), -1):
        test_content = content[:i]

        # Count brackets to add proper closing
        open_braces = test_content.count('{')
        close_braces = test_content.count('}')
        open_brackets = test_content.count('[')
        close_brackets = test_content.count(']')

        # Calculate needed closers
        need_braces = open_braces - close_braces
        need_brackets = open_brackets - close_brackets

        if need_braces < 0 or need_brackets < 0:
            # More closers than openers - skip
            continue

        # Build closing sequence
        # We need to close in the right order - try both orders
        for closer in [']' * need_brackets + '}' * need_braces,
                       '}' * need_braces + ']' * need_brackets]:
            try:
                test_full = test_content.rstrip(',\n\t ') + closer
                json.loads(test_full)
                return test_full, True
            except json.JSONDecodeError:
                continue

    return content, False


def get_error_context(content: str, error_position: int, context_chars: int = 50) -> str:
    """
    Get context around the JSON error position for debugging.

    Args:
        content: The JSON content
        error_position: Position where the error occurred
        context_chars: Number of characters to show before and after

    Returns:
        String showing the error context with marker
    """
    if error_position < 0 or error_position >= len(content):
        return f"Position {error_position} out of bounds (content length: {len(content)})"

    start = max(0, error_position - context_chars)
    end = min(len(content), error_position + context_chars)

    before = content[start:error_position]
    char_at_error = content[error_position] if error_position < len(content) else "EOF"
    after = content[error_position + 1:end] if error_position + 1 < len(content) else ""

    # Show newlines as visible characters
    before = before.replace('\n', '\\n').replace('\t', '\\t')
    after = after.replace('\n', '\\n').replace('\t', '\\t')

    return f"...{before}>>>{repr(char_at_error)}<<<{after}..."
