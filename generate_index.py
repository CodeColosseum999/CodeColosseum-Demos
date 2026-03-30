#!/usr/bin/env python3
"""
generate_index.py — Regenerate index.html from demo folders.

Scans all YYYY-MM-DD_* folders, reads prompt.txt for the idea description,
and renders index_template.html with a card grid of all demos.
Run manually or via GitHub Actions on every push to main.
"""

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
TEMPLATE_PATH = REPO_ROOT / "index_template.html"
OUTPUT_PATH = REPO_ROOT / "index.html"

# -------------------------------------------------------------------
# Card HTML builder
# -------------------------------------------------------------------

MODEL_LABELS = {
    "claude":   {"label": "Claude",   "class": "model-claude",   "symbol": "◆"},
    "gpt":      {"label": "ChatGPT",  "class": "model-gpt",      "symbol": "◆"},
    "gemini":   {"label": "Gemini",   "class": "model-gemini",   "symbol": "◆"},
    "deepseek": {"label": "DeepSeek", "class": "model-deepseek", "symbol": "◆"},
}

# Regex to strip markdown headers and leading numbers ("1. The Rule:" → "The Rule:")
_STRIP_HEADER_RE = re.compile(r'^#+\s*', re.MULTILINE)
_STRIP_NUMBERED_RE = re.compile(r'^\d+\)\s*', re.MULTILINE)

def clean_prompt(text: str) -> str:
    """Strip markdown headers and leading numbers from prompt text."""
    text = _STRIP_HEADER_RE.sub('', text)
    text = _STRIP_NUMBERED_RE.sub('', text)
    text = text.strip()
    # Collapse blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def first_sentence(text: str, max_len: int = 120) -> str:
    """Return the first sentence, trimmed to max_len."""
    sentence_end = re.search(r'[.!?]\s', text)
    end = sentence_end.end() if sentence_end else len(text)
    snippet = text[:end].strip()
    if len(snippet) > max_len:
        snippet = snippet[:max_len - 3] + "..."
    return snippet


def build_card(folder: Path) -> str:
    """Build a .card HTML block for one demo folder."""
    # Read prompt.txt if it exists
    prompt_file = folder / "prompt.txt"
    if prompt_file.exists():
        raw = prompt_file.read_text(encoding="utf-8", errors="replace")
        # Extract the Idea section only
        idea_match = re.search(r'#\s*Idea\s*\n(.*?)(?:\n#|\Z)', raw, re.DOTALL | re.IGNORECASE)
        idea_text = clean_prompt(idea_match.group(1).strip()) if idea_match else ""
        prompt_snippet = first_sentence(idea_text, max_len=140)
    else:
        prompt_snippet = "No prompt available."

    # Parse date from folder name
    folder_name = folder.name
    date_match = re.match(r'^(\d{4}-\d{2}-\d{2})_', folder_name)
    date_str = date_match.group(1) if date_match else folder_name[:10]

    # Build model links
    links_html = ""
    for model, info in MODEL_LABELS.items():
        html_file = folder / f"{model}.html"
        if html_file.exists():
            href = f"{folder_name}/{model}.html"
            links_html += (
                f'      <a class="{info["class"]}" href="{href}">'
                f'{info["symbol"]} {info["label"]}</a>\n'
            )
        else:
            links_html += (
                f'      <span class="{info["class"]}" style="opacity:0.3; cursor:default;">'
                f'{info["symbol"]} {info["label"]} (n/a)</span>\n'
            )

    # Truncate prompt snippet for display
    display_prompt = (prompt_snippet[:200] + "...") if len(prompt_snippet) > 200 else prompt_snippet

    card = f"""    <article class="card">
      <div class="card-header">
        <span class="card-title">{folder_name[11:].replace('_', ' ').title()}</span>
        <span class="card-date">{date_str}</span>
      </div>
      <p class="card-prompt">{display_prompt}</p>
      <div class="model-links">
{links_html}      </div>
    </article>"""
    return card


# -------------------------------------------------------------------
# Main render
# -------------------------------------------------------------------

def render_index() -> None:
    # Load template
    if not TEMPLATE_PATH.exists():
        print(f"ERROR: index_template.html not found at {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Scan demo folders (sorted newest first)
    demo_folders = sorted(
        [p for p in REPO_ROOT.iterdir() if p.is_dir() and re.match(r'^\d{4}-\d{2}-\d{2}_', p.name)],
        reverse=True  # newest first
    )

    if not demo_folders:
        cards_html = "    <p style='color:#888;grid-column:1/-1;text-align:center;'>No demos yet — check back soon!</p>"
    else:
        cards = [build_card(f) for f in demo_folders]
        cards_html = "\n\n".join(cards)

    title = "Code Colosseum · Battle Demos"
    description = (
        "Watch AI models battle it out in generative art &amp; physics simulations. "
        "Click any model to run its demo directly in your browser."
    )
    html = template.replace("{{TITLE}}", title).replace("{{DESCRIPTION}}", description).replace("{{CARDS}}", cards_html)

    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"✓ Written: {OUTPUT_PATH}  ({len(demo_folders)} demos)")


if __name__ == "__main__":
    render_index()
