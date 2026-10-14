#!/usr/bin/env python
"""Live web console for the orchestrator <-> worker-agent bridge.

  python -I tools/console.py [--port 8765] [--open]

Shows bridge/chat.jsonl live (orchestrator / worker agents / you), the task board from bridge/TASKS.md, and lets you post messages.
Binds to 127.0.0.1 only.
"""
import argparse, json, os, re, sys, time, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CFG, CHAT_LOG as LOG, read_tasks  # noqa: E402

ORCH = CFG['orchestrator']
lock = threading.Lock()

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Singularity Bridge Console</title>
<style>
:root{--bg:#0f1115;--panel:#171a21;--line:#262b36;--fg:#e6e8ee;--dim:#8b93a7;--claude:#ff9a3c;--gem:#5bd68a;--user:#6cb4ff}
@media (prefers-color-scheme: light){:root{--bg:#f6f7fa;--panel:#fff;--line:#dfe3ec;--fg:#1b2030;--dim:#667089;--claude:#c25e00;--gem:#1c8a4a;--user:#1a67c4}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,Segoe UI,sans-serif;height:100vh;display:grid;grid-template-columns:300px 1fr;grid-template-rows:auto 1fr auto}
header{grid-column:1/3;display:flex;gap:12px;align-items:center;padding:10px 16px;border-bottom:1px solid var(--line);background:var(--panel)}
header h1{font-size:15px;margin:0}header .st{color:var(--dim);font-size:12px;margin-left:auto}
aside{border-right:1px solid var(--line);overflow:auto;padding:10px;background:var(--panel)}
aside h2{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);margin:8px 6px}
.task{padding:6px 8px;border-radius:6px;cursor:pointer;display:flex;justify-content:space-between;gap:8px;font-size:12.5px}
.task:hover,.task.sel{background:var(--line)}.badge{font-size:11px;padding:1px 6px;border-radius:9px;border:1px solid var(--line);color:var(--dim);white-space:nowrap}
.b-CLAIMED{color:var(--gem);border-color:var(--gem)}.b-REVIEW{color:var(--claude);border-color:var(--claude)}.b-DONE{color:var(--user);border-color:var(--user)}
main{overflow:auto;padding:14px 18px;scroll-behavior:smooth}
.msg{max-width:860px;margin:0 0 10px;padding:8px 12px;border-radius:10px;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--dim)}
.msg.claude{border-left-color:var(--claude)}.msg.user{border-left-color:var(--user)}.msg.agent{border-left-color:var(--gem)}
.meta{font-size:11.5px;color:var(--dim);margin-bottom:3px}.meta b{color:var(--fg)}
.msg.claude .meta b{color:var(--claude)}.msg.agent .meta b{color:var(--gem)}.msg.user .meta b{color:var(--user)}
.txt{white-space:pre-wrap;word-wrap:anywhere}
footer{grid-column:1/3;display:flex;gap:8px;padding:10px 16px;border-top:1px solid var(--line);background:var(--panel)}
input,select,button{font:inherit;color:var(--fg);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:7px 9px}
#text{flex:1}button{cursor:pointer;background:var(--user);color:#fff;border:0}
@media(max-width:700px){body{grid-template-columns:1fr}aside{display:none}header,footer{grid-column:1}}
</style></head><body>
<header><h1>Singularity · orchestrator ↔ agents</h1><span class="st" id="st">…</span></header>
<aside><h2>Filter</h2><div class="task sel" data-t="">All messages</div><h2>Tasks in progress</h2><div id="tasks"></div></aside>
<main id="log"></main>
<footer><select id="to"></select><input id="task" placeholder="task (T011)" size="9"><input id="text" placeholder="Message from you…" autocomplete="off"><button id="send">Send</button></footer>
<script>
let last=0,filter='',names=new Set(['ORCH_NAME','all']);const log=document.getElementById('log');
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function cls(f){return f==='ORCH_NAME'?'claude':f==='user'?'user':'agent'}
function add(m){names.add(m.from);const d=document.createElement('div');d.className='msg '+cls(m.from);d.dataset.task=m.task||'';
 d.innerHTML=`<div class="meta"><b>${esc(m.from)}</b> → ${esc(m.to)}${m.task?' · '+esc(m.task):''} · #${m.id} · ${m.ts.slice(11)}</div><div class="txt">${esc(m.text)}</div>`;
 if(filter&&d.dataset.task!==filter)d.style.display='none';log.appendChild(d)}
async function poll(){try{const r=await fetch('/api/chat?since='+last);const a=await r.json();
 const atEnd=log.scrollHeight-log.scrollTop-log.clientHeight<80;a.forEach(m=>{last=Math.max(last,m.id);add(m)});
 if(a.length&&atEnd)log.scrollTop=log.scrollHeight;
 const sel=document.getElementById('to');const cur=sel.value;sel.innerHTML=[...names].filter(n=>n!=='user').map(n=>`<option>${n}</option>`).join('');if(cur)sel.value=cur;
 document.getElementById('st').textContent='online · messages: '+last}catch(e){document.getElementById('st').textContent='console offline'}}
async function tasks(){try{const a=await (await fetch('/api/tasks')).json();
 document.getElementById('tasks').innerHTML=a.map(t=>`<div class="task${filter===t.id?' sel':''}" data-t="${t.id}"><span>${t.id} ${esc(t.path)}</span><span class="badge b-${t.status.split(' ')[0]}">${esc(t.status.split(' ')[0])}</span></div>`).join('')||'<div class="task">none yet</div>'}catch(e){}}
document.addEventListener('click',e=>{const t=e.target.closest('.task');if(!t)return;filter=t.dataset.t||'';
 document.querySelectorAll('.task').forEach(x=>x.classList.toggle('sel',x.dataset.t===filter));
 [...log.children].forEach(c=>c.style.display=(!filter||c.dataset.task===filter)?'':'none');log.scrollTop=log.scrollHeight});
async function send(){const text=document.getElementById('text').value.trim();if(!text)return;
 await fetch('/api/post',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:'user',to:document.getElementById('to').value||'ORCH_NAME',task:document.getElementById('task').value.trim(),text})});
 document.getElementById('text').value='';poll()}
document.getElementById('send').onclick=send;document.getElementById('text').addEventListener('keydown',e=>{if(e.key==='Enter')send()});
poll();tasks();setInterval(poll,1000);setInterval(tasks,5000);
</script></body></html>"""


def load(since=0):
    out = []
    if os.path.exists(LOG):
        with open(LOG, encoding='utf8') as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    try:
                        m = json.loads(ln)
                    except ValueError:
                        continue
                    if m['id'] > since:
                        out.append(m)
    return out


def tasks():
    return [{'id': t['id'], 'path': t['scope'], 'status': t['status']} for t in read_tasks()
            if re.match(r'(CLAIMED|REVIEW|RETURNED|DONE)', t['status'])]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype='application/json; charset=utf-8'):
        b = body.encode('utf8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == '/':
            self._send(200, PAGE.replace('ORCH_NAME', ORCH), 'text/html; charset=utf-8')
        elif u.path == '/api/chat':
            since = int(parse_qs(u.query).get('since', ['0'])[0])
            self._send(200, json.dumps(load(since), ensure_ascii=False))
        elif u.path == '/api/tasks':
            self._send(200, json.dumps(tasks(), ensure_ascii=False))
        else:
            self._send(404, '{}')

    def do_POST(self):
        if urlparse(self.path).path != '/api/post':
            return self._send(404, '{}')
        n = int(self.headers.get('Content-Length', 0))
        d = json.loads(self.rfile.read(n).decode('utf8', errors='replace'))
        with lock:
            ms = load()
            mid = (ms[-1]['id'] + 1) if ms else 1
            m = {'id': mid, 'ts': time.strftime('%Y-%m-%d %H:%M:%S'), 'from': 'user', 'to': d.get('to') or ORCH,
                 'task': d.get('task', ''), 'text': d['text'][:4000]}
            with open(LOG, 'a', encoding='utf8') as f:
                f.write(json.dumps(m, ensure_ascii=False) + '\n')
        self._send(200, json.dumps(m, ensure_ascii=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--open', action='store_true')
    a = ap.parse_args()
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), H)
    url = f'http://127.0.0.1:{a.port}/'
    print('console on', url, flush=True)
    if a.open:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    srv.serve_forever()
