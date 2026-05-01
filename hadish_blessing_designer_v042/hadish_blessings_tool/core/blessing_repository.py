import json
from pathlib import Path

class BlessingRepository:
    def __init__(self, data_path=None):
        base = Path(__file__).resolve().parents[1]
        self.data_path = Path(data_path) if data_path else base / 'data' / 'blessings.json'
        self.items = []
        self.load()

    def load(self):
        if self.data_path.exists():
            self.items = json.loads(self.data_path.read_text(encoding='utf-8'))
        else:
            self.items = []
        return self.items

    def save(self):
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_path.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding='utf-8')

    def values(self, key):
        return sorted({item.get(key, '') for item in self.items if item.get(key, '')})

    def search(self, query='', event='הכל', recipient='הכל', product='הכל', style='הכל', favorites=None):
        q = (query or '').strip().lower()
        favorites = favorites or set()
        results = []
        for item in self.items:
            if event != 'הכל' and item.get('event') != event: continue
            if recipient != 'הכל' and item.get('recipient') != recipient: continue
            if product != 'הכל' and item.get('product') != product: continue
            if style != 'הכל' and style not in item.get('style', []): continue
            blob = ' '.join([item.get('text',''), item.get('event',''), item.get('recipient',''), item.get('product',''), ' '.join(item.get('style', []))]).lower()
            if q and q not in blob: continue
            copy = dict(item)
            copy['favorite'] = item.get('id') in favorites
            results.append(copy)
        results.sort(key=lambda x: (not x.get('favorite', False), x.get('event',''), x.get('recipient',''), x.get('product','')))
        return results

    def delete_item(self, item_id):
        before = len(self.items)
        self.items = [x for x in self.items if x.get('id') != item_id]
        if len(self.items) != before:
            self.save()
            return True
        return False

    def add_item(self, item):
        existing = {x['id'] for x in self.items}
        base_id = item.get('id') or 'custom'
        new_id = base_id
        n = 1
        while new_id in existing:
            n += 1
            new_id = f'{base_id}_{n}'
        item['id'] = new_id
        self.items.append(item)
        self.save()
        return item
