# Genera l'audio (voce neurale Microsoft via edge-tts) delle uscite recenti di data/digests.json.
# Crea audio/<id>.mp3 per quelle che non l'hanno, toglie quelle vecchie e scrive audio/index.json.
import asyncio, json, os, re, shutil, subprocess, sys, datetime
import edge_tts

VOICE = os.environ.get('VOICE', 'it-IT-IsabellaNeural')
KEEP_DAYS = 14
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

def shrink(path):
    # voce parlata: mono a 32 kbit/s basta e dimezza quasi il peso del file
    if not shutil.which('ffmpeg'):
        return
    tmp = path + '.tmp.mp3'
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', path, '-ac', '1', '-b:a', '32k', tmp])
    if r.returncode == 0 and os.path.getsize(tmp) > 2000:
        os.replace(tmp, path)
    elif os.path.exists(tmp):
        os.remove(tmp)

async def make(e, path):
    last = None
    for attempt in range(3):
        try:
            await asyncio.wait_for(edge_tts.Communicate(text_of(e), VOICE, rate='+0%').save(path), timeout=120)
            if os.path.getsize(path) > 2000:
                shrink(path)
                print('Creato', path, os.path.getsize(path), flush=True)
                return True
        except BaseException as ex:  # rete, blocco del servizio o tempo scaduto
            last = repr(ex)
            print('Tentativo', attempt + 1, 'fallito per', e['id'], last, flush=True)
            if isinstance(ex, (KeyboardInterrupt, SystemExit)):
                raise
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
    maxn = int(os.environ.get('MAX_NEW', '0')) or None
    made = 0
    fails = 0
    ids = []
    for e in wanted:
        path = 'audio/%s.mp3' % e['id']
        if os.path.exists(path):
            ids.append(e['id'])
        elif (maxn is None or made < maxn) and fails < 3:
            if await make(e, path):
                ids.append(e['id']); made += 1
            else:
                fails += 1
    for f in os.listdir('audio'):
        if f.endswith('.mp3') and f[:-4] not in ids:
            os.remove(os.path.join('audio', f))
    json.dump({'voice': VOICE, 'ids': ids}, open('audio/index.json', 'w'), indent=1)
    print('Audio disponibili:', len(ids))

asyncio.run(main())
