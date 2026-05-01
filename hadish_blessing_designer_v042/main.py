import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from pathlib import Path
import json, random, os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageTk

try:
    from bidi.algorithm import get_display
except Exception:
    get_display = None

APP_DIR   = Path(__file__).resolve().parent
BG_DIR    = APP_DIR / "assets" / "backgrounds"
FRAME_DIR = APP_DIR / "assets" / "frames"
BLESSINGS_PATH = APP_DIR / "templates" / "blessings.json"
EXPORT_DIR = APP_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)
TOOL_DIR  = APP_DIR / "hadish_blessings_tool"
LOGO_PATH = APP_DIR / "LOGO.png"
SETTINGS_PATH = APP_DIR / "designer_settings.json"

def _make_logo_tk(height_px: int) -> "ImageTk.PhotoImage | None":
    """Load LOGO.png, scale to height_px, return a PhotoImage (or None)."""
    if not LOGO_PATH.exists():
        return None
    try:
        img = Image.open(LOGO_PATH).convert("RGBA")
        ratio = height_px / img.height
        w = max(1, int(img.width * ratio))
        img = img.resize((w, height_px), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# ── inject tool on sys.path ───────────────────────────────────────────────────
_BlessingRepo = None
TOOL_AVAILABLE = False
if TOOL_DIR.exists():
    _tp = str(TOOL_DIR)
    if _tp not in sys.path:
        sys.path.insert(0, _tp)
    try:
        from core.blessing_repository import BlessingRepository as _BlessingRepo
        TOOL_AVAILABLE = True
    except Exception:
        pass

# ── constants ─────────────────────────────────────────────────────────────────
PRODUCT_PRESETS_CM = {
    "A5":           {"size": (14.8, 21.0),  "title": "A5",           "desc": "ברכה קלאסית למתנה, יפה למסגרת קטנה או צירוף למארז."},
    "A4":           {"size": (21.0, 29.7),  "title": "A4",           "desc": "מתאים לפוסטר קטן, ברכה גדולה, תלייה או הצגה על שולחן."},
    "10x15":        {"size": (10.0, 15.0),  "title": "10x15",        "desc": "גודל קטן ומהיר, מתאים לצירוף למתנה או הדפסה פוטו."},
    "20x20":        {"size": (20.0, 20.0),  "title": "20x20",        "desc": "ריבוע מעוצב, מתאים למראה מודרני או מתנה מיוחדת."},
    "מותאם אישית": {"size": (14.8, 21.0),  "title": "מותאם אישית", "desc": "הזנת מידה ידנית בס״מ לכל מוצר מיוחד."},
}
CATEGORY_TO_BG = {
    "יום הולדת": "birthday_fun.png", "מורה/גננת": "teacher_calm.png",
    "גיוס": "army_clean.png",         "תודה": "hadish_soft.png",
    "חתונה": "cream_elegant.png",     "בר/בת מצווה": "bar_mitzvah_blue.png",
    "אהבה": "pink_love_light.png",
}
STYLE_TO_FRAME = {"מרגש": "gold_double.png", "מצחיק": "red_corner.png", "רשמי": "blue_rounded.png"}

BRAND = {
    "bg":      "#0B1628", "surface": "#142040", "panel":  "#1A2C52",
    "border":  "#2D4472", "accent":  "#2563EB", "gold":   "#F59E0B",
    "orange":  "#F97316", "red":     "#DC2626",  "green":  "#16A34A",
    "text":    "#F1F5F9", "muted":   "#94A3B8",  "yellow": "#FDE68A",
}
THEMES = {
    "dark": dict(BRAND),
    "light": {
        "bg": "#EEF2F7", "surface": "#FFFFFF", "panel": "#F8FAFC",
        "border": "#CBD5E1", "accent": "#2563EB", "gold": "#B45309",
        "orange": "#EA580C", "red": "#DC2626", "green": "#16A34A",
        "text": "#0F172A", "muted": "#475569", "yellow": "#FDE68A",
    },
}

def set_brand_theme(mode):
    BRAND.clear()
    BRAND.update(THEMES.get(mode, THEMES["dark"]))

RECIPIENT_COLORS = {
    "מתגייס": "#DCFCE7", "מתגייסת": "#DCFCE7", "גיוס לגבר": "#DCFCE7", "גיוס לאישה": "#DCFCE7",
    "סבא": "#DBEAFE",    "סבתא": "#FCE7F3",
    "נוער בנות": "#F3E8FF", "חברה טובה (נוער)": "#F3E8FF",
    "לידה ותינוקות": "#FFE4E6", "תינוקת": "#FFE4E6", "תינוק": "#E0F2FE",
    "בן זוג": "#E0E7FF", "בת זוג": "#FCE7F3",
    "מורה": "#FEF3C7",   "גננת": "#FFEDD5",
    "רופא": "#E0F2FE",   "עורך דין": "#EDE9FE",
    "רואה חשבון": "#ECFDF5", "מנהל": "#E2E8F0", "מפקד": "#DCFCE7", "עובד": "#F1F5F9",
}

# ── font scanning ─────────────────────────────────────────────────────────────
def _scan_win_fonts():
    d = Path(r"C:\Windows\Fonts")
    fonts = {}
    if d.exists():
        for f in sorted(d.glob("*.ttf")) + sorted(d.glob("*.TTF")):
            fonts[f.stem.lower()] = str(f)
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]:
        p = Path(path)
        if p.exists():
            fonts[p.stem.lower()] = str(p)
    return fonts

SYSTEM_FONTS = _scan_win_fonts()

_FONT_MATRIX = {
    (False, False): ["segoeui",   "arial",   "calibri",  "dejavu sans"],
    (True,  False): ["seguisb",   "arialbd", "calibrib", "seguibl"],
    (False, True):  ["segoeuii",  "ariali",  "calibrii"],
    (True,  True):  ["seguisbi",  "arialbi", "calibriz"],
}

def find_font_path(bold=False, italic=False):
    for stem in _FONT_MATRIX.get((bold, italic), ["segoeui"]):
        if stem in SYSTEM_FONTS:
            return SYSTEM_FONTS[stem]
    return next(iter(SYSTEM_FONTS.values()), None)

FONT_REG        = find_font_path()
FONT_BOLD       = find_font_path(bold=True)  or FONT_REG
FONT_ITALIC     = find_font_path(italic=True) or FONT_REG
FONT_BOLD_ITALIC= find_font_path(bold=True, italic=True) or FONT_BOLD

DISPLAY_FONTS = sorted({
    k for k in SYSTEM_FONTS
    if not any(x in k for x in ["symbol","wingdings","marlett","webdings","mt extra"])
})

HEBREW_FONT_HINTS = (
    "arial", "david", "frank", "gisha", "hadas", "miriam", "narkisim",
    "segoe", "tahoma", "times", "aharoni", "rubik", "assistant", "almoni",
)

def font_likely_supports_hebrew(name):
    lname = (name or "").lower()
    if any(hint in lname for hint in HEBREW_FONT_HINTS):
        return True
    path = SYSTEM_FONTS.get(lname)
    if not path:
        return False
    try:
        font = ImageFont.truetype(path, 36)
        return bool(font.getmask("א").getbbox())
    except Exception:
        return False

def ordered_fonts(favorites=None):
    favorites = set(favorites or [])
    return sorted(
        DISPLAY_FONTS,
        key=lambda f: (
            f not in favorites,
            not font_likely_supports_hebrew(f),
            f.lower(),
        ),
    )

def make_vertical_gradient(size, top_hex, bottom_hex):
    width, height = size
    top = hex_to_rgb(top_hex)
    bottom = hex_to_rgb(bottom_hex)
    if height <= 1:
        return Image.new("RGBA", size, top + (255,))
    gradient = Image.new("RGBA", size, (0, 0, 0, 0))
    pix = gradient.load()
    for y in range(height):
        t = y / (height - 1)
        rgb = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(width):
            pix[x, y] = rgb + (255,)
    return gradient

def draw_gradient_text(base, pos, text, font, top_hex, bottom_hex):
    x, y = pos
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), text, font=font)
    width = max(1, right - left)
    height = max(1, bottom - top)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).text((-left, -top), text, font=font, fill=255)
    gradient = make_vertical_gradient((width, height), top_hex, bottom_hex)
    layer = Image.composite(gradient, Image.new("RGBA", (width, height), (0,0,0,0)), mask)
    base.alpha_composite(layer, (int(x + left), int(y + top)))

def resolve_font(stem_display, bold=False, italic=False):
    """Resolve display font name to a .ttf path, applying bold/italic variants."""
    base = (stem_display or "").lower().strip()
    # try bold/italic suffix combos
    suffixes_bi = [base + "bi", base + "z"]
    suffixes_b  = [base + "bd", base + "b"]
    suffixes_i  = [base + "i"]
    if bold and italic:
        candidates = suffixes_bi + suffixes_b + [base]
    elif bold:
        candidates = suffixes_b + [base]
    elif italic:
        candidates = suffixes_i + [base]
    else:
        candidates = [base]
    for c in candidates:
        if c in SYSTEM_FONTS:
            return SYSTEM_FONTS[c]
    return find_font_path(bold, italic)

# ── image helpers ─────────────────────────────────────────────────────────────
def cm_to_px(cm, dpi=300):
    return int(round(cm / 2.54 * dpi))

def hex_to_rgb(hex_color):
    h = str(hex_color).strip().lstrip("#")
    if len(h) == 3: h = "".join(c*2 for c in h)
    try:    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except: return (255, 255, 255)

def bidi_text(text):
    if get_display:
        try:    return get_display(text)
        except: return text
    return text[::-1] if any("֐" <= c <= "׿" for c in text) else text

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bb = draw.textbbox((0,0), bidi_text(test), font=font)
        if bb[2] - bb[0] <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines

def fit_text(draw, text, box, font_path, max_size, min_size=20, line_spacing=1.22):
    x1, y1, x2, y2 = box
    max_w, max_h = x2-x1, y2-y1
    fp = font_path if font_path and Path(font_path).exists() else FONT_REG
    for size in range(max_size, min_size-1, -2):
        try:
            font = ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        all_lines = []
        for para in text.split("\n"):
            if para.strip(): all_lines.extend(wrap_text(draw, para.strip(), font, max_w))
            else:            all_lines.append("")
        lh = int(size * line_spacing)
        total_h = lh * len(all_lines)
        widest = max((draw.textbbox((0,0), bidi_text(l), font=font)[2] -
                      draw.textbbox((0,0), bidi_text(l), font=font)[0])
                     for l in all_lines) if all_lines else 0
        if total_h <= max_h and widest <= max_w:
            return font, all_lines, lh
    try:
        font = ImageFont.truetype(fp, min_size) if fp else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    lines = []
    for para in text.split("\n"):
        if para.strip(): lines.extend(wrap_text(draw, para.strip(), font, max_w))
        else:            lines.append("")
    return font, lines, int(min_size * line_spacing)


# ── QuoteRepository (inline, mirrors hadish_blessings_tool) ──────────────────
class QuoteRepository:
    def __init__(self, data_path=None):
        self.data_path = Path(data_path) if data_path else TOOL_DIR / "data" / "sources_quotes.json"
        self.items = []
        self.load()

    def load(self):
        if self.data_path.exists():
            try: self.items = json.loads(self.data_path.read_text(encoding="utf-8"))
            except Exception: self.items = []
        return self.items

    def values(self, key):
        return sorted({item.get(key, "") for item in self.items if item.get(key, "")})

    def source_groups(self):
        return sorted({
            item.get("source_group") or item.get("section") or item.get("source", "")
            for item in self.items
            if item.get("source_group") or item.get("section") or item.get("source")
        })

    def search(self, query="", category="הכל", source="הכל", product="הכל",
               style="הכל", favorites=None):
        q = (query or "").strip().lower()
        favorites = favorites or set()
        results = []
        for item in self.items:
            if category != "הכל" and item.get("category") != category: continue
            grp = item.get("source_group") or item.get("section") or item.get("source")
            if source  != "הכל" and grp != source: continue
            if product != "הכל" and item.get("product") != product: continue
            if style   != "הכל" and style not in item.get("style", []): continue
            blob = " ".join([item.get("text",""), item.get("category",""),
                             item.get("source",""), item.get("source_group",""),
                             item.get("product",""), " ".join(item.get("style",[]))]).lower()
            if q and q not in blob: continue
            copy = dict(item)
            copy["favorite"] = item.get("id") in favorites
            results.append(copy)
        results.sort(key=lambda x: (not x.get("favorite",False),
                                     x.get("source_group",""), x.get("category","")))
        return results


# ── EmbeddedBlessingWidget ────────────────────────────────────────────────────
class EmbeddedBlessingWidget(tk.Frame):
    """Full blessing-tool UI embedded in the Wizard's step 4."""

    def __init__(self, parent, on_selected, **kwargs):
        super().__init__(parent, bg="white", **kwargs)
        self.on_selected = on_selected
        self.selected_item = None
        self.mode = "blessings"
        self.filtered = []
        self.repo       = _BlessingRepo() if TOOL_AVAILABLE and _BlessingRepo else None
        self.quote_repo = QuoteRepository() if (TOOL_DIR / "data" / "sources_quotes.json").exists() else None
        self._fav_path  = TOOL_DIR / "data" / "favorites.json"
        self._qfav_path = TOOL_DIR / "data" / "quote_favorites.json"
        self.favorites       = self._load_favs(self._fav_path)
        self.quote_favorites = self._load_favs(self._qfav_path)
        self._logo_tk = _make_logo_tk(40)   # keep reference alive
        self._build()
        self.switch_mode("blessings")

    # ── favorites helpers ─────────────────────────────────────────────────────
    def _load_favs(self, path):
        if path.exists():
            try: return set(json.loads(path.read_text(encoding="utf-8")))
            except Exception: pass
        return set()

    def _save_favs(self):
        for path, data in [(self._fav_path, self.favorites), (self._qfav_path, self.quote_favorites)]:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(sorted(data), ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception: pass

    # ── UI build ──────────────────────────────────────────────────────────────
    def _build(self):
        # header
        hdr = tk.Frame(self, bg="#1E3A6E", height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="מחולל ברכות וציטוטים", bg="#1E3A6E", fg="white",
                 font=("Segoe UI", 15, "bold")).pack(side="right", padx=20, pady=10)
        if self._logo_tk:
            tk.Label(hdr, image=self._logo_tk, bg="#1E3A6E").pack(side="right", padx=(0,8), pady=6)
        tabs = tk.Frame(hdr, bg="#1E3A6E")
        tabs.pack(side="left", padx=14, pady=8)
        self._bt_bless = tk.Button(tabs, text="💌  ברכות",   command=lambda: self.switch_mode("blessings"),
                                   bg="#F59E0B", fg="#0B1628", bd=0, padx=20, pady=7,
                                   font=("Segoe UI", 11, "bold"), cursor="hand2")
        self._bt_bless.pack(side="right", padx=4)
        self._bt_quote = tk.Button(tabs, text="📜  ציטוטים", command=lambda: self.switch_mode("quotes"),
                                   bg="#334155", fg="white",   bd=0, padx=20, pady=7,
                                   font=("Segoe UI", 11, "bold"), cursor="hand2")
        self._bt_quote.pack(side="right", padx=4)

        # action bar
        abar = tk.Frame(self, bg="white", highlightthickness=1, highlightbackground="#E2E8F0")
        abar.pack(fill="x")
        def abtn(txt, cmd, bg, fg="white"):
            b = tk.Button(abar, text=txt, command=cmd, bg=bg, fg=fg, bd=0,
                          padx=13, pady=8, font=("Segoe UI", 10, "bold"), cursor="hand2")
            b.pack(side="right", padx=5, pady=7)
            return b
        self._btn_use    = abtn("✅ הוסף לעיצוב",  self._use,        "#16A34A")
        self._btn_copy   = abtn("📋 העתק",          self._copy,       "#2563EB")
        self._btn_fav    = abtn("⭐ מועדף",          self._toggle_fav, "#FACC15", "#0B1628")
        self._btn_random = abtn("🎲 אקראי",          self._random,     "#7C3AED")
        tk.Label(abar, text="לחץ כפול על ברכה → הוסף לעיצוב", bg="white",
                 fg="#64748B", font=("Segoe UI", 9)).pack(side="left", padx=12)

        # filters
        self._fbox = tk.Frame(self, bg="#F8FAFC", highlightthickness=1, highlightbackground="#E2E8F0")
        self._fbox.pack(fill="x")
        self.sv_search = tk.StringVar()
        self.sv_f1 = tk.StringVar(value="הכל")
        self.sv_f2 = tk.StringVar(value="הכל")
        self.sv_prod  = tk.StringVar(value="הכל")
        self.sv_style = tk.StringVar(value="הכל")
        self._lbl_f1 = self._lbl_f2 = None
        self._cb_f1 = self._cb_f2 = self._cb_prod = self._cb_style = None
        self._build_filters()
        for v in [self.sv_search, self.sv_f1, self.sv_f2, self.sv_prod, self.sv_style]:
            v.trace_add("write", lambda *_: self.refresh())

        # body: treeview + side panel
        body = tk.Frame(self, bg="#F5F7FF")
        body.pack(fill="both", expand=True)

        lf = tk.Frame(body, bg="white", highlightthickness=1, highlightbackground="#E2E8F0")
        lf.pack(side="right", fill="both", expand=True)

        self._setup_tree_style()
        cols = ("fav","text","main","sub","product","style")
        self.tree = ttk.Treeview(lf, columns=cols, show="headings", selectmode="browse")
        for col, text, w, anc, stretch in [
            ("fav","★",44,"center",False), ("text","הטקסט",490,"e",True),
            ("main","אירוע",115,"center",False), ("sub","למי",138,"center",False),
            ("product","מוצר",105,"center",False), ("style","סגנון",148,"center",False),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor=anc, stretch=stretch)

        vsb = ttk.Scrollbar(lf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_sel)
        self.tree.bind("<Double-1>",         self._on_dbl)
        self.tree.bind("<Button-1>",         self._on_click)

        # side preview
        side = tk.Frame(body, bg="white", width=298, highlightthickness=1, highlightbackground="#E2E8F0")
        side.pack(side="left", fill="y"); side.pack_propagate(False)
        tk.Label(side, text="תצוגה מהירה", bg="white", fg="#1E3A6E",
                 font=("Segoe UI", 14, "bold")).pack(anchor="e", padx=14, pady=(12,4))
        self._meta = tk.Label(side, text="", bg="white", fg="#64748B",
                              font=("Segoe UI", 9), wraplength=270, justify="right")
        self._meta.pack(anchor="e", padx=14, pady=(0,4))
        self._prev_txt = tk.Text(side, wrap="word", height=9, bg="#F8FAFC", fg="#111827",
                                 font=("Segoe UI", 13), bd=0, padx=12, pady=12)
        self._prev_txt.pack(fill="x", padx=12, pady=8)
        self._prev_txt.configure(state="disabled")
        self._status = tk.Label(side, text="", bg="white", fg="#64748B",
                                 font=("Segoe UI", 9), wraplength=276, justify="right")
        self._status.pack(fill="x", padx=14, pady=6)

    def _setup_tree_style(self):
        s = ttk.Style()
        try:
            s.configure("BlessTree.Treeview", rowheight=58, font=("Segoe UI", 11),
                        background="white", fieldbackground="white", foreground="#0F172A")
            s.configure("BlessTree.Treeview.Heading", font=("Segoe UI", 10, "bold"))
            s.map("BlessTree.Treeview",
                  background=[("selected","#2563EB")],
                  foreground=[("selected","white")])
        except Exception:
            pass

    def _build_filters(self):
        for w in self._fbox.winfo_children(): w.destroy()
        def mf(lbl_text, var, col, is_entry=False):
            box = tk.Frame(self._fbox, bg="#F8FAFC")
            box.grid(row=0, column=col, padx=7, pady=7, sticky="ew")
            self._fbox.grid_columnconfigure(col, weight=1)
            lbl = tk.Label(box, text=lbl_text, bg="#F8FAFC", fg="#334155",
                           font=("Segoe UI", 9, "bold"))
            lbl.pack(anchor="e")
            if is_entry:
                w = tk.Entry(box, textvariable=var, font=("Segoe UI", 11),
                             relief="flat", bg="#EFF6FF", justify="right")
                w.pack(fill="x", ipady=5, pady=(2,0))
            else:
                w = ttk.Combobox(box, textvariable=var, state="readonly",
                                 justify="right", font=("Segoe UI", 10))
                w.pack(fill="x", pady=(2,0))
            return lbl, w
        self._lbl_search, _ = mf("חיפוש חופשי", self.sv_search, 0, is_entry=True)
        self._lbl_f1, self._cb_f1   = mf("אירוע", self.sv_f1,  1)
        self._lbl_f2, self._cb_f2   = mf("למי?",  self.sv_f2,  2)
        _,            self._cb_prod  = mf("מוצר",  self.sv_prod, 3)
        _,            self._cb_style = mf("סגנון", self.sv_style,4)
        btns = tk.Frame(self._fbox, bg="#F8FAFC")
        btns.grid(row=0, column=5, padx=7, pady=7, sticky="ns")
        tk.Button(btns, text="נקה", command=self._clear_f, bg="#EEF2FF", fg="#1E3A6E",
                  bd=0, padx=9, pady=6, font=("Segoe UI", 9, "bold")).pack(fill="x", pady=2)
        tk.Button(btns, text="אקראי", command=self._random, bg="#F59E0B", fg="#0B1628",
                  bd=0, padx=9, pady=6, font=("Segoe UI", 9, "bold")).pack(fill="x", pady=2)

    def _configure_tags(self):
        self.tree.tag_configure("default", background="white",   foreground="#0F172A")
        self.tree.tag_configure("quote",   background="#F8FAFC",  foreground="#0F172A")
        self.tree.tag_configure("source",  background="#FFF7ED",  foreground="#111827")
        for key, color in RECIPIENT_COLORS.items():
            self.tree.tag_configure(f"r_{key}", background=color, foreground="#0F172A")

    # ── mode ──────────────────────────────────────────────────────────────────
    def switch_mode(self, mode):
        self.mode = mode
        self.selected_item = None
        self.sv_search.set(""); self.sv_f1.set("הכל"); self.sv_f2.set("הכל")
        self.sv_prod.set("הכל"); self.sv_style.set("הכל")
        if mode == "blessings":
            self._bt_bless.configure(bg="#F59E0B", fg="#0B1628")
            self._bt_quote.configure(bg="#334155", fg="white")
            self.tree.heading("main", text="אירוע"); self.tree.heading("sub", text="למי")
            if self._lbl_f1: self._lbl_f1.config(text="אירוע")
            if self._lbl_f2: self._lbl_f2.config(text="למי?")
        else:
            self._bt_bless.configure(bg="#334155", fg="white")
            self._bt_quote.configure(bg="#F59E0B", fg="#0B1628")
            self.tree.heading("main", text="קטגוריה"); self.tree.heading("sub", text="מקור")
            if self._lbl_f1: self._lbl_f1.config(text="קטגוריה")
            if self._lbl_f2: self._lbl_f2.config(text="מקור")
        self._refresh_filter_values()
        self.refresh()

    def _refresh_filter_values(self):
        if self.mode == "blessings" and self.repo:
            v1 = ["הכל"] + self.repo.values("event")
            v2 = ["הכל"] + self.repo.values("recipient")
            vp = ["הכל"] + self.repo.values("product")
            vs = ["הכל"] + sorted({s for it in self.repo.items for s in it.get("style",[])})
        elif self.mode == "quotes" and self.quote_repo:
            v1 = ["הכל"] + self.quote_repo.values("category")
            v2 = ["הכל"] + self.quote_repo.source_groups()
            vp = ["הכל"] + self.quote_repo.values("product")
            vs = ["הכל"] + sorted({s for it in self.quote_repo.items for s in it.get("style",[])})
        else:
            v1 = v2 = vp = vs = ["הכל"]
        if self._cb_f1:    self._cb_f1["values"]    = v1
        if self._cb_f2:    self._cb_f2["values"]    = v2
        if self._cb_prod:  self._cb_prod["values"]  = vp
        if self._cb_style: self._cb_style["values"] = vs

    def _clear_f(self):
        self.sv_search.set(""); self.sv_f1.set("הכל"); self.sv_f2.set("הכל")
        self.sv_prod.set("הכל"); self.sv_style.set("הכל")

    # ── data refresh ──────────────────────────────────────────────────────────
    def refresh(self):
        q, e, r, p, s = (self.sv_search.get(), self.sv_f1.get(), self.sv_f2.get(),
                          self.sv_prod.get(), self.sv_style.get())
        if self.mode == "blessings" and self.repo:
            self.filtered = self.repo.search(q, e, r, p, s, self.favorites)
        elif self.mode == "quotes" and self.quote_repo:
            self.filtered = self.quote_repo.search(q, e, r, p, s, self.quote_favorites)
        else:
            self.filtered = []
        self.tree.delete(*self.tree.get_children())
        self._configure_tags()
        for i, item in enumerate(self.filtered):
            fav   = "★" if item.get("favorite") else "☆"
            text  = item.get("text","")
            short = text if len(text) <= 120 else text[:117] + "..."
            sty   = ", ".join(item.get("style",[])[:3])
            if self.mode == "blessings":
                main = item.get("event",""); sub = item.get("recipient","")
                tag  = self._row_tag(sub, main)
            else:
                main = item.get("category",""); sub = item.get("source","")
                tag  = "source" if item.get("section") == "מקורות וברכות" else "quote"
            self.tree.insert("", "end", iid=str(i),
                             values=(fav, short, main, sub, item.get("product",""), sty),
                             tags=(tag,))
        n = len(self.filtered)
        mode_str = "ברכות" if self.mode == "blessings" else "ציטוטים"
        self._status.config(text=f"נמצאו {n} {mode_str}. לחיצה כפולה = הוסף לעיצוב")
        self._clear_preview()

    def _row_tag(self, recipient, event):
        if recipient in RECIPIENT_COLORS: return f"r_{recipient}"
        if event == "גיוס": return "r_מתגייס"
        return "default"

    def _clear_preview(self):
        self._meta.config(text="")
        self._prev_txt.configure(state="normal"); self._prev_txt.delete("1.0","end")
        self._prev_txt.configure(state="disabled")

    def _on_sel(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        self.selected_item = self.filtered[int(sel[0])]
        if self.mode == "blessings":
            meta = f"{self.selected_item.get('event','')} • {self.selected_item.get('recipient','')} • {self.selected_item.get('product','')}"
        else:
            meta = f"{self.selected_item.get('category','')} • {self.selected_item.get('source','')}"
        self._meta.config(text=meta)
        self._prev_txt.configure(state="normal"); self._prev_txt.delete("1.0","end")
        self._prev_txt.insert("1.0", self.selected_item.get("text",""))
        self._prev_txt.configure(state="disabled")

    def _on_dbl(self, event):
        col = self.tree.identify_column(event.x)
        if self.tree.identify("region", event.x, event.y) == "cell" and col == "#1":
            self._toggle_fav()
        else:
            self._use()

    def _on_click(self, event):
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if self.tree.identify("region", event.x, event.y) == "cell" and col == "#1" and row:
            self.tree.selection_set(row); self._on_sel(); self._toggle_fav()
            return "break"

    def _use(self):
        if not self.selected_item:
            self._status.config(text="בחר/י ברכה תחילה."); return
        self.on_selected(self.selected_item.get("text",""))

    def _copy(self):
        if not self.selected_item: return
        try:
            self.clipboard_clear(); self.clipboard_append(self.selected_item.get("text",""))
            self._status.config(text="הועתק ללוח ✅")
        except Exception: pass

    def _toggle_fav(self):
        if not self.selected_item: return
        favs    = self.favorites if self.mode == "blessings" else self.quote_favorites
        item_id = self.selected_item.get("id")
        if item_id in favs: favs.remove(item_id)
        else:               favs.add(item_id)
        self._save_favs(); self.refresh()

    def _random(self):
        if not self.filtered: return
        idx = random.randrange(len(self.filtered))
        self.tree.selection_set(str(idx)); self.tree.see(str(idx)); self._on_sel()


# ── Collapsible panel ─────────────────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text, delay=450):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after = None
        self._tip = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._after = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after:
            self.widget.after_cancel(self._after)
            self._after = None

    def _show(self):
        if self._tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self._tip, text=self.text, bg="#0F172A", fg="white",
            font=("Segoe UI", 9), padx=8, pady=5, relief="solid", bd=1,
            justify="right",
        ).pack()

    def _hide(self, _event=None):
        self._cancel()
        if self._tip:
            self._tip.destroy()
            self._tip = None


class Collapsible:
    def __init__(self, parent, title, start_open=True, bg="#1A2C52"):
        self.frame = tk.Frame(parent, bg=bg)
        self.frame.pack(fill="x", padx=16, pady=4)
        self.open  = tk.BooleanVar(value=start_open)
        self.title = title
        self.bg    = bg
        btn_text = ("▼  " if start_open else "▶  ") + title
        self.btn = tk.Button(self.frame, text=btn_text, command=self.toggle,
                             bg="#233660", fg=BRAND["gold"], bd=0, anchor="e",
                             font=("Segoe UI", 10, "bold"), padx=12, pady=7, cursor="hand2")
        self.btn.pack(fill="x")
        self.body = tk.Frame(self.frame, bg=bg, padx=10, pady=4)
        if start_open: self.body.pack(fill="x")

    def toggle(self):
        if self.open.get():
            self.body.pack_forget(); self.open.set(False)
            self.btn.configure(text="▶  " + self.title)
        else:
            self.body.pack(fill="x"); self.open.set(True)
            self.btn.configure(text="▼  " + self.title)


# ── Main Application ──────────────────────────────────────────────────────────
class BlessingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hadish Blessing Designer v0.5")
        self._settings_cache = self._load_settings()
        set_brand_theme(self._settings_cache.get("theme", "dark"))
        self._show_splash()
        # Respect Windows taskbar — cap height to screen minus ~70px
        sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
        win_w = min(1400, sw); win_h = min(860, sh - 70)
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(1000, 660)
        self.root.configure(bg=BRAND["bg"])
        self.blessings  = json.loads(BLESSINGS_PATH.read_text(encoding="utf-8"))
        self.last_image = None
        self.tk_preview = None
        self.asset_thumbs = []
        self._blessing_widget = None
        # logos (PhotoImage must stay referenced — store on self)
        self._logo_nav     = None  # nav bar   ~44 px tall
        self._logo_preview = None  # preview header ~36 px tall
        self._snackbar_after = None
        self.init_state()
        self.build_style()
        self.build_menu()
        self.build_ui()
        self.show_step("size")

    # ── state ─────────────────────────────────────────────────────────────────
    def _show_splash(self):
        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        splash.configure(bg=BRAND["bg"])
        w, h = 420, 240
        x = max(0, (self.root.winfo_screenwidth() - w) // 2)
        y = max(0, (self.root.winfo_screenheight() - h) // 2)
        splash.geometry(f"{w}x{h}+{x}+{y}")
        logo = _make_logo_tk(82)
        splash._logo = logo
        if logo:
            tk.Label(splash, image=logo, bg=BRAND["bg"]).pack(pady=(34, 12))
        tk.Label(splash, text="Hadish Blessing Designer", bg=BRAND["bg"],
                 fg=BRAND["gold"], font=("Segoe UI Semibold", 18)).pack()
        pulse = tk.Label(splash, text="●  ●  ●", bg=BRAND["bg"], fg=BRAND["muted"],
                         font=("Segoe UI", 14))
        pulse.pack(pady=14)
        frames = ["●  ○  ○", "○  ●  ○", "○  ○  ●", "○  ●  ○"]
        def animate(i=0):
            if not splash.winfo_exists():
                return
            pulse.configure(text=frames[i % len(frames)])
            splash.after(110, animate, i + 1)
        animate()
        self.root.after(520, splash.destroy)

    def _load_settings(self):
        if SETTINGS_PATH.exists():
            try:
                return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_settings(self):
        data = {
            "font_favorites": sorted(getattr(self, "font_favorites", set())),
            "style_presets": getattr(self, "style_presets", {}),
            "theme": getattr(self, "theme_mode", tk.StringVar(value="dark")).get(),
        }
        try:
            SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def init_state(self):
        self.step_order  = ["size","background","frame","blessings","text"]
        self.step_titles = {
            "size":       "בחירת מידה",
            "background": "בחירת רקע",
            "frame":      "בחירת מסגרת",
            "blessings":  "מחולל ברכות",
            "text":       "עיצוב טקסט ויצוא",
        }
        self.current_step = "size"
        self.product      = tk.StringVar(value="A5")
        self.orientation  = tk.StringVar(value="Portrait")
        self.category     = tk.StringVar(value="יום הולדת")
        self.style_var    = tk.StringVar(value="מרגש")
        self.name         = tk.StringVar(value="שם")
        self.title_text   = tk.StringVar(value="")
        self.bg           = tk.StringVar(value="birthday_fun.png")
        self.frame_var    = tk.StringVar(value="gold_double.png")
        self.width_cm     = tk.DoubleVar(value=14.8)
        self.height_cm    = tk.DoubleVar(value=21.0)
        self.size_unit    = tk.StringVar(value="cm")
        self.custom_width = tk.StringVar(value="14.8")
        self.custom_height= tk.StringVar(value="21.0")
        settings = getattr(self, "_settings_cache", self._load_settings())
        self.font_favorites = set(settings.get("font_favorites", []))
        self.style_presets = settings.get("style_presets", {})
        self.theme_mode = tk.StringVar(value=settings.get("theme", "dark"))
        self.preset_name = tk.StringVar(value="")
        # card
        self.card_enabled = tk.BooleanVar(value=True)
        self.card_color   = tk.StringVar(value="#FFFFFF")
        self.card_opacity = tk.IntVar(value=58)
        # title style
        self.title_color  = tk.StringVar(value="#144C8A")
        self.title_size   = tk.IntVar(value=72)
        self.title_shadow = tk.BooleanVar(value=False)
        self.title_italic = tk.BooleanVar(value=False)
        self.title_gradient = tk.BooleanVar(value=False)
        self.title_preset = tk.StringVar(value="נקי כחול")
        self.title_font   = tk.StringVar(value="segoeui")
        self.title_x_off  = tk.IntVar(value=0)
        self.title_y_off  = tk.IntVar(value=0)
        # body style
        self.body_color   = tk.StringVar(value="#1E293B")
        self.body_size    = tk.IntVar(value=54)
        self.body_shadow  = tk.BooleanVar(value=False)
        self.body_italic  = tk.BooleanVar(value=False)
        self.body_gradient = tk.BooleanVar(value=False)
        self.body_line_spacing = tk.IntVar(value=122)
        self.body_preset  = tk.StringVar(value="נקי כהה")
        self.body_font    = tk.StringVar(value="segoeui")
        self.body_x_off   = tk.IntVar(value=0)
        self.body_y_off   = tk.IntVar(value=0)
        self._text_cache  = ""

    # ── styles ────────────────────────────────────────────────────────────────
    def build_style(self):
        s = ttk.Style(); s.theme_use("clam")
        bg = BRAND["bg"]; panel = BRAND["panel"]; surface = BRAND["surface"]
        s.configure("TFrame",        background=bg)
        s.configure("Panel.TFrame",  background=panel)
        s.configure("Surface.TFrame",background=surface)
        s.configure("TLabel",        background=panel, foreground=BRAND["text"],  font=("Segoe UI", 10))
        s.configure("Muted.TLabel",  background=panel, foreground=BRAND["muted"], font=("Segoe UI", 9))
        s.configure("Title.TLabel",  background=panel, foreground=BRAND["gold"],  font=("Segoe UI Semibold", 17))
        s.configure("BigTitle.TLabel", background=bg,  foreground=BRAND["gold"],  font=("Segoe UI Semibold", 20))
        s.configure("TButton",       font=("Segoe UI Semibold", 10), padding=8)
        s.configure("Primary.TButton", font=("Segoe UI Semibold", 11), padding=10)
        s.configure("TCombobox",     padding=5)
        s.configure("TScrollbar",    background=BRAND["border"])

    # ── menu ──────────────────────────────────────────────────────────────────
    def build_menu(self):
        menubar    = tk.Menu(self.root)
        steps_menu = tk.Menu(menubar, tearoff=0, bg=BRAND["surface"], fg=BRAND["text"])
        for key in self.step_order:
            steps_menu.add_command(label=self.step_titles[key], command=lambda k=key: self.show_step(k))
        menubar.add_cascade(label="שלבים", menu=steps_menu)
        export_menu = tk.Menu(menubar, tearoff=0, bg=BRAND["surface"], fg=BRAND["text"])
        export_menu.add_command(label="יצוא PNG",         command=self.export_png)
        export_menu.add_command(label="יצוא PDF",         command=self.export_pdf)
        export_menu.add_separator()
        export_menu.add_command(label="פתח תיקיית יצוא", command=self.open_exports)
        menubar.add_cascade(label="יצוא", menu=export_menu)
        view_menu = tk.Menu(menubar, tearoff=0, bg=BRAND["surface"], fg=BRAND["text"])
        view_menu.add_command(label="Toggle Dark/Light", command=self.toggle_theme)
        menubar.add_cascade(label="View", menu=view_menu)
        self.root.config(menu=menubar)

    # ── UI skeleton ───────────────────────────────────────────────────────────
    def build_ui(self):
        # ── persistent nav bar (bottom, always visible) ──────────────────────
        self.nav_bar = tk.Frame(self.root, bg=BRAND["bg"], height=62)
        self.nav_bar.pack(side="bottom", fill="x", padx=14, pady=(4,12))
        self.nav_bar.pack_propagate(False)

        self.back_btn = tk.Button(
            self.nav_bar, text="⬅  חזור", command=self.prev_step,
            bg=BRAND["red"], fg="white", activebackground="#B91C1C",
            font=("Segoe UI Semibold", 13), padx=22, pady=10, bd=0, cursor="hand2")
        self.back_btn.pack(side="left", padx=4, pady=6)

        self.next_btn = tk.Button(
            self.nav_bar, text="הבא  ➜", command=self.next_step,
            bg=BRAND["green"], fg="white", activebackground="#15803D",
            font=("Segoe UI Semibold", 13), padx=22, pady=10, bd=0, cursor="hand2")
        self.next_btn.pack(side="right", padx=4, pady=6)

        self.progress_lbl = tk.Label(self.nav_bar, text="", bg=BRAND["bg"],
                                     fg=BRAND["muted"], font=("Segoe UI", 10))
        self.progress_lbl.pack(side="left", padx=16)
        self.theme_btn = tk.Button(
            self.nav_bar, text=("☀" if self.theme_mode.get() == "dark" else "🌙"),
            command=self.toggle_theme, bg=BRAND["surface"], fg=BRAND["text"],
            bd=0, padx=10, pady=6, cursor="hand2", font=("Segoe UI", 12, "bold"))
        self.theme_btn.pack(side="left", padx=4, pady=8)
        Tooltip(self.theme_btn, "החלף מצב כהה/בהיר")
        self.step_title_lbl = tk.Label(self.nav_bar, text="", bg=BRAND["bg"],
                                       fg=BRAND["gold"], font=("Segoe UI Semibold", 14))
        self.step_title_lbl.pack(side="right", padx=16)

        self.progress_dots = tk.Frame(self.nav_bar, bg=BRAND["bg"])
        self.progress_dots.pack(side="right", padx=10)
        self._dot_labels = []
        for i in range(1, 6):
            lbl = tk.Label(
                self.progress_dots, text=str(i), width=2, height=1,
                bg=BRAND["surface"], fg=BRAND["muted"],
                font=("Segoe UI Semibold", 10), relief="flat",
            )
            lbl.pack(side="left", padx=3)
            self._dot_labels.append(lbl)

        # logo — centered in nav bar
        self._logo_nav = _make_logo_tk(46)
        if self._logo_nav:
            tk.Label(self.nav_bar, image=self._logo_nav, bg=BRAND["bg"],
                     cursor="hand2").pack(side="left", padx=24)

        # ── content area ─────────────────────────────────────────────────────
        self.content = tk.Frame(self.root, bg=BRAND["bg"])
        self.content.pack(fill="both", expand=True, padx=14, pady=(12,4))

        # normal view (left controls + right preview)
        self.normal_view = tk.Frame(self.content, bg=BRAND["bg"])

        self.left = tk.Frame(self.normal_view, bg=BRAND["panel"], width=516)
        self.left.pack(side="left", fill="both", padx=(0,10))
        self.left.pack_propagate(False)

        self.right = tk.Frame(self.normal_view, bg=BRAND["panel"])
        self.right.pack(side="right", fill="both", expand=True)

        preview_hdr = tk.Frame(self.right, bg=BRAND["panel"])
        preview_hdr.pack(fill="x", padx=18, pady=(14,4))
        tk.Label(preview_hdr, text="תצוגה מקדימה", bg=BRAND["panel"],
                 fg=BRAND["gold"], font=("Segoe UI Semibold", 14)).pack(side="right")
        self._logo_preview = _make_logo_tk(36)
        if self._logo_preview:
            tk.Label(preview_hdr, image=self._logo_preview,
                     bg=BRAND["panel"]).pack(side="left", padx=4)
        self.preview_label = tk.Label(self.right, text="", bg=BRAND["panel"])
        self.preview_label.pack(fill="both", expand=True, padx=16, pady=12)
        self.preview_label.bind("<ButtonPress-1>", self._preview_drag_start)
        self.preview_label.bind("<B1-Motion>", self._preview_drag_move)
        self.preview_label.bind("<ButtonRelease-1>", self._preview_drag_end)

        # step header inside left panel
        self._step_hdr_frame = tk.Frame(self.left, bg=BRAND["panel"])
        self._step_hdr_frame.pack(fill="x", padx=0, pady=(14,0))

        # step area (scrollable)
        self._left_canvas = tk.Canvas(self.left, bg=BRAND["panel"], highlightthickness=0)
        self._left_vsb    = ttk.Scrollbar(self.left, orient="vertical", command=self._left_canvas.yview)
        self._left_canvas.configure(yscrollcommand=self._left_vsb.set)
        self._left_vsb.pack(side="right", fill="y")
        self._left_canvas.pack(side="left", fill="both", expand=True)
        self.step_area = tk.Frame(self._left_canvas, bg=BRAND["panel"])
        self._sa_window = self._left_canvas.create_window((0,0), window=self.step_area, anchor="nw")
        self.step_area.bind("<Configure>", self._on_step_area_resize)
        self._left_canvas.bind("<Configure>", self._on_canvas_resize)
        self._bind_mousewheel(self._left_canvas)

        # blessing full-screen view
        self.blessing_view = tk.Frame(self.content, bg=BRAND["bg"])
        self.snackbar = tk.Label(
            self.root, text="", bg="#111827", fg="white",
            font=("Segoe UI", 10, "bold"), padx=16, pady=8,
        )

    def _on_step_area_resize(self, event):
        self._left_canvas.configure(scrollregion=self._left_canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self._left_canvas.itemconfig(self._sa_window, width=event.width)

    def _bind_mousewheel(self, widget):
        def on_wheel(event):
            widget.yview_scroll(int(-1*(event.delta/120)), "units")
        widget.bind_all("<MouseWheel>", on_wheel)

    # ── step routing ──────────────────────────────────────────────────────────
    def clear_step(self):
        for w in self.step_area.winfo_children(): w.destroy()

    def show_step(self, step):
        self.current_step = step
        idx = self.step_order.index(step) + 1
        total = len(self.step_order)
        self.progress_lbl.configure(text=f"שלב {idx} מתוך {total}")
        self.step_title_lbl.configure(text=self.step_titles[step])
        self._update_progress_dots(idx)

        if step == "blessings":
            self._enter_blessing_fullscreen()
        else:
            self._exit_blessing_fullscreen()
            self.clear_step()
            if   step == "size":       self.build_size_step()
            elif step == "background": self.build_background_step()
            elif step == "frame":      self.build_frame_step()
            else:                      self.build_text_step()
            # flush layout so text_box.get() returns the inserted text reliably
            self.root.update_idletasks()
            self.render_preview()
            self._animate_step_in()
            if step == "text":
                # belt-and-suspenders: re-render once widgets are fully settled
                self.root.after(80, self.render_preview)

        self.back_btn.configure(state=("disabled" if idx == 1 else "normal"))
        self.next_btn.configure(text=("יצוא PNG  ➜" if step == "text" else "הבא  ➜"))

    def _update_progress_dots(self, active_idx):
        for i, lbl in enumerate(getattr(self, "_dot_labels", []), start=1):
            done = i < active_idx
            active = i == active_idx
            lbl.configure(
                bg=BRAND["gold"] if active else (BRAND["green"] if done else BRAND["surface"]),
                fg=BRAND["bg"] if (active or done) else BRAND["muted"],
            )

    def notify(self, text):
        if self._snackbar_after:
            self.root.after_cancel(self._snackbar_after)
            self._snackbar_after = None
        self.snackbar.configure(text=text)
        self.snackbar.place(relx=0.5, rely=1.0, anchor="s", y=-82)
        self._snackbar_after = self.root.after(3000, self.snackbar.place_forget)

    def _animate_step_in(self):
        try:
            width = max(80, self._left_canvas.winfo_width())
            self._left_canvas.coords(self._sa_window, width, 0)
            steps = 9
            def slide(i=0):
                if i > steps:
                    self._left_canvas.coords(self._sa_window, 0, 0)
                    return
                x = int(width * (1 - i / steps))
                self._left_canvas.coords(self._sa_window, x, 0)
                self.root.after(14, slide, i + 1)
            slide()
        except Exception:
            pass

    def toggle_theme(self):
        new_mode = "light" if self.theme_mode.get() == "dark" else "dark"
        self.theme_mode.set(new_mode)
        set_brand_theme(new_mode)
        self._save_settings()
        self.build_style()
        for child in list(self.root.winfo_children()):
            child.destroy()
        self.build_menu()
        self.build_ui()
        self.show_step(self.current_step)
        self.notify("Theme updated")

    def _enter_blessing_fullscreen(self):
        self.normal_view.pack_forget()
        # destroy old blessing widget if exists
        for w in self.blessing_view.winfo_children(): w.destroy()
        self._blessing_widget = EmbeddedBlessingWidget(
            self.blessing_view, on_selected=self._on_blessing_chosen)
        self._blessing_widget.pack(fill="both", expand=True)
        self.blessing_view.pack(fill="both", expand=True)

    def _exit_blessing_fullscreen(self):
        if self.blessing_view.winfo_ismapped():
            self.blessing_view.pack_forget()
        if not self.normal_view.winfo_ismapped():
            self.normal_view.pack(fill="both", expand=True)

    def _on_blessing_chosen(self, text):
        self._text_cache = text
        self.show_step("text")

    def next_step(self):
        if self.current_step == "text":
            self.export_png(); return
        if self.current_step == "blessings":
            # user pressed Next without picking — go to text with whatever is cached
            self.show_step("text"); return
        idx = self.step_order.index(self.current_step)
        self.show_step(self.step_order[idx + 1])

    def prev_step(self):
        idx = self.step_order.index(self.current_step)
        if idx > 0: self.show_step(self.step_order[idx - 1])

    # ── Step 1: size ──────────────────────────────────────────────────────────
    def build_size_step(self):
        self._section_hint("בחר/י את גודל הברכה. ניתן לשנות בכל עת.")
        for key, data in PRODUCT_PRESETS_CM.items():
            sel = self.product.get() == key
            bg  = BRAND["accent"] if sel else BRAND["surface"]
            card = tk.Frame(self.step_area, bg=bg, padx=12, pady=10)
            card.pack(fill="x", padx=16, pady=4)
            tk.Label(card, text=data["title"], bg=bg, fg=BRAND["gold"],
                     font=("Segoe UI Semibold", 14), anchor="e").pack(fill="x")
            tk.Label(card, text=data["desc"], bg=bg, fg=BRAND["text"],
                     font=("Segoe UI", 10), anchor="e", justify="right", wraplength=420).pack(fill="x", pady=(2,6))
            tk.Button(card, text="בחר", command=lambda k=key: self.select_product(k),
                      bg=BRAND["gold"], fg=BRAND["bg"], bd=0, padx=14, pady=5,
                      font=("Segoe UI", 10, "bold"), cursor="hand2").pack(anchor="e")
            for w in (card,): w.bind("<Button-1>", lambda e, k=key: self.select_product(k))

        sep = tk.Frame(self.step_area, bg=BRAND["border"], height=1)
        sep.pack(fill="x", padx=16, pady=(12,4))
        self._lbl("מידה ידנית בס״מ")
        row = tk.Frame(self.step_area, bg=BRAND["panel"])
        row.pack(fill="x", padx=16, pady=4)
        for lbl, var in [("רוחב", self.width_cm), ("גובה", self.height_cm)]:
            tk.Label(row, text=lbl, bg=BRAND["panel"], fg=BRAND["muted"],
                     font=("Segoe UI",10)).pack(side="right", padx=(8,2))
            tk.Entry(row, textvariable=var, width=7, justify="center",
                     bg=BRAND["surface"], fg=BRAND["text"], insertbackground="white",
                     relief="flat", font=("Segoe UI",11)).pack(side="right", padx=2)
        tk.Button(row, text="עדכן", command=lambda: [
            self.product.set("מותאם אישית"), self.render_preview()],
            bg=BRAND["orange"], fg="white", bd=0, padx=10, pady=4,
            font=("Segoe UI",9,"bold"), cursor="hand2").pack(side="right", padx=8)
        unit_row = tk.Frame(self.step_area, bg=BRAND["panel"])
        unit_row.pack(fill="x", padx=16, pady=(0,4))
        tk.Label(unit_row, text="יחידת מידה לערכים הידניים", bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI",9)).pack(side="right", padx=6)
        ttk.Combobox(unit_row, textvariable=self.size_unit, values=["cm", "inch"],
                     state="readonly", width=8, justify="center").pack(side="right")
        tk.Button(unit_row, text="המר ועדכן", command=self.apply_custom_size,
                  bg=BRAND["surface"], fg=BRAND["text"], bd=0, padx=10, pady=4,
                  font=("Segoe UI",9,"bold"), cursor="hand2").pack(side="right", padx=8)
        self._combo("אוריינטציה", self.orientation, ["Portrait","Landscape","Auto"], self.render_preview)

    def select_product(self, key):
        self.product.set(key)
        w, h = PRODUCT_PRESETS_CM[key]["size"]
        self.width_cm.set(w); self.height_cm.set(h)
        self.render_preview()
        self.show_step("background")

    def apply_custom_size(self):
        try:
            w = float(str(self.width_cm.get()).replace(",", "."))
            h = float(str(self.height_cm.get()).replace(",", "."))
            if self.size_unit.get() == "inch":
                w *= 2.54
                h *= 2.54
            if w <= 0 or h <= 0:
                raise ValueError("size must be positive")
            self.width_cm.set(round(w, 3))
            self.height_cm.set(round(h, 3))
            self.product.set("מותאם אישית")
            self.render_preview()
            self.notify("המידה עודכנה")
        except Exception:
            self.notify("לא הצלחתי לקרוא את המידה")

    # ── Step 2: background ────────────────────────────────────────────────────
    def build_background_step(self):
        self._section_hint("בחר/י רקע. התצוגה מתעדכנת מיד.")
        self.asset_grid(BG_DIR, self.bg, "background", columns=3, height=480)

    # ── Step 3: frame ─────────────────────────────────────────────────────────
    def build_frame_step(self):
        self._section_hint("בחר/י מסגרת, או המשך ללא מסגרת.")
        bg_none = BRAND["accent"] if self.frame_var.get() == "__none__" else BRAND["surface"]
        card = tk.Frame(self.step_area, bg=bg_none, padx=12, pady=10)
        card.pack(fill="x", padx=16, pady=(0,8))
        tk.Label(card, text="ללא מסגרת", bg=bg_none, fg=BRAND["gold"],
                 font=("Segoe UI Semibold", 13), anchor="e").pack(fill="x")
        tk.Label(card, text="מתאים לעיצוב נקי כשהרקע דומיננטי.", bg=bg_none, fg=BRAND["text"],
                 anchor="e", justify="right").pack(fill="x")
        tk.Button(card, text="בחר ללא מסגרת", command=self.select_frame_none,
                  bg=BRAND["gold"], fg=BRAND["bg"], bd=0, padx=14, pady=5,
                  font=("Segoe UI",10,"bold"), cursor="hand2").pack(anchor="e", pady=(6,0))
        self.asset_grid(FRAME_DIR, self.frame_var, "frame", columns=3, height=380)

    def select_frame_none(self):
        self.frame_var.set("__none__"); self.render_preview(); self.show_step("frame")

    # ── Step 5: text editor ───────────────────────────────────────────────────
    def build_text_step(self):
        self._section_hint("עצב/י את הטקסט. Ctrl+C/V/A ותפריט ימני עובדים בכל תיבה.")

        # ── Title collapsible ─────────────────────────────────────────────
        title_col = Collapsible(self.step_area, "כותרת", start_open=True)
        self._lbl2("טקסט כותרת", title_col.body)
        ent_title = tk.Entry(title_col.body, textvariable=self.title_text,
                             justify="right", bg=BRAND["surface"], fg=BRAND["text"],
                             insertbackground="white", relief="flat",
                             font=("Segoe UI",12))
        ent_title.pack(fill="x", pady=4, padx=4)
        ent_title.bind("<KeyRelease>", lambda e: self.render_preview())
        self._add_copy_paste(ent_title)

        r = tk.Frame(title_col.body, bg=BRAND["panel"])
        r.pack(fill="x", pady=4)
        self._inline_btn(r, "צבע כותרת", self.pick_title_color)
        self._chk(r, "צל",  self.title_shadow)
        self._chk(r, "נטוי", self.title_italic)
        self._chk(r, "Gradient", self.title_gradient)

        self._lbl2("גודל כותרת", title_col.body)
        tk.Scale(title_col.body, from_=24, to=150, orient="horizontal",
                 variable=self.title_size, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)

        self._font_combo("גופן כותרת", self.title_font, title_col.body)
        self._combo2("סגנון כותרת", self.title_preset,
                     ["נקי כחול","זהב אלגנטי","אדום חגיגי","כהה עם צל"],
                     self.apply_title_preset, title_col.body)

        self._lbl2("מיקום X (אופקי)", title_col.body)
        tk.Scale(title_col.body, from_=-50, to=50, orient="horizontal",
                 variable=self.title_x_off, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)
        self._lbl2("מיקום Y (אנכי)", title_col.body)
        tk.Scale(title_col.body, from_=-50, to=50, orient="horizontal",
                 variable=self.title_y_off, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)

        # ── Body collapsible ──────────────────────────────────────────────
        body_col = Collapsible(self.step_area, "ברכה / גוף טקסט", start_open=True)
        self.text_box = self._make_text(body_col.body, height=8)
        self.text_box.pack(fill="x", pady=(0,6), padx=4)
        self.text_box.delete("1.0","end")
        self.text_box.insert("1.0", self._text_cache)
        self.text_box.bind("<KeyRelease>", lambda e: self.cache_and_render())

        rb = tk.Frame(body_col.body, bg=BRAND["panel"])
        rb.pack(fill="x", pady=4)
        self._inline_btn(rb, "צבע טקסט",    self.pick_body_color)
        self._inline_btn(rb, "הדבק מהלוח",   self.paste_to_main)
        self._chk(rb, "צל",  self.body_shadow)
        self._chk(rb, "נטוי", self.body_italic)
        self._chk(rb, "Gradient", self.body_gradient)

        self._lbl2("גודל טקסט", body_col.body)
        tk.Scale(body_col.body, from_=18, to=110, orient="horizontal",
                 variable=self.body_size, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)

        self._lbl2("מרווח בין שורות", body_col.body)
        tk.Scale(body_col.body, from_=80, to=180, orient="horizontal",
                 variable=self.body_line_spacing, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)

        self._font_combo("גופן ברכה", self.body_font, body_col.body)
        self._combo2("סגנון טקסט", self.body_preset,
                     ["נקי כהה","כחול רך","רומנטי","מודרני עם צל"],
                     self.apply_body_preset, body_col.body)

        self._lbl2("מיקום X (אופקי)", body_col.body)
        tk.Scale(body_col.body, from_=-50, to=50, orient="horizontal",
                 variable=self.body_x_off, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)
        self._lbl2("מיקום Y (אנכי)", body_col.body)
        tk.Scale(body_col.body, from_=-50, to=50, orient="horizontal",
                 variable=self.body_y_off, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)

        # ── Card bg collapsible ───────────────────────────────────────────
        card_col = Collapsible(self.step_area, "רקע מאחורי הטקסט", start_open=False)
        self._chk2(card_col.body, "הצג תיבה", self.card_enabled)
        self._lbl2("שקיפות תיבה", card_col.body)
        tk.Scale(card_col.body, from_=0, to=100, orient="horizontal",
                 variable=self.card_opacity, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)
        self._inline_btn(card_col.body, "צבע תיבה", self.pick_card_color, anchor="e")

        preset_col = Collapsible(self.step_area, "Presets", start_open=False)
        preset_row = tk.Frame(preset_col.body, bg=BRAND["panel"])
        preset_row.pack(fill="x", pady=4)
        self.preset_combo = ttk.Combobox(
            preset_row, textvariable=self.preset_name,
            values=sorted(self.style_presets.keys()), state="normal", justify="right")
        self.preset_combo.pack(side="right", fill="x", expand=True, padx=4)
        for txt, cmd in [
            ("שמור", self.save_style_preset),
            ("טען", self.load_style_preset),
            ("מחק", self.delete_style_preset),
        ]:
            btn = tk.Button(preset_row, text=txt, command=cmd, bg=BRAND["surface"],
                            fg=BRAND["text"], bd=0, padx=10, pady=5,
                            font=("Segoe UI",9,"bold"), cursor="hand2")
            btn.pack(side="right", padx=3)
            Tooltip(btn, txt)

        # ── Export / SPP collapsible ──────────────────────────────────────
        exp_col = Collapsible(self.step_area, "יצוא ושיתוף", start_open=True)
        row_exp = tk.Frame(exp_col.body, bg=BRAND["panel"])
        row_exp.pack(fill="x", pady=4)
        for txt, cmd, bg in [
            ("יצוא PNG",         self.export_png,    BRAND["accent"]),
            ("יצוא PDF",         self.export_pdf,    BRAND["surface"]),
            ("תיקיית יצוא",      self.open_exports,  BRAND["surface"]),
            ("שלח ל-SPP  🔗",    self._spp_stub,     BRAND["orange"]),
        ]:
            tk.Button(row_exp, text=txt, command=cmd, bg=bg, fg="white",
                      bd=0, padx=12, pady=6, font=("Segoe UI",10,"bold"),
                      cursor="hand2").pack(side="right", padx=3)

    def _spp_stub(self):
        self.notify("חיבור ל-SPP יתווסף בגרסה הבאה")

    # ── widget helpers ────────────────────────────────────────────────────────
    def _section_hint(self, text):
        tk.Label(self.step_area, text=text, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI",9), wraplength=470, justify="right",
                 anchor="e").pack(fill="x", padx=18, pady=(6,8))

    def _lbl(self, text):
        tk.Label(self.step_area, text=text, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI",9)).pack(anchor="e", padx=18, pady=(4,0))

    def _lbl2(self, text, parent):
        tk.Label(parent, text=text, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI",9)).pack(anchor="e", pady=(4,0))

    def _chk(self, parent, text, var):
        tk.Checkbutton(parent, text=text, variable=var, command=self.render_preview,
                       bg=BRAND["panel"], fg=BRAND["text"], selectcolor=BRAND["bg"],
                       activebackground=BRAND["panel"]).pack(side="right", padx=6)

    def _chk2(self, parent, text, var):
        tk.Checkbutton(parent, text=text, variable=var, command=self.render_preview,
                       bg=BRAND["panel"], fg=BRAND["text"], selectcolor=BRAND["bg"],
                       activebackground=BRAND["panel"], anchor="e").pack(fill="x")

    def _inline_btn(self, parent, text, cmd, anchor="right"):
        btn = tk.Button(parent, text=text, command=cmd, bg=BRAND["surface"], fg=BRAND["text"],
                        bd=0, padx=10, pady=5, font=("Segoe UI",9,"bold"),
                        cursor="hand2")
        btn.pack(side=anchor, padx=4)
        Tooltip(btn, text)
        return btn

    def _combo(self, label, var, values, command=None):
        row = tk.Frame(self.step_area, bg=BRAND["panel"])
        row.pack(fill="x", padx=18, pady=4)
        tk.Label(row, text=label, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI",9)).pack(anchor="e")
        cb = ttk.Combobox(row, textvariable=var, values=values, state="readonly", justify="right")
        cb.pack(fill="x", pady=2)
        if command: cb.bind("<<ComboboxSelected>>", lambda e: command())
        return cb

    def _combo2(self, label, var, values, command=None, parent=None):
        parent = parent or self.step_area
        row = tk.Frame(parent, bg=BRAND["panel"])
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI",9)).pack(anchor="e")
        cb = ttk.Combobox(row, textvariable=var, values=values, state="readonly", justify="right")
        cb.pack(fill="x", pady=2)
        if command: cb.bind("<<ComboboxSelected>>", lambda e: command())
        return cb

    def _font_combo(self, label, var, parent):
        row = tk.Frame(parent, bg=BRAND["panel"])
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI",9)).pack(anchor="e")
        top = tk.Frame(row, bg=BRAND["panel"])
        top.pack(fill="x", pady=2)
        star = tk.Button(top, text="☆", command=lambda: self.toggle_font_favorite(var),
                         bg=BRAND["surface"], fg=BRAND["gold"], bd=0,
                         width=3, cursor="hand2", font=("Segoe UI", 10, "bold"))
        star.pack(side="left", padx=(0,4))
        Tooltip(star, "סמן גופן כמועדף")
        cb = ttk.Combobox(top, textvariable=var, values=ordered_fonts(self.font_favorites),
                          state="normal", justify="right", font=("Segoe UI",9))
        cb.pack(side="right", fill="x", expand=True)
        preview = tk.Label(row, textvariable=var, bg=BRAND["panel"], fg=BRAND["text"],
                           font=("Segoe UI", 10), anchor="e")
        preview.pack(fill="x")
        def refresh(_event=None):
            star.configure(text=("★" if var.get() in self.font_favorites else "☆"))
            path = resolve_font(var.get())
            if path:
                try:
                    family = ImageFont.truetype(path, 12).getname()[0]
                    preview.configure(font=(family, 12))
                except Exception:
                    preview.configure(font=("Segoe UI", 10))
            self.render_preview()
        cb.bind("<<ComboboxSelected>>", refresh)
        cb.bind("<KeyRelease>", refresh)
        refresh()
        return cb

    def toggle_font_favorite(self, var):
        name = var.get()
        if not name:
            return
        if name in self.font_favorites:
            self.font_favorites.remove(name)
            self.notify("הגופן הוסר מהמועדפים")
        else:
            self.font_favorites.add(name)
            self.notify("הגופן נוסף למועדפים")
        self._save_settings()
        self.render_preview()

    def _make_text(self, parent, height=6):
        txt = tk.Text(parent, height=height, wrap="word",
                      font=("Segoe UI",11), undo=True,
                      bg=BRAND["surface"], fg=BRAND["text"],
                      insertbackground="white", relief="flat",
                      padx=8, pady=6)
        self._add_copy_paste(txt)
        self._add_context_menu(txt)
        return txt

    def _add_copy_paste(self, widget):
        widget.bind("<Control-a>", self._ctrl_a)
        widget.bind("<Control-A>", self._ctrl_a)
        # let Tk handle C/V/X natively — just ensure no override breaks them
        for seq in ("<Control-c>","<Control-C>","<Control-v>","<Control-V>",
                    "<Control-x>","<Control-X>"):
            widget.bind(seq, lambda e, s=seq: None)

    def _ctrl_a(self, event):
        w = event.widget
        try:
            if isinstance(w, tk.Text):
                w.tag_add("sel","1.0","end-1c"); w.mark_set("insert","1.0")
            else:
                w.select_range(0,"end"); w.icursor("end")
            return "break"
        except Exception: return None

    def _add_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0, bg=BRAND["surface"], fg=BRAND["text"])
        menu.add_command(label="גזור",    command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="העתק",    command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="הדבק",    command=lambda: [widget.event_generate("<<Paste>>"),
                                                             self.root.after(50, self.cache_and_render)])
        menu.add_separator()
        menu.add_command(label="בחר הכל", command=lambda: self._ctrl_a(type("E",(),{"widget":widget})()))
        def show(event):
            try: menu.tk_popup(event.x_root, event.y_root)
            finally: menu.grab_release()
        widget.bind("<Button-3>", show)

    # ── asset grid ────────────────────────────────────────────────────────────
    def asset_grid(self, folder, var, kind, columns=3, height=470):
        outer = tk.Canvas(self.step_area, bg=BRAND["panel"], highlightthickness=0, height=height)
        vsb   = ttk.Scrollbar(self.step_area, orient="vertical", command=outer.yview)
        grid  = tk.Frame(outer, bg=BRAND["panel"])
        grid.bind("<Configure>", lambda e: outer.configure(scrollregion=outer.bbox("all")))
        outer.create_window((0,0), window=grid, anchor="nw")
        outer.configure(yscrollcommand=vsb.set)
        outer.pack(side="left", fill="both", expand=True, padx=(18,0), pady=4)
        vsb.pack(side="right", fill="y", pady=4)
        self.asset_thumbs = []
        for idx, path in enumerate(sorted(folder.glob("*.png"))):
            img = Image.open(path).convert("RGB"); img.thumbnail((112,112), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img); self.asset_thumbs.append(tk_img)
            sel = path.name == var.get()
            bg  = BRAND["accent"] if sel else BRAND["surface"]
            cell = tk.Frame(grid, bg=bg, padx=5, pady=5)
            r, c = divmod(idx, columns)
            cell.grid(row=r, column=c, padx=6, pady=6, sticky="n")
            tk.Button(cell, image=tk_img, command=lambda p=path, k=kind: self.select_asset(p.name, k),
                      bg=bg, activebackground=BRAND["border"], bd=0, cursor="hand2").pack()
            tk.Label(cell, text=path.stem[:16], bg=bg, fg=BRAND["text"],
                     wraplength=112, font=("Segoe UI",8)).pack(pady=(4,0))

    def select_asset(self, name, kind):
        if kind == "background": self.bg.set(name)
        elif kind == "frame":    self.frame_var.set(name)
        self.render_preview()
        self.show_step(kind if kind in ("background","frame") else kind)

    # ── blessings step helpers (old simple list, kept as fallback) ────────────
    def paste_to_main(self):
        try:
            txt = self.root.clipboard_get()
            if hasattr(self,"text_box"):
                self.text_box.insert("insert", txt); self.cache_and_render()
        except Exception:
            self.notify("לא נמצא טקסט להדבקה")

    def cache_and_render(self):
        if hasattr(self,"text_box") and self.text_box.winfo_exists():
            self._text_cache = self.text_box.get("1.0","end").strip()
        self.render_preview()

    # ── presets ───────────────────────────────────────────────────────────────
    def apply_title_preset(self):
        p = self.title_preset.get()
        if   p == "זהב אלגנטי":  self.title_color.set("#C99437"); self.title_shadow.set(True)
        elif p == "אדום חגיגי":   self.title_color.set("#DF463C"); self.title_shadow.set(False)
        elif p == "כהה עם צל":    self.title_color.set("#111827"); self.title_shadow.set(True)
        else:                      self.title_color.set("#144C8A"); self.title_shadow.set(False)
        self.render_preview()

    def apply_body_preset(self):
        p = self.body_preset.get()
        if   p == "כחול רך":      self.body_color.set("#1D4E89"); self.body_shadow.set(False)
        elif p == "רומנטי":        self.body_color.set("#9F2D55"); self.body_shadow.set(False)
        elif p == "מודרני עם צל":  self.body_color.set("#111827"); self.body_shadow.set(True)
        else:                       self.body_color.set("#1E293B"); self.body_shadow.set(False)
        self.render_preview()

    # ── color pickers ─────────────────────────────────────────────────────────
    def _style_snapshot(self):
        return {
            "title_color": self.title_color.get(), "title_size": self.title_size.get(),
            "title_shadow": self.title_shadow.get(), "title_italic": self.title_italic.get(),
            "title_gradient": self.title_gradient.get(), "title_font": self.title_font.get(),
            "body_color": self.body_color.get(), "body_size": self.body_size.get(),
            "body_shadow": self.body_shadow.get(), "body_italic": self.body_italic.get(),
            "body_gradient": self.body_gradient.get(), "body_line_spacing": self.body_line_spacing.get(),
            "body_font": self.body_font.get(), "card_enabled": self.card_enabled.get(),
            "card_color": self.card_color.get(), "card_opacity": self.card_opacity.get(),
        }

    def _apply_style_snapshot(self, data):
        mapping = {
            "title_color": self.title_color, "title_size": self.title_size,
            "title_shadow": self.title_shadow, "title_italic": self.title_italic,
            "title_gradient": self.title_gradient, "title_font": self.title_font,
            "body_color": self.body_color, "body_size": self.body_size,
            "body_shadow": self.body_shadow, "body_italic": self.body_italic,
            "body_gradient": self.body_gradient, "body_line_spacing": self.body_line_spacing,
            "body_font": self.body_font, "card_enabled": self.card_enabled,
            "card_color": self.card_color, "card_opacity": self.card_opacity,
        }
        for key, var in mapping.items():
            if key in data:
                var.set(data[key])
        self.render_preview()

    def save_style_preset(self):
        name = self.preset_name.get().strip()
        if not name:
            self.notify("בחר שם ל-Preset")
            return
        self.style_presets[name] = self._style_snapshot()
        self._save_settings()
        if hasattr(self, "preset_combo"):
            self.preset_combo.configure(values=sorted(self.style_presets.keys()))
        self.notify("Preset נשמר")

    def load_style_preset(self):
        data = self.style_presets.get(self.preset_name.get().strip())
        if not data:
            self.notify("Preset לא נמצא")
            return
        self._apply_style_snapshot(data)
        self.notify("Preset נטען")

    def delete_style_preset(self):
        name = self.preset_name.get().strip()
        if name in self.style_presets:
            del self.style_presets[name]
            self._save_settings()
            if hasattr(self, "preset_combo"):
                self.preset_combo.configure(values=sorted(self.style_presets.keys()))
            self.notify("Preset נמחק")

    def pick_card_color(self):
        c = colorchooser.askcolor(initialcolor=self.card_color.get(), title="צבע תיבת טקסט")
        if c and c[1]: self.card_color.set(c[1]); self.render_preview()

    def pick_title_color(self):
        c = colorchooser.askcolor(initialcolor=self.title_color.get(), title="צבע כותרת")
        if c and c[1]: self.title_color.set(c[1]); self.render_preview()

    def pick_body_color(self):
        c = colorchooser.askcolor(initialcolor=self.body_color.get(), title="צבע גוף טקסט")
        if c and c[1]: self.body_color.set(c[1]); self.render_preview()

    # ── canvas size ───────────────────────────────────────────────────────────
    def get_canvas_size(self):
        w, h = float(self.width_cm.get()), float(self.height_cm.get())
        ori = self.orientation.get()
        if ori == "Landscape" and h > w: w, h = h, w
        elif ori == "Portrait"  and w > h: w, h = h, w
        elif ori == "Auto" and len(self._text_cache) > 260 and h > w: w, h = h, w
        return cm_to_px(w), cm_to_px(h)

    # ── render ────────────────────────────────────────────────────────────────
    def render_image(self):
        Wpx, Hpx = self.get_canvas_size()
        bp = BG_DIR / self.bg.get()
        bg_img = Image.open(bp).convert("RGB").resize((Wpx,Hpx), Image.Resampling.LANCZOS) \
                 if bp.exists() else Image.new("RGB",(Wpx,Hpx),"white")
        img  = bg_img.convert("RGBA")
        safe = int(min(Wpx,Hpx) * 0.075)

        title     = self.title_text.get().strip()
        has_title = bool(title)
        tx_off    = int(self.title_x_off.get() * Wpx / 100)
        ty_off    = int(self.title_y_off.get() * Hpx / 100)
        bx_off    = int(self.body_x_off.get()  * Wpx / 100)
        by_off    = int(self.body_y_off.get()  * Hpx / 100)

        if has_title:
            body_box  = [safe*2, int(Hpx*0.30), Wpx-safe*2, int(Hpx*0.76)]
            title_y   = int(Hpx*0.205) + ty_off
            card_rect = [safe, int(Hpx*0.16), Wpx-safe, int(Hpx*0.82)]
        else:
            body_box  = [safe*2, int(Hpx*0.22), Wpx-safe*2, int(Hpx*0.77)]
            title_y   = None
            card_rect = [safe, int(Hpx*0.18), Wpx-safe, int(Hpx*0.82)]

        # shift body box by offset
        body_box[0] += bx_off; body_box[2] += bx_off
        body_box[1] += by_off; body_box[3] += by_off

        # card background
        if self.card_enabled.get() and self.card_opacity.get() > 0:
            ov = Image.new("RGBA", img.size, (0,0,0,0))
            od = ImageDraw.Draw(ov, "RGBA")
            rgb   = hex_to_rgb(self.card_color.get())
            alpha = int(255 * self.card_opacity.get() / 100)
            radius = max(24, int(min(Wpx,Hpx)*0.03))
            od.rounded_rectangle(card_rect, radius=radius,
                                 fill=rgb+(alpha,), outline=(255,255,255,min(alpha,120)), width=3)
            img = Image.alpha_composite(img, ov)

        # frame overlay
        fn = self.frame_var.get()
        if fn != "__none__":
            fp = FRAME_DIR / fn
            if fp.exists():
                fr = Image.open(fp).convert("RGBA").resize((Wpx,Hpx), Image.Resampling.LANCZOS)
                img.alpha_composite(fr)

        d = ImageDraw.Draw(img, "RGBA")

        # resolve fonts
        t_bold   = True
        t_italic = self.title_italic.get()
        b_italic = self.body_italic.get()
        t_fp = resolve_font(self.title_font.get(), bold=t_bold, italic=t_italic)
        b_fp = resolve_font(self.body_font.get(),  bold=False,  italic=b_italic)
        if not t_fp: t_fp = (FONT_BOLD_ITALIC if t_italic else FONT_BOLD) or FONT_REG
        if not b_fp: b_fp = (FONT_ITALIC      if b_italic else FONT_REG)

        # title
        if has_title:
            sz = int(self.title_size.get() * (min(Wpx,Hpx)/1748))
            sz = max(28, min(sz, 180))
            try:    tfont = ImageFont.truetype(t_fp, sz) if t_fp else ImageFont.load_default()
            except: tfont = ImageFont.load_default()
            vis   = bidi_text(title)
            bb    = d.textbbox((0,0), vis, font=tfont)
            tx    = (Wpx - (bb[2]-bb[0])) / 2 + tx_off
            if self.title_shadow.get():
                d.text((tx+5, title_y+5), vis, font=tfont, fill=(0,0,0,95))
            if self.title_gradient.get():
                draw_gradient_text(img, (tx, title_y), vis, tfont, self.title_color.get(), "#F59E0B")
            else:
                d.text((tx, title_y), vis, font=tfont, fill=hex_to_rgb(self.title_color.get())+(255,))

        # body
        body_text = self._text_cache.strip() or "הקלד/י כאן את הברכה..."
        max_sz    = int(self.body_size.get() * (min(Wpx,Hpx)/1748))
        max_sz    = max(20, min(max_sz, 130))
        try:
            font, lines, line_h = fit_text(
                d, body_text, body_box, b_fp, max_size=max_sz,
                line_spacing=max(0.8, self.body_line_spacing.get() / 100),
            )
        except Exception:
            try:    font = ImageFont.truetype(b_fp, 28) if b_fp else ImageFont.load_default()
            except: font = ImageFont.load_default()
            lines = [body_text]; line_h = 34
        total_h = line_h * len(lines)
        y = body_box[1] + max(0, (body_box[3]-body_box[1]-total_h)//2)
        body_rgb = hex_to_rgb(self.body_color.get())
        for line in lines:
            vis = bidi_text(line)
            bb  = d.textbbox((0,0), vis, font=font)
            x   = (Wpx - (bb[2]-bb[0])) / 2
            if self.body_shadow.get():
                d.text((x+4, y+4), vis, font=font, fill=(0,0,0,80))
            if self.body_gradient.get():
                draw_gradient_text(img, (x, y), vis, font, self.body_color.get(), "#2563EB")
            else:
                d.text((x, y), vis, font=font, fill=body_rgb+(255,))
            y += line_h

        return img.convert("RGB")

    def render_preview(self):
        try:
            if hasattr(self,"text_box") and self.text_box.winfo_exists():
                val = self.text_box.get("1.0", "end").strip()
                # only overwrite cache when the widget actually has content,
                # or when we intentionally want to clear it (val=="", cache already "")
                if val or not self._text_cache:
                    self._text_cache = val
            self.last_image = self.render_image()
            prev = self.last_image.copy()
            area_w = max(380, self.right.winfo_width()-40)
            area_h = max(380, self.right.winfo_height()-80)
            prev.thumbnail((area_w, area_h), Image.Resampling.LANCZOS)
            self._preview_size = prev.size
            self.tk_preview = ImageTk.PhotoImage(prev)
            self.preview_label.configure(image=self.tk_preview, text="")
        except Exception as e:
            self.preview_label.configure(text=f"שגיאה בתצוגה:\n{e}", image="")

    # ── export ────────────────────────────────────────────────────────────────
    def _preview_drag_start(self, event):
        size = getattr(self, "_preview_size", None)
        if not size:
            return
        label_w = max(1, self.preview_label.winfo_width())
        label_h = max(1, self.preview_label.winfo_height())
        img_w, img_h = size
        left = max(0, (label_w - img_w) // 2)
        top = max(0, (label_h - img_h) // 2)
        if not (left <= event.x <= left + img_w and top <= event.y <= top + img_h):
            return
        rel_y = (event.y - top) / max(1, img_h)
        target = "title" if self.title_text.get().strip() and rel_y < 0.34 else "body"
        self._drag_preview = {
            "target": target, "x": event.x, "y": event.y,
            "title_x": self.title_x_off.get(), "title_y": self.title_y_off.get(),
            "body_x": self.body_x_off.get(), "body_y": self.body_y_off.get(),
            "img_w": img_w, "img_h": img_h,
        }

    def _preview_drag_move(self, event):
        drag = getattr(self, "_drag_preview", None)
        if not drag:
            return
        dx = int((event.x - drag["x"]) / max(1, drag["img_w"]) * 100)
        dy = int((event.y - drag["y"]) / max(1, drag["img_h"]) * 100)
        if drag["target"] == "title":
            self.title_x_off.set(max(-50, min(50, drag["title_x"] + dx)))
            self.title_y_off.set(max(-50, min(50, drag["title_y"] + dy)))
        else:
            self.body_x_off.set(max(-50, min(50, drag["body_x"] + dx)))
            self.body_y_off.set(max(-50, min(50, drag["body_y"] + dy)))
        self.render_preview()

    def _preview_drag_end(self, _event):
        if getattr(self, "_drag_preview", None):
            self._drag_preview = None
            self.notify("מיקום הטקסט עודכן")

    def export_png(self):
        try:
            img  = self.render_image()
            path = filedialog.asksaveasfilename(
                initialdir=str(EXPORT_DIR), defaultextension=".png",
                filetypes=[("PNG Image","*.png")])
            if path:
                img.save(path, dpi=(300,300))
                self.notify(f"הקובץ נשמר: {path}")
        except Exception as e:
            self.notify(f"שגיאה: {e}")

    def export_pdf(self):
        try:
            img  = self.render_image()
            path = filedialog.asksaveasfilename(
                initialdir=str(EXPORT_DIR), defaultextension=".pdf",
                filetypes=[("PDF File","*.pdf")])
            if path:
                img.save(path, "PDF", resolution=300.0)
                self.notify(f"הקובץ נשמר: {path}")
        except Exception as e:
            self.notify(f"שגיאה: {e}")

    def open_exports(self):
        EXPORT_DIR.mkdir(exist_ok=True)
        if sys.platform.startswith("win"): os.startfile(EXPORT_DIR)
        elif sys.platform == "darwin":     subprocess.call(["open", str(EXPORT_DIR)])
        else:                              subprocess.call(["xdg-open", str(EXPORT_DIR)])


if __name__ == "__main__":
    root = tk.Tk()
    app  = BlessingApp(root)
    root.mainloop()
