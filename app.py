from flask import Flask, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"


# =========================
# CONEXIÓN SEGURA
# =========================
def get_db():
    return sqlite3.connect("database.db", timeout=10)


# =========================
# INICIALIZAR BASE
# =========================
def init_db():
    conn = get_db()
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

    # Crear admin si no existe
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
        conn = get_db()
        c = conn.cursor()

        username = request.form["username"]
        password = request.form["password"]

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
# DASHBOARD
# =========================
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    user_id = session["user_id"]
    rol = session["rol"]

    # Obtener sucursal del usuario
    c.execute("SELECT sucursal_id FROM usuarios WHERE id=?", (user_id,))
    sucursal_usuario = c.fetchone()[0]

    # =======================
    # FILTRO POR ROL
    # =======================
    if rol == "admin":
        c.execute("""
            SELECT lavados.id, paquetes.nombre, lavados.precio, usuarios.username, sucursales.nombre
            FROM lavados
            JOIN paquetes ON lavados.paquete_id = paquetes.id
            JOIN usuarios ON lavados.empleado_id = usuarios.id
            JOIN sucursales ON lavados.sucursal_id = sucursales.id
        """)
    else:
        c.execute("""
            SELECT lavados.id, paquetes.nombre, lavados.precio, usuarios.username, sucursales.nombre
            FROM lavados
            JOIN paquetes ON lavados.paquete_id = paquetes.id
            JOIN usuarios ON lavados.empleado_id = usuarios.id
            JOIN sucursales ON lavados.sucursal_id = sucursales.id
            WHERE lavados.sucursal_id = ?
        """, (sucursal_usuario,))

    lavados = c.fetchall()

    # Totales por empleado
    if rol == "admin":
        c.execute("""
            SELECT usuarios.username, SUM(lavados.precio)
            FROM lavados
            JOIN usuarios ON lavados.empleado_id = usuarios.id
            GROUP BY usuarios.username
        """)
    else:
        c.execute("""
            SELECT usuarios.username, SUM(lavados.precio)
            FROM lavados
            JOIN usuarios ON lavados.empleado_id = usuarios.id
            WHERE lavados.sucursal_id = ?
            GROUP BY usuarios.username
        """, (sucursal_usuario,))

    totales_empleado = c.fetchall()

    # Totales por sucursal
    c.execute("""
        SELECT sucursales.nombre, SUM(lavados.precio)
        FROM lavados
        JOIN sucursales ON lavados.sucursal_id = sucursales.id
        GROUP BY sucursales.nombre
    """)
    totales_sucursal = c.fetchall()

    # Obtener paquetes
    c.execute("SELECT * FROM paquetes")
    paquetes = c.fetchall()

    # Obtener sucursales
    c.execute("SELECT * FROM sucursales")
    sucursales = c.fetchall()

    conn.close()

    html = "<h1>Panel Principal</h1>"
    html += '<a href="/logout">Cerrar sesión</a><br><br>'

    # =====================
    # ADMIN: CREAR SUCURSAL
    # =====================
    if rol == "admin":
        html += """
        <h3>Crear Sucursal</h3>
        <form method="POST" action="/crear_sucursal">
            Nombre: <input name="nombre">
            <button type="submit">Crear</button>
        </form>
        """

        html += "<h3>Crear Empleado</h3>"
        html += """
        <form method="POST" action="/crear_usuario">
            Usuario: <input name="username">
            Contraseña: <input name="password">
            Rol:
            <select name="rol">
                <option value="empleado">Empleado</option>
                <option value="admin">Admin</option>
            </select>
            Sucursal:
            <select name="sucursal_id">
        """
        for s in sucursales:
            html += f"<option value='{s[0]}'>{s[1]}</option>"
        html += """
            </select>
            <button type="submit">Crear</button>
        </form>
        """

        html += "<h3>Crear Paquete</h3>"
        html += """
        <form method="POST" action="/crear_paquete">
            Nombre: <input name="nombre">
            Precio: <input name="precio">
            <button type="submit">Crear</button>
        </form>
        """

    # =====================
    # REGISTRAR LAVADO
    # =====================
    html += "<h3>Registrar Lavado</h3>"
    html += """
    <form method="POST" action="/agregar">
        Paquete:
        <select name="paquete_id">
    """
    for p in paquetes:
        html += f"<option value='{p[0]}'>{p[1]} - ${p[2]}</option>"
    html += """
        </select>
        <button type="submit">Registrar</button>
    </form>
    """

    # =====================
    # LISTA DE LAVADOS
    # =====================
    html += "<h3>Lavados Registrados</h3>"
    for l in lavados:
        html += f"{l[1]} - ${l[2]} - {l[3]} - {l[4]}<br>"

    # =====================
    # TOTALES
    # =====================
    html += "<h3>Total por Empleado</h3>"
    for t in totales_empleado:
        html += f"{t[0]}: ${t[1] if t[1] else 0}<br>"

    html += "<h3>Total por Sucursal</h3>"
    for t in totales_sucursal:
        html += f"{t[0]}: ${t[1] if t[1] else 0}<br>"

    return html


# =========================
# CREAR SUCURSAL
# =========================
@app.route("/crear_sucursal", methods=["POST"])
def crear_sucursal():
    if session.get("rol") != "admin":
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO sucursales (nombre) VALUES (?)", (request.form["nombre"],))
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

    conn = get_db()
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO usuarios (username, password, rol, sucursal_id)
            VALUES (?, ?, ?, ?)
        """, (
            request.form["username"],
            request.form["password"],
            request.form["rol"],
            request.form["sucursal_id"]
        ))
        conn.commit()
    except:
        conn.close()
        return "Usuario ya existe"

    conn.close()
    return redirect("/")


# =========================
# CREAR PAQUETE
# =========================
@app.route("/crear_paquete", methods=["POST"])
def crear_paquete():
    if session.get("rol") != "admin":
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO paquetes (nombre, precio)
        VALUES (?, ?)
    """, (request.form["nombre"], request.form["precio"]))
    conn.commit()
    conn.close()
    return redirect("/")


# =========================
# REGISTRAR LAVADO
# =========================
@app.route("/agregar", methods=["POST"])
def agregar():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    paquete_id = request.form["paquete_id"]
    empleado_id = session["user_id"]

    c.execute("SELECT precio FROM paquetes WHERE id=?", (paquete_id,))
    precio = c.fetchone()[0]

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
    app.run()
