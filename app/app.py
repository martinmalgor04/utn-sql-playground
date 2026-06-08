from flask import Flask, request, jsonify, render_template_string, Response
import psycopg2
import psycopg2.extras
import os
import re

app = Flask(__name__)

# Credenciales admin (para setup inicial y local)
ADMIN_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": 5432,
    "dbname": os.getenv("DB_NAME", "utn_bd"),
    "user": os.getenv("DB_ADMIN_USER", "admin"),
    "password": os.getenv("DB_ADMIN_PASS", "admin"),
}

# Credenciales para ejecutar queries del usuario (readonly en prod, admin en local)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": 5432,
    "dbname": os.getenv("DB_NAME", "utn_bd"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASS", "admin"),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def setup_readonly_user():
    """Crea el usuario readonly si no existe. Corre al iniciar la app."""
    readonly_user = os.getenv("DB_USER", "admin")
    readonly_pass = os.getenv("DB_PASS", "admin")
    if readonly_user == "admin":
        return  # modo local, no hace falta crear nada
    try:
        conn = psycopg2.connect(**ADMIN_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        # Crear usuario si no existe; si existe, sincronizar la contraseña
        cur.execute(f"SELECT 1 FROM pg_roles WHERE rolname = %s", (readonly_user,))
        if not cur.fetchone():
            cur.execute(f"CREATE USER {readonly_user} WITH PASSWORD %s", (readonly_pass,))
            print(f"[setup] Usuario '{readonly_user}' creado.")
        else:
            cur.execute(f"ALTER USER {readonly_user} WITH PASSWORD %s", (readonly_pass,))
            print(f"[setup] Contraseña de '{readonly_user}' sincronizada.")
        cur.execute(f"GRANT CONNECT ON DATABASE {ADMIN_CONFIG['dbname']} TO {readonly_user}")
        cur.execute(f"GRANT USAGE ON SCHEMA public TO {readonly_user}")
        cur.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {readonly_user}")
        cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {readonly_user}")
        cur.close()
        conn.close()
        print(f"[setup] Permisos SELECT otorgados a '{readonly_user}'.")
    except Exception as e:
        print(f"[setup] Error configurando usuario readonly: {e}")

BLOCKED_KEYWORDS = ['drop', 'delete', 'update', 'insert', 'truncate', 'alter', 'create', 'grant', 'revoke']

@app.route("/query", methods=["POST"])
def query():
    sql = (request.json or {}).get("sql", "").strip()
    if not sql:
        return jsonify({"error": "SQL vacío"}), 400
    sql_lower = sql.lower()
    for kw in BLOCKED_KEYWORDS:
        # chequear palabra completa (no substring: "selection" no debe bloquearse)
        if re.search(r'\b' + kw + r'\b', sql_lower):
            return jsonify({"error": f"⚠️ Operación '{kw.upper()}' no permitida. Solo se aceptan consultas SELECT."}), 403
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql)
        if cur.description:
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]
            data = [dict(r) for r in rows]
        else:
            conn.commit()
            cols = []
            data = []
            return jsonify({"cols": [], "rows": [], "affected": cur.rowcount, "msg": f"{cur.rowcount} fila(s) afectadas"})
        cur.close()
        conn.close()
        return jsonify({"cols": cols, "rows": data, "count": len(data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/apunte")
def apunte():
    return Response(APUNTE_HTML, mimetype='text/html')

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>SQL Playground — BD UTN</title>
<style>
:root{--bg:#0f1117;--s1:#1a1d27;--s2:#222538;--bd:#2e3250;--acc:#6c63ff;--g:#43d9ad;--r:#ff6584;--y:#ffd166;--o:#ff9f43;--tx:#e2e4f0;--mu:#8b8fad;--cb:#12141e;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--tx);font-family:'Segoe UI',system-ui,sans-serif;display:flex;height:100vh;overflow:hidden;}

/* SIDEBAR */
#sidebar{width:310px;flex-shrink:0;background:var(--s1);border-right:1px solid var(--bd);display:flex;flex-direction:column;overflow:hidden;}
#sidebar-header{padding:1rem 1.2rem;border-bottom:1px solid var(--bd);flex-shrink:0;}
#sidebar-header h1{font-size:1rem;font-weight:800;background:linear-gradient(135deg,#6c63ff,#43d9ad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
#sidebar-header p{font-size:0.72rem;color:var(--mu);margin-top:0.2rem;}
#progress-bar-wrap{margin-top:0.6rem;}
#progress-bar-bg{height:4px;background:var(--bd);border-radius:2px;}
#progress-bar-fill{height:100%;background:linear-gradient(90deg,#6c63ff,#43d9ad);border-radius:2px;transition:width .3s;}
#progress-label{font-size:0.7rem;color:var(--mu);margin-top:0.3rem;}

#scenarios{flex:1;overflow-y:auto;padding:0.5rem 0;}

.sc-group{}
.sc-title{display:flex;align-items:center;gap:0.5rem;padding:0.5rem 1.2rem;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--mu);cursor:pointer;user-select:none;}
.sc-title:hover{color:var(--tx);}
.sc-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.sc-chevron{margin-left:auto;transition:transform .2s;}
.sc-group.closed .sc-chevron{transform:rotate(-90deg);}
.sc-group.closed .sc-exercises{display:none;}

.ex-btn{display:flex;align-items:flex-start;gap:0.6rem;width:100%;text-align:left;background:none;border:none;color:var(--tx);padding:0.45rem 1.2rem 0.45rem 1.4rem;cursor:pointer;font-size:0.8rem;line-height:1.4;transition:background .12s;}
.ex-btn:hover{background:rgba(255,255,255,.04);}
.ex-btn.active{background:rgba(108,99,255,.12);border-right:2px solid var(--acc);}
.ex-btn.done{opacity:.55;}
.ex-num{font-size:0.68rem;font-weight:700;padding:0.15rem 0.4rem;border-radius:4px;flex-shrink:0;margin-top:1px;}
.ex-check{margin-left:auto;flex-shrink:0;font-size:0.8rem;color:var(--g);}

/* MAIN */
#main{flex:1;display:flex;flex-direction:column;overflow:hidden;}

/* TOOLBAR */
#toolbar{padding:0.6rem 1rem;background:var(--s1);border-bottom:1px solid var(--bd);display:flex;align-items:center;gap:0.7rem;flex-shrink:0;}
#scenario-badge{font-size:0.72rem;font-weight:700;padding:0.2rem 0.7rem;border-radius:20px;background:rgba(108,99,255,.15);color:#a09aff;flex-shrink:0;}
#toolbar-spacer{flex:1;}
#btn-run{background:var(--acc);color:#fff;border:none;border-radius:7px;padding:0.45rem 1.1rem;font-size:0.82rem;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:0.4rem;white-space:nowrap;}
#btn-run:hover{background:#7c75ff;}
#btn-clear{background:none;border:1px solid rgba(255,100,100,.35);color:#ff7070;border-radius:7px;padding:0.45rem 0.8rem;font-size:0.82rem;cursor:pointer;transition:all .15s;}
#btn-clear:hover{background:rgba(255,100,100,.12);border-color:#ff7070;color:#ffaaaa;}
#btn-clear.flashing{background:rgba(255,100,100,.25);}
#btn-done{background:none;border:1px solid rgba(67,217,173,.3);color:var(--g);border-radius:7px;padding:0.45rem 0.8rem;font-size:0.82rem;cursor:pointer;}
#btn-done:hover{background:rgba(67,217,173,.1);}
#btn-apunte{background:none;border:1px solid rgba(255,209,102,.3);color:var(--y);border-radius:7px;padding:0.45rem 0.8rem;font-size:0.82rem;cursor:pointer;text-decoration:none;white-space:nowrap;}
#btn-apunte:hover{background:rgba(255,209,102,.1);}
kbd{background:var(--s2);border:1px solid var(--bd);border-radius:3px;padding:0.05rem 0.35rem;font-size:0.68rem;color:var(--mu);}

/* EXERCISE CONTEXT BOX */
#ex-context{flex-shrink:0;border-bottom:1px solid var(--bd);padding:0.8rem 1.2rem;display:none;gap:1rem;background:var(--s1);}
#ex-context.visible{display:flex;flex-direction:column;gap:0.5rem;}
#ex-enunciado{font-size:0.9rem;font-weight:600;color:var(--tx);line-height:1.4;}
#ex-enunciado-label{font-size:0.68rem;text-transform:uppercase;letter-spacing:.08em;color:var(--mu);margin-bottom:0.15rem;}
#ex-schema{font-family:'Cascadia Code','Fira Code',monospace;font-size:0.75rem;color:var(--mu);line-height:1.7;background:var(--cb);border:1px solid var(--bd);border-radius:7px;padding:0.6rem 0.9rem;}
#ex-schema .tname{color:#ffd166;font-weight:700;}
#ex-schema .tpk{color:#43d9ad;}
#ex-schema .tattr{color:#c9d1ff;}
#ex-schema .ttype{color:#8b8fad;}

/* EDITOR */
#editor-wrap{padding:0.7rem 1rem;flex-shrink:0;border-bottom:1px solid var(--bd);}
#sql-editor{width:100%;height:110px;background:var(--cb);border:1px solid var(--bd);border-radius:8px;color:#c9d1ff;font-family:'Cascadia Code','Fira Code',monospace;font-size:0.88rem;line-height:1.6;padding:0.8rem 1rem;resize:vertical;outline:none;min-height:60px;}
#sql-editor:focus{border-color:var(--acc);}

/* RESULT */
#result-wrap{flex:1;overflow:auto;padding:0 1rem 1rem;}
#result-meta{font-size:0.75rem;color:var(--mu);padding:0.6rem 0 0.4rem;display:flex;align-items:center;gap:0.6rem;}
#result-count{color:var(--g);font-weight:700;}
.err-box{background:rgba(255,101,132,.08);border:1px solid rgba(255,101,132,.25);border-radius:8px;padding:0.8rem 1rem;color:var(--r);font-family:monospace;font-size:0.82rem;margin-top:0.5rem;}
.ok-box{background:rgba(67,217,173,.08);border:1px solid rgba(67,217,173,.25);border-radius:8px;padding:0.8rem 1rem;color:var(--g);font-size:0.82rem;margin-top:0.5rem;}

#result-table-wrap{overflow:auto;border-radius:8px;border:1px solid var(--bd);}
table{width:100%;border-collapse:collapse;font-size:0.8rem;}
thead th{background:var(--s2);color:var(--mu);text-align:left;padding:0.5rem 0.8rem;font-size:0.72rem;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid var(--bd);white-space:nowrap;position:sticky;top:0;}
tbody tr:hover td{background:rgba(255,255,255,.03);}
td{padding:0.45rem 0.8rem;border-bottom:1px solid rgba(255,255,255,.04);white-space:nowrap;max-width:300px;overflow:hidden;text-overflow:ellipsis;}
td.null{color:var(--mu);font-style:italic;}

/* EMPTY STATE */
#empty{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--mu);gap:0.5rem;padding:2rem;}
#empty .ico{font-size:2.5rem;}
#empty p{font-size:0.85rem;}
#empty small{font-size:0.75rem;color:#555;}
</style>
</head>
<body>

<!-- SIDEBAR -->
<nav id="sidebar">
  <div id="sidebar-header">
    <h1>SQL Playground · UTN BD</h1>
    <p>Parcial 25-jun-2026</p>
    <div id="progress-bar-wrap">
      <div id="progress-bar-bg"><div id="progress-bar-fill" style="width:0%"></div></div>
      <div id="progress-label">0 / 39 resueltos</div>
    </div>
  </div>
  <div id="scenarios">

    <div class="sc-group" id="g1">
      <div class="sc-title" onclick="toggleGroup('g1')">
        <span class="sc-dot" style="background:#a09aff"></span>
        1 · Proveedores
        <span class="sc-chevron">▾</span>
      </div>
      <div class="sc-exercises" id="ex-g1"></div>
    </div>

    <div class="sc-group" id="g2">
      <div class="sc-title" onclick="toggleGroup('g2')">
        <span class="sc-dot" style="background:#43d9ad"></span>
        2 · Vuelos & Pilotos
        <span class="sc-chevron">▾</span>
      </div>
      <div class="sc-exercises" id="ex-g2"></div>
    </div>

    <div class="sc-group" id="g3">
      <div class="sc-title" onclick="toggleGroup('g3')">
        <span class="sc-dot" style="background:#ff6584"></span>
        3 · Universidad
        <span class="sc-chevron">▾</span>
      </div>
      <div class="sc-exercises" id="ex-g3"></div>
    </div>

    <div class="sc-group" id="g4">
      <div class="sc-title" onclick="toggleGroup('g4')">
        <span class="sc-dot" style="background:#ffd166"></span>
        4 · Empresa
        <span class="sc-chevron">▾</span>
      </div>
      <div class="sc-exercises" id="ex-g4"></div>
    </div>

  </div>
</nav>

<!-- MAIN -->
<div id="main">

  <div id="toolbar">
    <span id="scenario-badge">—</span>
    <div id="toolbar-spacer"></div>
    <a href="/apunte" target="_blank" id="btn-apunte">📖 Apunte SQL</a>
    <button id="btn-done" onclick="markDone()" title="Marcar como resuelto">✓ Listo</button>
    <button id="btn-clear" onclick="clearEditor()">Limpiar</button>
    <button id="btn-run" onclick="runQuery()">▶ Ejecutar <kbd>Ctrl+↵</kbd></button>
  </div>

  <!-- EXERCISE CONTEXT: enunciado + schema -->
  <div id="ex-context">
    <div>
      <div id="ex-enunciado-label">Ejercicio</div>
      <div id="ex-enunciado">Seleccioná un ejercicio del panel izquierdo</div>
    </div>
    <div id="ex-schema"></div>
  </div>

  <div id="editor-wrap">
    <textarea id="sql-editor" placeholder="-- Escribí tu consulta SQL acá
-- Ctrl+Enter para ejecutar

SELECT * FROM proveedores;"></textarea>
  </div>

  <div id="result-wrap">
    <div id="empty">
      <div class="ico">🗄️</div>
      <p>Ejecutá una consulta para ver los resultados</p>
      <small>Seleccioná un ejercicio del panel izquierdo para empezar</small>
    </div>
    <div id="result-meta" style="display:none">
      Resultado: <span id="result-count"></span>
    </div>
    <div id="result-content"></div>
  </div>

</div>

<script>
// Schema definitions for display
const SCHEMAS = {
  g1: [
    {name:'Proveedores', pk:'sid', attrs:['sname:string','address:string']},
    {name:'Parts',       pk:'pid', attrs:['pname:string','color:string']},
    {name:'Catalog',     pk:'sid,pid', attrs:['cost:real']},
  ],
  g2: [
    {name:'Vuelos',      pk:'flno',    attrs:['from_city:string','to_city:string','distance:integer','departs:time','arrives:time']},
    {name:'Avion',       pk:'aid',     attrs:['aname:string','cruisingrange:integer']},
    {name:'Certificados',pk:'eid,aid', attrs:[]},
    {name:'Empleados',   pk:'eid',     attrs:['ename:string','salary:integer']},
  ],
  g3: [
    {name:'Student',   pk:'snum',    attrs:['sname:string','major:string','level:string','age:integer']},
    {name:'Class',     pk:'name',    attrs:['meets_at:string','room:string','fid:integer']},
    {name:'Inscripto', pk:'snum,cname', attrs:[]},
    {name:'Faculty',   pk:'fid',     attrs:['fname:string','deptid:integer']},
  ],
  g4: [
    {name:'Emp',   pk:'eid',     attrs:['ename:string','age:integer','salary:real']},
    {name:'Works', pk:'eid,did', attrs:['pct_time:integer']},
    {name:'Dept',  pk:'did',     attrs:['dname:string','budget:real','managerid:integer']},
  ],
};

function renderSchema(gid) {
  const tables = SCHEMAS[gid];
  return tables.map(t => {
    const pk = t.pk.split(',').map(p => `<span class="tpk">${p}</span>`).join(', ');
    const attrs = t.attrs.map(a => {
      const [n,type] = a.split(':');
      return `<span class="tattr">${n}</span><span class="ttype">:${type}</span>`;
    }).join(', ');
    const sep = t.attrs.length > 0 ? ', ' : '';
    return `<span class="tname">${t.name}</span>(${pk}${sep}${attrs})`;
  }).join('\n');
}

const EXERCISES = {
  g1: {
    color:'#a09aff', label:'Proveedores',
    schema:'Proveedores(sid,sname,address) · Parts(pid,pname,color) · Catalog(sid,pid,cost)',
    items:[
      {n:'1', text:'snames de Proveedores que provean alguna parte roja.', diff:'básico'},
      {n:'2', text:'sids de Proveedores que provean alguna parte roja o verde.', diff:'básico'},
      {n:'3', text:'sids de Proveedores que provean parte roja o vivan en "221 Packer Street".', diff:'básico'},
      {n:'4', text:'sids de Proveedores que provean parte roja Y parte verde.', diff:'medio'},
      {n:'5', text:'sids de Proveedores que provean CADA parte.', diff:'difícil'},
      {n:'6', text:'sids de Proveedores que provean CADA parte roja.', diff:'difícil'},
      {n:'7', text:'sids de Proveedores que provean cada parte verde O roja.', diff:'difícil'},
      {n:'8', text:'sids de Proveedores que provean cada parte roja O provean cada parte verde.', diff:'difícil'},
      {n:'9', text:'Pares de sids donde el primero cueste más por alguna parte que el segundo.', diff:'medio'},
      {n:'10',text:'pids de partes provistas por al menos dos proveedores diferentes.', diff:'medio'},
      {n:'11',text:'pids de las partes más caras provistas por "Yosemite Sham".', diff:'medio'},
      {n:'12',text:'pids de partes provistas por cada proveedor a menos de $200.', diff:'difícil'},
    ]
  },
  g2: {
    color:'#43d9ad', label:'Vuelos & Pilotos',
    schema:'Vuelos(flno,from_city,to_city,distance,departs,arrives) · Avion(aid,aname,cruisingrange) · Certificados(eid,aid) · Empleados(eid,ename,salary)',
    items:[
      {n:'a', text:'eids de pilotos certificados para algún avión Boeing.', diff:'básico'},
      {n:'b', text:'Nombres de pilotos certificados para algún avión Boeing.', diff:'básico'},
      {n:'c', text:'aids de aviones que pueden volar sin parada de Bonn a Madras.', diff:'medio'},
      {n:'d', text:'Vuelos piloteados por CADA piloto con salario > $100.000.', diff:'difícil'},
      {n:'e', text:'Nombres de pilotos con aviones de rango > 3000 millas que NO estén cert. para Boeing.', diff:'medio'},
      {n:'f', text:'eids de empleados que ganan el mayor salario.', diff:'medio'},
      {n:'g', text:'eids de empleados que ganan el segundo mayor salario.', diff:'difícil'},
      {n:'h', text:'eids de empleados certificados para el mayor número de aviones.', diff:'difícil'},
      {n:'i', text:'eids de empleados certificados para exactamente 3 aviones.', diff:'medio'},
      {n:'j', text:'Cantidad total de dinero pagado en salarios.', diff:'básico'},
    ]
  },
  g3: {
    color:'#ff6584', label:'Universidad',
    schema:'Student(snum,sname,major,level,age) · Class(name,meets_at,room,fid) · Inscripto(snum,cname) · Faculty(fid,fname,deptid)',
    items:[
      {n:'a', text:'Nombres de estudiantes JR inscriptos en una clase de I. Teach.', diff:'básico'},
      {n:'b', text:'Nombres de clases en aula R128 O con más de 5 inscriptos.', diff:'medio'},
      {n:'c', text:'Nombres de estudiantes inscriptos en dos clases a la misma hora.', diff:'medio'},
      {n:'d', text:'Nombres de docentes que dictan en CADA aula donde hay clases.', diff:'difícil'},
      {n:'e', text:'Nombres de docentes cuya inscripción combinada es menos de 5.', diff:'medio'},
      {n:'f', text:'Para cada nivel, promedio de edad de los estudiantes.', diff:'básico'},
      {n:'g', text:'Para todos los niveles EXCEPTO JR, nivel y promedio de edad.', diff:'básico'},
      {n:'h', text:'Docentes que dictan en R128: su nombre y total de clases.', diff:'medio'},
      {n:'i', text:'Nombres de estudiantes inscriptos en el máximo número de clases.', diff:'difícil'},
      {n:'j', text:'Nombres de estudiantes no inscriptos en ninguna clase.', diff:'medio'},
      {n:'k', text:'Para cada edad, el nivel que aparece más frecuentemente. Ej: (18, FR).', diff:'difícil'},
    ]
  },
  g4: {
    color:'#ffd166', label:'Empresa',
    schema:'Emp(eid,ename,age,salary) · Works(eid,did,pct_time) · Dept(did,dname,budget,managerid)',
    items:[
      {n:'a', text:'Nombres y edades de empleados que trabajan en Hardware Y Software.', diff:'medio'},
      {n:'b', text:'managerids de gerentes que administran SOLO deptos con budget > $1M.', diff:'difícil'},
      {n:'c', text:'enames de gerentes con los mayores presupuestos totales (suma por gerente).', diff:'difícil'},
      {n:'d', text:'managerids de gerentes que controlan más de $5M en presupuesto.', diff:'medio'},
      {n:'e', text:'managerids de gerentes que controlan los MAYORES presupuestos.', diff:'difícil'},
      {n:'f', text:'enames de gerentes con todos los deptos > $1M pero al menos uno < $5M.', diff:'difícil'},
    ]
  }
};

const DIFF_COLORS = {
  'básico': '#43d9ad',
  'medio': '#ffd166',
  'difícil': '#ff6584',
};

const STORAGE_KEY = 'sql_utn_done_v2';
let currentGroup = null, currentIdx = null;

function loadDone() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
}
function saveDone(d) { localStorage.setItem(STORAGE_KEY, JSON.stringify(d)); }
function doneKey(g, i) { return g + '_' + i; }

function buildSidebar() {
  const done = loadDone();
  let total = 0, doneCount = 0;
  Object.entries(EXERCISES).forEach(([gid, sc]) => {
    const wrap = document.getElementById('ex-' + gid);
    wrap.innerHTML = '';
    sc.items.forEach((ex, idx) => {
      total++;
      const key = doneKey(gid, idx);
      if (done[key]) doneCount++;
      const btn = document.createElement('button');
      btn.className = 'ex-btn' + (done[key] ? ' done' : '');
      btn.innerHTML = `<span class="ex-num" style="background:${sc.color}22;color:${sc.color}">${ex.n}</span><span style="flex:1">${ex.text}</span>${done[key] ? '<span class="ex-check">✓</span>' : ''}`;
      btn.onclick = () => selectEx(gid, idx);
      btn.id = 'btn-' + key;
      wrap.appendChild(btn);
    });
  });
  updateProgressBar(doneCount, total);
}

function updateProgressBar(done, total) {
  document.getElementById('progress-bar-fill').style.width = (done/total*100)+'%';
  document.getElementById('progress-label').textContent = done + ' / ' + total + ' resueltos';
}

function selectEx(gid, idx) {
  // deselect previous
  if (currentGroup !== null) {
    const prev = document.getElementById('btn-' + doneKey(currentGroup, currentIdx));
    if (prev) prev.classList.remove('active');
  }
  currentGroup = gid; currentIdx = idx;
  const btn = document.getElementById('btn-' + doneKey(gid, idx));
  if (btn) btn.classList.add('active');

  const sc = EXERCISES[gid];
  const ex = sc.items[idx];

  // Toolbar badge
  document.getElementById('scenario-badge').textContent = sc.label + ' · ' + ex.n;
  document.getElementById('scenario-badge').style.color = sc.color;
  document.getElementById('scenario-badge').style.background = sc.color + '22';

  // Context box: enunciado + schema
  const ctx = document.getElementById('ex-context');
  ctx.classList.add('visible');
  document.getElementById('ex-enunciado').textContent = 'Ejercicio ' + ex.n + ': ' + ex.text;
  document.getElementById('ex-schema').innerHTML = renderSchema(gid);

  // Editor placeholder
  document.getElementById('sql-editor').placeholder = '-- Escribí tu consulta acá\n\nSELECT ...';
  document.getElementById('sql-editor').focus();

  clearResult();
}

function toggleGroup(gid) {
  document.getElementById(gid).classList.toggle('closed');
}

function clearEditor() {
  document.getElementById('sql-editor').value = '';
  clearResult();
  // feedback visual
  const btn = document.getElementById('btn-clear');
  btn.textContent = '✓ Limpio';
  btn.classList.add('flashing');
  setTimeout(() => { btn.textContent = 'Limpiar'; btn.classList.remove('flashing'); }, 800);
}

function clearResult() {
  document.getElementById('empty').style.display = 'flex';
  document.getElementById('result-meta').style.display = 'none';
  document.getElementById('result-content').innerHTML = '';
}

function markDone() {
  if (currentGroup === null) return;
  const done = loadDone();
  const key = doneKey(currentGroup, currentIdx);
  done[key] = !done[key];
  saveDone(done);
  buildSidebar();
  // re-activate current
  const btn = document.getElementById('btn-' + key);
  if (btn) btn.classList.add('active');
}

async function runQuery() {
  const sql = document.getElementById('sql-editor').value.trim();
  if (!sql) return;
  document.getElementById('empty').style.display = 'none';
  document.getElementById('result-meta').style.display = 'none';
  document.getElementById('result-content').innerHTML = '<div style="color:var(--mu);padding:.5rem;font-size:.8rem">Ejecutando...</div>';

  try {
    const res = await fetch('/query', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({sql})
    });
    const data = await res.json();

    if (data.error) {
      document.getElementById('result-content').innerHTML = `<div class="err-box">❌ ${escHtml(data.error)}</div>`;
      return;
    }

    if (data.msg) {
      document.getElementById('result-content').innerHTML = `<div class="ok-box">✅ ${escHtml(data.msg)}</div>`;
      return;
    }

    const meta = document.getElementById('result-meta');
    meta.style.display = 'flex';
    document.getElementById('result-count').textContent = data.count + ' fila' + (data.count !== 1 ? 's' : '');

    if (data.count === 0) {
      document.getElementById('result-content').innerHTML = '<div style="color:var(--mu);padding:.8rem;font-size:.82rem">Sin resultados — la consulta es válida pero no devuelve filas.</div>';
      return;
    }

    let html = '<div id="result-table-wrap"><table><thead><tr>';
    data.cols.forEach(c => { html += `<th>${escHtml(c)}</th>`; });
    html += '</tr></thead><tbody>';
    data.rows.forEach(row => {
      html += '<tr>';
      data.cols.forEach(c => {
        const v = row[c];
        if (v === null || v === undefined) html += '<td class="null">NULL</td>';
        else html += `<td>${escHtml(String(v))}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    document.getElementById('result-content').innerHTML = html;

  } catch(e) {
    document.getElementById('result-content').innerHTML = `<div class="err-box">❌ Error de red: ${escHtml(e.message)}</div>`;
  }
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Ctrl+Enter to run
document.getElementById('sql-editor').addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); runQuery(); }
});

buildSidebar();
</script>
</body>
</html>
"""

APUNTE_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Apunte SQL — BD UTN</title>
<style>
:root{--bg:#0f1117;--s1:#1a1d27;--s2:#222538;--bd:#2e3250;--acc:#6c63ff;--g:#43d9ad;--r:#ff6584;--y:#ffd166;--tx:#e2e4f0;--mu:#8b8fad;--cb:#12141e;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--tx);font-family:'Segoe UI',system-ui,sans-serif;display:flex;}

/* SIDEBAR */
#sidebar{width:220px;flex-shrink:0;background:var(--s1);border-right:1px solid var(--bd);padding:1.2rem 0.8rem;position:sticky;top:0;height:100vh;overflow-y:auto;}
#sidebar h2{font-size:0.65rem;text-transform:uppercase;letter-spacing:.1em;color:var(--mu);margin-bottom:0.8rem;padding-bottom:0.5rem;border-bottom:1px solid var(--bd);}
.nav-item{display:block;padding:0.35rem 0.6rem;border-radius:6px;font-size:0.8rem;color:var(--mu);text-decoration:none;margin-bottom:0.1rem;}
.nav-item:hover{background:rgba(255,255,255,.05);color:var(--tx);}
.nav-sep{font-size:0.65rem;text-transform:uppercase;letter-spacing:.08em;color:var(--mu);padding:0.7rem 0.6rem 0.2rem;margin-top:0.3rem;}
.back-btn{display:flex;align-items:center;gap:0.4rem;padding:0.4rem 0.6rem;border-radius:6px;background:rgba(108,99,255,.15);color:#a09aff;text-decoration:none;font-size:0.78rem;font-weight:600;margin-bottom:1rem;}
.back-btn:hover{background:rgba(108,99,255,.25);}

/* MAIN */
#main{flex:1;padding:2rem 2.5rem;max-width:900px;}
header{margin-bottom:2.5rem;padding-bottom:1.2rem;border-bottom:1px solid var(--bd);}
header h1{font-size:2rem;font-weight:800;background:linear-gradient(135deg,#6c63ff,#43d9ad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
header p{color:var(--mu);font-size:0.88rem;margin-top:0.3rem;}

/* SECTIONS */
.section{margin-bottom:2.5rem;}
.section-header{display:flex;align-items:center;gap:0.8rem;margin-bottom:1rem;}
.section-icon{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;}
.section-header h2{font-size:1.1rem;font-weight:700;}
.section-header p{font-size:0.78rem;color:var(--mu);}

/* CODE */
pre{background:var(--cb);border:1px solid var(--bd);border-radius:10px;padding:1rem 1.2rem;margin:0.8rem 0;overflow-x:auto;font-family:'Cascadia Code','Fira Code',monospace;font-size:0.84rem;line-height:1.75;}
.kw{color:#6c63ff;font-weight:700;}
.fn{color:#43d9ad;font-weight:600;}
.str{color:#ffd166;}
.num{color:#ff9f43;}
.cmt{color:#555e7a;font-style:italic;}
.tbl{color:#e2e4f0;font-weight:600;}
.op{color:#ff6584;}

/* CARDS */
.card-grid{display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;margin:0.8rem 0;}
.card{background:var(--s1);border:1px solid var(--bd);border-radius:10px;padding:1rem;}
.card h3{font-size:0.82rem;font-weight:700;margin-bottom:0.5rem;}
.card p,.card li{font-size:0.8rem;color:var(--mu);line-height:1.5;}
.card ul{padding-left:1.2rem;}
.card code{background:var(--cb);border-radius:4px;padding:.1em .4em;font-family:monospace;font-size:.82em;color:var(--g);}

/* ALERT */
.alert{border-radius:8px;padding:.7rem 1rem;margin:.7rem 0;font-size:.82rem;display:flex;gap:.6rem;}
.alert-y{background:rgba(255,209,102,.08);border-left:3px solid var(--y);}
.alert-g{background:rgba(67,217,173,.08);border-left:3px solid var(--g);}
.alert-r{background:rgba(255,101,132,.08);border-left:3px solid var(--r);}
.alert-p{background:rgba(108,99,255,.08);border-left:3px solid var(--acc);}

/* TABLE */
table{width:100%;border-collapse:collapse;font-size:.82rem;margin:.8rem 0;}
th{background:var(--s2);color:var(--mu);text-align:left;padding:.5rem .8rem;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;border-bottom:2px solid var(--bd);}
td{padding:.45rem .8rem;border-bottom:1px solid rgba(255,255,255,.04);}
tr:hover td{background:rgba(255,255,255,.02);}
code{background:var(--cb);border-radius:4px;padding:.1em .4em;font-family:monospace;font-size:.82em;color:var(--g);}
p{margin:.5rem 0;font-size:.88rem;line-height:1.6;}
h3{font-size:.95rem;color:var(--g);margin:1.1rem 0 .4rem;}
h4{font-size:.85rem;color:var(--y);margin:.9rem 0 .3rem;}
hr{border:none;border-top:1px solid var(--bd);margin:2rem 0;}
@media(max-width:640px){#sidebar{display:none;}.card-grid{grid-template-columns:1fr;}}
</style>
</head>
<body>

<nav id="sidebar">
  <a href="/" class="back-btn">← Volver al Playground</a>
  <h2>Contenido</h2>
  <a href="#select" class="nav-item">SELECT básico</a>
  <a href="#where" class="nav-item">WHERE y operadores</a>
  <a href="#joins" class="nav-item">JOINs</a>
  <a href="#agrega" class="nav-item">Agregación</a>
  <a href="#groupby" class="nav-item">GROUP BY / HAVING</a>
  <a href="#subq" class="nav-item">Subconsultas</a>
  <a href="#sets" class="nav-item">UNION / INTERSECT / EXCEPT</a>
  <a href="#division" class="nav-item">División en SQL</a>
  <a href="#max2" class="nav-item">Máximo y 2do máximo</a>
  <a href="#patterns" class="nav-item">Patrones frecuentes</a>
  <div class="nav-sep">DDL / DML</div>
  <a href="#dml" class="nav-item">INSERT / UPDATE / DELETE</a>
  <a href="#ddl" class="nav-item">CREATE / ALTER / DROP</a>
</nav>

<main id="main">
<header>
  <h1>Apunte Práctico — SQL</h1>
  <p>Unidad V · Bases de Datos · UTN · Parcial 25-jun-2026</p>
</header>

<!-- ═══ 1. SELECT BÁSICO ═══ -->
<section class="section" id="select">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(108,99,255,.15);color:#a09aff">🔍</div>
    <div><h2>SELECT — Estructura base</h2><p>El orden de las cláusulas es fijo</p></div>
  </div>

<pre><span class="kw">SELECT</span>   col1, col2, ...          <span class="cmt">-- qué columnas mostrar</span>
<span class="kw">FROM</span>     tabla                    <span class="cmt">-- de qué tabla</span>
<span class="kw">WHERE</span>    condición                 <span class="cmt">-- filtro de filas (antes de agrupar)</span>
<span class="kw">GROUP BY</span> col1                     <span class="cmt">-- agrupar resultados</span>
<span class="kw">HAVING</span>   condición_de_grupo       <span class="cmt">-- filtro sobre grupos</span>
<span class="kw">ORDER BY</span> col1 <span class="kw">ASC</span>|<span class="kw">DESC</span>            <span class="cmt">-- ordenar resultado</span>
<span class="kw">LIMIT</span>    n;                       <span class="cmt">-- limitar cantidad de filas</span></pre>

  <div class="alert alert-p">
    <span>💡</span>
    <div><strong>Orden de ejecución real:</strong> FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT<br>
    El SELECT se ejecuta <em>después</em> del WHERE y del GROUP BY — por eso no podés usar alias del SELECT en el WHERE.</div>
  </div>

<pre><span class="cmt">-- DISTINCT: elimina filas duplicadas</span>
<span class="kw">SELECT DISTINCT</span> color <span class="kw">FROM</span> <span class="tbl">Parts</span>;

<span class="cmt">-- Alias de columna y tabla</span>
<span class="kw">SELECT</span> p.sid <span class="kw">AS</span> proveedor_id, p.sname <span class="kw">AS</span> nombre
<span class="kw">FROM</span>   <span class="tbl">Proveedores</span> p;</pre>
</section>

<hr>

<!-- ═══ 2. WHERE ═══ -->
<section class="section" id="where">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(67,217,173,.15);color:#43d9ad">⚡</div>
    <div><h2>WHERE — Filtros y operadores</h2><p>Filtra filas antes de cualquier agrupación</p></div>
  </div>

  <div class="card-grid">
    <div class="card">
      <h3>Comparación</h3>
      <ul>
        <li><code>=</code> igual</li>
        <li><code>&lt;&gt;</code> o <code>!=</code> distinto</li>
        <li><code>&lt;  &gt;  &lt;=  &gt;=</code></li>
      </ul>
    </div>
    <div class="card">
      <h3>Lógicos</h3>
      <ul>
        <li><code>AND</code> — ambas condiciones</li>
        <li><code>OR</code> — al menos una</li>
        <li><code>NOT</code> — negación</li>
      </ul>
    </div>
    <div class="card">
      <h3>Rango y lista</h3>
      <ul>
        <li><code>BETWEEN a AND b</code></li>
        <li><code>IN (v1, v2, ...)</code></li>
        <li><code>NOT IN (...)</code></li>
      </ul>
    </div>
    <div class="card">
      <h3>Texto y nulos</h3>
      <ul>
        <li><code>LIKE 'Bo%'</code> — empieza con Bo</li>
        <li><code>LIKE '%ing'</code> — termina en ing</li>
        <li><code>IS NULL</code> / <code>IS NOT NULL</code></li>
      </ul>
    </div>
  </div>

<pre><span class="kw">SELECT</span> * <span class="kw">FROM</span> <span class="tbl">Proveedores</span>
<span class="kw">WHERE</span>  address = <span class="str">'221 Packer Street'</span>
   <span class="kw">OR</span>  sid <span class="kw">IN</span> (<span class="num">1</span>, <span class="num">3</span>, <span class="num">5</span>);

<span class="kw">SELECT</span> * <span class="kw">FROM</span> <span class="tbl">Empleados</span>
<span class="kw">WHERE</span>  salary <span class="kw">BETWEEN</span> <span class="num">80000</span> <span class="kw">AND</span> <span class="num">120000</span>;

<span class="kw">SELECT</span> * <span class="kw">FROM</span> <span class="tbl">Avion</span>
<span class="kw">WHERE</span>  aname <span class="kw">LIKE</span> <span class="str">'Boeing%'</span>;   <span class="cmt">-- cualquier avión Boeing</span></pre>
</section>

<hr>

<!-- ═══ 3. JOINS ═══ -->
<section class="section" id="joins">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(255,101,132,.15);color:#ff6584">🔗</div>
    <div><h2>JOINs — Combinar tablas</h2><p>El más usado en parciales: INNER JOIN</p></div>
  </div>

  <table>
    <tr><th>Tipo</th><th>Qué devuelve</th></tr>
    <tr><td><code>INNER JOIN</code></td><td>Solo filas que coinciden en ambas tablas</td></tr>
    <tr><td><code>LEFT JOIN</code></td><td>Todas las de la izquierda + las que coinciden de la derecha (NULL si no hay)</td></tr>
    <tr><td><code>RIGHT JOIN</code></td><td>Todas las de la derecha + coincidencias de la izquierda</td></tr>
    <tr><td><code>CROSS JOIN</code></td><td>Producto cartesiano — todas las combinaciones</td></tr>
  </table>

<pre><span class="cmt">-- INNER JOIN (el más común)</span>
<span class="kw">SELECT</span> p.sname, pt.pname, c.cost
<span class="kw">FROM</span>   <span class="tbl">Proveedores</span> p
<span class="kw">JOIN</span>   <span class="tbl">Catalog</span>     c  <span class="kw">ON</span> p.sid  = c.sid
<span class="kw">JOIN</span>   <span class="tbl">Parts</span>       pt <span class="kw">ON</span> c.pid  = pt.pid
<span class="kw">WHERE</span>  pt.color = <span class="str">'roja'</span>;

<span class="cmt">-- Self JOIN: comparar filas de la misma tabla</span>
<span class="kw">SELECT</span> c1.sid <span class="kw">AS</span> sid1, c2.sid <span class="kw">AS</span> sid2
<span class="kw">FROM</span>   <span class="tbl">Catalog</span> c1
<span class="kw">JOIN</span>   <span class="tbl">Catalog</span> c2 <span class="kw">ON</span> c1.pid = c2.pid
<span class="kw">WHERE</span>  c1.cost > c2.cost;  <span class="cmt">-- ej 9: proveedor que cobra más que otro</span></pre>

  <div class="alert alert-y">
    <span>⚠️</span>
    <div><strong>Truco parcial:</strong> <code>JOIN</code> solo = <code>INNER JOIN</code>. Siempre especificá el <code>ON</code> con la clave foránea correcta, no mezcles claves distintas.</div>
  </div>
</section>

<hr>

<!-- ═══ 4. AGREGACIÓN ═══ -->
<section class="section" id="agrega">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(255,209,102,.15);color:#ffd166">∑</div>
    <div><h2>Funciones de Agregación</h2><p>Operan sobre grupos de filas</p></div>
  </div>

  <table>
    <tr><th>Función</th><th>Qué hace</th><th>Ignora NULL</th></tr>
    <tr><td><code>COUNT(*)</code></td><td>Cuenta todas las filas del grupo</td><td>No</td></tr>
    <tr><td><code>COUNT(col)</code></td><td>Cuenta filas donde col no es NULL</td><td>Sí</td></tr>
    <tr><td><code>SUM(col)</code></td><td>Suma los valores</td><td>Sí</td></tr>
    <tr><td><code>AVG(col)</code></td><td>Promedio</td><td>Sí</td></tr>
    <tr><td><code>MAX(col)</code></td><td>Valor máximo</td><td>Sí</td></tr>
    <tr><td><code>MIN(col)</code></td><td>Valor mínimo</td><td>Sí</td></tr>
  </table>

<pre><span class="kw">SELECT</span> <span class="fn">COUNT</span>(*) <span class="kw">AS</span> total_empleados <span class="kw">FROM</span> <span class="tbl">Empleados</span>;

<span class="kw">SELECT</span> <span class="fn">SUM</span>(salary) <span class="kw">AS</span> masa_salarial <span class="kw">FROM</span> <span class="tbl">Empleados</span>;  <span class="cmt">-- ej j</span>

<span class="kw">SELECT</span> <span class="fn">MAX</span>(salary) <span class="kw">FROM</span> <span class="tbl">Empleados</span>;  <span class="cmt">-- mayor salario</span></pre>
</section>

<hr>

<!-- ═══ 5. GROUP BY / HAVING ═══ -->
<section class="section" id="groupby">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(108,99,255,.15);color:#a09aff">📊</div>
    <div><h2>GROUP BY / HAVING</h2><p>Agrupar filas y filtrar grupos</p></div>
  </div>

  <div class="alert alert-g">
    <span>🔑</span>
    <div><strong>Regla:</strong> toda columna en el SELECT que <em>no</em> sea una función de agregación, <strong>debe estar en el GROUP BY</strong>.<br>
    <strong>WHERE</strong> filtra filas <em>antes</em> de agrupar · <strong>HAVING</strong> filtra grupos <em>después</em> de agrupar.</div>
  </div>

<pre><span class="cmt">-- Cantidad de aviones por piloto (ej h, i)</span>
<span class="kw">SELECT</span>   eid, <span class="fn">COUNT</span>(aid) <span class="kw">AS</span> cant_aviones
<span class="kw">FROM</span>     <span class="tbl">Certificados</span>
<span class="kw">GROUP BY</span> eid
<span class="kw">HAVING</span>   <span class="fn">COUNT</span>(aid) = <span class="num">3</span>;          <span class="cmt">-- exactamente 3 aviones (ej i)</span>

<span class="cmt">-- Presupuesto total por gerente (ej d, e)</span>
<span class="kw">SELECT</span>   managerid, <span class="fn">SUM</span>(budget) <span class="kw">AS</span> total
<span class="kw">FROM</span>     <span class="tbl">Dept</span>
<span class="kw">GROUP BY</span> managerid
<span class="kw">HAVING</span>   <span class="fn">SUM</span>(budget) > <span class="num">5000000</span>;   <span class="cmt">-- ej d</span>

<span class="cmt">-- Partes con al menos 2 proveedores (ej 10)</span>
<span class="kw">SELECT</span>   pid
<span class="kw">FROM</span>     <span class="tbl">Catalog</span>
<span class="kw">GROUP BY</span> pid
<span class="kw">HAVING</span>   <span class="fn">COUNT</span>(<span class="kw">DISTINCT</span> sid) >= <span class="num">2</span>;

<span class="cmt">-- Promedio de edad por nivel (ej f)</span>
<span class="kw">SELECT</span>   level, <span class="fn">AVG</span>(age) <span class="kw">AS</span> prom_edad
<span class="kw">FROM</span>     <span class="tbl">Student</span>
<span class="kw">GROUP BY</span> level
<span class="kw">HAVING</span>   level <span class="op">&lt;&gt;</span> <span class="str">'JR'</span>;            <span class="cmt">-- ej g: excepto JR</span></pre>
</section>

<hr>

<!-- ═══ 6. SUBCONSULTAS ═══ -->
<section class="section" id="subq">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(255,101,132,.15);color:#ff6584">🔄</div>
    <div><h2>Subconsultas</h2><p>Consultas dentro de consultas — el corazón del parcial</p></div>
  </div>

  <h3>IN / NOT IN</h3>
<pre><span class="cmt">-- eids de pilotos Boeing (ej a)</span>
<span class="kw">SELECT</span> eid <span class="kw">FROM</span> <span class="tbl">Certificados</span>
<span class="kw">WHERE</span>  aid <span class="kw">IN</span> (
  <span class="kw">SELECT</span> aid <span class="kw">FROM</span> <span class="tbl">Avion</span> <span class="kw">WHERE</span> aname <span class="kw">LIKE</span> <span class="str">'Boeing%'</span>
);

<span class="cmt">-- pilotos con rango > 3000 que NO son Boeing (ej e)</span>
<span class="kw">SELECT</span> ename <span class="kw">FROM</span> <span class="tbl">Empleados</span>
<span class="kw">WHERE</span>  eid <span class="kw">IN</span> (
    <span class="kw">SELECT</span> eid <span class="kw">FROM</span> <span class="tbl">Certificados</span> <span class="kw">JOIN</span> <span class="tbl">Avion</span> <span class="kw">USING</span>(aid)
    <span class="kw">WHERE</span>  cruisingrange > <span class="num">3000</span>
)
<span class="kw">AND</span>    eid <span class="kw">NOT IN</span> (
    <span class="kw">SELECT</span> eid <span class="kw">FROM</span> <span class="tbl">Certificados</span> <span class="kw">JOIN</span> <span class="tbl">Avion</span> <span class="kw">USING</span>(aid)
    <span class="kw">WHERE</span>  aname <span class="kw">LIKE</span> <span class="str">'Boeing%'</span>
);</pre>

  <h3>EXISTS / NOT EXISTS</h3>
  <p>Más eficiente que IN cuando la subconsulta es correlacionada. Devuelve verdadero si la subconsulta retorna al menos una fila.</p>
<pre><span class="cmt">-- Estudiantes no inscriptos en ninguna clase (ej j)</span>
<span class="kw">SELECT</span> sname <span class="kw">FROM</span> <span class="tbl">Student</span> s
<span class="kw">WHERE NOT EXISTS</span> (
  <span class="kw">SELECT</span> <span class="num">1</span> <span class="kw">FROM</span> <span class="tbl">Inscripto</span> i
  <span class="kw">WHERE</span>  i.snum = s.snum    <span class="cmt">-- correlación: referencia a la fila externa</span>
);</pre>

  <h3>Subconsulta escalar (devuelve un solo valor)</h3>
<pre><span class="cmt">-- partes más caras de Yosemite Sham (ej 11)</span>
<span class="kw">SELECT</span> pid <span class="kw">FROM</span> <span class="tbl">Catalog</span> c
<span class="kw">JOIN</span>   <span class="tbl">Proveedores</span> p <span class="kw">ON</span> c.sid = p.sid
<span class="kw">WHERE</span>  p.sname = <span class="str">'Yosemite Sham'</span>
  <span class="kw">AND</span>  c.cost = (
    <span class="kw">SELECT MAX</span>(c2.cost) <span class="kw">FROM</span> <span class="tbl">Catalog</span> c2
    <span class="kw">JOIN</span>  <span class="tbl">Proveedores</span> p2 <span class="kw">ON</span> c2.sid = p2.sid
    <span class="kw">WHERE</span> p2.sname = <span class="str">'Yosemite Sham'</span>
  );</pre>

  <h3>ALL / ANY</h3>
<pre><span class="cmt">-- aviones que pueden cubrir distancia Bonn→Madras (ej c)</span>
<span class="kw">SELECT</span> aid <span class="kw">FROM</span> <span class="tbl">Avion</span>
<span class="kw">WHERE</span>  cruisingrange >= (
  <span class="kw">SELECT</span> distance <span class="kw">FROM</span> <span class="tbl">Vuelos</span>
  <span class="kw">WHERE</span>  from_city = <span class="str">'Bonn'</span> <span class="kw">AND</span> to_city = <span class="str">'Madras'</span>
);</pre>
</section>

<hr>

<!-- ═══ 7. UNION / INTERSECT / EXCEPT ═══ -->
<section class="section" id="sets">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(67,217,173,.15);color:#43d9ad">∪</div>
    <div><h2>UNION · INTERSECT · EXCEPT</h2><p>Operaciones de conjuntos — mismas columnas y tipos</p></div>
  </div>

  <table>
    <tr><th>Operador</th><th>Equivale a AR</th><th>Elimina duplicados</th></tr>
    <tr><td><code>UNION</code></td><td>∪ Unión</td><td>Sí</td></tr>
    <tr><td><code>UNION ALL</code></td><td>∪ sin dedup</td><td>No</td></tr>
    <tr><td><code>INTERSECT</code></td><td>∩ Intersección</td><td>Sí</td></tr>
    <tr><td><code>EXCEPT</code></td><td>− Diferencia</td><td>Sí</td></tr>
  </table>

<pre><span class="cmt">-- sids que proveen parte roja O parte verde (ej 2)</span>
<span class="kw">SELECT</span> sid <span class="kw">FROM</span> <span class="tbl">Catalog</span> <span class="kw">JOIN</span> <span class="tbl">Parts</span> <span class="kw">USING</span>(pid) <span class="kw">WHERE</span> color=<span class="str">'roja'</span>
<span class="kw">UNION</span>
<span class="kw">SELECT</span> sid <span class="kw">FROM</span> <span class="tbl">Catalog</span> <span class="kw">JOIN</span> <span class="tbl">Parts</span> <span class="kw">USING</span>(pid) <span class="kw">WHERE</span> color=<span class="str">'verde'</span>;

<span class="cmt">-- sids que proveen roja Y verde (ej 4)</span>
<span class="kw">SELECT</span> sid <span class="kw">FROM</span> <span class="tbl">Catalog</span> <span class="kw">JOIN</span> <span class="tbl">Parts</span> <span class="kw">USING</span>(pid) <span class="kw">WHERE</span> color=<span class="str">'roja'</span>
<span class="kw">INTERSECT</span>
<span class="kw">SELECT</span> sid <span class="kw">FROM</span> <span class="tbl">Catalog</span> <span class="kw">JOIN</span> <span class="tbl">Parts</span> <span class="kw">USING</span>(pid) <span class="kw">WHERE</span> color=<span class="str">'verde'</span>;</pre>

  <div class="alert alert-y">
    <span>⚠️</span>
    <div>Las columnas de ambas partes deben ser <strong>compatibles en cantidad y tipo</strong>. Usá alias si los nombres difieren.</div>
  </div>
</section>

<hr>

<!-- ═══ 8. DIVISIÓN ═══ -->
<section class="section" id="division">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(255,209,102,.15);color:#ffd166">÷</div>
    <div><h2>División en SQL — "TODOS"</h2><p>No existe como operador — se implementa con NOT EXISTS doble</p></div>
  </div>

  <div class="alert alert-r">
    <span>🔑</span>
    <div><strong>Cada vez que el enunciado diga "TODOS" o "CADA" — pensá en división.</strong><br>
    En SQL se implementa con doble <code>NOT EXISTS</code>: "no existe ningún X para el que no existe Y".</div>
  </div>

  <h3>Patrón: ¿Quién provee CADA parte? (ej 5)</h3>
<pre><span class="cmt">-- Traducción lógica: "no existe ninguna parte que este proveedor NO provea"</span>
<span class="kw">SELECT</span> s.sid
<span class="kw">FROM</span>   <span class="tbl">Proveedores</span> s
<span class="kw">WHERE NOT EXISTS</span> (          <span class="cmt">-- no existe ninguna parte...</span>
  <span class="kw">SELECT</span> <span class="num">1</span> <span class="kw">FROM</span> <span class="tbl">Parts</span> pt
  <span class="kw">WHERE NOT EXISTS</span> (        <span class="cmt">-- ...que NO esté en el catálogo de este proveedor</span>
    <span class="kw">SELECT</span> <span class="num">1</span> <span class="kw">FROM</span> <span class="tbl">Catalog</span> c
    <span class="kw">WHERE</span>  c.sid = s.sid
      <span class="kw">AND</span>  c.pid = pt.pid
  )
);</pre>

  <h3>Patrón: ¿Quién provee CADA parte roja? (ej 6)</h3>
<pre><span class="kw">SELECT</span> s.sid
<span class="kw">FROM</span>   <span class="tbl">Proveedores</span> s
<span class="kw">WHERE NOT EXISTS</span> (
  <span class="kw">SELECT</span> <span class="num">1</span> <span class="kw">FROM</span> <span class="tbl">Parts</span> pt
  <span class="kw">WHERE</span>  pt.color = <span class="str">'roja'</span>    <span class="cmt">-- solo las rojas</span>
    <span class="kw">AND NOT EXISTS</span> (
      <span class="kw">SELECT</span> <span class="num">1</span> <span class="kw">FROM</span> <span class="tbl">Catalog</span> c
      <span class="kw">WHERE</span>  c.sid = s.sid <span class="kw">AND</span> c.pid = pt.pid
    )
);</pre>

  <h3>Alternativa con COUNT (más legible)</h3>
<pre><span class="cmt">-- Proveedores que tienen en catálogo TODAS las partes rojas</span>
<span class="kw">SELECT</span> sid
<span class="kw">FROM</span>   <span class="tbl">Catalog</span> c
<span class="kw">JOIN</span>   <span class="tbl">Parts</span>   p <span class="kw">USING</span>(pid)
<span class="kw">WHERE</span>  p.color = <span class="str">'roja'</span>
<span class="kw">GROUP BY</span> sid
<span class="kw">HAVING</span> <span class="fn">COUNT</span>(<span class="kw">DISTINCT</span> pid) = (
  <span class="kw">SELECT COUNT</span>(*) <span class="kw">FROM</span> <span class="tbl">Parts</span> <span class="kw">WHERE</span> color = <span class="str">'roja'</span>
);</pre>
</section>

<hr>

<!-- ═══ 9. MÁXIMO Y 2do MÁXIMO ═══ -->
<section class="section" id="max2">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(108,99,255,.15);color:#a09aff">🏆</div>
    <div><h2>Máximo y 2do mayor salario</h2><p>Patrones que siempre caen en parcial</p></div>
  </div>

  <h3>El mayor salario (ej f)</h3>
<pre><span class="cmt">-- Opción 1: con MAX</span>
<span class="kw">SELECT</span> eid <span class="kw">FROM</span> <span class="tbl">Empleados</span>
<span class="kw">WHERE</span>  salary = (<span class="kw">SELECT MAX</span>(salary) <span class="kw">FROM</span> <span class="tbl">Empleados</span>);

<span class="cmt">-- Opción 2: no existe nadie que gane más</span>
<span class="kw">SELECT</span> eid <span class="kw">FROM</span> <span class="tbl">Empleados</span> e
<span class="kw">WHERE NOT EXISTS</span> (
  <span class="kw">SELECT</span> <span class="num">1</span> <span class="kw">FROM</span> <span class="tbl">Empleados</span> e2
  <span class="kw">WHERE</span>  e2.salary > e.salary
);</pre>

  <h3>El 2do mayor salario (ej g)</h3>
<pre><span class="cmt">-- Opción 1: MAX excluyendo el máximo</span>
<span class="kw">SELECT</span> eid <span class="kw">FROM</span> <span class="tbl">Empleados</span>
<span class="kw">WHERE</span>  salary = (
  <span class="kw">SELECT MAX</span>(salary) <span class="kw">FROM</span> <span class="tbl">Empleados</span>
  <span class="kw">WHERE</span>  salary < (<span class="kw">SELECT MAX</span>(salary) <span class="kw">FROM</span> <span class="tbl">Empleados</span>)
);

<span class="cmt">-- Opción 2: existe exactamente 1 que gana más</span>
<span class="kw">SELECT</span> eid <span class="kw">FROM</span> <span class="tbl">Empleados</span> e
<span class="kw">WHERE</span> (
  <span class="kw">SELECT COUNT</span>(<span class="kw">DISTINCT</span> salary) <span class="kw">FROM</span> <span class="tbl">Empleados</span>
  <span class="kw">WHERE</span> salary > e.salary
) = <span class="num">1</span>;</pre>

  <h3>El mayor COUNT (ej h — más aviones)</h3>
<pre><span class="kw">SELECT</span> eid
<span class="kw">FROM</span>   <span class="tbl">Certificados</span>
<span class="kw">GROUP BY</span> eid
<span class="kw">HAVING</span> <span class="fn">COUNT</span>(aid) = (
  <span class="kw">SELECT MAX</span>(cnt) <span class="kw">FROM</span> (
    <span class="kw">SELECT COUNT</span>(aid) <span class="kw">AS</span> cnt
    <span class="kw">FROM</span>   <span class="tbl">Certificados</span>
    <span class="kw">GROUP BY</span> eid
  ) <span class="kw">AS</span> sub
);</pre>
</section>

<hr>

<!-- ═══ 10. PATRONES FRECUENTES ═══ -->
<section class="section" id="patterns">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(67,217,173,.15);color:#43d9ad">🎯</div>
    <div><h2>Patrones frecuentes en parciales</h2></div>
  </div>

  <h3>"Empleados que trabajan en Hardware Y en Software" (ej 4a)</h3>
<pre><span class="kw">SELECT</span> e.ename, e.age
<span class="kw">FROM</span>   <span class="tbl">Emp</span> e
<span class="kw">WHERE</span>  e.eid <span class="kw">IN</span> (
  <span class="kw">SELECT</span> w.eid <span class="kw">FROM</span> <span class="tbl">Works</span> w <span class="kw">JOIN</span> <span class="tbl">Dept</span> d <span class="kw">USING</span>(did) <span class="kw">WHERE</span> d.dname=<span class="str">'Hardware'</span>
)
<span class="kw">AND</span>    e.eid <span class="kw">IN</span> (
  <span class="kw">SELECT</span> w.eid <span class="kw">FROM</span> <span class="tbl">Works</span> w <span class="kw">JOIN</span> <span class="tbl">Dept</span> d <span class="kw">USING</span>(did) <span class="kw">WHERE</span> d.dname=<span class="str">'Software'</span>
);</pre>

  <h3>"Solo departamentos con X" — gerentes que NO tienen ninguno fuera (ej 4b)</h3>
<pre><span class="cmt">-- Gerentes que administran SOLO deptos con budget > 1M</span>
<span class="kw">SELECT</span> managerid <span class="kw">FROM</span> <span class="tbl">Dept</span>
<span class="kw">GROUP BY</span> managerid
<span class="kw">HAVING</span> <span class="fn">MIN</span>(budget) > <span class="num">1000000</span>;   <span class="cmt">-- si el mínimo > 1M, todos > 1M</span></pre>

  <h3>"Estudiantes con mayor número de clases" (ej 3i)</h3>
<pre><span class="kw">SELECT</span> s.sname
<span class="kw">FROM</span>   <span class="tbl">Student</span> s <span class="kw">JOIN</span> <span class="tbl">Inscripto</span> i <span class="kw">USING</span>(snum)
<span class="kw">GROUP BY</span> s.snum, s.sname
<span class="kw">HAVING</span> <span class="fn">COUNT</span>(*) = (
  <span class="kw">SELECT MAX</span>(cnt) <span class="kw">FROM</span> (
    <span class="kw">SELECT COUNT</span>(*) <span class="kw">AS</span> cnt <span class="kw">FROM</span> <span class="tbl">Inscripto</span> <span class="kw">GROUP BY</span> snum
  ) sub
);</pre>

  <h3>"Dos clases a la misma hora" — self join (ej 3c)</h3>
<pre><span class="kw">SELECT DISTINCT</span> s.sname
<span class="kw">FROM</span>   <span class="tbl">Student</span>   s
<span class="kw">JOIN</span>   <span class="tbl">Inscripto</span> i1 <span class="kw">ON</span> s.snum = i1.snum
<span class="kw">JOIN</span>   <span class="tbl">Inscripto</span> i2 <span class="kw">ON</span> s.snum = i2.snum <span class="kw">AND</span> i1.cname <span class="op">&lt;&gt;</span> i2.cname
<span class="kw">JOIN</span>   <span class="tbl">Class</span>     c1 <span class="kw">ON</span> i1.cname = c1.name
<span class="kw">JOIN</span>   <span class="tbl">Class</span>     c2 <span class="kw">ON</span> i2.cname = c2.name
<span class="kw">WHERE</span>  c1.meets_at = c2.meets_at;</pre>
</section>

<hr>

<!-- ═══ DML ═══ -->
<section class="section" id="dml">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(255,101,132,.15);color:#ff6584">✏️</div>
    <div><h2>DML — Modificar datos</h2></div>
  </div>

<pre><span class="cmt">-- INSERT: agregar filas</span>
<span class="kw">INSERT INTO</span> <span class="tbl">Parts</span> (pid, pname, color) <span class="kw">VALUES</span> (<span class="num">109</span>, <span class="str">'Tornillo'</span>, <span class="str">'azul'</span>);

<span class="cmt">-- INSERT múltiple</span>
<span class="kw">INSERT INTO</span> <span class="tbl">Parts</span> (pid, pname, color) <span class="kw">VALUES</span>
  (<span class="num">110</span>, <span class="str">'Perno'</span>,   <span class="str">'roja'</span>),
  (<span class="num">111</span>, <span class="str">'Resorte'</span>, <span class="str">'verde'</span>);

<span class="cmt">-- UPDATE: modificar filas existentes</span>
<span class="kw">UPDATE</span> <span class="tbl">Empleados</span>
<span class="kw">SET</span>    salary = salary * <span class="num">1.10</span>    <span class="cmt">-- aumento del 10%</span>
<span class="kw">WHERE</span>  eid = <span class="num">101</span>;

<span class="cmt">-- DELETE: eliminar filas</span>
<span class="kw">DELETE FROM</span> <span class="tbl">Catalog</span>
<span class="kw">WHERE</span>  cost > <span class="num">500</span>;</pre>

  <div class="alert alert-r">
    <span>⚠️</span>
    <div><strong>UPDATE y DELETE sin WHERE</strong> afectan <em>todas</em> las filas. Siempre revisá el WHERE antes de ejecutar.</div>
  </div>
</section>

<hr>

<!-- ═══ DDL ═══ -->
<section class="section" id="ddl">
  <div class="section-header">
    <div class="section-icon" style="background:rgba(255,209,102,.15);color:#ffd166">🏗️</div>
    <div><h2>DDL — Definir estructura</h2></div>
  </div>

<pre><span class="cmt">-- CREATE TABLE con restricciones</span>
<span class="kw">CREATE TABLE</span> <span class="tbl">Jugador</span> (
  noJugador  <span class="fn">INT</span>          <span class="kw">PRIMARY KEY</span>,
  nombre     <span class="fn">VARCHAR</span>(<span class="num">50</span>) <span class="kw">NOT NULL</span>,
  edad       <span class="fn">INT</span>          <span class="kw">CHECK</span> (edad >= <span class="num">16</span>),
  equipoId   <span class="fn">INT</span>          <span class="kw">REFERENCES</span> <span class="tbl">Equipo</span>(noEquipo)
);

<span class="cmt">-- ALTER: agregar columna</span>
<span class="kw">ALTER TABLE</span> <span class="tbl">Jugador</span> <span class="kw">ADD</span> posicion <span class="fn">VARCHAR</span>(<span class="num">30</span>);

<span class="cmt">-- ALTER: eliminar columna</span>
<span class="kw">ALTER TABLE</span> <span class="tbl">Jugador</span> <span class="kw">DROP COLUMN</span> posicion;

<span class="cmt">-- DROP: eliminar tabla completa (¡irreversible!)</span>
<span class="kw">DROP TABLE</span> <span class="tbl">Jugador</span>;
<span class="kw">DROP TABLE IF EXISTS</span> <span class="tbl">Jugador</span>;  <span class="cmt">-- sin error si no existe</span></pre>

  <h3>Tipos de datos en PostgreSQL</h3>
  <table>
    <tr><th>Tipo</th><th>Uso</th></tr>
    <tr><td><code>INTEGER / INT</code></td><td>Enteros</td></tr>
    <tr><td><code>REAL / FLOAT</code></td><td>Decimales de punto flotante</td></tr>
    <tr><td><code>NUMERIC(p,s)</code></td><td>Decimal exacto (p dígitos, s decimales)</td></tr>
    <tr><td><code>VARCHAR(n)</code></td><td>Texto variable hasta n caracteres</td></tr>
    <tr><td><code>TEXT</code></td><td>Texto sin límite</td></tr>
    <tr><td><code>BOOLEAN</code></td><td>TRUE / FALSE</td></tr>
    <tr><td><code>DATE</code></td><td>Fecha (YYYY-MM-DD)</td></tr>
    <tr><td><code>TIME</code></td><td>Hora (HH:MM:SS)</td></tr>
    <tr><td><code>TIMESTAMP</code></td><td>Fecha + hora</td></tr>
  </table>
</section>

<p style="text-align:center;color:var(--mu);font-size:.75rem;margin:2rem 0 1rem">BD · UTN · Martín Malgor · 2026</p>

</main>
</body>
</html>
"""

if __name__ == "__main__":
    setup_readonly_user()
    app.run(host="0.0.0.0", port=5000, debug=False)
