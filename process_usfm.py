#!/usr/bin/env python3
"""
process_usfm.py
───────────────
Converts STEPBible WEB USFM files → data/verses/{BOOKID}.json
Also converts openscriptures Strong's JS files → data/strongs.json

DROP YOUR FILES IN:
  usfm/       ← STEPBible USFM files (e.g. WEB_01GEN.usfm, etc.)
  strongs/    ← strongs-hebrew-dictionary.js + strongs-greek-dictionary.js

THEN RUN:
  python3 process_usfm.py

OUTPUT:
  data/verses/GEN.json  (one per book, lazy-loaded in app)
  data/strongs.json     (full 8700-entry dictionary)
  data/tagged_verses.json (merged, for quick prototype loading)
"""

import json, os, re, sys
from pathlib import Path

# ── Book ID mapping ────────────────────────────────────────────
BOOK_MAP = {
  # STEPBible uses OSIS IDs — map to our short IDs
  'Gen':'GEN','Exod':'EXO','Lev':'LEV','Num':'NUM','Deut':'DEU',
  'Josh':'JOS','Judg':'JDG','Ruth':'RUT','1Sam':'1SA','2Sam':'2SA',
  '1Kgs':'1KI','2Kgs':'2KI','1Chr':'1CH','2Chr':'2CH','Ezra':'EZR',
  'Neh':'NEH','Esth':'EST','Job':'JOB','Ps':'PSA','Prov':'PRO',
  'Eccl':'ECC','Song':'SNG','Isa':'ISA','Jer':'JER','Lam':'LAM',
  'Ezek':'EZK','Dan':'DAN','Hos':'HOS','Joel':'JOL','Amos':'AMO',
  'Obad':'OBA','Jonah':'JON','Mic':'MIC','Nah':'NAH','Hab':'HAB',
  'Zeph':'ZEP','Hag':'HAG','Zech':'ZEC','Mal':'MAL',
  'Matt':'MAT','Mark':'MRK','Luke':'LUK','John':'JHN','Acts':'ACT',
  'Rom':'ROM','1Cor':'1CO','2Cor':'2CO','Gal':'GAL','Eph':'EPH',
  'Phil':'PHP','Col':'COL','1Thess':'1TH','2Thess':'2TH',
  '1Tim':'1TI','2Tim':'2TI','Titus':'TIT','Phlm':'PHM',
  'Heb':'HEB','Jas':'JAS','1Pet':'1PE','2Pet':'2PE',
  '1John':'1JN','2John':'2JN','3John':'3JN','Jude':'JUD','Rev':'REV',
}

# Also handle filename-based detection (WEB_01GEN.usfm → GEN)
FILENAME_MAP = {
  '01GEN':'GEN','02EXO':'EXO','03LEV':'LEV','04NUM':'NUM','05DEU':'DEU',
  '06JOS':'JOS','07JDG':'JDG','08RUT':'RUT','091SA':'1SA','102SA':'2SA',
  '111KI':'1KI','122KI':'2KI','131CH':'1CH','142CH':'2CH','15EZR':'EZR',
  '16NEH':'NEH','17EST':'EST','18JOB':'JOB','19PSA':'PSA','20PRO':'PRO',
  '21ECC':'ECC','22SNG':'SNG','23ISA':'ISA','24JER':'JER','25LAM':'LAM',
  '26EZK':'EZK','27DAN':'DAN','28HOS':'HOS','29JOL':'JOL','30AMO':'AMO',
  '31OBA':'OBA','32JON':'JON','33MIC':'MIC','34NAH':'NAH','35HAB':'HAB',
  '36ZEP':'ZEP','37HAG':'HAG','38ZEC':'ZEC','39MAL':'MAL',
  '40MAT':'MAT','41MRK':'MRK','42LUK':'LUK','43JHN':'JHN','44ACT':'ACT',
  '45ROM':'ROM','461CO':'1CO','472CO':'2CO','48GAL':'GAL','49EPH':'EPH',
  '50PHP':'PHP','51COL':'COL','521TH':'1TH','532TH':'2TH',
  '541TI':'1TI','552TI':'2TI','56TIT':'TIT','57PHM':'PHM',
  '58HEB':'HEB','59JAS':'JAS','601PE':'1PE','612PE':'2PE',
  '621JN':'1JN','632JN':'2JN','643JN':'3JN','65JUD':'JUD','66REV':'REV',
}

def detect_book_id(filepath):
  """Detect book ID from filename or USFM content"""
  name = Path(filepath).stem.upper()
  # Try filename patterns
  for key, val in FILENAME_MAP.items():
    if key in name:
      return val
  # Try last 3 chars of filename
  suffix = name[-3:]
  if suffix in FILENAME_MAP.values():
    return suffix
  return None

def parse_strongs_js(js_text, prefix):
  """Parse openscriptures Strong's dictionary JS file"""
  # Find the JSON object in the JS file
  match = re.search(r'=\s*(\{.*\})\s*;?\s*$', js_text, re.DOTALL)
  if not match:
    # Try alternate format
    match = re.search(r'(\{["\s]*[HG]\d+.*\})', js_text, re.DOTALL)
  if not match:
    print(f"  ⚠ Could not parse {prefix} dictionary JS — check file format")
    return {}

  try:
    raw = json.loads(match.group(1))
  except json.JSONDecodeError as e:
    print(f"  ⚠ JSON error in {prefix} dictionary: {e}")
    return {}

  out = {}
  for num_str, entry in raw.items():
    # Normalize key: H001 → H1, G0002 → G2
    num = str(int(re.sub(r'[^\d]','',num_str)))
    key = f"{prefix}{num}"
    out[key] = {
      "lemma": entry.get("lemma",""),
      "xlit":  entry.get("xlit",""),
      "pron":  entry.get("pron",""),
      "definition": entry.get("strongs_def", entry.get("kjv_def", entry.get("def",""))),
      "pos":   entry.get("pos",""),
    }
  return out

def parse_usfm_file(filepath, book_id):
  """
  Parse a USFM file with Strong's tags.
  
  STEPBible format uses USFM 3 word attributes:
    \\w word|strong="H1234"\\w*
    \\w word|strong="G5678"\\w*
  
  Some files may use older format:
    \\w word\\w* with separate \\str H1234 \\str*
  """
  text = Path(filepath).read_text(encoding='utf-8', errors='replace')
  
  chapters = {}
  current_ch = None
  current_v = None
  
  lines = text.split('\n')
  i = 0
  
  while i < len(lines):
    line = lines[i].strip()
    
    # Chapter marker: \c 1
    ch_match = re.match(r'\\c\s+(\d+)', line)
    if ch_match:
      current_ch = int(ch_match.group(1))
      current_v = None
      i += 1
      continue
    
    # Verse marker: \v 1 text...
    v_match = re.match(r'\\v\s+(\d+)\s*(.*)', line)
    if v_match and current_ch is not None:
      current_v = int(v_match.group(1))
      verse_text = v_match.group(2)
      
      # Verse may continue on subsequent lines until next \v or \c
      j = i + 1
      while j < len(lines):
        next_line = lines[j].strip()
        if re.match(r'\\[vc]\s+\d+', next_line):
          break
        if re.match(r'\\[pqm]', next_line):
          verse_text += ' ' + next_line
        elif next_line and not next_line.startswith('\\s') and not next_line.startswith('\\d'):
          verse_text += ' ' + next_line
        j += 1
      
      # Parse word tokens from verse text
      tokens = parse_verse_tokens(verse_text)
      if tokens:
        if current_ch not in chapters:
          chapters[current_ch] = {}
        chapters[current_ch][current_v] = tokens
      
      i = j
      continue
    
    i += 1
  
  return chapters

def parse_verse_tokens(text):
  """
  Parse USFM verse text into word tokens.
  
  Handles:
  - \\w word|strong="H1234"\\w*
  - \\w word|strong="H1234" x-morph="..."\\w*
  - plain words (no Strong's)
  - punctuation
  """
  tokens = []
  
  # Remove USFM tags we don't need
  # Remove notes: \f ... \f*  \x ... \x*
  text = re.sub(r'\\f\s.*?\\f\*', '', text, flags=re.DOTALL)
  text = re.sub(r'\\x\s.*?\\x\*', '', text, flags=re.DOTALL)
  # Remove formatting markers
  text = re.sub(r'\\(add|nd|wj|tl|sc|it|bd|bdit|em|qt)\*?', '', text)
  
  # Try USFM 3 \w word|attr="val"\w* format
  w_pattern = re.compile(r'\\w\s+(.*?)\|([^\\]*?)\\w\*|\\w\s+(.*?)\\w\*', re.DOTALL)
  
  pos = 0
  last_end = 0
  
  for m in w_pattern.finditer(text):
    # Any plain text before this \w token?
    gap = text[last_end:m.start()].strip()
    if gap:
      gap_tokens = tokenize_plain(gap)
      tokens.extend(gap_tokens)
    
    if m.group(1):  # Has attributes
      word_part = m.group(1).strip()
      attrs = m.group(2)
      strong_match = re.search(r'strong="([HG]\d+(?:[a-z])?)"', attrs)
      strongs = None
      if strong_match:
        raw_s = strong_match.group(1)
        # Normalize: H001 → H1
        s_num = re.sub(r'^([HG])0*(\d+)([a-zA-Z]?)$', lambda x: x.group(1)+str(int(x.group(2)))+x.group(3), raw_s)
        strongs = s_num
      
      # Word may have trailing punctuation
      punct_match = re.match(r"^(.*?)([,;:.!?\"'""'']+)$", word_part)
      if punct_match:
        w, p = punct_match.group(1).strip(), punct_match.group(2)
        if w:
          tok = {"w": w}
          if strongs: tok["s"] = strongs
          if p: tok["p"] = p
          tokens.append(tok)
      else:
        if word_part:
          tok = {"w": word_part}
          if strongs: tok["s"] = strongs
          tokens.append(tok)
    else:  # No attributes
      word_part = (m.group(3) or '').strip()
      if word_part:
        tokens.extend(tokenize_plain(word_part))
    
    last_end = m.end()
  
  # Any remaining text
  remainder = text[last_end:].strip()
  if remainder:
    tokens.extend(tokenize_plain(remainder))
  
  # If no \w tags found at all, treat as plain text
  if not any(t.get('s') for t in tokens) and not tokens:
    tokens = tokenize_plain(text)
  
  # Filter empty tokens
  return [t for t in tokens if t.get('w') or t.get('p')]

def tokenize_plain(text):
  """Tokenize plain text without Strong's markup"""
  tokens = []
  # Remove remaining USFM tags
  text = re.sub(r'\\[a-z]+\d*\*?', ' ', text)
  # Tokenize
  for m in re.finditer(r"([A-Za-z''\u2019]+(?:-[A-Za-z]+)*)([,;:.!?\"'""'']*)", text):
    word = m.group(1)
    punct = m.group(2)
    if word:
      tok = {"w": word}
      if punct: tok["p"] = punct
      tokens.append(tok)
  return tokens

# ── MAIN ──────────────────────────────────────────────────────

def main():
  usfm_dir = Path('usfm')
  strongs_dir = Path('strongs')
  data_dir = Path('data')
  verses_dir = data_dir / 'verses'
  verses_dir.mkdir(parents=True, exist_ok=True)

  # ── Process Strong's dictionaries ──────────────────────────
  print('Processing Strong\'s dictionaries...')
  all_strongs = {}

  heb_file = strongs_dir / 'strongs-hebrew-dictionary.js'
  grk_file = strongs_dir / 'strongs-greek-dictionary.js'

  if heb_file.exists():
    raw = heb_file.read_text(encoding='utf-8')
    parsed = parse_strongs_js(raw, 'H')
    all_strongs.update(parsed)
    print(f'  Hebrew: {len(parsed):,} entries')
  else:
    print(f'  ⚠ Not found: {heb_file}')

  if grk_file.exists():
    raw = grk_file.read_text(encoding='utf-8')
    parsed = parse_strongs_js(raw, 'G')
    all_strongs.update(parsed)
    print(f'  Greek:  {len(parsed):,} entries')
  else:
    print(f'  ⚠ Not found: {grk_file}')

  if all_strongs:
    out_path = data_dir / 'strongs.json'
    with open(out_path, 'w', encoding='utf-8') as f:
      json.dump(all_strongs, f, ensure_ascii=False, separators=(',',':'))
    size_kb = out_path.stat().st_size // 1024
    print(f'  ✓ Wrote {len(all_strongs):,} entries → {out_path} ({size_kb} KB)')
  else:
    print('  No Strong\'s data written — place JS files in strongs/ directory')

  # ── Process USFM files ──────────────────────────────────────
  print('\nProcessing USFM files...')

  if not usfm_dir.exists():
    print(f'  ⚠ usfm/ directory not found — create it and add .usfm files')
    return

  usfm_files = sorted(usfm_dir.glob('*.usfm')) + sorted(usfm_dir.glob('*.USFM'))
  if not usfm_files:
    print('  ⚠ No .usfm files found in usfm/ directory')
    return

  all_verses = {}   # For combined tagged_verses.json
  book_count = 0
  verse_count = 0
  tagged_count = 0

  for fpath in usfm_files:
    book_id = detect_book_id(fpath)
    if not book_id:
      # Try reading \id tag from file
      try:
        head = fpath.read_text(encoding='utf-8', errors='replace')[:500]
        id_match = re.search(r'\\id\s+([A-Z1-9]{3})', head)
        if id_match:
          osis_id = id_match.group(1)
          book_id = BOOK_MAP.get(osis_id, osis_id)
      except:
        pass
    
    if not book_id:
      print(f'  ⚠ Could not detect book ID for {fpath.name} — skipping')
      continue

    try:
      chapters = parse_usfm_file(fpath, book_id)
    except Exception as e:
      print(f'  ✗ Error parsing {fpath.name}: {e}')
      continue

    if not chapters:
      print(f'  ⚠ No verses found in {fpath.name}')
      continue

    # Count tagged words
    book_tagged = 0
    book_verses = 0
    for ch_data in chapters.values():
      for verse_tokens in ch_data.values():
        book_verses += 1
        book_tagged += sum(1 for t in verse_tokens if t.get('s'))

    # Write per-book file
    out_path = verses_dir / f'{book_id}.json'
    with open(out_path, 'w', encoding='utf-8') as f:
      json.dump(chapters, f, ensure_ascii=False, separators=(',',':'))
    
    size_kb = out_path.stat().st_size // 1024
    print(f'  ✓ {book_id:5} {book_verses:4} verses  {book_tagged:5} tagged words  ({size_kb} KB)')
    
    all_verses[book_id] = chapters
    book_count += 1
    verse_count += book_verses
    tagged_count += book_tagged

  # Write combined file (used by app for initial load)
  if all_verses:
    combined_path = data_dir / 'tagged_verses.json'
    with open(combined_path, 'w', encoding='utf-8') as f:
      json.dump(all_verses, f, ensure_ascii=False, separators=(',',':'))
    size_kb = combined_path.stat().st_size // 1024
    print(f'\n✓ Combined: {book_count} books, {verse_count:,} verses, {tagged_count:,} tagged words')
    print(f'  Wrote → {combined_path} ({size_kb:,} KB)')
    
    if size_kb > 5000:
      print(f'\n  ⚠ Combined file is {size_kb} KB — consider switching to per-book lazy loading.')
      print(f'  See README for how to update index.html to load data/verses/BOOK.json on demand.')

  print(f'\nDone. Refresh your browser or re-deploy to GitHub Pages.')

if __name__ == '__main__':
  main()
