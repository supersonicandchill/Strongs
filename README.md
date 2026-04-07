# Strongs Bible — ASV
### Mobile PWA · Full Strong's Concordance · 331,000+ tagged words · Study Notes

---

## Deploy in 3 steps

```bash
# 1. Create GitHub repo named "strongs-bible"
# 2. Push this folder
git init && git add . && git commit -m "Strongs Bible"
git remote add origin https://github.com/YOUR_USERNAME/strongs-bible.git
git push -u origin main

# 3. Enable Pages: Settings → Pages → Source: main / root
# Live at: https://YOUR_USERNAME.github.io/strongs-bible/
```

## Add to iPhone

Safari → Share → "Add to Home Screen" → installs as full-screen app, works offline.

---

## What's included

| | |
|---|---|
| Bible text | American Standard Version (public domain) |
| Coverage | All 66 books, 29,818 verses |
| Tagged words | 331,150 linked to Strong's numbers |
| Dictionary | 14,298 entries (8,674 Hebrew + 5,624 Greek) |
| Loading | Per-book lazy-loading — only fetches what you're reading |
| Offline | Service worker caches books as you read them |

## Features

**Reading**
- All 66 books with chapter navigation
- Prev/Next chapter buttons at top of each chapter
- Amber underline = Hebrew (OT) · Blue underline = Greek (NT)
- Tap any underlined word → Strong's definition drawer
- Inline Strong's number badges (toggle on/off)
- Hide Hebrew / Greek highlighting independently
- Font size A− / A+ control

**Strong's Drawer**
- Original Hebrew/Greek word + transliteration
- Phonetic pronunciation
- Full definition
- KJV usage notes
- Add note for that verse directly from the drawer

**Study Notes**
- Tap any verse number to add/edit a note
- Green dot appears on verse numbers with notes
- Notes tab shows all notes sorted by most recent
- Tap any note to jump back to that verse
- Export all notes as .txt (canonical order)
- Export all notes as PDF (printable, formatted)

**Search**
- Full-text search across all books you've read
- Books are added to search index as you navigate to them

---

## Data format reference

`data/verses/GEN.json` (example):
```json
{
  "1": {
    "1": [
      {"w": "In", "s": "H7225"},
      {"w": "the"},
      {"w": "beginning", "s": "H7225"},
      {"w": "God", "s": "H430"},
      {"w": "created", "s": "H1254", "p": "."}
    ]
  }
}
```
- `w` = English word
- `s` = Strong's number (H = Hebrew, G = Greek) — optional
- `p` = trailing punctuation — optional
- All keys are **strings** (JSON requirement)

`data/strongs.json` (example):
```json
{
  "H430": {
    "lemma": "אֱלֹהִים",
    "xlit": "ʼĕlôhîym",
    "pron": "el-o-heem'",
    "definition": "God; the supreme God...",
    "kjv": "God, god, judge...",
    "pos": ""
  }
}
```

---

## File structure
```
strongs-bible/
├── index.html           ← Complete PWA (single file)
├── manifest.json        ← PWA install config
├── sw.js                ← Smart offline caching
├── icon-192.png         ← App icon
├── icon-512.png         ← App icon
├── process_usfm.py      ← Rebuild data from USFM source
├── data/
│   ├── strongs.json     ← Full dictionary (14,298 entries, ~3MB)
│   ├── tagged_verses.json ← Full Bible combined (fallback)
│   └── verses/          ← Per-book files (lazy loaded)
│       ├── GEN.json     (703 KB)
│       ├── PSA.json     (804 KB)
│       └── ... 66 files total
└── .github/workflows/
    └── deploy.yml       ← Auto-deploy to GitHub Pages
```

---

*American Standard Version · Strong's Exhaustive Concordance · Public Domain*
