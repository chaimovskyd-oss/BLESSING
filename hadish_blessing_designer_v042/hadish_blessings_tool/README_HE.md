# חדיש — מחולל ברכות וציטוטים v06

גרסה ראשונית-מתקדמת לכלי פנימי לחנות:
- מחולל ברכות לפי אירוע, למי מתאים, מוצר וסגנון.
- אגף ציטוטים ומקורות עם סינון לפי סוג מקור: תנ״ך/מסורתי, אנשי חינוך, דמויות ציוניות, דיסני וספרי ילדים, משפטים ידועים ועוד.
- שורת פעולות עליונה קבועה: העתק, הוסף לקנבס, מועדף, הוסף חדש, מחק.
- מחיקת משפט עם חלון אישור.
- כוכב ☆/★ למועדפים ליד כל משפט.
- מאגר JSON חיצוני שקל להרחיב בעתיד.
- חיבור עתידי לקנבס דרך integration/canvas_bridge.py.

## הפעלה
פתחו PowerShell בתיקייה אחרי חילוץ הקובץ והריצו:

```bash
py main.py
```

או:

```bash
python main.py
```

## קבצי נתונים
- `data/blessings.json` — ברכות ומשפטים לפי אירועים ומוצרים.
- `data/sources_quotes.json` — ציטוטים, מקורות וברכות מוכרות.
- `data/favorites.json` ו־`data/quote_favorites.json` נוצרים אחרי סימון מועדפים.

## חיבור עתידי לקנבס
אפשר לפתוח את הפאנל עם callback:

```python
from main import BlessingApp

app = BlessingApp(on_insert_text=my_canvas_add_text_function)
app.mainloop()
```

הפונקציה צריכה לקבל טקסט:

```python
def my_canvas_add_text_function(text: str):
    # להוסיף טקסט לקנבס של האפליקציה הראשית
    pass
```
