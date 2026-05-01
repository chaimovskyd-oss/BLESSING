import json
import random
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from core.blessing_repository import BlessingRepository
from integration.canvas_bridge import CanvasBridge

APP_TITLE = 'חדיש - ברכות וציטוטים'
BRAND_COLORS = {
    'blue': '#1E5BFF', 'cyan': '#17B8FF', 'yellow': '#FFD23F',
    'orange': '#FF8A24', 'red': '#E63946', 'dark': '#151B2D', 'card': '#FFFFFF'
}

RECIPIENT_COLORS = {
    'מתגייס': '#DCFCE7',
    'מתגייסת': '#DCFCE7',
    'גיוס לגבר': '#DCFCE7',
    'גיוס לאישה': '#DCFCE7',
    'סבא': '#DBEAFE',
    'סבתא': '#FCE7F3',
    'נוער בנות': '#F3E8FF',
    'חברה טובה (נוער)': '#F3E8FF',
    'לידה ותינוקות': '#FFE4E6',
    'תינוקת': '#FFE4E6',
    'תינוק': '#E0F2FE',
    'בן זוג': '#E0E7FF',
    'בת זוג': '#FCE7F3',
    'מורה': '#FEF3C7',
    'גננת': '#FFEDD5',
    'רופא': '#E0F2FE',
    'עורך דין': '#EDE9FE',
    'רואה חשבון': '#ECFDF5',
    'מנהל': '#E2E8F0',
    'מפקד': '#DCFCE7',
    'עובד': '#F1F5F9',
}
DEFAULT_ROW_BG = '#FFFFFF'

class QuoteRepository:
    def __init__(self, data_path=None):
        base = Path(__file__).resolve().parent
        self.data_path = Path(data_path) if data_path else base / 'data' / 'sources_quotes.json'
        self.items = []
        self.load()

    def load(self):
        if self.data_path.exists():
            self.items = json.loads(self.data_path.read_text(encoding='utf-8'))
        return self.items

    def save(self):
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_path.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding='utf-8')

    def values(self, key):
        return sorted({item.get(key, '') for item in self.items if item.get(key, '')})

    def source_groups(self):
        return sorted({item.get('source_group') or item.get('section') or item.get('source', '') for item in self.items if (item.get('source_group') or item.get('section') or item.get('source'))})

    def delete_item(self, item_id):
        before = len(self.items)
        self.items = [x for x in self.items if x.get('id') != item_id]
        if len(self.items) != before:
            self.save()
            return True
        return False

    def search(self, query='', category='הכל', source='הכל', product='הכל', style='הכל', favorites=None):
        q = (query or '').strip().lower()
        favorites = favorites or set()
        results = []
        for item in self.items:
            if category != 'הכל' and item.get('category') != category:
                continue
            item_source_group = item.get('source_group') or item.get('section') or item.get('source')
            if source != 'הכל' and item_source_group != source:
                continue
            if product != 'הכל' and item.get('product') != product:
                continue
            if style != 'הכל' and style not in item.get('style', []):
                continue
            blob = ' '.join([
                item.get('text',''), item.get('category',''), item.get('source',''), item.get('source_group',''),
                item.get('product',''), ' '.join(item.get('style', []))
            ]).lower()
            if q and q not in blob:
                continue
            copy = dict(item)
            copy['favorite'] = item.get('id') in favorites
            results.append(copy)
        results.sort(key=lambda x: (not x.get('favorite', False), x.get('source_group',''), x.get('category',''), x.get('source','')))
        return results

class BlessingApp(tk.Tk):
    def __init__(self, on_insert_text=None):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry('1240x780')
        self.minsize(1000, 640)
        self.repo = BlessingRepository()
        self.quote_repo = QuoteRepository()
        self.bridge = CanvasBridge(on_insert_text)
        self.data_dir = Path(__file__).resolve().parent / 'data'
        self.fav_path = self.data_dir / 'favorites.json'
        self.quote_fav_path = self.data_dir / 'quote_favorites.json'
        self.favorites = self.load_favorites(self.fav_path)
        self.quote_favorites = self.load_favorites(self.quote_fav_path)
        self.mode = 'blessings'
        self.filtered = []
        self.selected_item = None
        self.configure(bg='#F5F7FF')
        self.setup_style()
        self.build_ui()
        self.switch_mode('blessings')

    def setup_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TCombobox', padding=6, font=('Segoe UI', 11))
        style.configure('Treeview', rowheight=62, font=('Segoe UI', 11), background='white', fieldbackground='white', foreground='#0F172A')
        style.configure('Treeview.Heading', font=('Segoe UI', 11, 'bold'), foreground='#111827')
        style.map('Treeview', background=[('selected', '#1E5BFF')], foreground=[('selected', 'white')])

    def load_favorites(self, path):
        if path.exists():
            try:
                return set(json.loads(path.read_text(encoding='utf-8')))
            except Exception:
                return set()
        return set()

    def save_favorites(self):
        self.fav_path.write_text(json.dumps(sorted(self.favorites), ensure_ascii=False, indent=2), encoding='utf-8')
        self.quote_fav_path.write_text(json.dumps(sorted(self.quote_favorites), ensure_ascii=False, indent=2), encoding='utf-8')

    def build_ui(self):
        header = tk.Frame(self, bg=BRAND_COLORS['dark'], height=96)
        header.pack(fill='x')
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg=BRAND_COLORS['dark'])
        title_box.pack(side='right', fill='y', padx=24)
        tk.Label(title_box, text='🎁 חדיש', bg=BRAND_COLORS['dark'], fg='white',
                 font=('Segoe UI', 18, 'bold')).pack(anchor='e', pady=(16, 0))
        tk.Label(title_box, text='ברכות, ציטוטים ומקורות להדפסה', bg=BRAND_COLORS['dark'], fg='#DDE6FF',
                 font=('Segoe UI', 10)).pack(anchor='e')

        tabs = tk.Frame(header, bg=BRAND_COLORS['dark'])
        tabs.pack(side='right', padx=20, pady=20)
        self.blessings_btn = tk.Button(tabs, text='💌  מחולל ברכות', command=lambda: self.switch_mode('blessings'),
                                       bg=BRAND_COLORS['yellow'], fg=BRAND_COLORS['dark'], bd=0,
                                       padx=28, pady=15, font=('Segoe UI', 14, 'bold'), cursor='hand2')
        self.blessings_btn.pack(side='right', padx=8)
        self.quotes_btn = tk.Button(tabs, text='📜  ציטוטים ומקורות', command=lambda: self.switch_mode('quotes'),
                                    bg='#334155', fg='white', bd=0,
                                    padx=28, pady=15, font=('Segoe UI', 14, 'bold'), cursor='hand2')
        self.quotes_btn.pack(side='right', padx=8)

        main = tk.Frame(self, bg='#F5F7FF')
        main.pack(fill='both', expand=True, padx=18, pady=16)

        # שורת פעולות עליונה קבועה — תמיד גלויה, בלי תלות בתפריט צד
        action_bar = tk.Frame(main, bg='#FFFFFF', bd=0, highlightthickness=1, highlightbackground='#E2E8F0')
        action_bar.pack(fill='x', pady=(0, 12))

        def action_button(text, command, bg, fg='white'):
            btn = tk.Button(action_bar, text=text, command=command, bg=bg, fg=fg, bd=0,
                            padx=18, pady=11, font=('Segoe UI', 11, 'bold'), cursor='hand2')
            btn.pack(side='right', padx=7, pady=10)
            return btn

        self.btn_copy = action_button('📋 העתק', self.copy_selected, BRAND_COLORS['blue'])
        self.btn_canvas = action_button('➕ הוסף לקנבס', self.insert_selected, '#16A34A')
        self.btn_fav = action_button('⭐ מועדף', self.toggle_favorite, '#FACC15', BRAND_COLORS['dark'])
        self.btn_add = action_button('✍️ הוסף חדש', self.open_add_dialog, BRAND_COLORS['orange'])
        self.btn_delete = action_button('🗑️ מחק', self.delete_selected, '#DC2626')
        tk.Label(action_bar, text='בחר משפט מהרשימה ואז לחץ על פעולה', bg='white', fg='#64748B',
                 font=('Segoe UI', 10)).pack(side='left', padx=16)

        self.filters = tk.Frame(main, bg='#FFFFFF', bd=0, highlightthickness=1, highlightbackground='#E2E8F0')
        self.filters.pack(fill='x', pady=(0, 14))

        self.search_var = tk.StringVar()
        self.filter1_var = tk.StringVar(value='הכל')
        self.filter2_var = tk.StringVar(value='הכל')
        self.product_var = tk.StringVar(value='הכל')
        self.style_var = tk.StringVar(value='הכל')

        self.filter_widgets = []
        self.add_filter(self.filters, 'חיפוש חופשי', self.search_var, 0, is_entry=True)
        self.add_filter(self.filters, 'אירוע', self.filter1_var, 1)
        self.add_filter(self.filters, 'למי?', self.filter2_var, 2)
        self.add_filter(self.filters, 'מוצר', self.product_var, 3)
        self.add_filter(self.filters, 'סגנון', self.style_var, 4)

        btns = tk.Frame(self.filters, bg='white')
        btns.grid(row=0, column=5, padx=10, pady=14, sticky='ns')
        tk.Button(btns, text='נקה סינון', command=self.clear_filters, bg='#EEF2FF', fg=BRAND_COLORS['dark'],
                  bd=0, padx=16, pady=9, font=('Segoe UI', 10, 'bold')).pack(fill='x', pady=2)
        tk.Button(btns, text='בחירה אקראית', command=self.random_pick, bg=BRAND_COLORS['yellow'],
                  fg=BRAND_COLORS['dark'], bd=0, padx=16, pady=9, font=('Segoe UI', 10, 'bold')).pack(fill='x', pady=2)

        body = tk.Frame(main, bg='#F5F7FF')
        body.pack(fill='both', expand=True)

        list_frame = tk.Frame(body, bg='white', highlightthickness=1, highlightbackground='#E2E8F0')
        list_frame.pack(side='right', fill='both', expand=True, padx=(0, 12))

        columns = ('fav', 'text', 'main', 'sub', 'product', 'style')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='browse')
        self.tree.heading('fav', text='★')
        self.tree.heading('text', text='הטקסט')
        self.tree.heading('main', text='אירוע')
        self.tree.heading('sub', text='למי')
        self.tree.heading('product', text='מוצר')
        self.tree.heading('style', text='סגנון')
        self.tree.column('fav', width=48, anchor='center', stretch=False)
        self.tree.column('text', width=560, anchor='e')
        self.tree.column('main', width=125, anchor='center')
        self.tree.column('sub', width=150, anchor='center')
        self.tree.column('product', width=118, anchor='center')
        self.tree.column('style', width=165, anchor='center')
        scroll = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=8, pady=8)
        scroll.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Button-1>', self.on_tree_click)

        side = tk.Frame(body, bg='white', width=330, highlightthickness=1, highlightbackground='#E2E8F0')
        side.pack(side='left', fill='y')
        side.pack_propagate(False)
        self.preview_title = tk.Label(side, text='תצוגה מהירה', bg='white', fg=BRAND_COLORS['dark'], font=('Segoe UI', 18, 'bold'))
        self.preview_title.pack(anchor='e', padx=18, pady=(10, 4))
        self.preview_meta = tk.Label(side, text='', bg='white', fg='#64748B', font=('Segoe UI', 10), wraplength=285, justify='right')
        self.preview_meta.pack(anchor='e', padx=18, pady=(0, 4))
        self.preview = tk.Text(side, wrap='word', height=7, bg='#F8FAFC', fg='#111827', font=('Segoe UI', 14), bd=0, padx=14, pady=14)
        self.preview.pack(fill='x', padx=16, pady=8)
        self.preview.configure(state='disabled')
        tk.Label(side, text='הפעולות עברו לשורה העליונה כדי שלא ייחתכו במסכים קטנים.',
                 bg='white', fg='#64748B', font=('Segoe UI', 10), wraplength=285, justify='right').pack(fill='x', padx=16, pady=8)
        self.status = tk.Label(side, text='', bg='white', fg='#64748B', font=('Segoe UI', 10), wraplength=290, justify='right')
        self.status.pack(fill='x', padx=16, pady=6)

        for var in [self.search_var, self.filter1_var, self.filter2_var, self.product_var, self.style_var]:
            var.trace_add('write', lambda *_: self.refresh_results())

        self.configure_row_tags()

    def configure_row_tags(self):
        self.tree.tag_configure('default', background=DEFAULT_ROW_BG, foreground='#0F172A')
        self.tree.tag_configure('quote', background='#F8FAFC', foreground='#0F172A')
        self.tree.tag_configure('source', background='#FFF7ED', foreground='#111827')
        for key, color in RECIPIENT_COLORS.items():
            self.tree.tag_configure(f'recipient_{key}', background=color, foreground='#0F172A')

    def add_filter(self, parent, label, var, col, is_entry=False):
        box = tk.Frame(parent, bg='white')
        box.grid(row=0, column=col, padx=8, pady=12, sticky='ew')
        parent.grid_columnconfigure(col, weight=1)
        lbl = tk.Label(box, text=label, bg='white', fg='#334155', font=('Segoe UI', 10, 'bold'))
        lbl.pack(anchor='e')
        if is_entry:
            widget = tk.Entry(box, textvariable=var, font=('Segoe UI', 12), relief='flat', bg='#F1F5F9', justify='right')
            widget.pack(fill='x', ipady=8, pady=(4,0))
        else:
            widget = ttk.Combobox(box, textvariable=var, state='readonly', justify='right')
            widget.pack(fill='x', pady=(4,0))
        self.filter_widgets.append((label, lbl, widget))

    def switch_mode(self, mode):
        self.mode = mode
        self.selected_item = None
        self.search_var.set('')
        self.filter1_var.set('הכל')
        self.filter2_var.set('הכל')
        self.product_var.set('הכל')
        self.style_var.set('הכל')

        if mode == 'blessings':
            self.blessings_btn.configure(bg=BRAND_COLORS['yellow'], fg=BRAND_COLORS['dark'])
            self.quotes_btn.configure(bg='#334155', fg='white')
            self.tree.heading('main', text='אירוע')
            self.tree.heading('sub', text='למי')
            self.set_filter_label(1, 'אירוע')
            self.set_filter_label(2, 'למי?')
            self.preview_title.config(text='תצוגה מהירה')
        else:
            self.blessings_btn.configure(bg='#334155', fg='white')
            self.quotes_btn.configure(bg=BRAND_COLORS['yellow'], fg=BRAND_COLORS['dark'])
            self.tree.heading('main', text='קטגוריה')
            self.tree.heading('sub', text='מקור / מייחס')
            self.set_filter_label(1, 'קטגוריה')
            self.set_filter_label(2, 'סוג מקור')
            self.preview_title.config(text='מקור / ציטוט')

        self.refresh_filters()
        self.refresh_results()

    def set_filter_label(self, index, text):
        _, lbl, _ = self.filter_widgets[index]
        lbl.config(text=text)

    def refresh_filters(self):
        if self.mode == 'blessings':
            values1 = ['הכל'] + self.repo.values('event')
            values2 = ['הכל'] + self.repo.values('recipient')
            products = ['הכל'] + self.repo.values('product')
            styles = sorted({s for item in self.repo.items for s in item.get('style', [])})
        else:
            values1 = ['הכל'] + self.quote_repo.values('category')
            values2 = ['הכל'] + self.quote_repo.source_groups()
            products = ['הכל'] + self.quote_repo.values('product')
            styles = sorted({s for item in self.quote_repo.items for s in item.get('style', [])})
        self.filter_widgets[1][2]['values'] = values1
        self.filter_widgets[2][2]['values'] = values2
        self.filter_widgets[3][2]['values'] = products
        self.filter_widgets[4][2]['values'] = ['הכל'] + styles

    def clear_filters(self):
        self.search_var.set('')
        self.filter1_var.set('הכל')
        self.filter2_var.set('הכל')
        self.product_var.set('הכל')
        self.style_var.set('הכל')

    def refresh_results(self):
        if self.mode == 'blessings':
            self.filtered = self.repo.search(self.search_var.get(), self.filter1_var.get(), self.filter2_var.get(),
                                             self.product_var.get(), self.style_var.get(), self.favorites)
        else:
            self.filtered = self.quote_repo.search(self.search_var.get(), self.filter1_var.get(), self.filter2_var.get(),
                                                   self.product_var.get(), self.style_var.get(), self.quote_favorites)

        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(self.filtered):
            fav = '★' if item.get('favorite') else '☆'
            text = item.get('text', '')
            text_short = text if len(text) <= 120 else text[:117] + '...'
            style = ', '.join(item.get('style', [])[:3])
            if self.mode == 'blessings':
                main = item.get('event','')
                sub = item.get('recipient','')
                tag = self.row_tag_for_recipient(sub, main)
            else:
                main = item.get('category','')
                sub = item.get('source','')
                tag = 'source' if item.get('section') == 'מקורות וברכות' else 'quote'
            self.tree.insert('', 'end', iid=str(i), values=(fav, text_short, main, sub, item.get('product',''), style), tags=(tag,))

        mode_text = 'ברכות' if self.mode == 'blessings' else 'ציטוטים ומקורות'
        self.status.config(text=f'נמצאו {len(self.filtered)} {mode_text}. כוכב קטן מסמן מועדף. לחיצה כפולה מוסיפה לקנבס.')
        self.clear_preview()

    def row_tag_for_recipient(self, recipient, event):
        if recipient in RECIPIENT_COLORS:
            return f'recipient_{recipient}'
        if event == 'גיוס':
            return 'recipient_מתגייס'
        if event == 'לידה ותינוקות':
            return 'recipient_לידה ותינוקות'
        return 'default'

    def clear_preview(self):
        self.preview_meta.config(text='')
        self.preview.configure(state='normal')
        self.preview.delete('1.0', 'end')
        self.preview.configure(state='disabled')

    def on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_item = self.filtered[int(sel[0])]
        if self.mode == 'blessings':
            meta = f"{self.selected_item.get('event','')} • {self.selected_item.get('recipient','')} • {self.selected_item.get('product','')}"
        else:
            meta = f"{self.selected_item.get('source_group', self.selected_item.get('section',''))} • {self.selected_item.get('category','')} • {self.selected_item.get('source','')} • {self.selected_item.get('product','')}"
        self.preview_meta.config(text=meta)
        self.preview.configure(state='normal')
        self.preview.delete('1.0', 'end')
        self.preview.insert('1.0', self.selected_item.get('text',''))
        self.preview.configure(state='disabled')

    def on_double_click(self, event):
        region = self.tree.identify('region', event.x, event.y)
        col = self.tree.identify_column(event.x)
        if region == 'cell' and col == '#1':
            self.toggle_favorite_for_row()
        else:
            self.insert_selected()

    def on_tree_click(self, event):
        region = self.tree.identify('region', event.x, event.y)
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if region == 'cell' and col == '#1' and row:
            self.tree.selection_set(row)
            self.on_select()
            self.toggle_favorite_for_row()
            return 'break'

    def current_fav_set(self):
        return self.favorites if self.mode == 'blessings' else self.quote_favorites

    def toggle_favorite_for_row(self):
        if not self.selected_item:
            return
        favs = self.current_fav_set()
        item_id = self.selected_item.get('id')
        if item_id in favs:
            favs.remove(item_id)
        else:
            favs.add(item_id)
        self.save_favorites()
        self.refresh_results()

    def toggle_favorite(self):
        self.toggle_favorite_for_row()

    def copy_selected(self):
        if not self.selected_item:
            return
        self.clipboard_clear()
        self.clipboard_append(self.selected_item.get('text',''))
        self.status.config(text='הטקסט הועתק ללוח ✅')

    def insert_selected(self):
        if not self.selected_item:
            return
        inserted = self.bridge.add_text(self.selected_item.get('text',''))
        if inserted:
            self.status.config(text='הטקסט נשלח לקנבס ✅')
        else:
            self.copy_selected()
            self.status.config(text='מצב עצמאי: אין קנבס מחובר, אז הטקסט הועתק ללוח ✅')

    def random_pick(self):
        if not self.filtered:
            return
        idx = random.randrange(len(self.filtered))
        self.tree.selection_set(str(idx))
        self.tree.see(str(idx))
        self.on_select()


    def delete_selected(self):
        if not self.selected_item:
            messagebox.showinfo('מחיקה', 'בחר קודם משפט למחיקה.')
            return
        text = self.selected_item.get('text','')
        short = text if len(text) <= 90 else text[:87] + '...'
        ok = messagebox.askyesno('אישור מחיקה', f'האם למחוק את המשפט הזה?\n\n{short}')
        if not ok:
            return
        item_id = self.selected_item.get('id')
        if self.mode == 'blessings':
            deleted = self.repo.delete_item(item_id)
            self.favorites.discard(item_id)
        else:
            deleted = self.quote_repo.delete_item(item_id)
            self.quote_favorites.discard(item_id)
        self.save_favorites()
        self.selected_item = None
        self.refresh_filters()
        self.refresh_results()
        self.status.config(text='המשפט נמחק ✅' if deleted else 'לא הצלחתי למחוק את המשפט.')

    def open_add_dialog(self):
        if self.mode != 'blessings':
            messagebox.showinfo('הוספת טקסט', 'בשלב הזה הוספה ידנית זמינה במחולל הברכות. ציטוטים ומקורות נשמרים בקובץ data/sources_quotes.json.')
            return
        win = tk.Toplevel(self)
        win.title('הוספת משפט חדש')
        win.geometry('520x470')
        win.configure(bg='white')
        fields = {}
        defaults = {'event': self.filter1_var.get(), 'recipient': self.filter2_var.get(), 'product': self.product_var.get(), 'style': self.style_var.get()}
        for label, key in [('אירוע','event'),('למי','recipient'),('מוצר','product'),('סגנון','style')]:
            tk.Label(win, text=label, bg='white', font=('Segoe UI', 10, 'bold')).pack(anchor='e', padx=16, pady=(10,0))
            e = tk.Entry(win, justify='right', font=('Segoe UI', 11))
            e.pack(fill='x', padx=16, ipady=6)
            e.insert(0, '' if defaults[key]=='הכל' else defaults[key])
            fields[key]=e
        tk.Label(win, text='המשפט', bg='white', font=('Segoe UI', 10, 'bold')).pack(anchor='e', padx=16, pady=(10,0))
        txt = tk.Text(win, height=5, wrap='word', font=('Segoe UI', 12))
        txt.pack(fill='both', expand=True, padx=16, pady=6)
        def save():
            text = txt.get('1.0','end').strip()
            if not text:
                messagebox.showwarning('חסר משפט','יש להזין משפט.')
                return
            item = {
                'id': 'custom',
                'event': fields['event'].get().strip() or 'כללי',
                'recipient': fields['recipient'].get().strip() or 'כללי',
                'product': fields['product'].get().strip() or 'כללי',
                'style': [s.strip() for s in fields['style'].get().split(',') if s.strip()] or ['מותאם אישית'],
                'length': 'קצר' if len(text)<55 else 'בינוני',
                'text': text
            }
            self.repo.add_item(item)
            self.refresh_filters()
            self.refresh_results()
            win.destroy()
        tk.Button(win, text='שמור משפט', command=save, bg=BRAND_COLORS['blue'], fg='white', bd=0,
                  font=('Segoe UI', 12, 'bold'), pady=10).pack(fill='x', padx=16, pady=14)

if __name__ == '__main__':
    app = BlessingApp()
    app.mainloop()
