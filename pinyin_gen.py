import json, re, os, sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

# ── Tone conversion ──────────────────────────────────────────────────

TONE_MAP = {
    "ā": "a1", "á": "a2", "ǎ": "a3", "à": "a4",
    "ō": "o1", "ó": "o2", "ǒ": "o3", "ò": "o4",
    "ē": "e1", "é": "e2", "ě": "e3", "è": "e4",
    "ī": "i1", "í": "i2", "ǐ": "i3", "ì": "i4",
    "ū": "u1", "ú": "u2", "ǔ": "u3", "ù": "u4",
    "ǖ": "v1", "ǘ": "v2", "ǚ": "v3", "ǜ": "v4",
    "ü": "v0",
    "ń": "n2", "ň": "n3", "ǹ": "n4",
    "ḿ": "m2",
}

def tone_mark_to_number(s: str) -> str:
    if any(ch.isdigit() for ch in s):
        return s.lower().replace("ü", "v")
    out = []
    found_tone = None
    for ch in s:
        if ch in TONE_MAP:
            rep = TONE_MAP[ch]
            out.append(rep[0])
            if rep[1] != "0":
                found_tone = rep[1]
        else:
            out.append(ch.lower())
    base = "".join(out).replace("ü", "v")
    return base + (found_tone if found_tone else "5")


# ── Pinyin engine ────────────────────────────────────────────────────

HANZI_BLOCK_RE = re.compile(r"[\u4e00-\u9fff]+")


class PinyinEngine:
    def __init__(self, pinyin_json_path, polyphone_json_path=None):
        with open(pinyin_json_path, "r", encoding="utf-8") as f:
            self.char_map = json.load(f)

        # Build word dictionary from polyphone data
        # word_dict[word][char_index] = pinyin_with_tone_number
        self.word_dict: dict[str, dict[int, str]] = {}
        if polyphone_json_path and os.path.exists(polyphone_json_path):
            with open(polyphone_json_path, "r", encoding="utf-8") as f:
                polyphone = json.load(f)
            self._build_word_dict(polyphone)

        self.max_word_len = max((len(w) for w in self.word_dict), default=1)

    def _build_word_dict(self, polyphone):
        # polyphone: { char: { pinyin: [[start_words], [middle_words], [end_words]] } }
        for char, pronunciations in polyphone.items():
            for pinyin, positions in pronunciations.items():
                pinyin_num = tone_mark_to_number(pinyin)
                all_words = positions[0] + positions[1] + positions[2]
                for word in all_words:
                    if len(word) < 2:
                        continue
                    if word not in self.word_dict:
                        self.word_dict[word] = {}
                    for i, c in enumerate(word):
                        if c == char:
                            self.word_dict[word][i] = pinyin_num

    def _get_char_pinyin(self, ch: str) -> str:
        pys = self.char_map.get(ch)
        if not pys:
            return "?"
        return tone_mark_to_number(pys[0])

    def _get_word_pinyin(self, word: str) -> list[str]:
        known = self.word_dict.get(word, {})
        return [
            known[i] if i in known else self._get_char_pinyin(ch)
            for i, ch in enumerate(word)
        ]

    def _segment(self, block: str) -> list[str]:
        """Longest-match-first greedy segmentation."""
        words = []
        i = 0
        while i < len(block):
            matched = False
            for length in range(min(self.max_word_len, len(block) - i), 1, -1):
                candidate = block[i : i + length]
                if candidate in self.word_dict:
                    words.append(candidate)
                    i += length
                    matched = True
                    break
            if not matched:
                words.append(block[i])
                i += 1
        return words

    # ── Formatting ───────────────────────────────────────────────────

    def _parse(self, text: str):
        """Yield ('text', str) or ('word', str, [pinyin]) chunks."""
        last = 0
        for m in HANZI_BLOCK_RE.finditer(text):
            if m.start() > last:
                yield ("text", text[last : m.start()])
            for word in self._segment(m.group(0)):
                yield ("word", word, self._get_word_pinyin(word))
            last = m.end()
        if last < len(text):
            yield ("text", text[last:])

    def format_inline(self, text: str) -> str:
        parts = []
        for chunk in self._parse(text):
            if chunk[0] == "text":
                parts.append(chunk[1])
            else:
                word, pinyins = chunk[1], chunk[2]
                parts.append(f"{word}({' '.join(pinyins)})")
        return "".join(parts)

    def format_ruby(self, text: str) -> str:
        html = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'>",
            "<style>",
            "body { font-size: 24px; line-height: 2.8; font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; padding: 20px; }",
            "ruby { margin: 0 1px; }",
            "rt { font-size: 0.5em; color: #555; }",
            "</style></head><body>",
        ]
        for chunk in self._parse(text):
            if chunk[0] == "text":
                html.append(chunk[1].replace("\n", "<br>\n"))
            else:
                word, pinyins = chunk[1], chunk[2]
                for ch, py in zip(word, pinyins):
                    html.append(f"<ruby>{ch}<rt>{py}</rt></ruby>")
        html.append("</body></html>")
        return "".join(html)

    def format_sidebyside(self, text: str) -> str:
        lines = text.split("\n")
        out = []
        for line in lines:
            if not HANZI_BLOCK_RE.search(line):
                out.append(line)
                continue
            cn_cols = []
            py_cols = []
            for chunk in self._parse(line):
                if chunk[0] == "text":
                    cn_cols.append(chunk[1])
                    py_cols.append(chunk[1])
                else:
                    word, pinyins = chunk[1], chunk[2]
                    for ch, py in zip(word, pinyins):
                        # Each column: 1 CJK char (~2 cols) vs its pinyin
                        width = max(2, len(py))
                        cn_cols.append(ch + " " * (width - 2))
                        py_cols.append(py.ljust(width))
            out.append("  ".join(cn_cols))
            out.append("  ".join(py_cols))
            out.append("")
        return "\n".join(out)

    def annotate(self, text: str, fmt: str) -> str:
        if fmt == "inline":
            return self.format_inline(text)
        elif fmt == "ruby":
            return self.format_ruby(text)
        elif fmt == "sidebyside":
            return self.format_sidebyside(text)
        return self.format_inline(text)


# ── Locate data files ────────────────────────────────────────────────

def find_data_files():
    base = os.path.dirname(os.path.abspath(__file__))
    pinyin_candidates = [
        os.path.join(base, "pinyin_data", "pinyin", "pinyin.json"),
        os.path.join(base, "mono", "pinyin.json"),
        os.path.join(base, "multi", "pinyin.json"),
    ]
    polyphone_candidates = [
        os.path.join(base, "pinyin_data", "polyphone", "polyphone.json"),
    ]
    pinyin_path = next((p for p in pinyin_candidates if os.path.exists(p)), None)
    polyphone_path = next((p for p in polyphone_candidates if os.path.exists(p)), None)
    return pinyin_path, polyphone_path


# ── GUI ──────────────────────────────────────────────────────────────

FORMAT_OPTIONS = {
    "Inline  —  国王(guo2 wang2)": "inline",
    "Ruby HTML  —  pinyin above characters": "ruby",
    "Side-by-side  —  Chinese + pinyin lines": "sidebyside",
}

OUTPUT_EXT = {
    "inline": lambda orig: os.path.splitext(orig)[0] + "_pinyin" + os.path.splitext(orig)[1],
    "ruby": lambda orig: os.path.splitext(orig)[0] + "_pinyin.html",
    "sidebyside": lambda orig: os.path.splitext(orig)[0] + "_pinyin" + os.path.splitext(orig)[1],
}


class PinyinApp(tk.Tk):
    def __init__(self, engine: PinyinEngine):
        super().__init__()
        self.engine = engine
        self.title("Pinyin Generator")
        self.geometry("600x420")
        self.resizable(False, False)
        self.configure(bg="#f5f5f5")
        self._build_ui()

    def _build_ui(self):
        # ── File selection ───────────────────────────────────
        frame_file = ttk.LabelFrame(self, text="Input Files", padding=10)
        frame_file.pack(fill="x", padx=16, pady=(16, 8))

        self.file_list = tk.Listbox(frame_file, height=6, selectmode="extended")
        self.file_list.pack(fill="x", side="left", expand=True)

        btn_frame = ttk.Frame(frame_file)
        btn_frame.pack(side="right", padx=(8, 0))

        ttk.Button(btn_frame, text="Browse…", command=self._browse).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Remove", command=self._remove_selected).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Clear", command=self._clear_files).pack(fill="x", pady=2)

        # ── Format selection ─────────────────────────────────
        frame_fmt = ttk.LabelFrame(self, text="Output Format", padding=10)
        frame_fmt.pack(fill="x", padx=16, pady=8)

        self.fmt_var = tk.StringVar(value=list(FORMAT_OPTIONS.keys())[0])
        for label in FORMAT_OPTIONS:
            ttk.Radiobutton(frame_fmt, text=label, variable=self.fmt_var, value=label).pack(anchor="w")

        # ── Generate ─────────────────────────────────────────
        ttk.Button(self, text="Generate Pinyin", command=self._generate).pack(pady=12)

        # ── Status ───────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, foreground="#666").pack(side="bottom", pady=8)

    def _browse(self):
        paths = filedialog.askopenfilenames(
            title="Select files",
            filetypes=[("Text / Markdown", "*.txt *.md"), ("All files", "*.*")],
        )
        for p in paths:
            if p not in self.file_list.get(0, "end"):
                self.file_list.insert("end", p)

    def _remove_selected(self):
        for i in reversed(self.file_list.curselection()):
            self.file_list.delete(i)

    def _clear_files(self):
        self.file_list.delete(0, "end")

    def _generate(self):
        files = self.file_list.get(0, "end")
        if not files:
            messagebox.showwarning("No files", "Please add at least one file.")
            return

        fmt_key = FORMAT_OPTIONS[self.fmt_var.get()]
        count = 0
        errors = []

        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read()
                result = self.engine.annotate(text, fmt_key)
                out_path = OUTPUT_EXT[fmt_key](fpath)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(result)
                count += 1
            except Exception as e:
                errors.append(f"{os.path.basename(fpath)}: {e}")

        if errors:
            messagebox.showerror("Errors", "\n".join(errors))
        self.status_var.set(f"Done — {count} file(s) generated")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    pinyin_path, polyphone_path = find_data_files()
    if not pinyin_path:
        messagebox.showerror("Missing data", "Could not find pinyin.json.\nPlace it next to this script or in pinyin_data/pinyin/.")
        sys.exit(1)

    engine = PinyinEngine(pinyin_path, polyphone_path)
    app = PinyinApp(engine)
    app.mainloop()


if __name__ == "__main__":
    main()
