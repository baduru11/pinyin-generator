# Pinyin Generator

A desktop tool that annotates Chinese characters with their pinyin pronunciations. Drop in any `.txt` or `.md` file containing Chinese text and get an annotated version back.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **41,000+ character** pinyin database sourced from the [Unicode Unihan](https://unicode.org/charts/unihan.html) standard
- **Word-aware annotation** — uses polyphone context data (1,600+ words) to pick the correct reading for polyphonic characters (e.g. 参**与** → yù, not yǔ)
- **Three output formats:**

| Format | Description | Output |
|--------|-------------|--------|
| **Inline** | Pinyin in parentheses after each word | `参与(can1 yu4)` |
| **Ruby HTML** | Pinyin rendered above characters in browser | Opens in any browser |
| **Side-by-side** | Chinese line with aligned pinyin underneath | Two-line layout |

- Batch processing — select multiple files at once
- Zero external dependencies — runs on Python's standard library

## Quick Start

```bash
git clone https://github.com/<your-username>/pinyin-generator.git
cd pinyin-generator
python pinyin_gen.py
```

> Requires **Python 3.10+** with Tkinter (included in standard Python installs on Windows and macOS).

## Usage

1. Run `python pinyin_gen.py`
2. Click **Browse** to select one or more `.txt` / `.md` files
3. Choose an output format
4. Click **Generate Pinyin**

Output files are saved next to the originals with a `_pinyin` suffix:

```
input.txt    →  input_pinyin.txt     (inline / side-by-side)
input.md     →  input_pinyin.html    (ruby HTML)
```

## Example

**Input** (`sample.txt`):
```
国王今日参与长城建设
```

**Inline output** (`sample_pinyin.txt`):
```
国(guo2)王(wang2)今(jin1)日(ri4)参与(can1 yu4)长(zhang3)城(cheng2)建(jian4)设(she4)
```

**Side-by-side output** (`sample_pinyin.txt`):
```
国    王     今    日   参    与   长      城      建     设
guo2  wang2  jin1  ri4  can1  yu4  zhang3  cheng2  jian4  she4
```

**Ruby HTML output** (`sample_pinyin.html`):

Each character displays its pinyin reading directly above it in the browser.

## Project Structure

```
├── pinyin_gen.py                  # Main application
└── pinyin_data/                   # Pinyin database (git submodule)
    ├── pinyin/pinyin.json         # 41,216 character → pinyin mappings
    ├── polyphone/polyphone.json   # Context-dependent pronunciation data
    ├── data/                      # Raw Unicode Unihan source data
    └── parser/                    # Scripts that generated the JSON files
```

## How It Works

1. **Segmentation** — Chinese text is split into tokens using longest-match-first against the polyphone word dictionary. Unrecognized sequences fall back to single characters.
2. **Lookup** — Each token is looked up in the polyphone database first (for context-sensitive readings), then falls back to the main pinyin database (first/most common reading).
3. **Tone conversion** — Tone-mark pinyin (ā, á, ǎ, à) is converted to tone-number format (a1–a4, with 5 for neutral tone).

## Data Sources

The pinyin database in `pinyin_data/` is derived from:

- [Unicode Unihan Database](https://www.unicode.org/reports/tr38/) — kMandarin, kXHC1983, kHanyuPinlu, kHanyuPinyin fields
- Polyphone context data from Chinese language reference materials

## License

MIT
