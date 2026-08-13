from __future__ import annotations
import hashlib, json, os, re, secrets, sqlite3, subprocess, sys, threading, time, uuid, webbrowser
from pathlib import Path
import neo_hud_runtime
try:
    import psutil
except Exception:
    psutil=None
try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse
    import uvicorn
    WEB_OK=True
except Exception:
    WEB_OK=False

ROOT=Path(__file__).resolve().parent
DATA=Path.home()/'.jarvis_neo'; DATA.mkdir(exist_ok=True)
PLUGINS=ROOT/'plugins'; PLUGINS.mkdir(exist_ok=True)
USER_PLUGINS=DATA/'plugins'; USER_PLUGINS.mkdir(exist_ok=True)
DB=DATA/'neo_platform.db'; DEVICES=DATA/'authorized_devices.json'; SECURITY=DATA/'security.json'
PORT=int(os.getenv('JARVIS_NEO_PORT','8890'))

def rjson(p,d):
    try:return json.loads(p.read_text(encoding='utf8')) if p.exists() else d
    except:return d

def wjson(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8')

class Store:
    def __init__(self):
        with sqlite3.connect(DB) as c:
            c.execute('CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,ts REAL,kind TEXT,message TEXT,level TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY,ts REAL,kind TEXT,content TEXT)')
    def event(self,k,m,l='INFO'):
        with sqlite3.connect(DB) as c:c.execute('INSERT INTO events(ts,kind,message,level) VALUES(?,?,?,?)',(time.time(),k,m,l))
    def events(self):
        with sqlite3.connect(DB) as c:r=c.execute('SELECT id,ts,kind,message,level FROM events ORDER BY id DESC LIMIT 200').fetchall()
        return [dict(id=x[0],ts=x[1],kind=x[2],message=x[3],level=x[4]) for x in r]
    def remember(self,k,t):
        with sqlite3.connect(DB) as c:c.execute('INSERT INTO memories(ts,kind,content) VALUES(?,?,?)',(time.time(),k,t))
    def memories(self,q=''):
        with sqlite3.connect(DB) as c:r=c.execute('SELECT id,ts,kind,content FROM memories WHERE content LIKE ? ORDER BY id DESC LIMIT 100',(f'%{q}%',)).fetchall()
        return [dict(id=x[0],ts=x[1],kind=x[2],content=x[3]) for x in r]
    def forget(self,i):
        with sqlite3.connect(DB) as c:c.execute('DELETE FROM memories WHERE id=?',(i,))

class PluginAPI:
    def __init__(self,p,pid,permissions):self.p,self.pid,self.permissions=p,pid,set(permissions)
    def require(self,x):
        if x not in self.permissions:raise PermissionError(f'Permission refusée: {x}')
    def notify(self,x):self.p.store.event('plugin',f'{self.pid}: {x}')
    def remember(self,x):self.p.store.remember('plugin',x)
    def system(self):self.require('system');return self.p.system()
    def search(self,x):self.require('network');return self.p.search(x)
    def open(self,x):self.require('files');return self.p.open_path(x)

class Plugins:
    ALLOWED={'network','system','files','camera','microphone','keyboard','clipboard'}
    def __init__(self,p):self.p=p;self.data={};self.scan()
    def scan(self):
        for root in (PLUGINS,USER_PLUGINS):
            for d in root.iterdir():
                m=d/'manifest.json'; code=d/'plugin.py'
                if not d.is_dir() or not m.exists() or not code.exists():continue
                try:
                    x=json.loads(m.read_text(encoding='utf8')); pid=str(x.get('id') or d.name)
                    self.data[pid]={'id':pid,'path':str(d),'manifest':x,'permissions':[q for q in x.get('permissions',[]) if q in self.ALLOWED],'module':self.data.get(pid,{}).get('module'),'active':self.data.get(pid,{}).get('active',False),'error':None}
                except Exception as e:self.p.store.event('plugin',f'Manifest {d.name}: {e}','ERROR')
        return self.list()
    def list(self):return[{k:v for k,v in x.items() if k!='module'} for x in self.data.values()]
    def load(self,pid):
        p=self.data[pid]
        try:
            import importlib.util
            spec=importlib.util.spec_from_file_location('jarvis_'+re.sub(r'\W','_',pid),str(Path(p['path'])/'plugin.py'))
            mod=importlib.util.module_from_spec(spec);mod.jarvis=PluginAPI(self.p,pid,p['permissions']);spec.loader.exec_module(mod)
            if hasattr(mod,'on_load'):mod.on_load(mod.jarvis)
            p.update(module=mod,active=True,error=None);self.p.store.event('plugin',f'{pid} chargé');return True
        except Exception as e:p.update(active=False,error=str(e));self.p.store.event('plugin',f'{pid}: {e}','ERROR');return False
    def unload(self,pid):
        p=self.data.get(pid)
        if not p:return False
        try:
            if p.get('module') and hasattr(p['module'],'on_unload'):p['module'].on_unload()
        except Exception as e:p['error']=str(e)
        p.update(module=None,active=False);self.p.store.event('plugin',f'{pid} déchargé');return True
    def reload(self,pid):self.unload(pid);return self.load(pid)
    def commands(self):
        out={}
        for pid,p in self.data.items():
            if p['active'] and p['module']:
                for n,f in getattr(p['module'],'COMMANDS',{}).items():out[f'{pid}:{n}']=f
        return out

class Agent:
    def __init__(self,p):self.p=p;self.stop_event=threading.Event()
    def stop(self):self.stop_event.set();return True
    def run(self,text,confirmed=False):
        text=str(text).strip();low=text.lower()
        sensitive=any(x in low for x in ('supprime','efface','éteins','eteins','shutdown','redémarre','redemarre','ferme'))
        if sensitive and not confirmed:return {'ok':False,'confirmation_required':True,'message':'Confirmation requise.'}
        m=re.match(r'ouvre(?:z)?\s+(?:le\s+)?(.+)',text,re.I)
        if m:return self.p.open_path(m.group(1).strip())
        return self.p.dispatch(text)

class Mobile:
    def __init__(self,p):self.p=p;self.devices=rjson(DEVICES,{});self.code=None;self.expires=0;self.clients=set()
    def new_code(self):self.code=f'{secrets.randbelow(1000000):06d}';self.expires=time.time()+300;return self.code
    def pair(self,code,name):
        if not self.code or time.time()>self.expires or not secrets.compare_digest(str(code),self.code):raise PermissionError('Code invalide ou expiré')
        did=str(uuid.uuid4());token=secrets.token_urlsafe(32);self.devices[did]={'name':str(name)[:60],'token':token,'revoked':False,'created':time.time()};wjson(DEVICES,self.devices);self.code=None;self.p.store.event('mobile',f'Appareil autorisé: {name}');return {'device_id':did,'token':token}
    def auth(self,t):return any(x.get('token')==t and not x.get('revoked') for x in self.devices.values())
    def revoke(self,d):
        if d in self.devices:self.devices[d]['revoked']=True;wjson(DEVICES,self.devices);self.p.store.event('security',f'Appareil révoqué: {d}')

class Platform:
    VERSION='4.0.0'
    def __init__(self):
        self.store=Store();self.assistant=None;self.plugins=Plugins(self);self.agent=Agent(self);self.mobile=Mobile(self);self.app=FastAPI(title='J.A.R.V.I.S. NEO') if WEB_OK else None
        if self.app:self.routes()
    def system(self):
        if not psutil:return {'available':False}
        b=psutil.sensors_battery();root=Path.home().anchor or '/'
        return {'cpu':psutil.cpu_percent(),'ram':psutil.virtual_memory().percent,'disk':psutil.disk_usage(root).percent,'battery':b.percent if b else None,'uptime':int(time.time()-psutil.boot_time()),'processes':len(psutil.pids())}
    def open_path(self,target):
        p=Path(os.path.expandvars(os.path.expanduser(str(target))))
        if not p.is_absolute():p=next((x for x in (Path.cwd()/p,Path.home()/p) if x.exists()),p)
        if not p.exists():return {'ok':False,'error':f'Introuvable: {target}'}
        try:
            if sys.platform=='win32':os.startfile(str(p))
            elif sys.platform=='darwin':subprocess.Popen(['open',str(p)])
            else:subprocess.Popen(['xdg-open',str(p)])
            return {'ok':True,'path':str(p)}
        except Exception as e:return {'ok':False,'error':str(e)}
    def dispatch(self,text):
        if self.assistant is None:return 'Commande reçue.'
        for n in ('processor','command_processor','core'):
            o=getattr(self.assistant,n,None)
            if o and hasattr(o,'process'):return o.process(text)
        if hasattr(self.assistant,'process_command'):return self.assistant.process_command(text)
        return 'Processeur J.A.R.V.I.S. introuvable.'
    def search(self,q):
        try:
            import requests
            from bs4 import BeautifulSoup
            s=BeautifulSoup(requests.get('https://html.duckduckgo.com/html/',params={'q':q},headers={'User-Agent':'JARVIS-NEO'},timeout=8).text,'html.parser')
            return [{'title':a.get_text(' ',strip=True),'url':a.get('href'),'snippet':r.get_text(' ',strip=True) if r else ''} for x in s.select('.result')[:8] if (a:=x.select_one('.result__a')) and (r:=x.select_one('.result__snippet'))]
        except Exception as e:return [{'error':str(e)}]
    def routes(self):
        @self.app.get('/',response_class=HTMLResponse)
        async def home():return DASHBOARD
        @self.app.get('/api/system')
        async def system():return self.system()
        @self.app.get('/api/plugins')
        async def plugins():return self.plugins.scan()
        @self.app.post('/api/plugins/{pid}/{action}')
        async def plugin(pid,action):
            if action not in ('load','unload','reload'):raise HTTPException(400,'Action invalide')
            return {'ok':getattr(self.plugins,action)(pid)}
        @self.app.post('/api/pair-code')
        async def pair_code():return {'code':self.mobile.new_code(),'expires_in':300}
        @self.app.post('/api/pair')
        async def pair(b:dict):
            try:return self.mobile.pair(b.get('code'),b.get('name','Téléphone'))
            except PermissionError as e:raise HTTPException(403,str(e))
        @self.app.get('/api/devices')
        async def devices():return [{'id':k,'name':v['name'],'revoked':v.get('revoked',False)} for k,v in self.mobile.devices.items()]
        @self.app.post('/api/devices/{did}/revoke')
        async def revoke(did,b:dict):
            if not self.mobile.auth(b.get('token')):raise HTTPException(401,'Non autorisé')
            self.mobile.revoke(did);return {'ok':True}
        @self.app.post('/api/agent')
        async def agent(b:dict):return self.agent.run(b.get('instruction',''),bool(b.get('confirmed')))
        @self.app.post('/api/agent/stop')
        async def stop():return {'ok':self.agent.stop()}
        @self.app.get('/api/memory')
        async def memory(q:str=''):return self.store.memories(q)
        @self.app.delete('/api/memory/{mid}')
        async def forget(mid:int):self.store.forget(mid);return {'ok':True}
        @self.app.get('/api/events')
        async def events():return self.store.events()
        @self.app.get('/api/search')
        async def search(q:str):return self.search(q)
        @self.app.post('/api/command')
        async def command(b:dict):
            if not self.mobile.auth(b.get('token')):raise HTTPException(401,'Non autorisé')
            return self.agent.run(b.get('command',''),bool(b.get('confirmed')))
        @self.app.websocket('/ws')
        async def ws(s:WebSocket):
            if not self.mobile.auth(s.query_params.get('token','')):await s.close(code=1008);return
            await s.accept();self.mobile.clients.add(s)
            try:
                while True:await s.receive_text()
            except WebSocketDisconnect:pass
            finally:self.mobile.clients.discard(s)
    def start(self):
        if not WEB_OK:return False
        threading.Thread(target=lambda:uvicorn.run(self.app,host='0.0.0.0',port=PORT,log_level='warning'),daemon=True).start();return True

DASHBOARD='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>J.A.R.V.I.S. NEO</title><style>body{margin:0;background:#020617;color:#dffcff;font:15px Segoe UI,Arial}header{padding:18px;border-bottom:1px solid #16445b}nav{display:flex;gap:6px;overflow:auto;padding:10px;border-bottom:1px solid #16445b}button{background:#071b32;color:#dffcff;border:1px solid #08718c;border-radius:7px;padding:9px;margin:3px}.p{display:none;padding:20px;max-width:1100px;margin:auto}.on{display:block}.card{background:#050d1f;border:1px solid #12354a;border-radius:10px;padding:15px;margin:9px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}.v{font-size:26px;color:#00f3ff}textarea,input{width:100%;padding:10px;background:#020817;color:#dffcff;border:1px solid #16445b;border-radius:7px;box-sizing:border-box}</style><header><b>◈ J.A.R.V.I.S. NEO</b> — v4.0</header><nav><button onclick="S('home')">🏠 Accueil</button><button onclick="S('chat')">💬 Chat</button><button onclick="S('plugins')">🧩 Plugins</button><button onclick="S('devices')">📱 Appareils</button><button onclick="S('agent')">🤖 Agent</button><button onclick="S('memory')">🧠 Mémoire</button><button onclick="S('security')">🛡️ Sécurité</button><button onclick="S('settings')">⚙️ Paramètres</button></nav><main>
<section id="home" class="p on"><h2>Accueil</h2><div class="grid"><div class="card">CPU<div id="cpu" class="v">—</div></div><div class="card">RAM<div id="ram" class="v">—</div></div><div class="card">Disque<div id="disk" class="v">—</div></div><div class="card">Batterie<div id="bat" class="v">—</div></div></div><pre id="events"></pre></section>
<section id="chat" class="p"><h2>Chat</h2><textarea id="cq" rows="4" placeholder="Commande..."></textarea><button onclick="agent('cq','co',false)">Envoyer</button><pre id="co"></pre></section>
<section id="plugins" class="p"><h2>Plugins</h2><div id="pl"></div></section>
<section id="devices" class="p"><h2>Appareils</h2><button onclick="pc()">Générer un code</button><h1 id="code">—</h1><div id="dev"></div></section>
<section id="agent" class="p"><h2>Mode Agent</h2><textarea id="aq" rows="4" placeholder="Ouvre un programme ou un fichier..."></textarea><button onclick="agent('aq','ao',false)">Exécuter</button><button onclick="agent('aq','ao',true)">Confirmer</button><button onclick="fetch('/api/agent/stop',{method:'POST'})">🛑 Arrêter</button><pre id="ao"></pre></section>
<section id="memory" class="p"><h2>Mémoire</h2><input id="mq" placeholder="Rechercher"><button onclick="mem()">Rechercher</button><div id="ml"></div></section>
<section id="security" class="p"><h2>Sécurité</h2><div class="card">Journal d'événements, PIN et appareils autorisés sont centralisés ici.</div></section><section id="settings" class="p"><h2>Paramètres</h2><div class="card">Serveur mobile: port '''+str(PORT)+''' — REST + WebSocket<br>Plugins: ./plugins et ~/.jarvis_neo/plugins</div></section></main><script>const J=x=>fetch(x).then(r=>r.json());function S(x){document.querySelectorAll('.p').forEach(e=>e.classList.remove('on'));document.getElementById(x).classList.add('on');if(x==='plugins')pl();if(x==='devices')dev();if(x==='memory')mem()}async function ref(){let s=await J('/api/system');cpu.textContent=(s.cpu??'—')+'%';ram.textContent=(s.ram??'—')+'%';disk.textContent=(s.disk??'—')+'%';bat.textContent=s.battery==null?'—':s.battery+'%';events.textContent=(await J('/api/events')).map(e=>new Date(e.ts*1000).toLocaleTimeString()+' '+e.level+' '+e.kind+' — '+e.message).join('\n')}async function pl(){let a=await J('/api/plugins');pl.innerHTML=a.map(p=>'<div class=card><b>'+((p.manifest||{}).name||p.id)+'</b> v'+((p.manifest||{}).version||'?')+'<br>'+((p.manifest||{}).description||'')+'<br>'+(p.active?'🟢 Actif':'⚪ Inactif')+'<br>Permissions: '+(p.permissions||[]).join(', ')+'<br><button onclick="P(\''+p.id+'\',\'load\')">Charger</button><button onclick="P(\''+p.id+'\',\'unload\')">Décharger</button><button onclick="P(\''+p.id+'\',\'reload\')">Recharger</button>'+(p.error?'<pre>'+p.error+'</pre>':'')+'</div>').join('')}async function P(i,a){await fetch('/api/plugins/'+encodeURIComponent(i)+'/'+a,{method:'POST'});pl()}async function pc(){code.textContent=(await fetch('/api/pair-code',{method:'POST'}).then(r=>r.json())).code}async function dev(){dev.innerHTML=(await J('/api/devices')).map(d=>'<div class=card>'+d.name+' — '+(d.revoked?'❌ Révoqué':'🟢 Autorisé')+'</div>').join('')}async function agent(i,o,c){let x=await fetch('/api/agent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({instruction:document.getElementById(i).value,confirmed:c})}).then(r=>r.json());document.getElementById(o).textContent=JSON.stringify(x,null,2);ref()}async function mem(){let a=await J('/api/memory?q='+encodeURIComponent(mq.value));ml.innerHTML=a.map(m=>'<div class=card><b>'+m.kind+'</b><p>'+m.content+'</p><button onclick="fetch(\'/api/memory/'+m.id+'\',{method:\'DELETE\'}).then(mem)">Supprimer</button></div>').join('')}ref();setInterval(ref,3000)</script></html>'''

def main():
    p=Platform();p.start()
    try:
        import assistant
        p.assistant=assistant
        p.store.event('system','Plateforme NEO v4 démarrée')       
        neo_hud_runtime.main()
    except Exception as e:
        p.store.event('system',f'Erreur assistant.py: {e}','ERROR')
        if WEB_OK:
            webbrowser.open(f'http://127.0.0.1:{PORT}')
            while True:time.sleep(60)
        raise
if __name__=='__main__':main()
