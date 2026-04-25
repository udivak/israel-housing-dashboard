# כללי עבודה

## זהב
- `common/` נעול. שינוי שם דורש הסכמה של שני החוקרים (משתלבים על כולם).
- ה-test set לא נחשף בקוד של המודל. ה-runner הוא היחיד שקורא ל-`predict(X_test)`.
- `leaderboard.json` נערך **רק** על-ידי `run.py`. אין לערוך ידנית.

## תיקייה אישית (`models/{person}/`)
- הבעלים של התיקייה הוא היחיד שמשנה בה.
- `OWNERS` — קובץ עם האימייל שלך.
- `EXPERIMENTS.md` — יומן אישי. תעד מה ניסית, מה עבד, מה לא.
- מודל = קובץ `.py` בודד עם `train()` ו-`predict()`.

## הוגנות
- `seed=42` קבוע. אם בודקים יציבות — מריצים 3 seeds ומדווחים ממוצע.
- אותו dataset, אותם splits, אותן metrics — כולם עוברים דרך `common/` ו-`run.py`.
- אסור לחשב feature על בסיס כל הדאטה (`X_train + X_test`). כל feature engineering — רק על `X_train`.

## הוספת מודל חדש — checklist
- [ ] קובץ ב-`models/{your_folder}/{name}.py`
- [ ] `train(X_train, y_train, X_val, y_val) → model`
- [ ] `predict(model, X) → np.ndarray`
- [ ] ריצה: `python run.py {your_folder}/{name}`
- [ ] עדכון `EXPERIMENTS.md`
