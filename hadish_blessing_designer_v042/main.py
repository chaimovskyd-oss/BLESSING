
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from pathlib import Path
import json, random, os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageTk

try:
    from bidi.algorithm import get_display
except Exception:
    get_display = None

APP_DIR = Path(__file__).resolve().parent
BG_DIR = APP_DIR / "assets" / "backgrounds"
FRAME_DIR = APP_DIR / "assets" / "frames"
BLESSINGS_PATH = APP_DIR / "templates" / "blessings.json"
EXPORT_DIR = APP_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

PRODUCT_PRESETS_CM = {
    "A5": {
        "size": (14.8, 21.0),
        "title": "A5",
        "desc": "ברכה קלאסית למתנה, יפה למסגרת קטנה או צירוף למארז."
    },
    "A4": {
        "size": (21.0, 29.7),
        "title": "A4",
        "desc": "מתאים לפוסטר קטן, ברכה גדולה, תלייה או הצגה על שולחן."
    },
    "10x15": {
        "size": (10.0, 15.0),
        "title": "10x15",
        "desc": "גודל קטן ומהיר, מתאים לצירוף למתנה או הדפסה פוטו."
    },
    "20x20": {
        "size": (20.0, 20.0),
        "title": "20x20",
        "desc": "ריבוע מעוצב, מתאים למראה מודרני או מתנה מיוחדת."
    },
    "מותאם אישית": {
        "size": (14.8, 21.0),
        "title": "מותאם אישית",
        "desc": "הזנת מידה ידנית בס״מ לכל מוצר מיוחד."
    },
}

CATEGORY_TO_BG = {
    "יום הולדת": "birthday_fun.png",
    "מורה/גננת": "teacher_calm.png",
    "גיוס": "army_clean.png",
    "תודה": "hadish_soft.png",
    "חתונה": "cream_elegant.png",
    "בר/בת מצווה": "bar_mitzvah_blue.png",
    "אהבה": "pink_love_light.png",
}

STYLE_TO_FRAME = {
    "מרגש": "gold_double.png",
    "מצחיק": "red_corner.png",
    "רשמי": "blue_rounded.png",
}

def cm_to_px(cm, dpi=300):
    return int(round(cm / 2.54 * dpi))

def hex_to_rgb(hex_color):
    hex_color = str(hex_color).strip().lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c*2 for c in hex_color)
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0,2,4))
    except Exception:
        return (255,255,255)

def find_font(bold=False):
    candidates = [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    bold_candidates = [
        r"C:\Windows\Fonts\seguisb.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for f in (bold_candidates if bold else candidates):
        if Path(f).exists():
            return f
    return None

FONT_REG = find_font(False)
FONT_BOLD = find_font(True) or FONT_REG

def bidi_text(text):
    if get_display:
        try:
            return get_display(text)
        except Exception:
            return text
    hebrew = any("\u0590" <= c <= "\u05ff" for c in text)
    return text[::-1] if hebrew else text

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0,0), bidi_text(test), font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def fit_text(draw, text, box, font_path, max_size, min_size=24, line_spacing=1.22):
    x1,y1,x2,y2 = box
    max_w, max_h = x2-x1, y2-y1
    for size in range(max_size, min_size-1, -2):
        font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        all_lines = []
        for para in text.split("\n"):
            if para.strip():
                all_lines.extend(wrap_text(draw, para.strip(), font, max_w))
            else:
                all_lines.append("")
        line_h = int(size * line_spacing)
        total_h = line_h * len(all_lines)
        widest = 0
        for line in all_lines:
            bbox = draw.textbbox((0,0), bidi_text(line), font=font)
            widest = max(widest, bbox[2]-bbox[0])
        if total_h <= max_h and widest <= max_w:
            return font, all_lines, line_h
    font = ImageFont.truetype(font_path, min_size) if font_path else ImageFont.load_default()
    lines = []
    for para in text.split("\n"):
        lines.extend(wrap_text(draw, para.strip(), font, max_w))
    return font, lines, int(min_size*line_spacing)

class Collapsible:
    def __init__(self, parent, title, start_open=True):
        self.frame = ttk.Frame(parent, style="Panel.TFrame")
        self.frame.pack(fill="x", padx=18, pady=6)
        self.open = tk.BooleanVar(value=start_open)
        self.btn = ttk.Button(self.frame, text=("▼ " if start_open else "▶ ") + title, command=self.toggle)
        self.btn.pack(fill="x")
        self.body = ttk.Frame(self.frame, style="Panel.TFrame")
        if start_open:
            self.body.pack(fill="x", pady=(6,0))
        self.title = title

    def toggle(self):
        if self.open.get():
            self.body.forget()
            self.open.set(False)
            self.btn.configure(text="▶ " + self.title)
        else:
            self.body.pack(fill="x", pady=(6,0))
            self.open.set(True)
            self.btn.configure(text="▼ " + self.title)

class BlessingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hadish Blessing Designer v0.4")
        self.root.geometry("1260x760")
        self.root.minsize(980, 620)
        self.root.configure(bg="#0f172a")
        self.blessings = json.loads(BLESSINGS_PATH.read_text(encoding="utf-8"))
        self.last_image = None
        self.tk_preview = None
        self.asset_thumbs = []
        self.init_state()
        self.build_menu()
        self.build_ui()
        self.show_step("size")

    def init_state(self):
        self.step_order = ["size", "background", "frame", "blessings", "text"]
        self.step_titles = {
            "size": "בחירת מידה",
            "background": "בחירת רקע",
            "frame": "בחירת מסגרת",
            "blessings": "מחולל ברכות",
            "text": "עיצוב טקסט ויצוא",
        }
        self.product = tk.StringVar(value="A5")
        self.orientation = tk.StringVar(value="Portrait")
        self.category = tk.StringVar(value="יום הולדת")
        self.style_var = tk.StringVar(value="מרגש")
        self.name = tk.StringVar(value="שם")
        self.title_text = tk.StringVar(value="")
        self.bg = tk.StringVar(value="birthday_fun.png")
        self.frame = tk.StringVar(value="gold_double.png")
        self.width_cm = tk.DoubleVar(value=14.8)
        self.height_cm = tk.DoubleVar(value=21.0)
        self.card_enabled = tk.BooleanVar(value=True)
        self.card_color = tk.StringVar(value="#FFFFFF")
        self.card_opacity = tk.IntVar(value=58)
        self.title_color = tk.StringVar(value="#144C8A")
        self.body_color = tk.StringVar(value="#1E293B")
        self.title_size = tk.IntVar(value=72)
        self.body_size = tk.IntVar(value=54)
        self.title_shadow = tk.BooleanVar(value=False)
        self.body_shadow = tk.BooleanVar(value=False)
        self.title_italic = tk.BooleanVar(value=False)
        self.body_italic = tk.BooleanVar(value=False)
        self.title_preset = tk.StringVar(value="נקי כחול")
        self.body_preset = tk.StringVar(value="נקי כהה")
        self._text_cache = ""
        self._free_text_started = False

    def build_menu(self):
        menubar = tk.Menu(self.root)
        steps_menu = tk.Menu(menubar, tearoff=0)
        for key in self.step_order:
            steps_menu.add_command(label=self.step_titles[key], command=lambda k=key: self.show_step(k))
        menubar.add_cascade(label="שלבים", menu=steps_menu)

        design_menu = tk.Menu(menubar, tearoff=0)
        design_menu.add_command(label="צבע תיבת טקסט...", command=self.pick_card_color)
        design_menu.add_command(label="צבע כותרת...", command=self.pick_title_color)
        design_menu.add_command(label="צבע גוף הטקסט...", command=self.pick_body_color)
        menubar.add_cascade(label="עיצוב", menu=design_menu)

        export_menu = tk.Menu(menubar, tearoff=0)
        export_menu.add_command(label="יצוא PNG", command=self.export_png)
        export_menu.add_command(label="יצוא PDF", command=self.export_pdf)
        export_menu.add_command(label="פתח תיקיית יצוא", command=self.open_exports)
        menubar.add_cascade(label="יצוא", menu=export_menu)
        self.root.config(menu=menubar)

    def build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#0f172a")
        style.configure("Panel.TFrame", background="#16213a")
        style.configure("Dark.TFrame", background="#0f172a")
        style.configure("TLabel", background="#16213a", foreground="#F8FAFC", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background="#16213a", foreground="#CBD5E1", font=("Segoe UI", 9))
        style.configure("Title.TLabel", background="#16213a", foreground="#F6B92C", font=("Segoe UI Semibold", 18))
        style.configure("BigTitle.TLabel", background="#16213a", foreground="#F6B92C", font=("Segoe UI Semibold", 22))
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=8)
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 11), padding=10)
        style.configure("TCombobox", padding=5)

        self.main = ttk.Frame(self.root)
        self.main.pack(fill="both", expand=True, padx=14, pady=14)

        self.left = ttk.Frame(self.main, style="Panel.TFrame", width=520)
        self.left.pack(side="left", fill="both", padx=(0,12))
        self.left.pack_propagate(False)

        self.right = ttk.Frame(self.main, style="Panel.TFrame")
        self.right.pack(side="right", fill="both", expand=True)

        self.progress_label = ttk.Label(self.left, text="", style="Muted.TLabel")
        self.progress_label.pack(anchor="e", padx=22, pady=(16,4))
        self.step_title_label = ttk.Label(self.left, text="", style="BigTitle.TLabel")
        self.step_title_label.pack(anchor="e", padx=22, pady=(0,8))

        self.step_area = ttk.Frame(self.left, style="Panel.TFrame")
        self.step_area.pack(fill="both", expand=True, padx=0, pady=0)

        # Navigation moved above preview so it is always visible and never cut by the left panel.
        preview_nav = tk.Frame(self.right, bg="#16213a")
        preview_nav.pack(fill="x", padx=18, pady=(14,4))
        self.back_btn = tk.Button(
            preview_nav, text="⬅ חזור", command=self.prev_step,
            bg="#B91C1C", fg="white", activebackground="#991B1B",
            font=("Segoe UI Semibold", 12), padx=18, pady=8, bd=0
        )
        self.back_btn.pack(side="left")
        self.next_btn = tk.Button(
            preview_nav, text="הבא ➜", command=self.next_step,
            bg="#15803D", fg="white", activebackground="#166534",
            font=("Segoe UI Semibold", 12), padx=18, pady=8, bd=0
        )
        self.next_btn.pack(side="right")

        ttk.Label(self.right, text="תצוגה מקדימה", style="Title.TLabel").pack(anchor="e", padx=18, pady=(6,8))
        self.preview_label = ttk.Label(self.right, text="")
        self.preview_label.pack(fill="both", expand=True, padx=20, pady=16)

    def clear_step(self):
        for w in self.step_area.winfo_children():
            w.destroy()

    def current_index(self):
        return self.step_order.index(self.current_step)

    def show_step(self, step):
        self.current_step = step
        idx = self.step_order.index(step) + 1
        total = len(self.step_order)
        self.progress_label.configure(text=f"שלב {idx} מתוך {total}")
        self.step_title_label.configure(text=self.step_titles[step])
        self.clear_step()

        if step == "size":
            self.build_size_step()
        elif step == "background":
            self.build_background_step()
        elif step == "frame":
            self.build_frame_step()
        elif step == "blessings":
            self.build_blessings_step()
        else:
            self.build_text_step()

        self.back_btn.configure(state=("disabled" if idx == 1 else "normal"))
        self.next_btn.configure(text=("יצוא PNG ➜" if step == "text" else "הבא ➜"))
        self.render_preview()

    def next_step(self):
        if self.current_step == "text":
            self.export_png()
            return
        idx = self.current_index()
        self.show_step(self.step_order[idx+1])

    def prev_step(self):
        idx = self.current_index()
        if idx > 0:
            self.show_step(self.step_order[idx-1])

    def build_size_step(self):
        ttk.Label(self.step_area, text="בחר/י את גודל הברכה. אפשר לשנות גם אחר כך דרך התפריט, אבל כדאי להתחיל נכון.", style="Muted.TLabel", wraplength=460).pack(anchor="e", padx=22, pady=(0,12))

        cards = ttk.Frame(self.step_area, style="Panel.TFrame")
        cards.pack(fill="x", padx=18, pady=4)

        for key, data in PRODUCT_PRESETS_CM.items():
            bg = "#0f172a" if self.product.get() == key else "#1e293b"
            card = tk.Frame(cards, bg=bg, padx=12, pady=10, bd=0)
            card.pack(fill="x", pady=5)
            title = tk.Label(card, text=data["title"], bg=bg, fg="#F6B92C", font=("Segoe UI Semibold", 14), anchor="e")
            title.pack(fill="x")
            desc = tk.Label(card, text=data["desc"], bg=bg, fg="white", font=("Segoe UI", 10), anchor="e", justify="right", wraplength=420)
            desc.pack(fill="x", pady=(2,6))
            btn = ttk.Button(card, text="בחר", command=lambda k=key: self.select_product(k))
            btn.pack(anchor="e")
            card.bind("<Button-1>", lambda e, k=key: self.select_product(k))
            title.bind("<Button-1>", lambda e, k=key: self.select_product(k))
            desc.bind("<Button-1>", lambda e, k=key: self.select_product(k))

        custom = ttk.Frame(self.step_area, style="Panel.TFrame")
        custom.pack(fill="x", padx=22, pady=(10,0))
        ttk.Label(custom, text="מידה ידנית בס״מ").pack(anchor="e")
        row = ttk.Frame(custom, style="Panel.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="רוחב").pack(side="right")
        tk.Entry(row, textvariable=self.width_cm, width=8, justify="center").pack(side="right", padx=6)
        ttk.Label(row, text="גובה").pack(side="right")
        tk.Entry(row, textvariable=self.height_cm, width=8, justify="center").pack(side="right", padx=6)
        ttk.Button(row, text="עדכן והמשך", command=lambda: [self.product.set("מותאם אישית"), self.render_preview(), self.show_step("background")]).pack(side="right", padx=8)

        self.add_combo("אוריינטציה", self.orientation, ["Portrait", "Landscape", "Auto"], self.render_preview, parent=self.step_area)

    def select_product(self, key):
        self.product.set(key)
        w,h = PRODUCT_PRESETS_CM[key]["size"]
        self.width_cm.set(w)
        self.height_cm.set(h)
        self.render_preview()
        self.show_step("background")

    def build_background_step(self):
        ttk.Label(self.step_area, text="בחר/י רקע. התצוגה מצד ימין מתעדכנת מיד.", style="Muted.TLabel", wraplength=460).pack(anchor="e", padx=22, pady=(0,10))
        self.asset_grid(BG_DIR, self.bg, "background", columns=3, height=500)

    def build_frame_step(self):
        ttk.Label(self.step_area, text="בחר/י מסגרת או המשך בלי מסגרת.", style="Muted.TLabel", wraplength=460).pack(anchor="e", padx=22, pady=(0,10))
        none_bg = "#0f172a" if self.frame.get() == "__none__" else "#1e293b"
        none = tk.Frame(self.step_area, bg=none_bg, padx=10, pady=10)
        none.pack(fill="x", padx=22, pady=(0,10))
        tk.Label(none, text="ללא מסגרת", bg=none_bg, fg="#F6B92C", font=("Segoe UI Semibold", 13), anchor="e").pack(fill="x")
        tk.Label(none, text="מתאים לעיצוב נקי כשהרקע מספיק דומיננטי.", bg=none_bg, fg="white", anchor="e", justify="right").pack(fill="x")
        ttk.Button(none, text="בחר ללא מסגרת", command=self.select_frame_none).pack(anchor="e", pady=(6,0))
        self.asset_grid(FRAME_DIR, self.frame, "frame", columns=3, height=410)

    def build_blessings_step(self):
        ttk.Label(self.step_area, text="בחר/י ברכה מוכנה. דאבל־קליק על ברכה מעביר אותה לעיצוב. אפשר גם לדלג ולכתוב חופשי.", style="Muted.TLabel", wraplength=460).pack(anchor="e", padx=22, pady=(0,10))

        controls = ttk.Frame(self.step_area, style="Panel.TFrame")
        controls.pack(fill="x", padx=18, pady=4)
        self.add_combo("סוג ברכה", self.category, list(self.blessings.keys()), self.refresh_blessing_list, parent=controls)
        self.add_combo("סגנון", self.style_var, ["מרגש", "מצחיק", "רשמי"], self.refresh_blessing_list, parent=controls)
        self.add_entry("שם/כינוי לשילוב", self.name, self.refresh_blessing_list, parent=controls)

        row = ttk.Frame(self.step_area, style="Panel.TFrame")
        row.pack(fill="x", padx=18, pady=(2,8))
        ttk.Button(row, text="רענן הצעות", command=self.refresh_blessing_list).pack(side="right", padx=3)
        ttk.Button(row, text="דלג / כתיבה חופשית", command=self.skip_blessing).pack(side="right", padx=3)

        list_frame = ttk.Frame(self.step_area, style="Panel.TFrame")
        list_frame.pack(fill="both", expand=True, padx=18, pady=4)
        self.blessing_list = tk.Listbox(list_frame, height=12, font=("Segoe UI", 11), selectmode="single", activestyle="dotbox")
        self.blessing_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.blessing_list.yview)
        sb.pack(side="right", fill="y")
        self.blessing_list.configure(yscrollcommand=sb.set)
        self.blessing_list.bind("<Double-Button-1>", lambda e: self.use_selected_blessing())

        preview_title = ttk.Label(self.step_area, text="תצוגת ברכה נבחרת:", style="Muted.TLabel")
        preview_title.pack(anchor="e", padx=18, pady=(8,2))
        self.blessing_preview = self.make_text_widget(self.step_area, height=7)
        self.blessing_preview.pack(fill="x", padx=18, pady=(0,8))
        self.blessing_list.bind("<<ListboxSelect>>", lambda e: self.preview_selected_blessing())

        row2 = ttk.Frame(self.step_area, style="Panel.TFrame")
        row2.pack(fill="x", padx=18, pady=4)
        ttk.Button(row2, text="השתמש בברכה שנבחרה", style="Primary.TButton", command=self.use_selected_blessing).pack(side="right", padx=3)
        ttk.Button(row2, text="הדבק ברכה מהלוח", command=self.paste_clipboard_to_blessing).pack(side="right", padx=3)

        self.refresh_blessing_list()

    def build_text_step(self):
        ttk.Label(self.step_area, text="כאן עורכים את הטקסט הסופי. Ctrl+C / Ctrl+V / Ctrl+A עובדים בתיבות הטקסט, ויש גם תפריט קליק ימני.", style="Muted.TLabel", wraplength=460).pack(anchor="e", padx=22, pady=(0,10))

        title_panel = Collapsible(self.step_area, "כותרת", start_open=True)
        ttk.Label(title_panel.body, text="טקסט כותרת").pack(anchor="e")
        title_entry = ttk.Entry(title_panel.body, textvariable=self.title_text, justify="right")
        title_entry.pack(fill="x", pady=4)
        title_entry.bind("<KeyRelease>", lambda e: self.render_preview())
        self.add_copy_paste_bindings(title_entry)

        row = ttk.Frame(title_panel.body, style="Panel.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Button(row, text="צבע כותרת", command=self.pick_title_color).pack(side="right", padx=3)
        tk.Checkbutton(row, text="צל", variable=self.title_shadow, command=self.render_preview, bg="#16213a", fg="white", selectcolor="#0f172a").pack(side="right", padx=8)
        tk.Checkbutton(row, text="נטוי", variable=self.title_italic, command=self.render_preview, bg="#16213a", fg="white", selectcolor="#0f172a").pack(side="right", padx=8)

        ttk.Label(title_panel.body, text="גודל כותרת").pack(anchor="e")
        tk.Scale(title_panel.body, from_=30, to=130, orient="horizontal", variable=self.title_size, command=lambda e: self.render_preview(), bg="#16213a", fg="white", highlightthickness=0).pack(fill="x")

        self.add_combo("סגנון כותרת", self.title_preset, ["נקי כחול", "זהב אלגנטי", "אדום חגיגי", "כהה עם צל"], self.apply_title_preset, parent=title_panel.body)

        body_panel = Collapsible(self.step_area, "ברכה / טקסט ראשי", start_open=True)
        self.text_box = self.make_text_widget(body_panel.body, height=9)
        self.text_box.pack(fill="x", pady=(0,8))
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", self._text_cache)
        self.text_box.bind("<KeyRelease>", lambda e: self.cache_text_and_render())

        rowb = ttk.Frame(body_panel.body, style="Panel.TFrame")
        rowb.pack(fill="x", pady=4)
        ttk.Button(rowb, text="צבע טקסט", command=self.pick_body_color).pack(side="right", padx=3)
        ttk.Button(rowb, text="הדבק מהלוח", command=self.paste_clipboard_to_main_text).pack(side="right", padx=3)
        tk.Checkbutton(rowb, text="צל", variable=self.body_shadow, command=self.render_preview, bg="#16213a", fg="white", selectcolor="#0f172a").pack(side="right", padx=8)
        tk.Checkbutton(rowb, text="נטוי", variable=self.body_italic, command=self.render_preview, bg="#16213a", fg="white", selectcolor="#0f172a").pack(side="right", padx=8)

        ttk.Label(body_panel.body, text="גודל טקסט").pack(anchor="e")
        tk.Scale(body_panel.body, from_=24, to=100, orient="horizontal", variable=self.body_size, command=lambda e: self.render_preview(), bg="#16213a", fg="white", highlightthickness=0).pack(fill="x")
        self.add_combo("סגנון טקסט", self.body_preset, ["נקי כהה", "כחול רך", "רומנטי", "מודרני עם צל"], self.apply_body_preset, parent=body_panel.body)

        card_panel = Collapsible(self.step_area, "רקע מאחורי הטקסט", start_open=False)
        tk.Checkbutton(card_panel.body, text="הצג תיבה מאחורי הטקסט", variable=self.card_enabled, command=self.render_preview, bg="#16213a", fg="white", selectcolor="#0f172a", activebackground="#16213a", anchor="e").pack(fill="x")
        ttk.Label(card_panel.body, text="שקיפות תיבה").pack(anchor="e")
        tk.Scale(card_panel.body, from_=0, to=100, orient="horizontal", variable=self.card_opacity, command=lambda e: self.render_preview(), bg="#16213a", fg="white", highlightthickness=0).pack(fill="x")
        ttk.Button(card_panel.body, text="צבע תיבה", command=self.pick_card_color).pack(anchor="e", pady=4)

        row3 = ttk.Frame(self.step_area, style="Panel.TFrame")
        row3.pack(fill="x", padx=18, pady=(10,8))
        ttk.Button(row3, text="יצוא PNG", command=self.export_png).pack(side="right", padx=3)
        ttk.Button(row3, text="יצוא PDF", command=self.export_pdf).pack(side="right", padx=3)
        ttk.Button(row3, text="תיקיית יצוא", command=self.open_exports).pack(side="right", padx=3)

    def make_text_widget(self, parent, height=6):
        txt = tk.Text(parent, height=height, wrap="word", font=("Segoe UI", 11), undo=True)
        self.add_copy_paste_bindings(txt)
        self.add_context_menu(txt)
        return txt

    def add_copy_paste_bindings(self, widget):
        # Make copy/paste/select-all reliable on Hebrew Windows keyboards too.
        widget.bind("<Control-a>", self.ctrl_a)
        widget.bind("<Control-A>", self.ctrl_a)
        widget.bind("<Control-c>", lambda e: None)
        widget.bind("<Control-v>", lambda e: None)
        widget.bind("<Control-x>", lambda e: None)

    def ctrl_a(self, event):
        w = event.widget
        try:
            if isinstance(w, tk.Text):
                w.tag_add("sel", "1.0", "end-1c")
                w.mark_set("insert", "1.0")
                w.see("insert")
            else:
                w.select_range(0, "end")
                w.icursor("end")
            return "break"
        except Exception:
            return None

    def add_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="גזור", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="העתק", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="הדבק", command=lambda: [widget.event_generate("<<Paste>>"), self.root.after(50, self.cache_text_and_render)])
        menu.add_separator()
        menu.add_command(label="בחר הכל", command=lambda: self.ctrl_a(type("Event", (), {"widget": widget})()))
        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        widget.bind("<Button-3>", show_menu)

    def asset_grid(self, folder, var, kind, columns=3, height=470):
        outer = tk.Canvas(self.step_area, bg="#16213a", highlightthickness=0, height=height)
        sb = ttk.Scrollbar(self.step_area, orient="vertical", command=outer.yview)
        grid = tk.Frame(outer, bg="#16213a")
        grid.bind("<Configure>", lambda e: outer.configure(scrollregion=outer.bbox("all")))
        outer.create_window((0,0), window=grid, anchor="nw")
        outer.configure(yscrollcommand=sb.set)
        outer.pack(side="left", fill="both", expand=True, padx=(18,0), pady=4)
        sb.pack(side="right", fill="y", pady=4)

        self.asset_thumbs = []
        files = sorted(folder.glob("*.png"))
        for idx, path in enumerate(files):
            img = Image.open(path).convert("RGB")
            img.thumbnail((118,118), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
            self.asset_thumbs.append(tk_img)
            selected = path.name == var.get()
            bg = "#0f172a" if selected else "#1e293b"
            cell = tk.Frame(grid, bg=bg, padx=6, pady=6)
            r, c = divmod(idx, columns)
            cell.grid(row=r, column=c, padx=7, pady=7, sticky="n")
            btn = tk.Button(cell, image=tk_img, command=lambda p=path, k=kind: self.select_asset(p.name, k), bg=bg, activebackground="#334155", bd=0)
            btn.pack()
            tk.Label(cell, text=path.stem[:18], bg=bg, fg="white", wraplength=118).pack(pady=(5,0))

    def select_asset(self, name, kind):
        if kind == "background":
            self.bg.set(name)
            self.render_preview()
            self.show_step("background")
        elif kind == "frame":
            self.frame.set(name)
            self.render_preview()
            self.show_step("frame")

    def select_frame_none(self):
        self.frame.set("__none__")
        self.render_preview()
        self.show_step("frame")

    def add_combo(self, label, var, values, command=None, parent=None):
        parent = parent or self.step_area
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", padx=0 if parent != self.step_area else 18, pady=5)
        ttk.Label(row, text=label).pack(anchor="e")
        cb = ttk.Combobox(row, textvariable=var, values=values, state="readonly", justify="right")
        cb.pack(fill="x", pady=3)
        if command:
            cb.bind("<<ComboboxSelected>>", lambda e: command())
        return cb

    def add_entry(self, label, var, command=None, parent=None):
        parent = parent or self.step_area
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", padx=0 if parent != self.step_area else 18, pady=5)
        ttk.Label(row, text=label).pack(anchor="e")
        ent = ttk.Entry(row, textvariable=var, justify="right")
        ent.pack(fill="x", pady=3)
        self.add_copy_paste_bindings(ent)
        if command:
            ent.bind("<KeyRelease>", lambda e: command())
        return ent

    def refresh_blessing_list(self):
        if hasattr(self, "text_box") and self.text_box.winfo_exists():
            self._text_cache = self.text_box.get("1.0", "end").strip()
        category = self.category.get()
        style = self.style_var.get()
        options = list(self.blessings.get(category, {}).get(style) or [])
        name = self.name.get().strip() or "שם"
        self._current_blessing_options = [x.replace("{name}", name) for x in options]
        if hasattr(self, "blessing_list"):
            self.blessing_list.delete(0, "end")
            for i, blessing in enumerate(self._current_blessing_options, start=1):
                first = blessing.replace("\n", " ")
                self.blessing_list.insert("end", f"{i}. {first[:90]}")
            if self._current_blessing_options:
                self.blessing_list.selection_set(0)
                self.preview_selected_blessing()
        self.render_preview()

    def preview_selected_blessing(self):
        if not hasattr(self, "blessing_preview"):
            return
        sel = self.blessing_list.curselection()
        txt = ""
        if sel:
            txt = self._current_blessing_options[sel[0]]
        self.blessing_preview.configure(state="normal")
        self.blessing_preview.delete("1.0", "end")
        self.blessing_preview.insert("1.0", txt)
        self.blessing_preview.configure(state="normal")

    def use_selected_blessing(self):
        sel = self.blessing_list.curselection() if hasattr(self, "blessing_list") else []
        if sel:
            self._text_cache = self._current_blessing_options[sel[0]]
        elif getattr(self, "_current_blessing_options", []):
            self._text_cache = self._current_blessing_options[0]
        self.show_step("text")

    def skip_blessing(self):
        if not self._text_cache:
            self._text_cache = ""
        self.show_step("text")

    def paste_clipboard_to_blessing(self):
        try:
            txt = self.root.clipboard_get()
            self._text_cache = txt
            self.show_step("text")
        except Exception:
            messagebox.showwarning("אין טקסט בלוח", "לא נמצא טקסט להדבקה מהלוח.")

    def paste_clipboard_to_main_text(self):
        try:
            txt = self.root.clipboard_get()
            if hasattr(self, "text_box"):
                self.text_box.insert("insert", txt)
                self.cache_text_and_render()
        except Exception:
            messagebox.showwarning("אין טקסט בלוח", "לא נמצא טקסט להדבקה מהלוח.")

    def cache_text_and_render(self):
        if hasattr(self, "text_box") and self.text_box.winfo_exists():
            self._text_cache = self.text_box.get("1.0","end").strip()
        self.render_preview()

    def apply_title_preset(self):
        p = self.title_preset.get()
        if p == "זהב אלגנטי":
            self.title_color.set("#C99437"); self.title_shadow.set(True)
        elif p == "אדום חגיגי":
            self.title_color.set("#DF463C"); self.title_shadow.set(False)
        elif p == "כהה עם צל":
            self.title_color.set("#111827"); self.title_shadow.set(True)
        else:
            self.title_color.set("#144C8A"); self.title_shadow.set(False)
        self.render_preview()

    def apply_body_preset(self):
        p = self.body_preset.get()
        if p == "כחול רך":
            self.body_color.set("#1D4E89"); self.body_shadow.set(False)
        elif p == "רומנטי":
            self.body_color.set("#9F2D55"); self.body_shadow.set(False)
        elif p == "מודרני עם צל":
            self.body_color.set("#111827"); self.body_shadow.set(True)
        else:
            self.body_color.set("#1E293B"); self.body_shadow.set(False)
        self.render_preview()

    def get_canvas_size(self):
        w = float(self.width_cm.get())
        h = float(self.height_cm.get())
        orientation = self.orientation.get()
        if orientation == "Landscape" and h > w:
            w,h = h,w
        elif orientation == "Portrait" and w > h:
            w,h = h,w
        elif orientation == "Auto":
            if len(self._text_cache) > 260 and h > w:
                w,h = h,w
        return cm_to_px(w), cm_to_px(h)

    def render_image(self):
        Wpx, Hpx = self.get_canvas_size()
        bg_path = BG_DIR / self.bg.get()
        if bg_path.exists():
            bg = Image.open(bg_path).convert("RGB").resize((Wpx,Hpx), Image.Resampling.LANCZOS)
        else:
            bg = Image.new("RGB", (Wpx,Hpx), "white")

        img = bg.convert("RGBA")
        safe = int(min(Wpx,Hpx)*0.075)
        title = self.title_text.get().strip()
        has_title = bool(title)

        if has_title:
            body_box = [safe*2, int(Hpx*0.30), Wpx-safe*2, int(Hpx*0.76)]
            title_y = int(Hpx*0.205)
            card = [safe, int(Hpx*0.16), Wpx-safe, int(Hpx*0.82)]
        else:
            body_box = [safe*2, int(Hpx*0.22), Wpx-safe*2, int(Hpx*0.77)]
            title_y = None
            card = [safe, int(Hpx*0.18), Wpx-safe, int(Hpx*0.82)]

        if self.card_enabled.get() and self.card_opacity.get() > 0:
            overlay = Image.new("RGBA", img.size, (0,0,0,0))
            od = ImageDraw.Draw(overlay, "RGBA")
            rgb = hex_to_rgb(self.card_color.get())
            alpha = int(255 * (self.card_opacity.get()/100))
            od.rounded_rectangle(card, radius=max(24,int(min(Wpx,Hpx)*0.03)), fill=rgb+(alpha,), outline=(255,255,255,min(alpha,120)), width=3)
            img = Image.alpha_composite(img, overlay)

        frame_name = self.frame.get()
        if frame_name != "__none__":
            frame_path = FRAME_DIR / frame_name
            if frame_path.exists():
                fr = Image.open(frame_path).convert("RGBA").resize((Wpx,Hpx), Image.Resampling.LANCZOS)
                img.alpha_composite(fr)

        d = ImageDraw.Draw(img, "RGBA")

        if has_title:
            title_font_size = int(self.title_size.get() * (min(Wpx,Hpx) / 1748))
            title_font_size = max(28, min(title_font_size, 150))
            title_font = ImageFont.truetype(FONT_BOLD, title_font_size) if FONT_BOLD else ImageFont.load_default()
            visual_title = bidi_text(title)
            title_bbox = d.textbbox((0,0), visual_title, font=title_font)
            tx = (Wpx-(title_bbox[2]-title_bbox[0]))/2
            if self.title_shadow.get():
                d.text((tx+5, title_y+5), visual_title, font=title_font, fill=(0,0,0,95))
            d.text((tx, title_y), visual_title, font=title_font, fill=hex_to_rgb(self.title_color.get())+(255,))

        body_text = self._text_cache.strip() or "הקלד/י כאן ברכה..."
        max_size = int(self.body_size.get() * (min(Wpx,Hpx) / 1748))
        max_size = max(24, min(max_size, 120))
        font, lines, line_h = fit_text(d, body_text, body_box, FONT_REG, max_size=max_size, min_size=20)
        total_h = line_h * len(lines)
        y = body_box[1] + max(0, (body_box[3]-body_box[1]-total_h)//2)
        body_rgb = hex_to_rgb(self.body_color.get())
        for line in lines:
            visual = bidi_text(line)
            bbox = d.textbbox((0,0), visual, font=font)
            x = (Wpx - (bbox[2]-bbox[0])) / 2
            if self.body_shadow.get():
                d.text((x+4,y+4), visual, font=font, fill=(0,0,0,80))
            d.text((x,y), visual, font=font, fill=body_rgb+(255,))
            y += line_h

        mark_font = ImageFont.truetype(FONT_BOLD, max(18, int(min(Wpx,Hpx)*0.022))) if FONT_BOLD else ImageFont.load_default()
        mark = bidi_text("חדיש • ברכות בעיצוב אישי")
        d.text((safe, Hpx-safe*0.8), mark, font=mark_font, fill=(20,76,138,170))
        return img.convert("RGB")

    def render_preview(self):
        try:
            if hasattr(self, "text_box") and self.text_box.winfo_exists():
                self._text_cache = self.text_box.get("1.0","end").strip()
            self.last_image = self.render_image()
            prev = self.last_image.copy()
            area_w = max(420, self.right.winfo_width()-60)
            area_h = max(420, self.right.winfo_height()-90)
            prev.thumbnail((area_w, area_h), Image.Resampling.LANCZOS)
            self.tk_preview = ImageTk.PhotoImage(prev)
            self.preview_label.configure(image=self.tk_preview, text="")
        except Exception as e:
            self.preview_label.configure(text=f"שגיאה בתצוגה: {e}", image="")

    def pick_card_color(self):
        color = colorchooser.askcolor(initialcolor=self.card_color.get(), title="בחר צבע תיבת טקסט")
        if color and color[1]:
            self.card_color.set(color[1])
            self.render_preview()

    def pick_title_color(self):
        color = colorchooser.askcolor(initialcolor=self.title_color.get(), title="בחר צבע כותרת")
        if color and color[1]:
            self.title_color.set(color[1])
            self.render_preview()

    def pick_body_color(self):
        color = colorchooser.askcolor(initialcolor=self.body_color.get(), title="בחר צבע גוף הטקסט")
        if color and color[1]:
            self.body_color.set(color[1])
            self.render_preview()

    def export_png(self):
        try:
            img = self.render_image()
            path = filedialog.asksaveasfilename(initialdir=str(EXPORT_DIR), defaultextension=".png", filetypes=[("PNG Image","*.png")])
            if path:
                img.save(path, dpi=(300,300))
                messagebox.showinfo("יצוא הושלם", f"הקובץ נשמר:\n{path}")
        except Exception as e:
            messagebox.showerror("שגיאה", str(e))

    def export_pdf(self):
        try:
            img = self.render_image()
            path = filedialog.asksaveasfilename(initialdir=str(EXPORT_DIR), defaultextension=".pdf", filetypes=[("PDF File","*.pdf")])
            if path:
                img.save(path, "PDF", resolution=300.0)
                messagebox.showinfo("יצוא הושלם", f"הקובץ נשמר:\n{path}")
        except Exception as e:
            messagebox.showerror("שגיאה", str(e))

    def open_exports(self):
        EXPORT_DIR.mkdir(exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(EXPORT_DIR)
        elif sys.platform == "darwin":
            subprocess.call(["open", str(EXPORT_DIR)])
        else:
            subprocess.call(["xdg-open", str(EXPORT_DIR)])

if __name__ == "__main__":
    root = tk.Tk()
    app = BlessingApp(root)
    root.mainloop()
