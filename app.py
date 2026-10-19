from flask import Flask, request, redirect, url_for, render_template_string, session, send_file, abort
import sqlite3, secrets, socket, io, os
from datetime import datetime, timezone
import qrcode

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "registros.db")
PORT = int(os.environ.get("PORT", "5000"))
# Para que el QR funcione desde otro teléfono, la app intenta detectar la IP local.
# Si detecta una IP incorrecta, definí DEMO_BASE_URL, por ejemplo:
# Windows: set DEMO_BASE_URL=http://192.168.1.25:5000
BASE_URL_OVERRIDE = os.environ.get("DEMO_BASE_URL", "").strip()
# Render define automáticamente esta variable con el dominio público del servicio.
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if not BASE_URL_OVERRIDE and RENDER_HOST:
    BASE_URL_OVERRIDE = f"https://{RENDER_HOST}"
ADMIN_KEY = os.environ.get("DEMO_ADMIN_KEY", "cambia-esta-clave")
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

PAGE = r"""
<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laboratorio QR</title>
<style>
*{box-sizing:border-box}body{margin:0;padding:20px;background:#101827;color:#edf3ff;font-family:system-ui,Segoe UI,sans-serif}
main{max-width:760px;margin:5vh auto;background:#1b2638;border:1px solid #34445d;border-radius:20px;padding:clamp(20px,4vw,36px)}
.tag{display:inline-block;border-radius:99px;background:#263f36;color:#a8f0c6;padding:6px 12px;font-size:.85rem}
h1{font-size:clamp(1.6rem,5vw,2.2rem)}p,li{line-height:1.55;color:#d1dced}
.card{background:#111a29;padding:20px;border-radius:14px;margin:18px 0}
button,a.btn{display:inline-block;border:0;border-radius:10px;background:#7dd3fc;color:#102033;padding:12px 16px;font-weight:700;text-decoration:none;cursor:pointer}
.secondary{background:#34445d!important;color:white!important}.warning{border-left:4px solid #fbbf24;background:#332c1b;padding:12px;border-radius:8px}
label{display:flex;gap:10px;align-items:flex-start;margin:18px 0;color:#e4eaf4}small{color:#aebbd0}input[type=password]{padding:10px;border-radius:8px}
table{width:100%;border-collapse:collapse;font-size:.9rem}td,th{text-align:left;padding:10px;border-bottom:1px solid #34445d;overflow-wrap:anywhere}
</style></head><body><main>
<span class="tag">LABORATORIO EDUCATIVO · QUISHING</span>
<h1>{{ title }}</h1>
{{ content|safe }}
</main></body></html>
"""

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS visits(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            visited_at TEXT NOT NULL,
            user_agent TEXT,
            event TEXT NOT NULL,
            consent INTEGER NOT NULL
        )""")

def local_ip():
    # Obtiene la dirección de salida local sin enviar datos a Internet.
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.connect(("192.0.2.1",80))
        ip=s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    try:
        for item in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET):
            ip=item[4][0]
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return "127.0.0.1"

def base_url():
    return BASE_URL_OVERRIDE.rstrip("/") if BASE_URL_OVERRIDE else f"http://{local_ip()}:{PORT}"

@app.route("/")
def home():
    return render_template_string(PAGE,title="Demostración de QR malicioso",content="""
    <p>Esta página es una simulación para una exposición de programación y ciberseguridad.
    Un QR puede dirigir a sitios de phishing; por eso hay que revisar el destino antes de abrirlo.</p>
    <div class="card"><h2>Antes de participar</h2>
    <p>Si aceptás, se registrarán la hora de participación, un identificador aleatorio de sesión
    y el tipo de navegador/dispositivo informado por el navegador (user-agent). No se guardan
    número telefónico, IMEI, contraseñas ni ubicación GPS. Estos datos son solo para la demostración.</p>
    <form method="post" action="/participar">
    <label><input type="checkbox" name="consent" value="yes" required>
    Entiendo qué datos se registran y acepto participar en esta demostración educativa.</label>
    <button type="submit">Participar en la demostración</button></form></div>
    <p class="warning"><b>Simulación segura:</b> esta página nunca bloquea el teléfono real, no cambia ajustes
    ni impide cerrar la pestaña.</p><small>Proyecto educativo local. No introduzcas contraseñas reales.</small>
    """)

@app.post("/participar")
def participate():
    if request.form.get("consent") != "yes":
        return redirect(url_for("home"))
    sid=session.get("demo_session_id") or secrets.token_urlsafe(12)
    session["demo_session_id"]=sid
    ua=(request.headers.get("User-Agent","desconocido"))[:300]
    now=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT INTO visits(session_id,visited_at,user_agent,event,consent) VALUES(?,?,?,?,1)",
                    (sid,now,ua,"participó con consentimiento"))
    return render_template_string(PAGE,title="Bloqueo simulado",content="""
    <div class="card" style="text-align:center"><div style="font-size:4rem">🔒</div>
    <h2>PANTALLA DE BLOQUEO (SIMULACIÓN)</h2>
    <p>Tu teléfono real no está bloqueado. Esta pantalla solo existe en el navegador.</p>
    <p>Para completar la demostración, pulsá el botón de abajo.</p>
    <form method="post" action="/desbloquear"><button type="submit">Desbloquear demostración</button></form>
    </div><p class="warning">En un ataque real, un QR podría abrir una página engañosa para robar datos.
    Nunca ingresés contraseñas después de abrir un enlace sospechoso.</p>
    """)

@app.post("/desbloquear")
def unlock():
    return render_template_string(PAGE,title="Demostración finalizada",content="""
    <div class="card"><h2>¡Desbloqueado!</h2><p>La simulación terminó. No se modificó el teléfono.</p>
    <a class="btn" href="/">Volver al inicio</a></div>
    """)

@app.route("/qr.png")
def qr_image():
    target=base_url()+"/"
    img=qrcode.make(target)
    buf=io.BytesIO()
    img.save(buf,format="PNG");buf.seek(0)
    return send_file(buf,mimetype="image/png",download_name="qr_laboratorio.png")

@app.route("/admin")
def admin():
    key=request.args.get("key","")
    if not secrets.compare_digest(key,ADMIN_KEY):
        return render_template_string(PAGE,title="Panel de administración",content="""
        <p>Ingresá la clave de administración en la URL como <code>/admin?key=TU_CLAVE</code>.</p>
        <p>La clave se configura con la variable de entorno DEMO_ADMIN_KEY.</p>"""),401
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory=sqlite3.Row
        rows=con.execute("SELECT id,session_id,visited_at,user_agent,event,consent FROM visits ORDER BY id DESC LIMIT 200").fetchall()
        total=con.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    body=f"<p>Participaciones registradas: <b>{total}</b>. Se muestran las últimas 200.</p>"
    body+="<p>Nota: un user-agent describe el navegador/dispositivo, pero no identifica de forma única a una persona o teléfono.</p>"
    body+="<div style='overflow-x:auto'><table><thead><tr><th>#</th><th>Fecha y hora</th><th>Sesión</th><th>Navegador/dispositivo</th><th>Evento</th><th>Consentimiento</th></tr></thead><tbody>"
    for r in rows:
        vals=[r["id"],r["visited_at"],r["session_id"],r["user_agent"],r["event"],"Sí" if r["consent"] else "No"]
        body+="<tr>"+"".join("<td>"+str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")+"</td>" for v in vals)+"</tr>"
    body+="</tbody></table></div><p><a class='btn secondary' href='/qr.png'>Ver/descargar QR</a></p>"
    return render_template_string(PAGE,title="Panel de administración",content=body)

@app.route("/health")
def health():
    return {"status":"ok","message":"Laboratorio educativo activo"}

if __name__=="__main__":
    init_db()
    print("\\n=== LABORATORIO EDUCATIVO QR ===")
    print(f"En esta computadora: http://127.0.0.1:{PORT}")
    print(f"Desde otro dispositivo conectado a la misma Wi-Fi: {base_url()}")
    print(f"QR: {base_url()}/qr.png")
    print(f"Panel admin: {base_url()}/admin?key={ADMIN_KEY}")
    print("Para cambiar la clave: configure DEMO_ADMIN_KEY antes de iniciar.")
    print("Presioná Ctrl+C para detener el servidor.\\n")
    app.run(host="0.0.0.0",port=PORT,debug=False)
