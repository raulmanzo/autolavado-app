from flask import Flask, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key_cambiar"

# ---------- INICIALIZAR BASE DE DATOS ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS sucursales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        rol TEXT,
        sucursal_id INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS lavados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        auto TEXT,
        precio REAL,
        fecha TEXT,
        usuario_id INTEGER,
        sucursal_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["rol"] = user[3]
            session["sucursal_id"] = user[4]
            return redirect("/dashboard")
        else:
            return "Usuario o contraseña incorrectos"

    return """
    <h2>Login</h2>
    <form method="POST">
        Usuario: <input name="username"><br><br>
        Contraseña: <input name="password" type="password"><br><br>
        <button type="submit">Ingresar</button>
    </form>
    """

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if session["rol"] == "admin":
        c.execute("""
        SELECT lavados.cliente, lavados.auto, lavados.precio, usuarios.username, sucursales.nombre
        FROM lavados
        JOIN usuarios ON lavados.usuario_id = usuarios.id
        JOIN sucursales ON lavados.sucursal_id = sucursales.id
        """)
    else:
        c.execute("""
        SELECT lavados.cliente, lavados.auto, lavados.precio, usuarios.username, sucursales.nombre
        FROM lavados
        JOIN usuarios ON lavados.usuario_id = usuarios.id
        JOIN sucursales ON lavados.sucursal_id = sucursales.id
        WHERE lavados.usuario_id=?
        """, (session["user_id"],))

    lavados = c.fetchall()

    total = sum(l[2] for l in lavados)

    html = "<h1>Dashboard Autolavado 🚗</h1>"
    html += "<a href='/logout'>Cerrar sesión</a><hr>"

    html += """
    <h2>Registrar lavado</h2>
    <form method="POST" action="/nuevo_lavado">
        Cliente: <input name="cliente"><br><br>
        Auto: <input name="auto"><br><br>
        Precio: <input name="precio" type="number" step="0.01"><br><br>
        <button type="submit">Guardar</button>
    </form>
    """

    html += "<h2>Historial</h2><ul>"
    for l in lavados:
        html += f"<li>{l[0]} - {l[1]} - ${l[2]} - {l[3]} - {l[4]}</li>"
    html += "</ul>"

    html += f"<h3>Total generado: ${total}</h3>"

    if session["rol"] == "admin":
        c.execute("""
        SELECT sucursales.nombre, SUM(lavados.precio)
        FROM lavados
        JOIN sucursales ON lavados.sucursal_id = sucursales.id
        GROUP BY sucursales.nombre
        """)
        totales_sucursal = c.fetchall()

        html += "<h2>Ingresos por Sucursal</h2><ul>"
        for s in totales_sucursal:
            html += f"<li>{s[0]}: ${s[1]}</li>"
        html += "</ul>"

    conn.close()
    return html

# ---------- NUEVO LAVADO ----------
@app.route("/nuevo_lavado", methods=["POST"])
def nuevo_lavado():
    if "user_id" not in session:
        return redirect("/")

    cliente = request.form["cliente"]
    auto = request.form["auto"]
    precio = float(request.form["precio"])
    fecha = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO lavados (cliente, auto, precio, fecha, usuario_id, sucursal_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (cliente, auto, precio, fecha, session["user_id"], session["sucursal_id"]))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------- CREAR USUARIO (SOLO ADMIN MANUALMENTE EN DB AL INICIO) ----------
@app.route("/crear_admin")
def crear_admin():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("INSERT OR IGNORE INTO usuarios (username, password, rol, sucursal_id) VALUES ('admin', '1234', 'admin', 1)")
    conn.commit()
    conn.close()

    return "Admin creado (usuario: admin, password: 1234)"

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run()
