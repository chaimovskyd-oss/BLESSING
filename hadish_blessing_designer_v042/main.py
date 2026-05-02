import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from pathlib import Path
import json, random, os, sys, subprocess, shutil, math, ctypes
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageTk

try:
    from bidi.algorithm import get_display
except Exception:
    get_display = None

try:
    import cairosvg as _cairosvg
except Exception:
    _cairosvg = None

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

# ?? inject tool on sys.path ???????????????????????????????????????????????????
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

# ?? constants ?????????????????????????????????????????????????????????????????
PRODUCT_PRESETS_CM = {
    "A5":           {"size": (14.8, 21.0),  "title": "A5",           "desc": "ברכה קלאסית למתנה, יפה למסגרת קטנה או צירוף למארז."},
    "A4":           {"size": (21.0, 29.7),  "title": "A4",           "desc": "מתאים לפוסטר קטן, ברכה גדולה, תלייה או הצגה על שולחן."},
    "10x15":        {"size": (10.2, 15.32),  "title": "10x15",        "desc": "גודל קטן ומהיר, מתאים לצירוף למתנה או הדפסה פוטו."},
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

# ?? font scanning ?????????????????????????????????????????????????????????????
_FONT_SKIP_TERMS = frozenset([
    "symbol","wingdings","marlett","webdings","mt extra","emoji","historic",
    "mdl2","seguiemj","seguihis","seguisym","seguipcl","segoepr","segoescl",
    "seguisl","segoeuisl","holomdl2","segoe mdl2",
])
_REGULAR_SUBFAMILIES = frozenset(["regular","book","roman","normal","","medium","plain"])

def _scan_font_dirs():
    """Scan system + user font directories. Returns (all_fonts_dict, display_dict).
    all_fonts_dict : stem_lower ג†’ path  (+ family_lower ג†’ path for resolve)
    display_dict   : "Family Name" ג†’ path  (Regular subfamily only, filtered)
    """
    all_fonts   = {}
    display     = {}   # {display_name: path}
    seen_lower  = set()

    dirs = [Path(r"C:\Windows\Fonts")]
    user_local = os.environ.get("LOCALAPPDATA", "")
    if user_local:
        u = Path(user_local) / "Microsoft" / "Windows" / "Fonts"
        if u.exists():
            dirs.append(u)
    # macOS / Linux fallbacks
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        if Path(p).exists():
            dirs.append(Path(p).parent)

    for d in dirs:
        if not d.exists():
            continue
        files = []
        for pat in ("*.ttf","*.TTF","*.otf","*.OTF","*.ttc","*.TTC"):
            files.extend(d.glob(pat))
        for f in sorted(files):
            stem = f.stem.lower()
            all_fonts[stem] = str(f)
            try:
                fo = ImageFont.truetype(str(f), 16)
                family, subfamily = fo.getname()
                family    = family    or ""
                subfamily = subfamily or ""
                fam_lower = family.lower()
                all_fonts.setdefault(fam_lower, str(f))
                if (any(t in fam_lower for t in _FONT_SKIP_TERMS) or
                        any(t in stem for t in _FONT_SKIP_TERMS)):
                    continue
                if subfamily.lower() in _REGULAR_SUBFAMILIES:
                    key = fam_lower
                    if key not in seen_lower:
                        seen_lower.add(key)
                        display[family] = str(f)
            except Exception:
                pass
    return all_fonts, display

SYSTEM_FONTS, _FONT_DISPLAY = _scan_font_dirs()
# Flat sorted list of clean display names (for ordered_fonts / comboboxes)
DISPLAY_FONTS = sorted(_FONT_DISPLAY.keys(), key=str.lower)

_FONT_MATRIX = {
    (False, False): ["segoeui",   "segoe ui",  "arial",   "calibri",  "dejavu sans"],
    (True,  False): ["seguisb",   "arialbd",   "calibrib","seguibl"],
    (False, True):  ["segoeuii",  "ariali",    "calibrii"],
    (True,  True):  ["seguisbi",  "arialbi",   "calibriz"],
}

def find_font_path(bold=False, italic=False):
    for stem in _FONT_MATRIX.get((bold, italic), ["segoeui", "segoe ui"]):
        if stem in SYSTEM_FONTS:
            return SYSTEM_FONTS[stem]
    return next(iter(SYSTEM_FONTS.values()), None)

FONT_REG        = find_font_path()
FONT_BOLD       = find_font_path(bold=True)  or FONT_REG
FONT_ITALIC     = find_font_path(italic=True) or FONT_REG
FONT_BOLD_ITALIC= find_font_path(bold=True, italic=True) or FONT_BOLD
_HEBREW_FONT_CACHE = {}

HEBREW_FONT_HINTS = (
    "arial", "david", "frank", "gisha", "hadas", "miriam", "narkisim",
    "segoe", "tahoma", "times", "aharoni", "rubik", "assistant", "almoni",
)

def _legacy_font_likely_supports_hebrew(name):
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

def font_likely_supports_hebrew(name):
    if name in _HEBREW_FONT_CACHE:
        return _HEBREW_FONT_CACHE[name]
    lname = (name or "").lower()
    if any(hint in lname for hint in HEBREW_FONT_HINTS):
        _HEBREW_FONT_CACHE[name] = True
        return True
    path = SYSTEM_FONTS.get(lname)
    if not path:
        _HEBREW_FONT_CACHE[name] = False
        return False
    try:
        font = ImageFont.truetype(path, 36)
        result = bool(font.getmask("\u05d0\u05d1\u05d2").getbbox())
    except Exception:
        result = False
    _HEBREW_FONT_CACHE[name] = result
    return result

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

def make_gradient(size, first_hex, second_hex, mode="linear", angle=90):
    width, height = size
    first = hex_to_rgb(first_hex)
    second = hex_to_rgb(second_hex)
    gradient = Image.new("RGBA", size, (0, 0, 0, 0))
    pix = gradient.load()
    mode = (mode or "linear").lower()
    if width <= 1 or height <= 1:
        return Image.new("RGBA", size, first + (255,))
    if mode == "radial":
        cx, cy = width / 2, height / 2
        max_d = max(1, math.hypot(cx, cy))
        for y in range(height):
            for x in range(width):
                t = min(1, math.hypot(x - cx, y - cy) / max_d)
                rgb = tuple(int(first[i] * (1 - t) + second[i] * t) for i in range(3))
                pix[x, y] = rgb + (255,)
        return gradient
    if mode == "mirror":
        for y in range(height):
            for x in range(width):
                t = abs((x / (width - 1)) * 2 - 1)
                rgb = tuple(int(first[i] * (1 - t) + second[i] * t) for i in range(3))
                pix[x, y] = rgb + (255,)
        return gradient
    theta = math.radians(float(angle or 0))
    vx, vy = math.cos(theta), math.sin(theta)
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    dots = [x * vx + y * vy for x, y in corners]
    mn, mx = min(dots), max(dots)
    span = max(1e-6, mx - mn)
    for y in range(height):
        for x in range(width):
            t = ((x * vx + y * vy) - mn) / span
            rgb = tuple(int(first[i] * (1 - t) + second[i] * t) for i in range(3))
            pix[x, y] = rgb + (255,)
    return gradient

def draw_gradient_text(base, pos, text, font, first_hex, second_hex,
                       mode="linear", angle=90, stroke_width=0, stroke_fill="#000000"):
    x, y = pos
    if stroke_width:
        ImageDraw.Draw(base, "RGBA").text(
            (x, y), text, font=font, fill=(0, 0, 0, 0),
            stroke_width=int(stroke_width), stroke_fill=hex_to_rgb(stroke_fill) + (255,))
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), text, font=font, stroke_width=int(stroke_width or 0))
    width = max(1, right - left)
    height = max(1, bottom - top)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).text((-left, -top), text, font=font, fill=255)
    gradient = make_gradient((width, height), first_hex, second_hex, mode, angle)
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

# ?? image helpers ?????????????????????????????????????????????????????????????
def _load_svg_as_pil(path, size=(1748, 2480)):
    """Render an SVG file to a PIL RGBA image. Requires cairosvg; falls back to placeholder."""
    if _cairosvg is not None:
        try:
            png_bytes = _cairosvg.svg2png(
                url=str(path),
                output_width=size[0], output_height=size[1])
            import io
            return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            pass
    # Fallback: grey placeholder with SVG label
    img = Image.new("RGBA", (400, 400), (180, 180, 180, 255))
    try:
        ImageDraw.Draw(img).text((20, 180), "SVG ? install cairosvg", fill=(60, 60, 60, 255))
    except Exception:
        pass
    return img

def cm_to_px(cm, dpi=300):
    return int(round(cm / 2.54 * dpi))

def hex_to_rgb(hex_color):
    h = str(hex_color).strip().lstrip("#")
    if len(h) == 3: h = "".join(c*2 for c in h)
    try:    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except: return (255, 255, 255)

def has_hebrew(text):
    return any("\u0590" <= c <= "\u05ff" for c in str(text or ""))

def bidi_text(text):
    if get_display:
        try:
            return get_display(text, base_dir="R" if has_hebrew(text) else None)
        except TypeError:
            try:    return get_display(text)
            except Exception: return text
        except Exception:
            return text
    return text

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


# ?? QuoteRepository (inline, mirrors hadish_blessings_tool) ??????????????????
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


# ?? EmbeddedBlessingWidget ????????????????????????????????????????????????????
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

    # ?? favorites helpers ?????????????????????????????????????????????????????
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

    # ?? UI build ??????????????????????????????????????????????????????????????
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
        self._btn_use    = abtn("+ הוסף לעיצוב",  self._use,        "#16A34A")
        self._btn_copy   = abtn("העתק",          self._copy,       "#2563EB")
        self._btn_fav    = abtn("☆ מועדף",          self._toggle_fav, "#FACC15", "#0B1628")
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
            ("fav","?",44,"center",False), ("text","הטקסט",490,"e",True),
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

    # ?? mode ??????????????????????????????????????????????????????????????????
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

    # ?? data refresh ??????????????????????????????????????????????????????????
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
            fav   = "?" if item.get("favorite") else "?"
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
            meta = f"{self.selected_item.get('event','')} ? {self.selected_item.get('recipient','')} ? {self.selected_item.get('product','')}"
        else:
            meta = f"{self.selected_item.get('category','')} ? {self.selected_item.get('source','')}"
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
            self._status.config(text="הועתק ללוח ?")
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


# ?? Collapsible panel ?????????????????????????????????????????????????????????
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
        btn_text = ("?  " if start_open else "?  ") + title
        self.btn = tk.Button(self.frame, text=btn_text, command=self.toggle,
                             bg="#233660", fg=BRAND["gold"], bd=0, anchor="e",
                             font=("Segoe UI", 10, "bold"), padx=12, pady=7, cursor="hand2")
        self.btn.pack(fill="x")
        self.body = tk.Frame(self.frame, bg=bg, padx=10, pady=4)
        if start_open: self.body.pack(fill="x")

    def toggle(self):
        if self.open.get():
            self.body.pack_forget(); self.open.set(False)
            self.btn.configure(text="?  " + self.title)
        else:
            self.body.pack(fill="x"); self.open.set(True)
            self.btn.configure(text="?  " + self.title)


# ?? Main Application ??????????????????????????????????????????????????????????
class NativeRtlText(tk.Frame):
    """Windows RichEdit wrapper: logical Unicode storage with native RTL editing."""

    _loaded = False

    def __init__(self, parent, height=6, font=("Segoe UI", 11), bg="#142040", fg="#F1F5F9",
                 insertbackground="white", **kwargs):
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0)
        self._font_spec = font
        self._bg = bg
        self._fg = fg
        self._hwnd = None
        self._font_handle = None
        self._callbacks = {}
        self._last_text = ""
        self._last_focus = False
        self.configure(height=max(84, int(height * 25)))
        self.bind("<Configure>", self._on_configure, add="+")
        self.after_idle(self._create)

    @staticmethod
    def available():
        return sys.platform.startswith("win")

    def _create(self):
        if self._hwnd or not self.winfo_exists():
            return
        try:
            if not NativeRtlText._loaded:
                ctypes.windll.kernel32.LoadLibraryW("Msftedit.dll")
                NativeRtlText._loaded = True
            style = 0x40000000 | 0x10000000 | 0x00200000 | 0x0004 | 0x0040 | 0x1000 | 0x0100 | 0x0002
            self._hwnd = ctypes.windll.user32.CreateWindowExW(
                0x00002000, "RICHEDIT50W", "", style,
                0, 0, max(1, self.winfo_width()), max(1, self.winfo_height()),
                self.winfo_id(), 0, 0, None)
            if not self._hwnd:
                raise OSError("CreateWindowExW(RICHEDIT50W) failed")
            self._apply_font()
            self._apply_colors()
            self._apply_rtl_paragraph()
            self._poll()
        except Exception:
            self._hwnd = None

    def _apply_font(self):
        if not self._hwnd:
            return
        family = self._font_spec[0] if self._font_spec else "Segoe UI"
        size = int(self._font_spec[1]) if len(self._font_spec) > 1 else 11
        height = -int(size * self.winfo_fpixels("1p"))
        self._font_handle = ctypes.windll.gdi32.CreateFontW(
            height, 0, 0, 0, 400, 0, 0, 0, 177, 0, 0, 5, 0, family)
        ctypes.windll.user32.SendMessageW(self._hwnd, 0x0030, self._font_handle, True)

    def _colorref(self, hex_color):
        r, g, b = hex_to_rgb(hex_color)
        return r | (g << 8) | (b << 16)

    def _apply_colors(self):
        if self._hwnd:
            ctypes.windll.user32.SendMessageW(self._hwnd, 0x0443, 0, self._colorref(self._bg))
            self._apply_char_format(0)

    def _apply_char_format(self, scope=0):
        if not self._hwnd:
            return

        class CHARFORMAT2(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint), ("dwMask", ctypes.c_uint), ("dwEffects", ctypes.c_uint),
                ("yHeight", ctypes.c_long), ("yOffset", ctypes.c_long), ("crTextColor", ctypes.c_uint),
                ("bCharSet", ctypes.c_ubyte), ("bPitchAndFamily", ctypes.c_ubyte),
                ("szFaceName", ctypes.c_wchar * 32), ("wWeight", ctypes.c_ushort),
                ("sSpacing", ctypes.c_short), ("crBackColor", ctypes.c_uint), ("lcid", ctypes.c_uint),
                ("dwReserved", ctypes.c_uint), ("sStyle", ctypes.c_short), ("wKerning", ctypes.c_ushort),
                ("bUnderlineType", ctypes.c_ubyte), ("bAnimation", ctypes.c_ubyte),
                ("bRevAuthor", ctypes.c_ubyte), ("bReserved1", ctypes.c_ubyte),
            ]

        cf = CHARFORMAT2()
        cf.cbSize = ctypes.sizeof(CHARFORMAT2)
        cf.dwMask = 0x40000000
        cf.crTextColor = self._colorref(self._fg)
        ctypes.windll.user32.SendMessageW(self._hwnd, 0x0444, scope, ctypes.byref(cf))

    def _apply_rtl_paragraph(self):
        if not self._hwnd:
            return

        class PARAFORMAT2(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_uint), ("dwMask", ctypes.c_uint),
                ("wNumbering", ctypes.c_ushort), ("wReserved", ctypes.c_ushort),
                ("dxStartIndent", ctypes.c_long), ("dxRightIndent", ctypes.c_long),
                ("dxOffset", ctypes.c_long), ("wAlignment", ctypes.c_ushort),
                ("cTabCount", ctypes.c_short), ("rgxTabs", ctypes.c_long * 32),
                ("dySpaceBefore", ctypes.c_long), ("dySpaceAfter", ctypes.c_long),
                ("dyLineSpacing", ctypes.c_long), ("sStyle", ctypes.c_short),
                ("bLineSpacingRule", ctypes.c_ubyte), ("bOutlineLevel", ctypes.c_ubyte),
                ("wShadingWeight", ctypes.c_ushort), ("wShadingStyle", ctypes.c_ushort),
                ("wNumberingStart", ctypes.c_ushort), ("wNumberingStyle", ctypes.c_ushort),
                ("wNumberingTab", ctypes.c_ushort), ("wBorderSpace", ctypes.c_ushort),
                ("wBorderWidth", ctypes.c_ushort), ("wBorders", ctypes.c_ushort),
            ]

        pf = PARAFORMAT2()
        pf.cbSize = ctypes.sizeof(PARAFORMAT2)
        pf.dwMask = 0x00000008
        pf.wAlignment = 3
        ctypes.windll.user32.SendMessageW(self._hwnd, 0x0447, 0, ctypes.byref(pf))

    def _on_configure(self, _event=None):
        if self._hwnd:
            ctypes.windll.user32.MoveWindow(
                self._hwnd, 0, 0, max(1, self.winfo_width()), max(1, self.winfo_height()), True)

    def _poll(self):
        if not self.winfo_exists() or not self._hwnd:
            return
        text = self.get("1.0", "end")
        focused = ctypes.windll.user32.GetFocus() == self._hwnd
        if focused and not self._last_focus:
            self._emit("<FocusIn>")
        if text != self._last_text:
            self._last_text = text
            self._apply_rtl_paragraph()
            self._emit("<KeyRelease>")
        self._last_focus = focused
        self.after(90, self._poll)

    def _emit(self, sequence):
        event = type("Event", (), {"widget": self})()
        for callback in self._callbacks.get(sequence, []):
            callback(event)

    def bind(self, sequence=None, func=None, add=None):
        if sequence and func and sequence in {"<KeyRelease>", "<FocusIn>", "<<Paste>>"}:
            if add == "+":
                self._callbacks.setdefault(sequence, []).append(func)
            else:
                self._callbacks[sequence] = [func]
            return ""
        return super().bind(sequence, func, add)

    def focus_set(self):
        if self._hwnd:
            ctypes.windll.user32.SetFocus(self._hwnd)
        else:
            super().focus_set()

    def get(self, start=None, end=None):
        if not self._hwnd:
            return self._last_text
        length = ctypes.windll.user32.SendMessageW(self._hwnd, 0x000E, 0, 0)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.SendMessageW(self._hwnd, 0x000D, length + 1, buf)
        return buf.value.replace("\r\n", "\n")

    def _set_text(self, text):
        text = str(text or "")
        if not self._hwnd:
            self._last_text = text
            self.after_idle(lambda: self._set_text(text))
            return
        ctypes.windll.user32.SendMessageW(self._hwnd, 0x000C, 0, text.replace("\n", "\r\n"))
        self._apply_char_format(4)
        self._last_text = self.get("1.0", "end")
        self._apply_rtl_paragraph()

    def delete(self, start, end=None):
        self._set_text("")

    def insert(self, index, text):
        text = str(text or "")
        if not self._hwnd:
            self._last_text = text + self._last_text if index in ("1.0", 0) else self._last_text + text
            self.after_idle(lambda: self._set_text(self._last_text))
            return
        if index in ("1.0", 0):
            ctypes.windll.user32.SendMessageW(self._hwnd, 0x00B1, 0, 0)
        ctypes.windll.user32.SendMessageW(self._hwnd, 0x00C2, True, text.replace("\n", "\r\n"))
        self._apply_char_format(4)
        self._last_text = self.get("1.0", "end")
        self._apply_rtl_paragraph()

    def select_range(self, start, end):
        if self._hwnd:
            end_pos = -1 if end == "end" else int(end)
            ctypes.windll.user32.SendMessageW(self._hwnd, 0x00B1, int(start), end_pos)

    def icursor(self, index):
        if self._hwnd:
            pos = -1 if index == "end" else int(index)
            ctypes.windll.user32.SendMessageW(self._hwnd, 0x00B1, pos, pos)


class BlessingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hadish Blessing Designer v0.5")
        self._settings_cache = self._load_settings()
        set_brand_theme(self._settings_cache.get("theme", "dark"))
        self._show_splash()
        # Respect Windows taskbar ? cap height to screen minus ~70px
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
        self._render_after = None
        self._image_cache = {}
        self._font_combo_widgets = []
        # logos (PhotoImage must stay referenced ? store on self)
        self._logo_nav     = None  # nav bar   ~44 px tall
        self._logo_preview = None  # preview header ~36 px tall
        self._snackbar_after = None
        self.init_state()
        self.build_style()
        self.build_menu()
        self.build_ui()
        self.show_step("size")

    # ?? state ?????????????????????????????????????????????????????????????????
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
            "last_body_text": getattr(self, "_text_cache", ""),
            "recent_colors": getattr(self, "_recent_colors", []),
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
        self.frame_var    = tk.StringVar(value="__none__")
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
        self.card_opacity = tk.IntVar(value=30)
        # title style
        self.title_color  = tk.StringVar(value="#144C8A")
        self.title_opacity = tk.IntVar(value=100)
        self.title_size   = tk.IntVar(value=72)
        self.title_shadow = tk.BooleanVar(value=False)
        self.title_shadow_color = tk.StringVar(value="#000000")
        self.title_shadow_size = tk.IntVar(value=5)
        self.title_shadow_angle = tk.IntVar(value=45)
        self.title_shadow_opacity = tk.IntVar(value=38)
        self.title_italic = tk.BooleanVar(value=False)
        self.title_bold   = tk.BooleanVar(value=True)
        self.title_align  = tk.StringVar(value="center")
        self.title_gradient = tk.BooleanVar(value=False)
        self.title_gradient_a = tk.StringVar(value="#144C8A")
        self.title_gradient_b = tk.StringVar(value="#F59E0B")
        self.title_gradient_mode = tk.StringVar(value="linear")
        self.title_gradient_angle = tk.IntVar(value=90)
        self.title_stroke_enabled = tk.BooleanVar(value=False)
        self.title_stroke_color = tk.StringVar(value="#FFFFFF")
        self.title_stroke_width = tk.IntVar(value=0)
        self.title_preset = tk.StringVar(value="נקי כחול")
        self.title_font   = tk.StringVar(value="Segoe UI")
        self.title_x_off  = tk.IntVar(value=0)
        self.title_y_off  = tk.IntVar(value=0)
        # body style
        self.body_color   = tk.StringVar(value="#1E293B")
        self.body_opacity = tk.IntVar(value=100)
        self.body_size    = tk.IntVar(value=54)
        self.body_shadow  = tk.BooleanVar(value=False)
        self.body_shadow_color = tk.StringVar(value="#000000")
        self.body_shadow_size = tk.IntVar(value=4)
        self.body_shadow_angle = tk.IntVar(value=45)
        self.body_shadow_opacity = tk.IntVar(value=32)
        self.body_bold    = tk.BooleanVar(value=False)
        self.body_italic  = tk.BooleanVar(value=False)
        self.body_gradient = tk.BooleanVar(value=False)
        self.body_gradient_a = tk.StringVar(value="#1E293B")
        self.body_gradient_b = tk.StringVar(value="#2563EB")
        self.body_gradient_mode = tk.StringVar(value="linear")
        self.body_gradient_angle = tk.IntVar(value=90)
        self.body_stroke_enabled = tk.BooleanVar(value=False)
        self.body_stroke_color = tk.StringVar(value="#FFFFFF")
        self.body_stroke_width = tk.IntVar(value=0)
        self.body_line_spacing = tk.IntVar(value=122)
        self.body_letter_spacing = tk.IntVar(value=0)
        self.body_align = tk.StringVar(value="center")
        self.body_preset  = tk.StringVar(value="נקי כהה")
        self.body_font    = tk.StringVar(value="Segoe UI")
        self.body_x_off   = tk.IntVar(value=0)
        self.body_y_off   = tk.IntVar(value=0)
        self.third_enabled = tk.BooleanVar(value=False)
        self.third_text    = tk.StringVar(value="")
        self.third_color   = tk.StringVar(value="#1E293B")
        self.third_opacity = tk.IntVar(value=100)
        self.third_size    = tk.IntVar(value=38)
        self.third_font    = tk.StringVar(value="Segoe UI")
        self.third_bold    = tk.BooleanVar(value=False)
        self.third_italic  = tk.BooleanVar(value=False)
        self.third_align   = tk.StringVar(value="center")
        self.third_gradient = tk.BooleanVar(value=False)
        self.third_gradient_a = tk.StringVar(value="#1E293B")
        self.third_gradient_b = tk.StringVar(value="#F59E0B")
        self.third_gradient_mode = tk.StringVar(value="linear")
        self.third_gradient_angle = tk.IntVar(value=0)
        self.third_stroke_enabled = tk.BooleanVar(value=False)
        self.third_stroke_color = tk.StringVar(value="#FFFFFF")
        self.third_stroke_width = tk.IntVar(value=0)
        self.third_shadow = tk.BooleanVar(value=False)
        self.third_shadow_color = tk.StringVar(value="#000000")
        self.third_shadow_size = tk.IntVar(value=3)
        self.third_shadow_angle = tk.IntVar(value=45)
        self.third_shadow_opacity = tk.IntVar(value=28)
        self.third_x_off  = tk.IntVar(value=0)
        self.third_y_off  = tk.IntVar(value=0)
        self._overflow_notice_after = None
        self._text_cache  = settings.get("last_body_text", "")
        self._recent_colors = list(settings.get("recent_colors", []))[:18]
        self._active_text_target = "body"
        self._editor_text_target = "body"
        self._tb_syncing = False

    # ?? styles ????????????????????????????????????????????????????????????????
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

    # ?? menu ??????????????????????????????????????????????????????????????????
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

    # ?? UI skeleton ???????????????????????????????????????????????????????????
    def build_ui(self):
        # ?? persistent nav bar (bottom, always visible) ??????????????????????
        self.nav_bar = tk.Frame(self.root, bg=BRAND["bg"], height=62)
        self.nav_bar.pack(side="bottom", fill="x", padx=14, pady=(4,12))
        self.nav_bar.pack_propagate(False)

        self.back_btn = tk.Button(
            self.nav_bar, text="ג¬…  חזור", command=self.prev_step,
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
            self.nav_bar, text=("?" if self.theme_mode.get() == "dark" else "🌙"),
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

        # logo ? centered in nav bar
        self._logo_nav = _make_logo_tk(46)
        if self._logo_nav:
            tk.Label(self.nav_bar, image=self._logo_nav, bg=BRAND["bg"],
                     cursor="hand2").pack(side="left", padx=24)

        # ?? content area ?????????????????????????????????????????????????????
        self.content = tk.Frame(self.root, bg=BRAND["bg"])
        self.content.pack(fill="both", expand=True, padx=14, pady=(12,4))

        # normal view (left controls + right preview)
        self.normal_view = tk.Frame(self.content, bg=BRAND["bg"])

        self.left = tk.Frame(self.normal_view, bg=BRAND["panel"], width=516)
        self.left.pack(side="left", fill="both", padx=(0,10))
        self.left.pack_propagate(False)

        self.right = tk.Frame(self.normal_view, bg=BRAND["panel"])
        self.right.pack(side="right", fill="both", expand=True)

        # right panel uses grid so topbar can be inserted between header and preview
        self.right.grid_columnconfigure(0, weight=1)
        self.right.grid_rowconfigure(2, weight=1)

        preview_hdr = tk.Frame(self.right, bg=BRAND["panel"])
        preview_hdr.grid(row=0, column=0, sticky="ew", padx=18, pady=(14,4))
        tk.Label(preview_hdr, text="תצוגה מקדימה", bg=BRAND["panel"],
                 fg=BRAND["gold"], font=("Segoe UI Semibold", 14)).pack(side="right")
        self._logo_preview = _make_logo_tk(36)
        if self._logo_preview:
            tk.Label(preview_hdr, image=self._logo_preview,
                     bg=BRAND["panel"]).pack(side="left", padx=4)

        self._build_text_topbar()  # builds row=1 (hidden until text step)

        self.preview_label = tk.Label(self.right, text="", bg=BRAND["panel"])
        self.preview_label.grid(row=2, column=0, sticky="nsew", padx=16, pady=12)
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

    # ?? step routing ??????????????????????????????????????????????????????????
    def clear_step(self):
        for w in self.step_area.winfo_children(): w.destroy()

    def show_step(self, step):
        if getattr(self, "current_step", None) == "text" and step != "text":
            self._save_editor_to_target()
        self.current_step = step
        idx = self.step_order.index(step) + 1
        total = len(self.step_order)
        self.progress_lbl.configure(text=f"שלב {idx} מתוך {total}")
        self.step_title_lbl.configure(text=self.step_titles[step])
        self._update_progress_dots(idx)

        if step == "blessings":
            self._hide_text_topbar()
            self._enter_blessing_fullscreen()
        else:
            self._exit_blessing_fullscreen()
            self.clear_step()
            if step != "text":
                self.left.configure(width=516, bg=BRAND["panel"])
                self.right.configure(bg=BRAND["panel"])
                self._left_canvas.configure(bg=BRAND["panel"])
                self.step_area.configure(bg=BRAND["panel"])
                self.preview_label.configure(bg=BRAND["panel"])
                if not self._left_vsb.winfo_ismapped():
                    self._left_vsb.pack(side="right", fill="y")
            if   step == "size":       self.build_size_step()
            elif step == "background": self.build_background_step()
            elif step == "frame":      self.build_frame_step()
            else:                      self.build_text_step()
            # flush layout so text_box.get() returns the inserted text reliably
            self.root.update_idletasks()
            self.render_preview()
            self._animate_step_in()
            if step == "text":
                self._show_text_topbar()
                # belt-and-suspenders: re-render once widgets are fully settled
                self.root.after(80, self.render_preview)
            else:
                self._hide_text_topbar()

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

    def schedule_render_preview(self, delay=140):
        if self._render_after:
            self.root.after_cancel(self._render_after)
        self._render_after = self.root.after(delay, self._run_scheduled_render)

    def _run_scheduled_render(self):
        self._render_after = None
        self.render_preview()

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
        self._set_body_text(text)
        self.show_step("text")
        self.root.after(120, lambda t=text: self._set_body_text(t, update_widget=True))

    def _set_body_text(self, text, update_widget=False):
        self._text_cache = str(text or "")
        self._save_settings()
        if update_widget and hasattr(self, "text_box") and self.text_box.winfo_exists():
            try:
                self.text_box.delete("1.0", "end")
                self.text_box.insert("1.0", self._text_cache)
            except Exception:
                pass
            self.render_preview()

    def _get_target_text(self, target):
        if target == "title":
            return self.title_text.get()
        if target == "third":
            return self.third_text.get()
        return self._text_cache

    def _set_target_text(self, target, text):
        text = str(text or "")
        if target == "title":
            self.title_text.set(text)
        elif target == "third":
            self.third_enabled.set(bool(text.strip()) or self.third_enabled.get())
            self.third_text.set(text)
        else:
            self._text_cache = text
            self._save_settings()

    def _save_editor_to_target(self):
        if hasattr(self, "text_box") and self.text_box.winfo_exists():
            self._set_target_text(getattr(self, "_editor_text_target", "body"),
                                  self.text_box.get("1.0", "end"))

    def _load_target_into_editor(self, target):
        self._save_editor_to_target()
        self._editor_text_target = target
        self._active_text_target = target
        if target == "third":
            self.third_enabled.set(True)
        if hasattr(self, "text_box") and self.text_box.winfo_exists():
            self.text_box.delete("1.0", "end")
            self.text_box.insert("1.0", self._get_target_text(target))
        self._tb_set_target(target)
        self._refresh_text_type_buttons()
        self.render_preview()

    def next_step(self):
        if self.current_step == "text":
            self.export_png(); return
        if self.current_step == "blessings":
            # user pressed Next without picking ? go to text with whatever is cached
            self.show_step("text"); return
        idx = self.step_order.index(self.current_step)
        self.show_step(self.step_order[idx + 1])

    def prev_step(self):
        idx = self.step_order.index(self.current_step)
        if idx > 0: self.show_step(self.step_order[idx - 1])

    # ?? Step 1: size ??????????????????????????????????????????????????????????
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

    # ?? Step 2: background ????????????????????????????????????????????????????
    def build_background_step(self):
        self._section_hint("בחר/י רקע. התצוגה מתעדכנת מיד.")
        upload = tk.Button(self.step_area, text="העלה רקע", command=self.upload_background,
                           bg=BRAND["orange"], fg="white", bd=0, padx=12, pady=7,
                           font=("Segoe UI",10,"bold"), cursor="hand2")
        upload.pack(anchor="e", padx=18, pady=(0,8))
        Tooltip(upload, "בחר תמונה מהמחשב ושמור אותה בתיקיית הרקעים")
        self.asset_grid(BG_DIR, self.bg, "background", columns=3, height=480)

    def upload_background(self):
        path = filedialog.askopenfilename(
            title="בחר רקע",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.svg"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            src = Path(path)
            stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in src.stem).strip("_") or "uploaded_bg"
            is_svg = src.suffix.lower() == ".svg"
            ext = ".png"  # always save as PNG for full support
            dest = BG_DIR / f"{stem}{ext}"
            i = 2
            while dest.exists():
                dest = BG_DIR / f"{stem}_{i}{ext}"
                i += 1
            if is_svg:
                img = _load_svg_as_pil(src)
            else:
                raw = Image.open(src)
                img = raw.convert("RGBA") if raw.mode in ("RGBA","LA","P") else raw.convert("RGB").convert("RGBA")
            img.save(dest)
            self.bg.set(dest.name)
            self.notify("הרקע הועלה ונשמר")
            self.show_step("background")
        except Exception as e:
            self.notify(f"שגיאה בהעלאת רקע: {e}")

    # ?? Step 3: frame ?????????????????????????????????????????????????????????
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

    # ?? Text Formatting Topbar ????????????????????????????????????????????????
    def _build_text_topbar(self):
        BAR = "#0F172A"
        bar = tk.Frame(self.content, bg=BAR, pady=8, padx=12)
        self._text_topbar = bar
        self._tb_target_btns = {}
        self._active_text_target = "body"

        def tool_button(text, command, width=None):
            btn = tk.Button(bar, text=text, command=command, bg=BRAND["surface"], fg=BRAND["text"],
                            bd=0, padx=10, pady=6, width=width,
                            font=("Segoe UI", 10, "bold"), cursor="hand2")
            btn.pack(side="right", padx=4)
            return btn

        self._tb_font_cb = ttk.Combobox(
            bar, width=18, state="readonly",
            values=ordered_fonts(getattr(self, "font_favorites", set())))
        self._tb_font_cb.pack(side="right", padx=6)
        self._tb_font_cb.bind("<<ComboboxSelected>>", lambda e: self._tb_apply())
        self._tb_font_star = tool_button("☆", self._tb_toggle_font_favorite, 3)

        self._tb_size_var = tk.IntVar(value=self.body_size.get())
        tool_button("+", lambda: [self._tb_size_var.set(self._tb_size_var.get() + 2), self._tb_apply()], 2)
        tk.Spinbox(bar, from_=10, to=300, textvariable=self._tb_size_var, width=5,
                   command=self._tb_apply, justify="center", bg=BRAND["surface"],
                   fg=BRAND["text"], relief="flat").pack(side="right", padx=2)
        tool_button("-", lambda: [self._tb_size_var.set(max(10, self._tb_size_var.get() - 2)), self._tb_apply()], 2)

        self._tb_color_btn = tool_button("■", self._tb_pick_color, 3)
        self._tb_eyedrop_btn = tool_button("🔍", self.toggle_eyedropper, 3)
        Tooltip(self._tb_eyedrop_btn, "דגימת צבע מהקנבס")
        self._tb_italic_var = tk.BooleanVar(value=self.body_italic.get())
        self._tb_italic_chk = tk.Checkbutton(
            bar, text="I", variable=self._tb_italic_var, command=self._tb_apply,
            font=("Segoe UI", 11, "italic"), bg=BRAND["surface"], fg=BRAND["text"],
            selectcolor=BRAND["accent"], activebackground=BAR,
            indicatoron=False, padx=10, pady=5, bd=0, cursor="hand2")
        self._tb_italic_chk.pack(side="right", padx=4)
        self._tb_bold_var = tk.BooleanVar(value=False)
        self._tb_bold_btn = tk.Checkbutton(
            bar, text="B", variable=self._tb_bold_var, command=self._tb_apply,
            font=("Segoe UI", 11, "bold"), bg=BRAND["surface"], fg=BRAND["text"],
            selectcolor=BRAND["accent"], activebackground=BAR,
            indicatoron=False, padx=10, pady=5, bd=0, cursor="hand2")
        self._tb_bold_btn.pack(side="right", padx=4)

        self._tb_align_btns = {}
        for value, label in [("left", "שמאל"), ("center", "מרכז"), ("right", "ימין")]:
            self._tb_align_btns[value] = tool_button(label, lambda v=value: self._set_active_align(v))

        self._tb_gradient_var = tk.BooleanVar(value=self.body_gradient.get())
        tk.Checkbutton(bar, text="גרדיינט", variable=self._tb_gradient_var, command=self._toggle_gradient_from_toolbar,
                       bg=BRAND["surface"], fg=BRAND["text"], selectcolor=BRAND["accent"],
                       activebackground=BAR, indicatoron=False, padx=10, pady=5,
                       bd=0, cursor="hand2").pack(side="right", padx=4)
        self._tb_shadow_var = tk.BooleanVar(value=self.body_shadow.get())
        tk.Checkbutton(bar, text="צל", variable=self._tb_shadow_var, command=self._toggle_shadow_from_toolbar,
                       bg=BRAND["surface"], fg=BRAND["text"], selectcolor=BRAND["accent"],
                       activebackground=BAR, indicatoron=False, padx=10, pady=5,
                       bd=0, cursor="hand2").pack(side="right", padx=4)
        self._tb_stroke_var = tk.BooleanVar(value=self.body_stroke_enabled.get())
        tk.Checkbutton(bar, text="קו", variable=self._tb_stroke_var, command=self._toggle_stroke_from_toolbar,
                       bg=BRAND["surface"], fg=BRAND["text"], selectcolor=BRAND["accent"],
                       activebackground=BAR, indicatoron=False, padx=10, pady=5,
                       bd=0, cursor="hand2").pack(side="right", padx=4)
        tool_button("תיבה", self._open_card_popup)

        self._tb_spacing_var = tk.IntVar(value=self.body_line_spacing.get())
        self._tb_x_var = tk.IntVar(value=0)
        self._tb_y_var = tk.IntVar(value=0)
        self._tb_sync_from_target()
        self._refresh_align_buttons()
        return
        BAR = "#0F172A"
        bar = tk.Frame(self.right, bg=BAR, pady=5, padx=6)
        self._text_topbar = bar
        # Placed in row=1 of the grid, hidden initially via grid_remove
        bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 0))
        bar.grid_remove()  # hidden until text step

        def sep():
            tk.Frame(bar, bg=BRAND["border"], width=1).pack(
                side="right", fill="y", padx=5, pady=3)

        # ?? Target selector (rightmost) ?????????????????????????????????????
        self._tb_target_btns = {}
        for tid, lbl in [("third", "תחתון"), ("body", "ברכה"), ("title", "כותרת")]:
            b = tk.Button(bar, text=lbl, bg=BRAND["surface"], fg=BRAND["text"],
                          bd=0, padx=10, pady=3, font=("Segoe UI", 9, "bold"),
                          cursor="hand2", relief="flat",
                          command=lambda t=tid: self._tb_set_target(t))
            b.pack(side="right", padx=2)
            self._tb_target_btns[tid] = b
        sep()

        # ?? Font ?????????????????????????????????????????????????????????????
        tk.Label(bar, text="גופן", bg=BAR, fg=BRAND["muted"],
                 font=("Segoe UI", 8)).pack(side="right", padx=(6, 2))
        self._tb_font_cb = ttk.Combobox(
            bar, width=13, state="readonly",
            values=ordered_fonts(getattr(self, "font_favorites", set())))
        self._tb_font_cb.pack(side="right", padx=2, pady=2)
        self._tb_font_cb.bind("<<ComboboxSelected>>", lambda e: self._tb_apply())
        sep()

        # ?? Size ?????????????????????????????????????????????????????????????
        tk.Label(bar, text="גודל", bg=BAR, fg=BRAND["muted"],
                 font=("Segoe UI", 8)).pack(side="right", padx=(6, 2))
        self._tb_size_var = tk.IntVar(value=54)
        sz = tk.Spinbox(bar, from_=10, to=300, textvariable=self._tb_size_var,
                        width=4, command=self._tb_apply, justify="center",
                        bg=BRAND["surface"], fg=BRAND["text"], relief="flat",
                        disabledbackground=BRAND["surface"])
        sz.pack(side="right", padx=2)
        sz.bind("<Return>",   lambda e: self._tb_apply())
        sz.bind("<FocusOut>", lambda e: self._tb_apply())
        sep()

        # ?? Bold + Italic ?????????????????????????????????????????????????????
        self._tb_italic_var = tk.BooleanVar(value=False)
        self._tb_italic_chk = tk.Checkbutton(
            bar, text=" I ", variable=self._tb_italic_var, command=self._tb_apply,
            font=("Segoe UI", 10, "italic"), bg=BAR, fg=BRAND["text"],
            selectcolor=BRAND["accent"], activebackground=BAR,
            indicatoron=False, padx=6, pady=2, bd=1, relief="groove",
            cursor="hand2")
        self._tb_italic_chk.pack(side="right", padx=2)

        self._tb_bold_btn = tk.Label(bar, text=" B ", bg=BRAND["surface"],
                                      fg=BRAND["muted"],
                                      font=("Segoe UI", 10, "bold"),
                                      padx=4, pady=2, relief="groove", bd=1)
        self._tb_bold_btn.pack(side="right", padx=2)
        Tooltip(self._tb_bold_btn, "כותרת תמיד מודגשת; ברכה/תחתון - לא")
        sep()

        # ?? Color swatch ?????????????????????????????????????????????????????
        self._tb_color_btn = tk.Button(bar, text="  ? צבע  ", bg="#144C8A",
                                        fg="white", bd=0, padx=8, pady=3,
                                        cursor="hand2", font=("Segoe UI", 9, "bold"),
                                        command=self._tb_pick_color)
        self._tb_color_btn.pack(side="right", padx=4)

        self._tb_eyedrop_btn = tk.Button(
            bar, text="🔍", bg=BRAND["surface"], fg=BRAND["text"],
            bd=0, padx=7, pady=3, cursor="hand2", font=("Segoe UI", 10),
            command=self.toggle_eyedropper)
        self._tb_eyedrop_btn.pack(side="right", padx=1)
        Tooltip(self._tb_eyedrop_btn, "בחר צבע מהקנבס")
        sep()

        # ?? Effects ???????????????????????????????????????????????????????????
        self._tb_shadow_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bar, text="צל", variable=self._tb_shadow_var,
                       command=self._tb_apply, bg=BAR, fg=BRAND["text"],
                       selectcolor=BRAND["accent"], activebackground=BAR,
                       font=("Segoe UI", 9)).pack(side="right", padx=3)

        self._tb_gradient_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bar, text="Gradient", variable=self._tb_gradient_var,
                       command=self._tb_apply, bg=BAR, fg=BRAND["text"],
                       selectcolor=BRAND["accent"], activebackground=BAR,
                       font=("Segoe UI", 9)).pack(side="right", padx=3)
        tk.Button(bar, text="?", bg=BRAND["surface"], fg=BRAND["text"],
                  bd=0, padx=6, pady=2, cursor="hand2", font=("Segoe UI", 9),
                  command=lambda: self.open_gradient_popup(
                      self._active_text_target)).pack(side="right", padx=1)

        self._tb_stroke_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bar, text="Stroke", variable=self._tb_stroke_var,
                       command=self._tb_apply, bg=BAR, fg=BRAND["text"],
                       selectcolor=BRAND["accent"], activebackground=BAR,
                       font=("Segoe UI", 9)).pack(side="right", padx=3)
        sep()

        # ?? Position X / Y ???????????????????????????????????????????????????
        self._tb_y_var = tk.IntVar(value=0)
        tk.Label(bar, text="Y", bg=BAR, fg=BRAND["muted"],
                 font=("Segoe UI", 8)).pack(side="right", padx=(8, 1))
        y_box = tk.Spinbox(bar, from_=-50, to=50, textvariable=self._tb_y_var,
                           width=4, command=self._tb_apply, justify="center",
                           bg=BRAND["surface"], fg=BRAND["text"], relief="flat")
        y_box.pack(side="right", padx=2)
        y_box.bind("<Return>",   lambda e: self._tb_apply())
        y_box.bind("<FocusOut>", lambda e: self._tb_apply())

        self._tb_x_var = tk.IntVar(value=0)
        tk.Label(bar, text="X", bg=BAR, fg=BRAND["muted"],
                 font=("Segoe UI", 8)).pack(side="right", padx=(8, 1))
        x_box = tk.Spinbox(bar, from_=-50, to=50, textvariable=self._tb_x_var,
                           width=4, command=self._tb_apply, justify="center",
                           bg=BRAND["surface"], fg=BRAND["text"], relief="flat")
        x_box.pack(side="right", padx=2)
        x_box.bind("<Return>",   lambda e: self._tb_apply())
        x_box.bind("<FocusOut>", lambda e: self._tb_apply())
        sep()

        # ?? Line spacing (body only, leftmost) ????????????????????????????????
        self._tb_spacing_var = tk.IntVar(value=122)
        self._tb_spacing_frame = tk.Frame(bar, bg=BAR)
        tk.Label(self._tb_spacing_frame, text="ג‰¡", bg=BAR, fg=BRAND["muted"],
                 font=("Segoe UI", 12)).pack(side="right", padx=(4, 1))
        sp = tk.Spinbox(self._tb_spacing_frame, from_=80, to=200,
                        textvariable=self._tb_spacing_var, width=4,
                        command=self._tb_apply, justify="center",
                        bg=BRAND["surface"], fg=BRAND["text"], relief="flat")
        sp.pack(side="right", padx=2)
        sp.bind("<Return>",   lambda e: self._tb_apply())
        sp.bind("<FocusOut>", lambda e: self._tb_apply())
        Tooltip(self._tb_spacing_frame, "מרווח שורות (לברכה בלבד)")

    def _show_text_topbar(self):
        if hasattr(self, "_text_topbar"):
            if self._text_topbar.winfo_manager() != "pack":
                if self.normal_view.winfo_ismapped():
                    self.normal_view.pack_forget()
                    self._text_topbar.pack(side="top", fill="x", pady=(0, 8))
                    self.normal_view.pack(fill="both", expand=True)
                else:
                    self._text_topbar.pack(side="top", fill="x", pady=(0, 8))
            target = getattr(self, "_active_text_target", getattr(self, "_editor_text_target", "body"))
            self._tb_set_target(target)

    def _hide_text_topbar(self):
        if hasattr(self, "_text_topbar"):
            self._text_topbar.pack_forget()

    def _tb_set_target(self, target):
        self._active_text_target = target
        if hasattr(self, "_text_type_buttons"):
            self._editor_text_target = target
            self._refresh_text_type_buttons()
        self._tb_sync_from_target()
        for tid, btn in self._tb_target_btns.items():
            active = tid == target
            btn.configure(bg=BRAND["gold"] if active else BRAND["surface"],
                          fg=BRAND["bg"] if active else BRAND["text"])
        self._refresh_text_toggle_buttons()
        if hasattr(self, "_tb_spacing_frame") and target == "body":
            self._tb_spacing_frame.pack(side="right")
        elif hasattr(self, "_tb_spacing_frame"):
            self._tb_spacing_frame.pack_forget()

    def _tb_sync_from_target(self):
        t = self._active_text_target
        self._tb_syncing = True
        try:
            font_val = getattr(self, f"{t}_font").get()
            if font_val in (self._tb_font_cb["values"] or ()):
                self._tb_font_cb.set(font_val)
            if hasattr(self, "_tb_font_star"):
                self._tb_font_star.configure(text="★" if font_val in self.font_favorites else "☆")
            size_attr = getattr(self, f"{t}_size", None)
            if size_attr:
                self._tb_size_var.set(size_attr.get())
                if hasattr(self, "_active_size_var"):
                    self._active_size_var.set(size_attr.get())
            opacity_attr = getattr(self, f"{t}_opacity", None)
            if opacity_attr and hasattr(self, "_active_opacity_var"):
                self._active_opacity_var.set(opacity_attr.get())
            italic_var = getattr(self, f"{t}_italic", None)
            self._tb_italic_var.set(italic_var.get() if italic_var else False)
            bold_var = getattr(self, f"{t}_bold", None)
            self._tb_bold_var.set(bold_var.get() if bold_var else False)
            self._tb_shadow_var.set(getattr(self, f"{t}_shadow").get())
            self._tb_gradient_var.set(getattr(self, f"{t}_gradient").get())
            self._tb_stroke_var.set(getattr(self, f"{t}_stroke_enabled").get())
            self._tb_x_var.set(getattr(self, f"{t}_x_off").get())
            self._tb_y_var.set(getattr(self, f"{t}_y_off").get())
            if t == "body":
                self._tb_spacing_var.set(self.body_line_spacing.get())
            self._refresh_align_buttons()
            color = getattr(self, f"{t}_color").get()
            r, g, b = hex_to_rgb(color)
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            self._tb_color_btn.configure(
                bg=color,
                fg="white" if luma < 128 else "#111827",
                text=f"  ■ {color}  ")
            self._refresh_text_toggle_buttons()
        except Exception:
            pass
        finally:
            self._tb_syncing = False

    def _tb_apply(self):
        if self._tb_syncing:
            return
        t = self._active_text_target
        try:
            font_val = self._tb_font_cb.get()
            if font_val:
                getattr(self, f"{t}_font").set(font_val)
            size_attr = getattr(self, f"{t}_size", None)
            if size_attr:
                try:
                    size_attr.set(int(self._tb_size_var.get()))
                except (ValueError, tk.TclError):
                    pass
            italic_var = getattr(self, f"{t}_italic", None)
            if italic_var:
                italic_var.set(self._tb_italic_var.get())
            bold_var = getattr(self, f"{t}_bold", None)
            if bold_var:
                bold_var.set(self._tb_bold_var.get())
            getattr(self, f"{t}_shadow").set(self._tb_shadow_var.get())
            getattr(self, f"{t}_gradient").set(self._tb_gradient_var.get())
            getattr(self, f"{t}_stroke_enabled").set(self._tb_stroke_var.get())
            if t == "body":
                self.body_line_spacing.set(self._tb_spacing_var.get())
                self.body_italic.set(self._tb_italic_var.get())
                self.body_gradient.set(self._tb_gradient_var.get())
                self.body_shadow.set(self._tb_shadow_var.get())
                self.body_stroke_enabled.set(self._tb_stroke_var.get())
        except Exception:
            pass
        self._refresh_text_toggle_buttons()
        self.schedule_render_preview()

    def _refresh_text_toggle_buttons(self):
        if hasattr(self, "_tb_bold_btn"):
            self._tb_bold_btn.configure(
                bg=BRAND["gold"] if self._tb_bold_var.get() else BRAND["surface"],
                fg=BRAND["bg"] if self._tb_bold_var.get() else BRAND["text"])
        if hasattr(self, "_tb_italic_chk"):
            self._tb_italic_chk.configure(
                bg=BRAND["gold"] if self._tb_italic_var.get() else BRAND["surface"],
                fg=BRAND["bg"] if self._tb_italic_var.get() else BRAND["text"])

    def _tb_toggle_font_favorite(self):
        font_name = self._tb_font_cb.get()
        if not font_name:
            return
        if font_name in self.font_favorites:
            self.font_favorites.remove(font_name)
        else:
            self.font_favorites.add(font_name)
        self._save_settings()
        values = ordered_fonts(self.font_favorites)
        self._tb_font_cb.configure(values=values)
        if hasattr(self, "_tb_font_star"):
            self._tb_font_star.configure(text="★" if font_name in self.font_favorites else "☆")
        for cb in getattr(self, "_font_combo_widgets", []):
            cb.configure(values=values)

    def _toggle_gradient_from_toolbar(self):
        getattr(self, f"{self._active_text_target}_gradient").set(self._tb_gradient_var.get())
        if self._tb_gradient_var.get():
            self.open_gradient_popup(self._active_text_target)
        self.schedule_render_preview()

    def _toggle_shadow_from_toolbar(self):
        getattr(self, f"{self._active_text_target}_shadow").set(self._tb_shadow_var.get())
        if self._tb_shadow_var.get():
            self._open_shadow_popup(self._active_text_target)
        self.schedule_render_preview()

    def _toggle_stroke_from_toolbar(self):
        getattr(self, f"{self._active_text_target}_stroke_enabled").set(self._tb_stroke_var.get())
        if self._tb_stroke_var.get():
            self._open_stroke_popup(self._active_text_target)
        self.schedule_render_preview()

    def _set_active_align(self, value):
        align_var = getattr(self, f"{self._active_text_target}_align", self.body_align)
        align_var.set(value)
        self._refresh_align_buttons()
        self.schedule_render_preview()

    def _set_body_align(self, value):
        self._set_active_align(value)

    def _set_active_size_from_panel(self):
        if getattr(self, "_tb_syncing", False):
            return
        size_attr = getattr(self, f"{self._active_text_target}_size", None)
        if not size_attr or not hasattr(self, "_active_size_var"):
            return
        try:
            size_attr.set(int(self._active_size_var.get()))
            if hasattr(self, "_tb_size_var"):
                self._tb_size_var.set(size_attr.get())
            self.schedule_render_preview()
        except (ValueError, tk.TclError):
            pass

    def _set_active_opacity_from_panel(self):
        if getattr(self, "_tb_syncing", False):
            return
        opacity_attr = getattr(self, f"{self._active_text_target}_opacity", None)
        if not opacity_attr or not hasattr(self, "_active_opacity_var"):
            return
        try:
            opacity_attr.set(max(0, min(100, int(self._active_opacity_var.get()))))
            self.schedule_render_preview()
        except (ValueError, tk.TclError):
            pass

    def _refresh_align_buttons(self):
        align_var = getattr(self, f"{self._active_text_target}_align", self.body_align)
        for value, btn in getattr(self, "_tb_align_btns", {}).items():
            active = value == align_var.get()
            btn.configure(bg=BRAND["gold"] if active else BRAND["surface"],
                          fg=BRAND["bg"] if active else BRAND["text"])

    def _refresh_text_type_buttons(self):
        current = getattr(self, "_editor_text_target", getattr(self, "_active_text_target", "body"))
        for target, btn in getattr(self, "_text_type_buttons", {}).items():
            active = target == current
            btn.configure(bg=BRAND["gold"] if active else BRAND["surface"],
                          fg=BRAND["bg"] if active else BRAND["text"])

    def _text_style_presets(self):
        return [
            {
                "id": "gold_gloss", "name": "זהב מבריק",
                "desc": "גרדיינט זהב, קו כהה עדין וצל רך",
                "color": "#B7791F", "opacity": 100, "bold": True, "italic": False,
                "gradient": True, "gradient_a": "#FFF7AD", "gradient_b": "#B7791F",
                "stroke": True, "stroke_color": "#5B3414", "stroke_width": 2,
                "shadow": True, "shadow_color": "#000000", "shadow_size": 5,
                "shadow_angle": 45, "shadow_opacity": 28,
            },
            {
                "id": "balloon", "name": "כתב בלון",
                "desc": "מילוי שקוף לגמרי, קו שחור עבה ונקי",
                "color": "#FFFFFF", "opacity": 0, "bold": True, "italic": False,
                "gradient": False,
                "stroke": True, "stroke_color": "#020617", "stroke_width": 7,
                "shadow": False, "shadow_color": "#000000", "shadow_size": 0,
                "shadow_angle": 45, "shadow_opacity": 0,
            },
            {
                "id": "three_d", "name": "תלת מימד",
                "desc": "כחול עמוק עם קו בהיר וצל מורגש",
                "color": "#123766", "opacity": 100, "bold": True, "italic": False,
                "gradient": True, "gradient_a": "#4DA3FF", "gradient_b": "#0B1B35",
                "stroke": True, "stroke_color": "#E0F2FE", "stroke_width": 2,
                "shadow": True, "shadow_color": "#07111F", "shadow_size": 12,
                "shadow_angle": 45, "shadow_opacity": 62,
            },
            {
                "id": "classic_luxury", "name": "יוקרתי קלאסי",
                "desc": "כחול כהה, קו זהב דק וצל מינימלי",
                "color": "#111827", "opacity": 100, "bold": True, "italic": False,
                "gradient": False,
                "stroke": True, "stroke_color": "#D6A84F", "stroke_width": 1,
                "shadow": True, "shadow_color": "#000000", "shadow_size": 3,
                "shadow_angle": 45, "shadow_opacity": 22,
            },
            {
                "id": "soft_wedding", "name": "חתונה רך",
                "desc": "גווני שיש אפור עדין עם נגיעה זהובה",
                "color": "#6B7280", "opacity": 100, "bold": False, "italic": True,
                "gradient": True, "gradient_a": "#F8FAFC", "gradient_b": "#C9A44C",
                "stroke": True, "stroke_color": "#D6A84F", "stroke_width": 1,
                "shadow": True, "shadow_color": "#64748B", "shadow_size": 3,
                "shadow_angle": 45, "shadow_opacity": 18,
            },
            {
                "id": "black_white_outline", "name": "שחור עם קו לבן",
                "desc": "כתב שחור ברור עם קו מתאר לבן בעובי 2",
                "color": "#020617", "opacity": 100, "bold": True, "italic": False,
                "gradient": False,
                "stroke": True, "stroke_color": "#FFFFFF", "stroke_width": 2,
                "shadow": False, "shadow_color": "#000000", "shadow_size": 0,
                "shadow_angle": 45, "shadow_opacity": 0,
            },
            {
                "id": "white_black_outline", "name": "לבן עם קו שחור",
                "desc": "כתב לבן נקי עם קו מתאר שחור בעובי 2",
                "color": "#FFFFFF", "opacity": 100, "bold": True, "italic": False,
                "gradient": False,
                "stroke": True, "stroke_color": "#020617", "stroke_width": 2,
                "shadow": False, "shadow_color": "#000000", "shadow_size": 0,
                "shadow_angle": 45, "shadow_opacity": 0,
            },
        ]

    def _build_text_style_picker(self, parent):
        wrap = tk.Frame(parent, bg="#111827")
        wrap.pack(fill="x", pady=(12, 0))
        tk.Label(wrap, text="סגנון כתב", bg="#111827", fg=BRAND["muted"],
                 font=("Segoe UI", 10)).pack(anchor="e", pady=(0, 5))
        self._style_picker_btn = tk.Button(
            wrap, text="בחר סגנון  ▾", command=self._open_text_style_dropdown,
            bg=BRAND["surface"], fg=BRAND["text"], bd=0, padx=14, pady=10,
            anchor="e", font=("Segoe UI", 10, "bold"), cursor="hand2")
        self._style_picker_btn.pack(fill="x")

    def _style_preview_image(self, style):
        img = Image.new("RGBA", (188, 54), (15, 23, 42, 255))
        d = ImageDraw.Draw(img, "RGBA")
        try:
            fp = resolve_font("Segoe UI", bold=style.get("bold", False), italic=style.get("italic", False))
            font = ImageFont.truetype(fp, 27) if fp else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        sample = bidi_text("ברכה")
        bb = d.textbbox((0, 0), sample, font=font, stroke_width=int(style.get("stroke_width", 0)))
        x = (img.width - (bb[2] - bb[0])) / 2
        y = (img.height - (bb[3] - bb[1])) / 2 - 4
        if style.get("shadow"):
            dx = int(round(math.cos(math.radians(style.get("shadow_angle", 45))) * style.get("shadow_size", 4)))
            dy = int(round(math.sin(math.radians(style.get("shadow_angle", 45))) * style.get("shadow_size", 4)))
            alpha = int(255 * style.get("shadow_opacity", 35) / 100)
            d.text((x + dx, y + dy), sample, font=font,
                   fill=hex_to_rgb(style.get("shadow_color", "#000000")) + (alpha,))
        stroke_width = int(style.get("stroke_width", 0)) if style.get("stroke") else 0
        if style.get("gradient"):
            if style.get("opacity", 100) > 0:
                draw_gradient_text(
                    img, (x, y), sample, font,
                    style.get("gradient_a", style["color"]),
                    style.get("gradient_b", style["color"]),
                    "linear", 90, stroke_width, style.get("stroke_color", "#000000"))
            elif stroke_width:
                d.text((x, y), sample, font=font, fill=(255, 255, 255, 0),
                       stroke_width=stroke_width,
                       stroke_fill=hex_to_rgb(style.get("stroke_color", "#000000")) + (255,))
        else:
            d.text((x, y), sample, font=font,
                   fill=hex_to_rgb(style["color"]) + (int(255 * style.get("opacity", 100) / 100),),
                   stroke_width=stroke_width,
                   stroke_fill=hex_to_rgb(style.get("stroke_color", "#000000")) + (255,))
        return ImageTk.PhotoImage(img)

    def _open_text_style_dropdown(self):
        if hasattr(self, "_style_dropdown") and self._style_dropdown.winfo_exists():
            self._style_dropdown.lift()
            return
        win = tk.Toplevel(self.root)
        self._style_dropdown = win
        win.title("סגנונות כתב")
        win.configure(bg="#0F172A")
        win.transient(self.root)
        win.resizable(False, False)
        win.grab_set()
        win._imgs = []
        tk.Label(win, text="סגנונות כתב", bg="#0F172A", fg=BRAND["gold"],
                 font=("Segoe UI Semibold", 15)).pack(anchor="e", padx=14, pady=(12, 4))
        tk.Label(win, text="הסגנון יחול על תיבת הטקסט הפעילה בלבד", bg="#0F172A",
                 fg=BRAND["muted"], font=("Segoe UI", 9)).pack(anchor="e", padx=14, pady=(0, 8))
        list_frame = tk.Frame(win, bg="#0F172A")
        list_frame.pack(fill="both", padx=10, pady=(0, 8))
        for style in self._text_style_presets():
            row = tk.Frame(list_frame, bg=BRAND["surface"], padx=10, pady=8,
                           highlightthickness=1, highlightbackground=BRAND["border"])
            row.pack(fill="x", padx=6, pady=4)
            img = self._style_preview_image(style)
            win._imgs.append(img)
            tk.Label(row, image=img, bg=BRAND["surface"]).pack(side="left", padx=(0, 9))
            txt = tk.Frame(row, bg=BRAND["surface"])
            txt.pack(side="right", fill="x", expand=True)
            tk.Label(txt, text=style["name"], bg=BRAND["surface"], fg=BRAND["gold"],
                     font=("Segoe UI", 10, "bold"), anchor="e").pack(fill="x")
            tk.Label(txt, text=style["desc"], bg=BRAND["surface"], fg=BRAND["muted"],
                     font=("Segoe UI", 8), anchor="e", justify="right", wraplength=180).pack(fill="x")
            for widget in (row, txt):
                widget.bind("<Button-1>", lambda e, s=style: self._apply_text_style(s))
            for child in txt.winfo_children():
                child.bind("<Button-1>", lambda e, s=style: self._apply_text_style(s))
        tk.Button(win, text="סגור", command=win.destroy, bg=BRAND["surface"],
                  fg=BRAND["text"], bd=0, padx=18, pady=7,
                  font=("Segoe UI", 10, "bold"), cursor="hand2").pack(pady=(0, 12))
        win.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - win.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - win.winfo_height()) // 2)
        win.geometry(f"+{x}+{y}")

    def _apply_text_style(self, style):
        target = getattr(self, "_active_text_target", "body")
        if hasattr(self, "_style_dropdown") and self._style_dropdown.winfo_exists():
            self._style_dropdown.destroy()
        getattr(self, f"{target}_color").set(style["color"])
        getattr(self, f"{target}_opacity").set(style.get("opacity", 100))
        bold_var = getattr(self, f"{target}_bold", None)
        if bold_var:
            bold_var.set(style.get("bold", False))
        italic_var = getattr(self, f"{target}_italic", None)
        if italic_var:
            italic_var.set(style.get("italic", False))
        getattr(self, f"{target}_gradient").set(style.get("gradient", False))
        if style.get("gradient"):
            getattr(self, f"{target}_gradient_a").set(style.get("gradient_a", style["color"]))
            getattr(self, f"{target}_gradient_b").set(style.get("gradient_b", style["color"]))
        getattr(self, f"{target}_stroke_enabled").set(style.get("stroke", False))
        getattr(self, f"{target}_stroke_color").set(style.get("stroke_color", "#FFFFFF"))
        getattr(self, f"{target}_stroke_width").set(style.get("stroke_width", 0))
        getattr(self, f"{target}_shadow").set(style.get("shadow", False))
        getattr(self, f"{target}_shadow_color").set(style.get("shadow_color", "#000000"))
        getattr(self, f"{target}_shadow_size").set(style.get("shadow_size", 0))
        getattr(self, f"{target}_shadow_angle").set(style.get("shadow_angle", 45))
        getattr(self, f"{target}_shadow_opacity").set(style.get("shadow_opacity", 35))
        for color_key in ("color", "gradient_a", "gradient_b", "stroke_color", "shadow_color"):
            if style.get(color_key):
                self._add_recent_color(style[color_key])
        if hasattr(self, "_style_picker_btn"):
            self._style_picker_btn.configure(text=f"{style['name']}  ▾")
        self._tb_sync_from_target()
        self.render_preview()

    def _tb_pick_color(self):
        t = self._active_text_target
        color_var = getattr(self, f"{t}_color")
        hex_c = self._ask_color(color_var.get(), "בחר צבע טקסט")
        if hex_c:
            color_var.set(hex_c)
            r, g, b = hex_to_rgb(hex_c)
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            self._tb_color_btn.configure(
                bg=hex_c,
                fg="white" if luma < 128 else "#111827",
                text=f"  ■ {hex_c}  ")
            self.schedule_render_preview()

    def _apply_text_type_preset(self, size, weight="normal"):
        self.body_size.set(size)
        if hasattr(self, "_tb_size_var"):
            self._tb_size_var.set(size)
        self.body_shadow.set(weight == "bold")
        self.schedule_render_preview()

    def _simple_number_control(self, parent, label, var, min_value, max_value):
        row = tk.Frame(parent, bg="#111827")
        row.pack(fill="x", pady=8)
        tk.Label(row, text=label, bg="#111827", fg=BRAND["muted"],
                 font=("Segoe UI", 10)).pack(anchor="e")
        box = tk.Frame(row, bg=BRAND["surface"])
        box.pack(fill="x", pady=(4, 0))
        tk.Button(box, text="+", command=lambda: [var.set(min(max_value, var.get() + 2)), self.schedule_render_preview()],
                  bg=BRAND["surface"], fg=BRAND["text"], bd=0, padx=12, pady=7).pack(side="left")
        tk.Label(box, textvariable=var, bg=BRAND["surface"], fg=BRAND["text"],
                 font=("Segoe UI", 11)).pack(side="left", fill="x", expand=True)
        tk.Button(box, text="-", command=lambda: [var.set(max(min_value, var.get() - 2)), self.schedule_render_preview()],
                  bg=BRAND["surface"], fg=BRAND["text"], bd=0, padx=12, pady=7).pack(side="left")

    def _simple_slider(self, parent, label, var, min_value, max_value):
        row = tk.Frame(parent, bg="#111827")
        row.pack(fill="x", pady=8)
        tk.Label(row, text=label, bg="#111827", fg=BRAND["muted"],
                 font=("Segoe UI", 10)).pack(anchor="e")
        tk.Scale(row, from_=min_value, to=max_value, orient="horizontal", variable=var,
                 command=lambda _=None: self.schedule_render_preview(),
                 bg="#111827", fg=BRAND["text"], highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x")

    def _open_shadow_popup(self, target):
        win = tk.Toplevel(self.root)
        win.title("צל")
        win.configure(bg=BRAND["panel"])
        win.transient(self.root)
        color = getattr(self, f"{target}_shadow_color")
        for label, var, lo, hi in [
            ("מרחק", getattr(self, f"{target}_shadow_size"), 0, 40),
            ("זווית", getattr(self, f"{target}_shadow_angle"), 0, 360),
            ("שקיפות", getattr(self, f"{target}_shadow_opacity"), 0, 100),
        ]:
            self._simple_slider(win, label, var, lo, hi)
        self._inline_btn(win, "צבע צל", lambda: self.pick_var_color(color, "צבע צל"), anchor="e")
        tk.Button(win, text="סגור", command=win.destroy, bg=BRAND["accent"], fg="white",
                  bd=0, padx=16, pady=7, font=("Segoe UI", 10, "bold")).pack(pady=12)

    def _open_stroke_popup(self, target):
        win = tk.Toplevel(self.root)
        win.title("קו מתאר")
        win.configure(bg=BRAND["panel"])
        win.transient(self.root)
        self._simple_slider(win, "עובי קו", getattr(self, f"{target}_stroke_width"), 0, 18)
        self._inline_btn(win, "צבע קו", lambda: self.pick_var_color(getattr(self, f"{target}_stroke_color"), "צבע קו"), anchor="e")
        tk.Button(win, text="סגור", command=win.destroy, bg=BRAND["accent"], fg="white",
                  bd=0, padx=16, pady=7, font=("Segoe UI", 10, "bold")).pack(pady=12)

    def _open_card_popup(self):
        win = tk.Toplevel(self.root)
        win.title("תיבת טקסט")
        win.configure(bg=BRAND["panel"])
        win.transient(self.root)
        self._chk2(win, "הצג תיבה", self.card_enabled)
        self._simple_slider(win, "שקיפות תיבה", self.card_opacity, 0, 100)
        self._inline_btn(win, "צבע תיבה", self.pick_card_color, anchor="e")
        tk.Button(win, text="סגור", command=win.destroy, bg=BRAND["accent"], fg="white",
                  bd=0, padx=16, pady=7, font=("Segoe UI", 10, "bold")).pack(pady=12)

    # ?? Step 5: text editor ???????????????????????????????????????????????????
    def build_text_step(self):
        self.left.configure(width=360, bg="#111827")
        self.right.configure(bg="#111827")
        self._left_vsb.pack_forget()
        self._left_canvas.configure(bg="#111827", highlightthickness=0)
        self.step_area.configure(bg="#111827")
        self.preview_label.configure(bg="#111827")

        header = tk.Frame(self.step_area, bg="#111827")
        header.pack(fill="x", padx=18, pady=(14, 10))
        tk.Label(header, text="מעצב ברכות", bg="#111827", fg=BRAND["text"],
                 font=("Segoe UI Semibold", 18)).pack(side="right")

        tabs = tk.Frame(self.step_area, bg=BRAND["surface"])
        tabs.pack(fill="x", padx=18, pady=(0, 12))
        tab_text_btn = tk.Button(tabs, text="טקסט", bd=0, padx=22, pady=12,
                                 font=("Segoe UI", 11, "bold"), cursor="hand2")
        tab_style_btn = tk.Button(tabs, text="עיצוב", bd=0, padx=22, pady=12,
                                  font=("Segoe UI", 11, "bold"), cursor="hand2")
        tab_style_btn.pack(side="left", fill="x", expand=True)
        tab_text_btn.pack(side="right", fill="x", expand=True)

        content = tk.Frame(self.step_area, bg="#111827")
        content.pack(fill="both", expand=True, padx=18)
        text_tab = tk.Frame(content, bg="#111827")
        style_tab = tk.Frame(content, bg="#111827")

        def show_tab(name):
            for frame in (text_tab, style_tab):
                frame.pack_forget()
            active_text = name == "text"
            (text_tab if active_text else style_tab).pack(fill="both", expand=True)
            tab_text_btn.configure(bg=BRAND["gold"] if active_text else BRAND["surface"],
                                   fg=BRAND["bg"] if active_text else BRAND["muted"])
            tab_style_btn.configure(bg=BRAND["gold"] if not active_text else BRAND["surface"],
                                    fg=BRAND["bg"] if not active_text else BRAND["muted"])

        tab_text_btn.configure(command=lambda: show_tab("text"))
        tab_style_btn.configure(command=lambda: show_tab("style"))

        tk.Label(text_tab, text="תיבת טקסט", bg="#111827", fg=BRAND["muted"],
                 font=("Segoe UI", 10)).pack(anchor="e", pady=(0, 6))
        editor_target = getattr(self, "_editor_text_target", getattr(self, "_active_text_target", "body"))
        if editor_target not in ("body", "title", "third"):
            editor_target = "body"
        self._editor_text_target = editor_target
        self._active_text_target = editor_target

        self.text_box = self._make_text(text_tab, height=10)
        self.text_box.pack(fill="both", expand=True, pady=(0, 14))
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", self._get_target_text(editor_target))
        self.text_box.bind("<KeyRelease>", lambda e: self.cache_and_render(debounce=True), add="+")
        self.text_box.bind("<FocusIn>", lambda e: self._tb_set_target(getattr(self, "_editor_text_target", "body")))

        type_row = tk.Frame(text_tab, bg="#111827")
        type_row.pack(fill="x", pady=(4, 0))
        self._text_type_buttons = {}
        for target, label in [("body", "תוכן"), ("third", "נושא"), ("title", "כותרת")]:
            btn = tk.Button(type_row, text=label, command=lambda t=target: self._load_target_into_editor(t),
                            bg=BRAND["surface"], fg=BRAND["text"], bd=0, padx=14, pady=9,
                            font=("Segoe UI", 10, "bold"), cursor="hand2")
            btn.pack(side="right", padx=4, fill="x", expand=True)
            self._text_type_buttons[target] = btn
        self._refresh_text_type_buttons()
        self._build_text_style_picker(text_tab)

        self._active_size_var = tk.IntVar(value=self.body_size.get())
        self._simple_slider(style_tab, "גודל טקסט נבחר", self._active_size_var, 10, 300)
        self._active_size_var.trace_add("write", lambda *_: self._set_active_size_from_panel())
        self._active_opacity_var = tk.IntVar(value=self.body_opacity.get())
        self._simple_slider(style_tab, "אטימות טקסט (0 שקוף)", self._active_opacity_var, 0, 100)
        self._active_opacity_var.trace_add("write", lambda *_: self._set_active_opacity_from_panel())
        self._font_combo("גופן", self.body_font, style_tab)
        self._simple_slider(style_tab, "ריווח בין שורות", self.body_line_spacing, 80, 180)
        self._simple_slider(style_tab, "ריווח בין אותיות", self.body_letter_spacing, 0, 40)
        align_row = tk.Frame(style_tab, bg="#111827")
        align_row.pack(fill="x", pady=(12, 0))
        for value, label in [("left", "שמאל"), ("center", "מרכז"), ("right", "ימין")]:
            tk.Button(align_row, text=label, command=lambda v=value: self._set_active_align(v),
                      bg=BRAND["surface"], fg=BRAND["text"], bd=0, padx=12, pady=8,
                      font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="right", padx=4, fill="x", expand=True)

        show_tab("text")
        self._tb_set_target(editor_target)
        self.render_preview()
        return
        self._font_combo_widgets = []
        self._section_hint("עצב/י את הטקסט. Ctrl+C/V/A ותפריט ימני עובדים בכל תיבה.")

        # ?? Title collapsible ?????????????????????????????????????????????
        title_col = Collapsible(self.step_area, "כותרת", start_open=True)
        self._lbl2("טקסט כותרת", title_col.body)
        ent_title = tk.Entry(title_col.body, textvariable=self.title_text,
                             justify="right", bg=BRAND["surface"], fg=BRAND["text"],
                             insertbackground="white", relief="flat",
                             font=("Segoe UI",12))
        ent_title.pack(fill="x", pady=4, padx=4)
        ent_title.bind("<KeyRelease>", lambda e: self.schedule_render_preview())
        ent_title.bind("<FocusIn>", lambda e: self._tb_set_target("title"))
        self._add_copy_paste(ent_title)

        r = tk.Frame(title_col.body, bg=BRAND["panel"])
        r.pack(fill="x", pady=4)
        self._inline_btn(r, "צבע כותרת", self.pick_title_color)
        self._chk(r, "צל",  self.title_shadow)
        self._chk(r, "נטוי", self.title_italic)
        self._chk(r, "Gradient", self.title_gradient)
        self._inline_btn(r, "Gradient...", lambda: self.open_gradient_popup("title"))

        self._lbl2("גודל כותרת", title_col.body)
        tk.Scale(title_col.body, from_=24, to=300, orient="horizontal",
                 variable=self.title_size, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)

        self._font_combo("גופן כותרת", self.title_font, title_col.body)
        self._shadow_controls(title_col.body, "title")
        self._stroke_controls(title_col.body, "title")
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

        # ?? Body collapsible ??????????????????????????????????????????????
        body_col = Collapsible(self.step_area, "ברכה / גוף טקסט", start_open=True)
        self.text_box = self._make_text(body_col.body, height=8)
        self.text_box.pack(fill="x", pady=(0,6), padx=4)
        self.text_box.delete("1.0","end")
        self.text_box.insert("1.0", self._text_cache)
        self._configure_rtl_input(self.text_box)
        self.text_box.bind("<KeyRelease>", lambda e: self.cache_and_render(debounce=True), add="+")
        self.text_box.bind("<FocusIn>", lambda e: self._tb_set_target("body"))

        rb = tk.Frame(body_col.body, bg=BRAND["panel"])
        rb.pack(fill="x", pady=4)
        self._inline_btn(rb, "צבע טקסט",    self.pick_body_color)
        self._inline_btn(rb, "הדבק מהלוח",   self.paste_to_main)
        self._chk(rb, "צל",  self.body_shadow)
        self._chk(rb, "נטוי", self.body_italic)
        self._chk(rb, "Gradient", self.body_gradient)
        self._inline_btn(rb, "Gradient...", lambda: self.open_gradient_popup("body"))

        self._lbl2("גודל טקסט", body_col.body)
        tk.Scale(body_col.body, from_=18, to=220, orient="horizontal",
                 variable=self.body_size, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)

        self._lbl2("מרווח בין שורות", body_col.body)
        tk.Scale(body_col.body, from_=80, to=180, orient="horizontal",
                 variable=self.body_line_spacing, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)

        self._font_combo("גופן ברכה", self.body_font, body_col.body)
        self._shadow_controls(body_col.body, "body")
        self._stroke_controls(body_col.body, "body")
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

        add_third = tk.Button(self.step_area, text="הוסף תיבת טקסט", command=self.add_third_text_box,
                              bg=BRAND["accent"], fg="white", bd=0, padx=12, pady=7,
                              font=("Segoe UI",10,"bold"), cursor="hand2")
        add_third.pack(anchor="e", padx=16, pady=(8,4))
        Tooltip(add_third, "הוסף טקסט תחתון, למשל שם נותן המתנה")
        if self.third_enabled.get():
            self._build_third_text_controls()

        # ?? Card bg collapsible ???????????????????????????????????????????
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

        # ?? Export / SPP collapsible ??????????????????????????????????????
        exp_col = Collapsible(self.step_area, "יצוא ושיתוף", start_open=True)
        row_exp = tk.Frame(exp_col.body, bg=BRAND["panel"])
        row_exp.pack(fill="x", pady=4)
        for txt, cmd, bg in [
            ("יצוא PNG",         self.export_png,    BRAND["accent"]),
            ("יצוא PDF",         self.export_pdf,    BRAND["surface"]),
            ("תיקיית יצוא",      self.open_exports,  BRAND["surface"]),
            ("שלח ל-SPP  ??",    self._spp_stub,     BRAND["orange"]),
        ]:
            tk.Button(row_exp, text=txt, command=cmd, bg=bg, fg="white",
                      bd=0, padx=12, pady=6, font=("Segoe UI",10,"bold"),
                      cursor="hand2").pack(side="right", padx=3)

    def _spp_stub(self):
        self.notify("חיבור ל-SPP יתווסף בגרסה הבאה")

    # ?? widget helpers ????????????????????????????????????????????????????????
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
        anchor = {"e": "right", "w": "left"}.get(anchor, anchor)
        btn.pack(side=anchor, padx=4)
        Tooltip(btn, text)
        return btn

    def _stroke_controls(self, parent, target):
        enabled = getattr(self, f"{target}_stroke_enabled")
        color = getattr(self, f"{target}_stroke_color")
        width = getattr(self, f"{target}_stroke_width")
        box = tk.Frame(parent, bg=BRAND["panel"])
        box.pack(fill="x", pady=4)
        self._chk(box, "Stroke", enabled)
        self._inline_btn(box, "צבע קו", lambda c=color: self.pick_var_color(c, "צבע קו מתאר"))
        tk.Label(box, text="עובי", bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI",9)).pack(side="right", padx=(8,2))
        tk.Spinbox(box, from_=0, to=18, textvariable=width, width=4, justify="center",
                   command=self.render_preview, bg=BRAND["surface"], fg=BRAND["text"],
                   relief="flat").pack(side="right")

    def _shadow_controls(self, parent, target):
        enabled = getattr(self, f"{target}_shadow")
        color = getattr(self, f"{target}_shadow_color")
        size = getattr(self, f"{target}_shadow_size")
        angle = getattr(self, f"{target}_shadow_angle")
        opacity = getattr(self, f"{target}_shadow_opacity")
        box = tk.Frame(parent, bg=BRAND["panel"])
        box.pack(fill="x", pady=4)
        self._chk(box, "Shadow", enabled)
        self._inline_btn(box, "צבע צל", lambda c=color: self.pick_var_color(c, "צבע צל"))
        for label, var, max_value in [("גודל", size, 40), ("זווית", angle, 360), ("שקיפות", opacity, 100)]:
            tk.Label(box, text=label, bg=BRAND["panel"], fg=BRAND["muted"],
                     font=("Segoe UI",9)).pack(side="right", padx=(8,2))
            tk.Spinbox(box, from_=0, to=max_value, textvariable=var, width=4, justify="center",
                       command=self.schedule_render_preview, bg=BRAND["surface"], fg=BRAND["text"],
                       relief="flat").pack(side="right")

    def add_third_text_box(self):
        self.third_enabled.set(True)
        if not self.third_text.get().strip():
            self.third_text.set("מאת ...")
        self.show_step("text")

    def _build_third_text_controls(self):
        third_col = Collapsible(self.step_area, "תיבת טקסט תחתונה", start_open=True)
        row = tk.Frame(third_col.body, bg=BRAND["panel"])
        row.pack(fill="x", pady=4)
        self._chk(row, "הצג", self.third_enabled)
        ent = tk.Entry(third_col.body, textvariable=self.third_text, justify="right",
                       bg=BRAND["surface"], fg=BRAND["text"], insertbackground="white",
                       relief="flat", font=("Segoe UI",12))
        ent.pack(fill="x", pady=4, padx=4)
        ent.bind("<KeyRelease>", lambda e: self.schedule_render_preview())
        ent.bind("<FocusIn>", lambda e: self._tb_set_target("third"))
        self._add_copy_paste(ent)
        tools = tk.Frame(third_col.body, bg=BRAND["panel"])
        tools.pack(fill="x", pady=4)
        self._inline_btn(tools, "צבע", lambda: self.pick_var_color(self.third_color, "צבע טקסט תחתון"))
        self._chk(tools, "Gradient", self.third_gradient)
        self._inline_btn(tools, "Gradient...", lambda: self.open_gradient_popup("third"))
        self._font_combo("גופן", self.third_font, third_col.body)
        self._shadow_controls(third_col.body, "third")
        self._stroke_controls(third_col.body, "third")
        self._lbl2("גודל", third_col.body)
        tk.Scale(third_col.body, from_=14, to=160, orient="horizontal",
                 variable=self.third_size, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)
        self._lbl2("מיקום X", third_col.body)
        tk.Scale(third_col.body, from_=-50, to=50, orient="horizontal",
                 variable=self.third_x_off, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)
        self._lbl2("מיקום Y", third_col.body)
        tk.Scale(third_col.body, from_=-50, to=50, orient="horizontal",
                 variable=self.third_y_off, command=lambda _: self.render_preview(),
                 bg=BRAND["panel"], fg="white", highlightthickness=0,
                 troughcolor=BRAND["surface"]).pack(fill="x", padx=4)

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
        star = tk.Button(top, text="?", command=lambda: self.toggle_font_favorite(var),
                         bg=BRAND["surface"], fg=BRAND["gold"], bd=0,
                         width=3, cursor="hand2", font=("Segoe UI", 10, "bold"))
        star.pack(side="left", padx=(0,4))
        Tooltip(star, "סמן גופן כמועדף")
        cb = ttk.Combobox(top, textvariable=var, values=ordered_fonts(self.font_favorites),
                          state="normal", justify="right", font=("Segoe UI",9))
        cb.pack(side="right", fill="x", expand=True)
        self._font_combo_widgets.append(cb)
        preview = tk.Label(row, text="", bg=BRAND["panel"], fg=BRAND["text"],
                           font=("Segoe UI", 10), anchor="e")
        preview.pack(fill="x")
        def refresh(_event=None):
            star.configure(text=("?" if var.get() in self.font_favorites else "?"))
            path = resolve_font(var.get())
            if path:
                try:
                    family = ImageFont.truetype(path, 12).getname()[0]
                    preview.configure(font=(family, 12), text=f"{var.get()}  אבגדה Hadish")
                except Exception:
                    preview.configure(font=("Segoe UI", 10), text=f"{var.get()}  אבגדה Hadish")
            self.schedule_render_preview()
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
        values = ordered_fonts(self.font_favorites)
        for cb in getattr(self, "_font_combo_widgets", []):
            try:
                cb.configure(values=values)
            except Exception:
                pass
        self.schedule_render_preview()

    def _make_text(self, parent, height=6):
        if NativeRtlText.available():
            txt = NativeRtlText(parent, height=height,
                                font=("Segoe UI", 11),
                                bg=BRAND["surface"], fg=BRAND["text"],
                                insertbackground="white")
            self._add_copy_paste(txt)
            self._add_context_menu(txt)
            return txt
        txt = tk.Text(parent, height=height, wrap="word",
                      font=("Segoe UI",11), undo=True,
                      bg=BRAND["surface"], fg=BRAND["text"],
                      insertbackground="white", relief="flat",
                      padx=8, pady=6)
        self._configure_rtl_input(txt)
        self._add_copy_paste(txt)
        self._add_context_menu(txt)
        return txt

    def _add_copy_paste(self, widget):
        self._configure_rtl_input(widget)
        widget.bind("<Control-a>", self._ctrl_a)
        widget.bind("<Control-A>", self._ctrl_a)
        # let Tk handle C/V/X natively ? just ensure no override breaks them
        for seq in ("<Control-c>","<Control-C>","<Control-v>","<Control-V>",
                    "<Control-x>","<Control-X>"):
            widget.bind(seq, lambda e, s=seq: None)
        self._add_rtl_bindings(widget)

    def _configure_rtl_input(self, widget):
        """Keep Hebrew input logical while displaying and selecting it RTL."""
        try:
            widget.configure(justify="right")
        except Exception:
            pass
        already_configured = getattr(widget, "_hadish_rtl_configured", False)
        if isinstance(widget, tk.Text):
            try:
                widget.tag_configure("rtl", justify="right", lmargin1=8, lmargin2=8, rmargin=8)
                widget.tag_add("rtl", "1.0", "end")
            except Exception:
                pass
            if already_configured:
                return
            def refresh_rtl(_event=None, w=widget):
                try:
                    w.tag_add("rtl", "1.0", "end")
                except Exception:
                    pass
            widget.bind("<KeyRelease>", refresh_rtl, add="+")
            widget.bind("<<Paste>>", lambda e, w=widget: w.after_idle(refresh_rtl), add="+")
            widget.bind("<FocusIn>", refresh_rtl, add="+")
        if not already_configured:
            try:
                widget._hadish_rtl_configured = True
            except Exception:
                pass

    def _add_rtl_bindings(self, widget):
        """Use Tk's native cursor, selection and deletion behavior for RTL text."""
        return None

    def _ctrl_a(self, event):
        w = event.widget
        try:
            if isinstance(w, tk.Text):
                w.tag_add("sel","1.0","end-1c"); w.mark_set("insert","end-1c")
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

    # ?? asset grid ????????????????????????????????????????????????????????????
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
        _globs = ["*.png","*.PNG","*.jpg","*.JPG","*.jpeg","*.JPEG"]
        if _cairosvg is not None:
            _globs += ["*.svg","*.SVG"]
        all_paths = sorted({p for g in _globs for p in folder.glob(g)},
                           key=lambda p: p.name.lower())
        for idx, path in enumerate(all_paths):
            try:
                if path.suffix.lower() == ".svg":
                    raw = _load_svg_as_pil(path)
                else:
                    raw = Image.open(path)
                raw.thumbnail((112, 112), Image.Resampling.LANCZOS)
                if raw.mode in ("RGBA", "LA", "P"):
                    rgba = raw.convert("RGBA")
                    white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                    img = Image.alpha_composite(white, rgba).convert("RGB")
                else:
                    img = raw.convert("RGB")
            except Exception:
                img = Image.new("RGB", (112, 112), "#334155")
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

    # ?? blessings step helpers (old simple list, kept as fallback) ????????????
    def paste_to_main(self):
        try:
            txt = self.root.clipboard_get()
            if hasattr(self,"text_box"):
                self.text_box.insert("insert", txt); self.cache_and_render()
        except Exception:
            self.notify("לא נמצא טקסט להדבקה")

    def cache_and_render(self, debounce=False):
        if hasattr(self,"text_box") and self.text_box.winfo_exists():
            if isinstance(self.text_box, tk.Text):
                val = self.text_box.get("1.0","end-1c")
            else:
                val = self.text_box.get("1.0","end")
            self._set_target_text(getattr(self, "_editor_text_target", "body"), val)
        if debounce:
            self.schedule_render_preview()
        else:
            self.render_preview()

    # ?? presets ???????????????????????????????????????????????????????????????
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

    # ?? color pickers ?????????????????????????????????????????????????????????
    def _style_snapshot(self):
        return {
            "title_color": self.title_color.get(), "title_size": self.title_size.get(),
            "title_shadow": self.title_shadow.get(), "title_italic": self.title_italic.get(),
            "title_shadow_color": self.title_shadow_color.get(), "title_shadow_size": self.title_shadow_size.get(),
            "title_shadow_angle": self.title_shadow_angle.get(), "title_shadow_opacity": self.title_shadow_opacity.get(),
            "title_gradient": self.title_gradient.get(), "title_font": self.title_font.get(),
            "title_gradient_a": self.title_gradient_a.get(), "title_gradient_b": self.title_gradient_b.get(),
            "title_gradient_mode": self.title_gradient_mode.get(), "title_gradient_angle": self.title_gradient_angle.get(),
            "title_stroke_enabled": self.title_stroke_enabled.get(), "title_stroke_color": self.title_stroke_color.get(),
            "title_stroke_width": self.title_stroke_width.get(),
            "body_color": self.body_color.get(), "body_size": self.body_size.get(),
            "body_shadow": self.body_shadow.get(), "body_italic": self.body_italic.get(),
            "body_shadow_color": self.body_shadow_color.get(), "body_shadow_size": self.body_shadow_size.get(),
            "body_shadow_angle": self.body_shadow_angle.get(), "body_shadow_opacity": self.body_shadow_opacity.get(),
            "body_gradient": self.body_gradient.get(), "body_line_spacing": self.body_line_spacing.get(),
            "body_gradient_a": self.body_gradient_a.get(), "body_gradient_b": self.body_gradient_b.get(),
            "body_gradient_mode": self.body_gradient_mode.get(), "body_gradient_angle": self.body_gradient_angle.get(),
            "body_stroke_enabled": self.body_stroke_enabled.get(), "body_stroke_color": self.body_stroke_color.get(),
            "body_stroke_width": self.body_stroke_width.get(),
            "body_font": self.body_font.get(), "card_enabled": self.card_enabled.get(),
            "card_color": self.card_color.get(), "card_opacity": self.card_opacity.get(),
            "third_enabled": self.third_enabled.get(), "third_color": self.third_color.get(),
            "third_size": self.third_size.get(), "third_font": self.third_font.get(),
            "third_gradient": self.third_gradient.get(), "third_gradient_a": self.third_gradient_a.get(),
            "third_gradient_b": self.third_gradient_b.get(), "third_gradient_mode": self.third_gradient_mode.get(),
            "third_gradient_angle": self.third_gradient_angle.get(),
            "third_stroke_enabled": self.third_stroke_enabled.get(), "third_stroke_color": self.third_stroke_color.get(),
            "third_stroke_width": self.third_stroke_width.get(),
            "third_shadow": self.third_shadow.get(), "third_shadow_color": self.third_shadow_color.get(),
            "third_shadow_size": self.third_shadow_size.get(), "third_shadow_angle": self.third_shadow_angle.get(),
            "third_shadow_opacity": self.third_shadow_opacity.get(),
        }

    def _apply_style_snapshot(self, data):
        mapping = {
            "title_color": self.title_color, "title_size": self.title_size,
            "title_shadow": self.title_shadow, "title_italic": self.title_italic,
            "title_shadow_color": self.title_shadow_color, "title_shadow_size": self.title_shadow_size,
            "title_shadow_angle": self.title_shadow_angle, "title_shadow_opacity": self.title_shadow_opacity,
            "title_gradient": self.title_gradient, "title_font": self.title_font,
            "title_gradient_a": self.title_gradient_a, "title_gradient_b": self.title_gradient_b,
            "title_gradient_mode": self.title_gradient_mode, "title_gradient_angle": self.title_gradient_angle,
            "title_stroke_enabled": self.title_stroke_enabled, "title_stroke_color": self.title_stroke_color,
            "title_stroke_width": self.title_stroke_width,
            "body_color": self.body_color, "body_size": self.body_size,
            "body_shadow": self.body_shadow, "body_italic": self.body_italic,
            "body_shadow_color": self.body_shadow_color, "body_shadow_size": self.body_shadow_size,
            "body_shadow_angle": self.body_shadow_angle, "body_shadow_opacity": self.body_shadow_opacity,
            "body_gradient": self.body_gradient, "body_line_spacing": self.body_line_spacing,
            "body_gradient_a": self.body_gradient_a, "body_gradient_b": self.body_gradient_b,
            "body_gradient_mode": self.body_gradient_mode, "body_gradient_angle": self.body_gradient_angle,
            "body_stroke_enabled": self.body_stroke_enabled, "body_stroke_color": self.body_stroke_color,
            "body_stroke_width": self.body_stroke_width,
            "body_font": self.body_font, "card_enabled": self.card_enabled,
            "card_color": self.card_color, "card_opacity": self.card_opacity,
            "third_enabled": self.third_enabled, "third_color": self.third_color,
            "third_size": self.third_size, "third_font": self.third_font,
            "third_gradient": self.third_gradient, "third_gradient_a": self.third_gradient_a,
            "third_gradient_b": self.third_gradient_b, "third_gradient_mode": self.third_gradient_mode,
            "third_gradient_angle": self.third_gradient_angle,
            "third_stroke_enabled": self.third_stroke_enabled, "third_stroke_color": self.third_stroke_color,
            "third_stroke_width": self.third_stroke_width,
            "third_shadow": self.third_shadow, "third_shadow_color": self.third_shadow_color,
            "third_shadow_size": self.third_shadow_size, "third_shadow_angle": self.third_shadow_angle,
            "third_shadow_opacity": self.third_shadow_opacity,
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

    # ?? color picker with recent colors ??????????????????????????????????????
    _PALETTE = [
        "#FFFFFF","#000000","#1E293B","#144C8A","#F59E0B","#DC2626",
        "#16A34A","#7C3AED","#DB2777","#0891B2","#D97706","#6B7280",
        "#DBEAFE","#FEF3C7","#DCFCE7","#FCE7F3","#F3E8FF","#FFE4E6",
    ]

    def _add_recent_color(self, hex_c: str):
        if not hasattr(self, "_recent_colors"):
            self._recent_colors = []
        hex_c = hex_c.lower()
        if hex_c in self._recent_colors:
            self._recent_colors.remove(hex_c)
        self._recent_colors.insert(0, hex_c)
        self._recent_colors = self._recent_colors[:18]
        self._save_settings()

    def _ask_color(self, initial="#FFFFFF", title="בחר צבע") -> "str | None":
        """Color picker dialog with recent-color swatches and a palette."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=BRAND["panel"])
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)
        result = [None]

        def _pick(hex_c):
            result[0] = hex_c
            self._add_recent_color(hex_c)
            win.destroy()

        def _open_system():
            win.withdraw()
            c = colorchooser.askcolor(initialcolor=initial, title=title)
            if c and c[1]:
                _pick(c[1])
            else:
                win.deiconify()

        def _swatch_row(parent, colors, label):
            if not colors:
                return
            tk.Label(parent, text=label, bg=BRAND["panel"], fg=BRAND["muted"],
                     font=("Segoe UI", 8)).pack(anchor="e", padx=12, pady=(8, 2))
            row = tk.Frame(parent, bg=BRAND["panel"])
            row.pack(padx=12, pady=(0, 4))
            for i, hc in enumerate(colors):
                relief = "sunken" if hc.lower() == initial.lower() else "solid"
                btn = tk.Button(row, bg=hc, width=2, height=1, bd=1,
                                relief=relief, cursor="hand2",
                                highlightbackground="#F59E0B" if relief=="sunken" else hc,
                                command=lambda h=hc: _pick(h))
                btn.grid(row=i//9, column=i%9, padx=1, pady=1)

        tk.Label(win, text=title, bg=BRAND["panel"], fg=BRAND["gold"],
                 font=("Segoe UI Semibold", 13)).pack(anchor="e", padx=14, pady=(12, 4))

        recent = getattr(self, "_recent_colors", [])
        _swatch_row(win, recent[:18], "צבעים אחרונים")
        _swatch_row(win, self._PALETTE, "פלטה")

        btns = tk.Frame(win, bg=BRAND["panel"])
        btns.pack(fill="x", padx=12, pady=(6, 12))
        tk.Button(btns, text="צבע נוסף...", command=_open_system,
                  bg=BRAND["surface"], fg=BRAND["text"], bd=0, padx=10, pady=5,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")
        tk.Button(btns, text="ביטול", command=win.destroy,
                  bg=BRAND["surface"], fg=BRAND["muted"], bd=0, padx=10, pady=5,
                  font=("Segoe UI", 9), cursor="hand2").pack(side="right", padx=4)

        self.root.wait_window(win)
        return result[0]

    # ?? eyedropper: pick color from canvas ???????????????????????????????????
    def toggle_eyedropper(self):
        self._eyedropper_active = not getattr(self, "_eyedropper_active", False)
        cursor = "crosshair" if self._eyedropper_active else ""
        self.preview_label.configure(cursor=cursor)
        if hasattr(self, "_tb_eyedrop_btn"):
            self._tb_eyedrop_btn.configure(
                bg=BRAND["gold"] if self._eyedropper_active else BRAND["surface"],
                fg=BRAND["bg"]  if self._eyedropper_active else BRAND["text"])
        if self._eyedropper_active:
            self.notify("לחץ על הקנבס לבחירת צבע")

    def _pick_color_from_preview(self, event):
        img = getattr(self, "last_image", None)
        if img is None:
            return
        size = getattr(self, "_preview_size", None)
        if not size:
            return
        lw = max(1, self.preview_label.winfo_width())
        lh = max(1, self.preview_label.winfo_height())
        iw, ih = size
        off_x = max(0, (lw - iw) // 2)
        off_y = max(0, (lh - ih) // 2)
        scale_x = img.width  / max(1, iw)
        scale_y = img.height / max(1, ih)
        px = int((event.x - off_x) * scale_x)
        py = int((event.y - off_y) * scale_y)
        px = max(0, min(px, img.width  - 1))
        py = max(0, min(py, img.height - 1))
        r, g, b = img.convert("RGB").getpixel((px, py))
        hex_c = f"#{r:02x}{g:02x}{b:02x}"
        t = getattr(self, "_active_text_target", "body")
        getattr(self, f"{t}_color").set(hex_c)
        self._add_recent_color(hex_c)
        if hasattr(self, "_tb_color_btn"):
            luma = 0.299*r + 0.587*g + 0.114*b
            self._tb_color_btn.configure(
                bg=hex_c, fg="white" if luma < 128 else "#111827",
                text=f"  ■ {hex_c}  ")
        self.schedule_render_preview()
        self.notify(f"צבע נבחר: {hex_c}")
        self._eyedropper_active = False
        self.preview_label.configure(cursor="")
        if hasattr(self, "_tb_eyedrop_btn"):
            self._tb_eyedrop_btn.configure(bg=BRAND["surface"], fg=BRAND["text"])

    def pick_card_color(self):
        c = self._ask_color(self.card_color.get(), "צבע תיבת טקסט")
        if c: self.card_color.set(c); self.render_preview()

    def pick_title_color(self):
        c = self._ask_color(self.title_color.get(), "צבע כותרת")
        if c: self.title_color.set(c); self.render_preview()

    def pick_body_color(self):
        c = self._ask_color(self.body_color.get(), "צבע גוף טקסט")
        if c: self.body_color.set(c); self.render_preview()

    # ?? canvas size ???????????????????????????????????????????????????????????
    def pick_var_color(self, var, title="בחר צבע"):
        c = self._ask_color(var.get(), title)
        if c:
            var.set(c)
            self.render_preview()

    def open_gradient_popup(self, target):
        enabled = getattr(self, f"{target}_gradient")
        color_a = getattr(self, f"{target}_gradient_a")
        color_b = getattr(self, f"{target}_gradient_b")
        mode = getattr(self, f"{target}_gradient_mode")
        angle = getattr(self, f"{target}_gradient_angle")
        enabled.set(True)
        win = tk.Toplevel(self.root)
        win.title("Gradient")
        win.configure(bg=BRAND["panel"])
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="Gradient", bg=BRAND["panel"], fg=BRAND["gold"],
                 font=("Segoe UI Semibold", 14)).pack(anchor="e", padx=16, pady=(12,6))
        row = tk.Frame(win, bg=BRAND["panel"])
        row.pack(fill="x", padx=16, pady=6)
        self._inline_btn(row, "צבע ראשון", lambda: self.pick_var_color(color_a, "צבע ראשון"))
        self._inline_btn(row, "צבע שני", lambda: self.pick_var_color(color_b, "צבע שני"))
        tk.Label(row, textvariable=color_a, bg=BRAND["panel"], fg=BRAND["text"]).pack(side="right", padx=8)
        tk.Label(row, textvariable=color_b, bg=BRAND["panel"], fg=BRAND["text"]).pack(side="right", padx=8)
        self._combo2("שיטת שילוב", mode, ["linear", "radial", "mirror"], self.render_preview, win)
        tk.Label(win, text="זווית", bg=BRAND["panel"], fg=BRAND["muted"],
                 font=("Segoe UI",9)).pack(anchor="e", padx=16)
        tk.Scale(win, from_=0, to=360, orient="horizontal", variable=angle,
                 command=lambda _: self.render_preview(), bg=BRAND["panel"],
                 fg="white", highlightthickness=0, troughcolor=BRAND["surface"]).pack(fill="x", padx=16)
        preview = tk.Canvas(win, width=260, height=54, bg=BRAND["surface"], highlightthickness=0)
        preview.pack(padx=16, pady=10)
        def paint_preview():
            if not win.winfo_exists():
                return
            img = make_gradient((260, 54), color_a.get(), color_b.get(), mode.get(), angle.get())
            tk_img = ImageTk.PhotoImage(img)
            preview._img = tk_img
            preview.delete("all")
            preview.create_image(0, 0, anchor="nw", image=tk_img)
            win.after(160, paint_preview)
        paint_preview()
        tk.Button(win, text="סגור", command=lambda: [self.render_preview(), win.destroy()],
                  bg=BRAND["accent"], fg="white", bd=0, padx=16, pady=7,
                  font=("Segoe UI",10,"bold"), cursor="hand2").pack(pady=(0,14))

    def get_canvas_size(self, dpi=300):
        w, h = float(self.width_cm.get()), float(self.height_cm.get())
        ori = self.orientation.get()
        if ori == "Landscape" and h > w: w, h = h, w
        elif ori == "Portrait"  and w > h: w, h = h, w
        elif ori == "Auto" and len(self._text_cache) > 260 and h > w: w, h = h, w
        return cm_to_px(w, dpi=dpi), cm_to_px(h, dpi=dpi)

    def _cached_resized_image(self, path, size, mode):
        key = (str(path), size, mode)
        cached = self._image_cache.get(key)
        if cached is not None:
            return cached.copy()
        p = Path(path)
        if p.suffix.lower() == ".svg":
            img = _load_svg_as_pil(p, size=size).convert(mode)
        else:
            img = Image.open(path).convert(mode)
        img = img.resize(size, Image.Resampling.LANCZOS)
        if len(self._image_cache) > 24:
            self._image_cache.clear()
        self._image_cache[key] = img.copy()
        return img

    def _shadow_args(self, target):
        enabled = getattr(self, f"{target}_shadow").get()
        if not enabled:
            return None
        size = int(getattr(self, f"{target}_shadow_size").get())
        angle = math.radians(float(getattr(self, f"{target}_shadow_angle").get()))
        opacity = max(0, min(100, int(getattr(self, f"{target}_shadow_opacity").get())))
        color = hex_to_rgb(getattr(self, f"{target}_shadow_color").get()) + (int(255 * opacity / 100),)
        return int(round(math.cos(angle) * size)), int(round(math.sin(angle) * size)), color

    def _draw_shadow(self, draw, target, pos, text, font):
        shadow = self._shadow_args(target)
        if not shadow:
            return
        dx, dy, fill = shadow
        draw.text((pos[0] + dx, pos[1] + dy), text, font=font, fill=fill)

    def _text_width_with_spacing(self, draw, text, font, spacing):
        if not spacing:
            bb = draw.textbbox((0, 0), text, font=font)
            return bb[2] - bb[0]
        return sum(draw.textbbox((0, 0), ch, font=font)[2] for ch in text) + max(0, len(text) - 1) * spacing

    def _bold_offsets(self, font, enabled):
        if not enabled:
            return [(0, 0)]
        size = int(getattr(font, "size", 48) or 48)
        radius = 1 if size < 90 else 2 if size < 170 else 3
        offsets = [(0, 0)]
        for r in range(1, radius + 1):
            offsets.extend([(r, 0), (-r, 0), (0, r), (0, -r)])
        return offsets

    def _draw_text_effect(self, img, draw, pos, text, font, fill, stroke_width=0,
                          stroke_fill=None, bold=False):
        stroke_width = int(stroke_width or 0)
        fill_alpha = int(fill[3]) if len(fill) > 3 else 255
        offsets = self._bold_offsets(font, bold)

        if fill_alpha <= 0 and stroke_width > 0 and stroke_fill:
            probe = ImageDraw.Draw(Image.new("L", (1, 1)))
            bbs = [
                probe.textbbox((dx, dy), text, font=font, stroke_width=stroke_width)
                for dx, dy in offsets
            ]
            left = min(bb[0] for bb in bbs)
            top = min(bb[1] for bb in bbs)
            right = max(bb[2] for bb in bbs)
            bottom = max(bb[3] for bb in bbs)
            width = max(1, right - left)
            height = max(1, bottom - top)
            stroke_mask = Image.new("L", (width, height), 0)
            fill_mask = Image.new("L", (width, height), 0)
            sd = ImageDraw.Draw(stroke_mask)
            fd = ImageDraw.Draw(fill_mask)
            for dx, dy in offsets:
                sd.text((dx - left, dy - top), text, font=font, fill=255,
                        stroke_width=stroke_width, stroke_fill=255)
                fd.text((dx - left, dy - top), text, font=font, fill=255)
            outline_mask = ImageChops.subtract(stroke_mask, fill_mask)
            layer = Image.new("RGBA", (width, height), stroke_fill)
            layer.putalpha(outline_mask)
            img.alpha_composite(layer, (int(pos[0] + left), int(pos[1] + top)))
            return

        if fill_alpha <= 0:
            return

        for dx, dy in offsets:
            draw.text((pos[0] + dx, pos[1] + dy), text, font=font, fill=fill,
                      stroke_width=stroke_width, stroke_fill=stroke_fill)

    def _draw_text_with_spacing(self, draw, pos, text, font, fill, spacing=0,
                                stroke_width=0, stroke_fill=None, bold=False):
        offsets = self._bold_offsets(font, bold)
        fill_alpha = int(fill[3]) if len(fill) > 3 else 255
        if fill_alpha <= 0 and not stroke_width:
            return
        if not spacing:
            for dx, dy in offsets:
                draw.text((pos[0] + dx, pos[1] + dy), text, font=font, fill=fill,
                          stroke_width=int(stroke_width or 0), stroke_fill=stroke_fill)
            return
        x, y = pos
        for ch in text:
            for dx, dy in offsets:
                draw.text((x + dx, y + dy), ch, font=font, fill=fill,
                          stroke_width=int(stroke_width or 0), stroke_fill=stroke_fill)
            bb = draw.textbbox((0, 0), ch, font=font, stroke_width=int(stroke_width or 0))
            x += (bb[2] - bb[0]) + spacing

    # ?? render ????????????????????????????????????????????????????????????????
    def render_image(self, dpi=300):
        self._render_overflow_messages = []
        Wpx, Hpx = self.get_canvas_size(dpi=dpi)
        bp = BG_DIR / self.bg.get()
        if bp.exists():
            raw_bg = self._cached_resized_image(bp, (Wpx,Hpx), "RGBA")
            white  = Image.new("RGBA", (Wpx, Hpx), (255, 255, 255, 255))
            img    = Image.alpha_composite(white, raw_bg)
        else:
            img = Image.new("RGBA", (Wpx, Hpx), (255, 255, 255, 255))
        safe = int(min(Wpx,Hpx) * 0.075)

        title     = self.title_text.get().strip()
        has_title = bool(title)
        tx_off    = int(self.title_x_off.get() * Wpx / 100)
        ty_off    = int(self.title_y_off.get() * Hpx / 100)
        bx_off    = int(self.body_x_off.get()  * Wpx / 100)
        by_off    = int(self.body_y_off.get()  * Hpx / 100)
        thx_off   = int(self.third_x_off.get() * Wpx / 100)
        thy_off   = int(self.third_y_off.get() * Hpx / 100)

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
                fr = self._cached_resized_image(fp, (Wpx,Hpx), "RGBA")
                img.alpha_composite(fr)

        d = ImageDraw.Draw(img, "RGBA")

        # resolve fonts
        t_bold   = getattr(self, "title_bold", tk.BooleanVar(value=True)).get()
        t_italic = self.title_italic.get()
        b_italic = self.body_italic.get()
        b_bold   = getattr(self, "body_bold", tk.BooleanVar(value=False)).get()
        t_fp = resolve_font(self.title_font.get(), bold=t_bold, italic=t_italic)
        b_fp = resolve_font(self.body_font.get(),  bold=b_bold,  italic=b_italic)
        if not t_fp: t_fp = (FONT_BOLD_ITALIC if t_bold and t_italic else FONT_BOLD if t_bold else FONT_ITALIC if t_italic else FONT_REG)
        if not b_fp: b_fp = (FONT_BOLD_ITALIC if b_bold and b_italic else FONT_BOLD if b_bold else FONT_ITALIC if b_italic else FONT_REG)

        # title
        if has_title:
            sz = int(self.title_size.get() * (min(Wpx,Hpx)/1748))
            sz = max(28, min(sz, 180))
            try:    tfont = ImageFont.truetype(t_fp, sz) if t_fp else ImageFont.load_default()
            except: tfont = ImageFont.load_default()
            vis   = bidi_text(title)
            bb    = d.textbbox((0,0), vis, font=tfont)
            title_w = bb[2] - bb[0]
            t_align = getattr(self, "title_align", tk.StringVar(value="center")).get()
            if t_align == "right":
                tx = Wpx - safe * 2 - title_w + tx_off
            elif t_align == "left":
                tx = safe * 2 + tx_off
            else:
                tx = (Wpx - title_w) / 2 + tx_off
            t_stroke = self.title_stroke_width.get() if self.title_stroke_enabled.get() else 0
            if bb[2] - bb[0] > Wpx - safe * 2:
                self._render_overflow_messages.append("הכותרת גדולה מדי לשטח הברכה")
            self._draw_shadow(d, "title", (tx, title_y), vis, tfont)
            title_alpha = int(255 * max(0, min(100, self.title_opacity.get())) / 100)
            if self.title_gradient.get() and title_alpha > 0:
                draw_gradient_text(
                    img, (tx, title_y), vis, tfont,
                    self.title_gradient_a.get(), self.title_gradient_b.get(),
                    self.title_gradient_mode.get(), self.title_gradient_angle.get(),
                    t_stroke, self.title_stroke_color.get())
            else:
                self._draw_text_effect(
                    img, d, (tx, title_y), vis, tfont,
                    hex_to_rgb(self.title_color.get()) + (title_alpha,),
                    t_stroke, hex_to_rgb(self.title_stroke_color.get()) + (255,),
                    bold=t_bold)

        # body
        body_text = self._text_cache.strip() or "הקלד/י כאן את הברכה..."
        max_sz    = int(self.body_size.get() * (min(Wpx,Hpx)/1748))
        max_sz    = max(20, min(max_sz, 260))
        try:
            font, lines, line_h = fit_text(
                d, body_text, body_box, b_fp, max_size=max_sz,
                line_spacing=max(0.8, self.body_line_spacing.get() / 100),
            )
            if getattr(font, "size", max_sz) < max_sz - 1:
                self._render_overflow_messages.append("גודל הטקסט חורג מהשטח ולכן הוקטן אוטומטית")
        except Exception:
            try:    font = ImageFont.truetype(b_fp, 28) if b_fp else ImageFont.load_default()
            except: font = ImageFont.load_default()
            lines = [body_text]; line_h = 34
        total_h = line_h * len(lines)
        y = body_box[1] + max(0, (body_box[3]-body_box[1]-total_h)//2)
        body_alpha = int(255 * max(0, min(100, self.body_opacity.get())) / 100)
        body_rgb = hex_to_rgb(self.body_color.get())
        b_stroke = self.body_stroke_width.get() if self.body_stroke_enabled.get() else 0
        letter_spacing = int(getattr(self, "body_letter_spacing", tk.IntVar(value=0)).get() * (min(Wpx,Hpx)/1748))
        for line in lines:
            vis = bidi_text(line)
            line_w = self._text_width_with_spacing(d, vis, font, letter_spacing)
            align = getattr(self, "body_align", tk.StringVar(value="center")).get()
            if align == "right":
                x = body_box[2] - line_w
            elif align == "left":
                x = body_box[0]
            else:
                x = body_box[0] + ((body_box[2] - body_box[0]) - line_w) / 2
            if letter_spacing:
                shadow = self._shadow_args("body")
                if shadow:
                    dx, dy, fill = shadow
                    self._draw_text_with_spacing(d, (x + dx, y + dy), vis, font, fill, letter_spacing, bold=b_bold)
                self._draw_text_with_spacing(
                    d, (x, y), vis, font, body_rgb+(body_alpha,), letter_spacing,
                    b_stroke, hex_to_rgb(self.body_stroke_color.get())+(255,), bold=b_bold)
            elif self.body_gradient.get() and body_alpha > 0:
                self._draw_shadow(d, "body", (x, y), vis, font)
                draw_gradient_text(
                    img, (x, y), vis, font,
                    self.body_gradient_a.get(), self.body_gradient_b.get(),
                    self.body_gradient_mode.get(), self.body_gradient_angle.get(),
                    b_stroke, self.body_stroke_color.get())
            else:
                self._draw_shadow(d, "body", (x, y), vis, font)
                self._draw_text_effect(
                    img, d, (x, y), vis, font, body_rgb + (body_alpha,),
                    b_stroke, hex_to_rgb(self.body_stroke_color.get()) + (255,),
                    bold=b_bold)
            y += line_h

        if self.third_enabled.get() and self.third_text.get().strip():
            third = bidi_text(self.third_text.get().strip())
            th_fp = resolve_font(
                self.third_font.get(),
                bold=getattr(self, "third_bold", tk.BooleanVar(value=False)).get(),
                italic=getattr(self, "third_italic", tk.BooleanVar(value=False)).get())
            th_sz = int(self.third_size.get() * (min(Wpx,Hpx)/1748))
            th_sz = max(14, min(th_sz, 180))
            try:    th_font = ImageFont.truetype(th_fp, th_sz) if th_fp else ImageFont.load_default()
            except: th_font = ImageFont.load_default()
            th_bb = d.textbbox((0,0), third, font=th_font)
            th_w = th_bb[2] - th_bb[0]
            th_align = getattr(self, "third_align", tk.StringVar(value="center")).get()
            if th_align == "right":
                th_x = Wpx - safe * 2 - th_w + thx_off
            elif th_align == "left":
                th_x = safe * 2 + thx_off
            else:
                th_x = (Wpx - th_w) / 2 + thx_off
            th_y = int(Hpx * 0.80) + thy_off
            if th_bb[2] - th_bb[0] > Wpx - safe * 2 or th_y + (th_bb[3] - th_bb[1]) > Hpx - safe:
                self._render_overflow_messages.append("תיבת הטקסט התחתונה חורגת מהברכה")
            th_stroke = self.third_stroke_width.get() if self.third_stroke_enabled.get() else 0
            third_alpha = int(255 * max(0, min(100, self.third_opacity.get())) / 100)
            if self.third_gradient.get() and third_alpha > 0:
                self._draw_shadow(d, "third", (th_x, th_y), third, th_font)
                draw_gradient_text(
                    img, (th_x, th_y), third, th_font,
                    self.third_gradient_a.get(), self.third_gradient_b.get(),
                    self.third_gradient_mode.get(), self.third_gradient_angle.get(),
                    th_stroke, self.third_stroke_color.get())
            else:
                self._draw_shadow(d, "third", (th_x, th_y), third, th_font)
                self._draw_text_effect(
                    img, d, (th_x, th_y), third, th_font,
                    hex_to_rgb(self.third_color.get()) + (third_alpha,),
                    th_stroke, hex_to_rgb(self.third_stroke_color.get()) + (255,),
                    bold=getattr(self, "third_bold", tk.BooleanVar(value=False)).get())

        return img.convert("RGB")

    def render_preview(self):
        try:
            if hasattr(self,"text_box") and self.text_box.winfo_exists():
                if isinstance(self.text_box, tk.Text):
                    val = self.text_box.get("1.0", "end-1c")
                else:
                    val = self.text_box.get("1.0", "end")
                self._set_target_text(getattr(self, "_editor_text_target", "body"), val)
            self.last_image = self.render_image(dpi=110)
            prev = self.last_image.copy()
            area_w = max(380, self.right.winfo_width()-40)
            area_h = max(380, self.right.winfo_height()-80)
            prev.thumbnail((area_w, area_h), Image.Resampling.LANCZOS)
            self._preview_size = prev.size
            self.tk_preview = ImageTk.PhotoImage(prev)
            self.preview_label.configure(image=self.tk_preview, text="")
            messages = getattr(self, "_render_overflow_messages", [])
            if messages and not self._overflow_notice_after:
                self.notify(messages[0])
                self._overflow_notice_after = self.root.after(3500, self._clear_overflow_notice_lock)
        except Exception as e:
            self.preview_label.configure(text=f"שגיאה בתצוגה:\n{e}", image="")

    # ?? export ????????????????????????????????????????????????????????????????
    def _clear_overflow_notice_lock(self):
        self._overflow_notice_after = None

    def _preview_drag_start(self, event):
        if getattr(self, "_eyedropper_active", False):
            self._pick_color_from_preview(event)
            return
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
        if self.third_enabled.get() and self.third_text.get().strip() and rel_y > 0.70:
            target = "third"
        else:
            target = "title" if self.title_text.get().strip() and rel_y < 0.34 else "body"
        if self.current_step == "text":
            self._load_target_into_editor(target)
        self._drag_preview = {
            "target": target, "x": event.x, "y": event.y,
            "title_x": self.title_x_off.get(), "title_y": self.title_y_off.get(),
            "body_x": self.body_x_off.get(), "body_y": self.body_y_off.get(),
            "third_x": self.third_x_off.get(), "third_y": self.third_y_off.get(),
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
        elif drag["target"] == "body":
            self.body_x_off.set(max(-50, min(50, drag["body_x"] + dx)))
            self.body_y_off.set(max(-50, min(50, drag["body_y"] + dy)))
        else:
            self.third_x_off.set(max(-50, min(50, drag["third_x"] + dx)))
            self.third_y_off.set(max(-50, min(50, drag["third_y"] + dy)))
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
