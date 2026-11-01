// Confronta digests.json con la versione precedente e manda una notifica Web Push.
const fs = require('fs');
const { execSync } = require('child_process');
const webpush = require('web-push');

const PUBLIC = 'BAd_Yge3vtG-3XPUfoydSh-DlLhE0g-xSr6C7RrNZmKU47zaxCB0Kl_kYU2mSegxN_rUBrl52iWoEB5c7iJaekw';
const NAMES = { evening: 'Evening', canzoni: 'Le canzoni', charlie: 'Charlie', streaming: 'Dicono che è bello al cinema', sunday: 'Sunday Post' };

if (!process.env.VAPID_PRIVATE || !process.env.PUSH_SUB) { console.log('Notifiche non configurate: mancano i segreti.'); process.exit(0); }

const now = JSON.parse(fs.readFileSync('data/digests.json', 'utf8'));
let before = { editions: [] };
try { before = JSON.parse(execSync('git show HEAD~1:data/digests.json', { encoding: 'utf8' })); } catch (e) {}
const old = new Set((before.editions || []).map((e) => e.id));
const fresh = (now.editions || []).filter((e) => !old.has(e.id));

let body;
if (fresh.length) {
  const names = [...new Set(fresh.map((e) => NAMES[e.source] || e.source))];
  body = 'Nuovi riassunti: ' + names.join(', ') + '.';
} else {
  console.log('Nessuna newsletter nuova: niente notifica.'); process.exit(0);
}
const payload = JSON.stringify({ title: 'Harmoreader', body, url: './#riassunto' });

webpush.setVapidDetails('mailto:noreply@harmoreader.invalid', PUBLIC, process.env.VAPID_PRIVATE);
const subs = [].concat(JSON.parse(process.env.PUSH_SUB));
Promise.all(subs.map((s) => webpush.sendNotification(s, payload, { TTL: 43200, urgency: 'normal' })
  .then((r) => console.log('Inviata:', r.statusCode))
  .catch((e) => { console.error('Errore:', e.statusCode, e.body); process.exitCode = 1; })));
