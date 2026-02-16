from flask import Flask, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"


# =========================
# INICIALIZAR BASE DE DATOS
# =========================
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
        precio REAL,
        empleado_id INTEGER,
        sucursal_id INTEGER
    )
    """)

    # Crear admin por defecto si no existe
    c.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not c.fetchone():
        c.execute("""
        INSERT INTO usuarios (username, password, rol)
        VALUES ('admin', '1234', 'admin')
        """)

    conn.commit()
    conn.close()


init_db()


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT id, rol FROM usuarios WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["rol"] = user[1]
            return redirect("/")
        else:
            return "Usuario o contraseña incorrectos"

    return """
    <h2>Login</h2>
    <form method="POST">
        Usuario: <input name="username"><br>
        Contraseña: <input type="password" name="password"><br>
        <button type="submit">Entrar</button>
    </form>
    """


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# HOME
# =========================
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    html = "<h1>Panel de Control</h1>"
    html += "<a href='/logout'>Cerrar sesión</a><hr>"

    # ================= ADMIN =================
    if session["rol"] == "admin":

        # Crear sucursal
        html += """
        <h2>Crear Sucursal</h2>
        <form method="POST" action="/crear_sucursal">
            Nombre: <input name="nombre">
            <button type="submit">Crear</button>
        </form>
        <hr>
        """

        # Obtener sucursales
        c.execute("SELECT id, nombre FROM sucursales")
        sucursales = c.fetchall()

        # Crear usuario
        html += """
        <h2>Crear Usuario</h2>
        <form method="POST" action="/crear_usuario">
            Usuario: <input name="username"><br>
            Contraseña: <input name="password"><br>
            Rol:
            <select name="rol">
                <option value="empleado">Empleado</option>
                <option value="admin">Admin</option>
            </select><br>
            Sucursal:
            <select name="sucursal_id">
        """

        for s in sucursales:
            html += f"<option value='{s[0]}'>{s[1]}</option>"

        html += """
            </select><br>
            <button type="submit">Crear</button>
        </form>
        <hr>
        """

    # ================= REGISTRAR LAVADO =================
    html += """
    <h2>Registrar Lavado</h2>
    <form method="POST" action="/agregar">
        Precio: <input name="precio">
        <button type="submit">Agregar</button>
    </form>
    <hr>
    """

    # ================= HISTORIAL =================
    c.execute("""
    SELECT lavados.id, lavados.precio, usuarios.username, sucursales.nombre
    FROM lavados
    JOIN usuarios ON lavados.empleado_id = usuarios.id
    JOIN sucursales ON lavados.sucursal_id = sucursales.id
    """)
    lavados = c.fetchall()

    html += "<h2>Historial</h2><ul>"
    total_general = 0

    for l in lavados:
        html += f"<li>ID {l[0]} - ${l[1]} - {l[2]} - {l[3]}</li>"
        total_general += l[1]

    html += "</ul>"
    html += f"<h3>Total General: ${total_general}</h3><hr>"

    # ================= TOTAL POR SUCURSAL =================
    c.execute("""
    SELECT sucursales.nombre, SUM(lavados.precio)
    FROM lavados
    JOIN sucursales ON lavados.sucursal_id = sucursales.id
    GROUP BY sucursales.nombre
    """)
    totales_sucursal = c.fetchall()

    html += "<h2>Ingresos por Sucursal</h2><ul>"
    for t in totales_sucursal:
        html += f"<li>{t[0]}: ${t[1]}</li>"
    html += "</ul><hr>"

    # ================= TOTAL POR EMPLEADO =================
    c.execute("""
    SELECT usuarios.username, SUM(lavados.precio)
    FROM lavados
    JOIN usuarios ON lavados.empleado_id = usuarios.id
    GROUP BY usuarios.username
    """)
    totales_empleado = c.fetchall()

    html += "<h2>Ingresos por Empleado</h2><ul>"
    for t in totales_empleado:
        html += f"<li>{t[0]}: ${t[1]}</li>"
    html += "</ul>"

    conn.close()

    return html


# =========================
# CREAR SUCURSAL
# =========================
@app.route("/crear_sucursal", methods=["POST"])
def crear_sucursal():
    if session.get("rol") != "admin":
        return redirect("/")

    nombre = request.form["nombre"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO sucursales (nombre) VALUES (?)", (nombre,))
    conn.commit()
    conn.close()

    return redirect("/")


# =========================
# CREAR USUARIO
# =========================
@app.route("/crear_usuario", methods=["POST"])
def crear_usuario():
    if session.get("rol") != "admin":
        return redirect("/")

    username = request.form["username"]
    password = request.form["password"]
    rol = request.form["rol"]
    sucursal_id = request.form["sucursal_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO usuarios (username, password, rol, sucursal_id)
        VALUES (?, ?, ?, ?)
    """, (username, password, rol, sucursal_id))
    conn.commit()
    conn.close()

    return redirect("/")


# =========================
# AGREGAR LAVADO
# =========================
@app.route("/agregar", methods=["POST"])
def agregar():
    if "user_id" not in session:
        return redirect("/login")

    precio = request.form["precio"]
    empleado_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT sucursal_id FROM usuarios WHERE id=?", (empleado_id,))
    sucursal = c.fetchone()

    c.execute("""
        INSERT INTO lavados (precio, empleado_id, sucursal_id)
        VALUES (?, ?, ?)
    """, (precio, empleado_id, sucursal[0]))
    conn.commit()
    conn.close()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
