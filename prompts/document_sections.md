You are an expert at recovering the section structure of World Bank Project Appraisal Documents (PADs) from MARKDOWN. Take your time.

INPUT
- project_id: a string (e.g., "P120304")
- markdown_text: the full PAD in markdown as plain text

GOAL
Identify the PAD’s TOP-LEVEL sections:
- Roman numeral sections: I., II., III., IV., V., VI., … (case-insensitive; may be uppercase in text).
- All Annexes (e.g., “Annex 1: …”, “Annex 2: …”) are also sections.

SECTION INDEXING (IMPORTANT)
- Return a numeric section_id starting at 0, increasing by 1 in document order across ALL top-level sections, including Annexes.
- Do NOT return roman numerals as the section_id.
- Example: section_id 0 might correspond to "I. STRATEGIC CONTEXT", section_id 1 to "II. PROJECT DEVELOPMENT OBJECTIVE", etc. Annexes continue the same numbering sequence.

METHOD (must follow)
1) Locate the Table of Contents (TOC) region if present (often contains “TABLE OF CONTENTS”).
2) From the TOC, extract ONLY top-level entries:
   - Roman numeral section entries (I., II., III., …).
   - Annex entries (“Annex 1: …”, etc.).
   Ignore sub-sections like “A. Country Context”, “B. …”, etc.
   Ignore page numbers and dot leaders (e.g., “….. 12”).
3) For each extracted TOC entry, find the corresponding section header in the BODY TEXT (not in the TOC):
   - Search the full document after the TOC.
   - Match robustly (case-insensitive; tolerate extra spaces; tolerate missing/extra punctuation; tolerate markdown heading markers like “#”, “##”, “###”).
4) Record the EXACT header line as it appears in the body text, including any markdown heading markers (#, ##, ###) and spacing.
   - Example valid header_text: "## I. STRATEGIC CONTEXT"
   - Example valid header_text: "I. STRATEGIC CONTEXT"
5) If a TOC is missing or incomplete, fall back to scanning the full document body for top-level headers that match:
   - Roman numeral pattern: optional markdown heading + roman numeral + "." + title
   - Annex pattern: optional markdown heading + "Annex" + number + ":" (or ".") + title
6) Do not hallucinate sections that are not present in the body text. If you cannot find a body header for a TOC entry, omit it.

OUTPUT (JSON ONLY; no prose)
Return a single JSON object with this schema:
{
  "project_id": "P120304",
  "sections": [
    {
      "section_id": 0,
      "section_title": "STRATEGIC CONTEXT",
      "header_text": "##I. STRATEGIC CONTEXT"
    }
  ]
}

OUTPUT RULES
- project_id must exactly match the provided input project_id.
- Preserve the document order.
- section_title should come from the body header’s title portion (not the TOC), but you may remove trailing page artifacts; otherwise keep it faithful.
- header_text must be copied exactly from the body line (including markdown prefix).
- JSON must be valid (double quotes, no trailing commas).