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
    CREATE TABLE IF NOT EXISTS paquetes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        precio REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS lavados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paquete_id INTEGER,
        precio REAL,
        empleado_id INTEGER,
        sucursal_id INTEGER
    )
    """)

    # Crear admin por defecto
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

    # ================= ADMIN ZONA =================
    if session["rol"] == "admin":

        # Crear sucursal
        html += """
        <h2>Crear Sucursal</h2>
        <form method="POST" action="/crear_sucursal">
            Nombre: <input name="nombre">
            <button type="submit">Crear</button>
        </form><hr>
        """

        # Crear paquete
        html += """
        <h2>Crear Paquete</h2>
        <form method="POST" action="/crear_paquete">
            Nombre: <input name="nombre">
            Precio: <input name="precio">
            <button type="submit">Crear</button>
        </form><hr>
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
        </form><hr>
        """

    # ================= REGISTRAR LAVADO =================
    c.execute("SELECT id, nombre, precio FROM paquetes")
    paquetes = c.fetchall()

    html += """
    <h2>Registrar Lavado</h2>
    <form method="POST" action="/agregar">
        Paquete:
        <select name="paquete_id">
    """

    for p in paquetes:
        html += f"<option value='{p[0]}'>{p[1]} - ${p[2]}</option>"

    html += """
        </select>
        <button type="submit">Registrar</button>
    </form><hr>
    """

    # ================= HISTORIAL =================

    if session["rol"] == "admin":
        c.execute("""
        SELECT lavados.id, paquetes.nombre, lavados.precio,
               usuarios.username, sucursales.nombre
        FROM lavados
        JOIN paquetes ON lavados.paquete_id = paquetes.id
        JOIN usuarios ON lavados.empleado_id = usuarios.id
        JOIN sucursales ON lavados.sucursal_id = sucursales.id
        """)
    else:
        c.execute("""
        SELECT lavados.id, paquetes.nombre, lavados.precio,
               usuarios.username, sucursales.nombre
        FROM lavados
        JOIN paquetes ON lavados.paquete_id = paquetes.id
        JOIN usuarios ON lavados.empleado_id = usuarios.id
        JOIN sucursales ON lavados.sucursal_id = sucursales.id
        WHERE lavados.sucursal_id = (
            SELECT sucursal_id FROM usuarios WHERE id=?
        )
        """, (session["user_id"],))

    lavados = c.fetchall()

    html += "<h2>Historial</h2><ul>"
    total_general = 0

    for l in lavados:
        html += f"<li>ID {l[0]} - {l[1]} - ${l[2]} - {l[3]} - {l[4]}</li>"
        total_general += l[2]

    html += "</ul>"
    html += f"<h3>Total General: ${total_general}</h3><hr>"

    # ================= TOTALES SOLO ADMIN =================
    if session["rol"] == "admin":

        # Total por sucursal
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

        # Total por empleado
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
# CREAR PAQUETE
# =========================
@app.route("/crear_paquete", methods=["POST"])
def crear_paquete():
    if session.get("rol") != "admin":
        return redirect("/")

    nombre = request.form["nombre"]
    precio = request.form["precio"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO paquetes (nombre, precio) VALUES (?, ?)", (nombre, precio))
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

    paquete_id = request.form["paquete_id"]
    empleado_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Precio del paquete
    c.execute("SELECT precio FROM paquetes WHERE id=?", (paquete_id,))
    precio = c.fetchone()[0]

    # Sucursal del empleado
    c.execute("SELECT sucursal_id FROM usuarios WHERE id=?", (empleado_id,))
    sucursal = c.fetchone()[0]

    c.execute("""
        INSERT INTO lavados (paquete_id, precio, empleado_id, sucursal_id)
        VALUES (?, ?, ?, ?)
    """, (paquete_id, precio, empleado_id, sucursal))

    conn.commit()
    conn.close()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
