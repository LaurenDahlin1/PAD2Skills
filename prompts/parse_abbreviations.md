You are a careful document parser.

TASK
Extract the abbreviations and acronyms list list from the provided markdown-like text and output it as ONE clean markdown table.

INPUT
- A markdown/plaintext excerpt from a World Bank document. Formatting may be messy: line breaks inside entries, inconsistent spacing, broken columns, and partial markdown tables embedded in the list.

OUTPUT (STRICT)
- Output ONLY a markdown table (no prose, no code fences).
- Table columns must be exactly: Abbreviation | Definition
- Include a header row and separator row.

WHAT TO EXTRACT
- Extract abbreviation/acronym → definition pairs that belong to the “ABBREVIATIONS AND ACRONYMS” section. The name of the section may be slightly different.
- The section ends at the first subsequent top-level heading (e.g., a line starting with “## ”) OR when the content clearly switches to non-abbreviation material (e.g., staff lists, country headers, currency equivalents).

PARSING RULES (IMPORTANT)
1) Accept multiple input formats:
   - “ABBR” on one line followed by definition on the next line(s).
   - “ABBR Definition” on the same line.
   - Rows inside existing markdown tables like: “| ABBR | Definition |”.
2) Multi-line definitions:
   - If a definition wraps onto following lines (including parenthetical translations), concatenate into a single line separated by spaces.
   - Preserve meaningful punctuation and parentheses.
3) Noise handling:
   - Ignore unrelated lines (e.g., “Public Disclosure Authorized”, currency tables, staff tables).
   - Do NOT treat random standalone words as abbreviations unless paired with a definition.
4) Duplicates:
   - If the same abbreviation appears multiple times with the same definition, keep only one row.
   - If the same abbreviation appears with different definitions, keep multiple rows (separate rows), preserving both definitions.
5) Cleanup:
   - Trim extra spaces.
   - Decode common HTML entities in text: “&amp;” → “&”.
   - Do not invent or guess missing definitions. If you cannot find a definition paired with an abbreviation, skip that abbreviation.

SORTING
- Keep rows in the original document order (stable), not alphabetical.