# Genera l'audio (voce neurale Microsoft via edge-tts) delle uscite recenti di data/digests.json.
# Crea audio/<id>.mp3 per quelle che non l'hanno, toglie quelle vecchie e scrive audio/index.json.
import asyncio, json, os, re, sys, datetime
import edge_tts

VOICE = os.environ.get('VOICE', 'it-IT-IsabellaNeural')
KEEP_DAYS = 30
LINK = re.compile(r'\[([^\]]+)\]\([^)]*\)')

def plain(t):
    return re.sub(r'\*\*(.+?)\*\*', r'\1', LINK.sub(r'\1', t or ''))

def text_of(e):
    t = [e['title'] + '.']
    if e.get('song'):
        t.append('%s, di %s.' % (e['song']['title'], e['song']['artist']))
    elif e.get('intro'):
        t.append(e['intro'])
    t += [plain(p) for p in e.get('paragraphs', [])]
    for s in e.get('sections', []):
        if s.get('heading'):
            t.append(s['heading'] + '.')
        t += [it['text'] for it in s.get('items', [])]
        t += [plain(p) for p in s.get('paragraphs', [])]
    return '\n\n'.join(x for x in t if x)

async def make(e, path):
    last = None
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text_of(e), VOICE, rate='+0%').save(path)
            if os.path.getsize(path) > 2000:
                return True
        except Exception as ex:  # rete o servizio non disponibile
            last = ex
            await asyncio.sleep(3 * (attempt + 1))
    print('Audio non generato per', e['id'], last, file=sys.stderr)
    if os.path.exists(path):
        os.remove(path)
    return False

async def main():
    d = json.load(open('data/digests.json', encoding='utf8'))
    os.makedirs('audio', exist_ok=True)
    limit = (datetime.date.today() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    wanted = [e for e in d['editions'] if e['date'] >= limit]
    ids = []
    for e in wanted:
        path = 'audio/%s.mp3' % e['id']
        if os.path.exists(path) or await make(e, path):
            ids.append(e['id'])
    for f in os.listdir('audio'):
        if f.endswith('.mp3') and f[:-4] not in ids:
            os.remove(os.path.join('audio', f))
    json.dump({'voice': VOICE, 'ids': ids}, open('audio/index.json', 'w'), indent=1)
    print('Audio disponibili:', len(ids))

asyncio.run(main())
