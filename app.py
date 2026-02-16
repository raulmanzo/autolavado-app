from flask import Flask, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

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
    CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
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
        empleado_id INTEGER,
        sucursal_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- PÁGINA PRINCIPAL ----------
@app.route("/")
def home():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Obtener datos básicos
    c.execute("SELECT * FROM sucursales")
    sucursales = c.fetchall()

    c.execute("SELECT * FROM empleados")
    empleados = c.fetchall()

    c.execute("""
    SELECT lavados.cliente, lavados.auto, lavados.precio,
           empleados.nombre, sucursales.nombre
    FROM lavados
    JOIN empleados ON lavados.empleado_id = empleados.id
    JOIN sucursales ON lavados.sucursal_id = sucursales.id
    """)
    lavados = c.fetchall()

    # Total general
    total_general = sum(l[2] for l in lavados)

    # Total por sucursal
    c.execute("""
    SELECT sucursales.nombre, SUM(lavados.precio)
    FROM lavados
    JOIN sucursales ON lavados.sucursal_id = sucursales.id
    GROUP BY sucursales.nombre
    """)
    totales_sucursal = c.fetchall()

    # Total por empleado
    c.execute("""
    SELECT empleados.nombre, SUM(lavados.precio)
    FROM lavados
    JOIN empleados ON lavados.empleado_id = empleados.id
    GROUP BY empleados.nombre
    """)
    totales_empleado = c.fetchall()

    conn.close()

    html = "<h1>Autolavado Pro 🚗💰</h1>"

    html += """
    <a href='/nueva_sucursal'>➕ Nueva Sucursal</a> |
    <a href='/nuevo_empleado'>➕ Nuevo Empleado</a>
    <hr>
    """

    # ---------- FORMULARIO LAVADO ----------
    html += """
    <h2>Registrar lavado</h2>
    <form method="POST" action="/nuevo_lavado">
        Cliente: <input name="cliente"><br><br>
        Auto: <input name="auto"><br><br>
        Precio: <input name="precio" type="number" step="0.01"><br><br>

        Empleado:
        <select name="empleado">
    """

    for e in empleados:
        html += f"<option value='{e[0]}'>{e[1]}</option>"

    html += "</select><br><br>Sucursal:<select name='sucursal'>"

    for s in sucursales:
        html += f"<option value='{s[0]}'>{s[1]}</option>"

    html += "</select><br><br><button type='submit'>Guardar</button></form>"

    # ---------- HISTORIAL ----------
    html += "<h2>Historial</h2><ul>"

    for l in lavados:
        html += f"<li>{l[0]} - {l[1]} - ${l[2]} - {l[3]} - {l[4]}</li>"

    html += "</ul>"

    # ---------- TOTALES ----------
    html += f"<h3>Total General: ${total_general}</h3>"

    html += "<h2>Ingresos por Sucursal</h2><ul>"
    for s in totales_sucursal:
        html += f"<li>{s[0]}: ${s[1]}</li>"
    html += "</ul>"

    html += "<h2>Ingresos por Empleado</h2><ul>"
    for e in totales_empleado:
        html += f"<li>{e[0]}: ${e[1]}</li>"
    html += "</ul>"

    return html


# ---------- CREAR SUCURSAL ----------
@app.route("/nueva_sucursal", methods=["GET", "POST"])
def nueva_sucursal():
    if request.method == "POST":
        nombre = request.form["nombre"]
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO sucursales (nombre) VALUES (?)", (nombre,))
        conn.commit()
        conn.close()
        return redirect("/")

    return """
    <h2>Crear nueva sucursal</h2>
    <form method="POST">
        Nombre: <input name="nombre"><br><br>
        <button type="submit">Guardar</button>
    </form>
    """


# ---------- CREAR EMPLEADO ----------
@app.route("/nuevo_empleado", methods=["GET", "POST"])
def nuevo_empleado():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        sucursal_id = request.form["sucursal"]
        c.execute("INSERT INTO empleados (nombre, sucursal_id) VALUES (?, ?)",
                  (nombre, sucursal_id))
        conn.commit()
        conn.close()
        return redirect("/")

    c.execute("SELECT * FROM sucursales")
    sucursales = c.fetchall()
    conn.close()

    html = """
    <h2>Crear nuevo empleado</h2>
    <form method="POST">
        Nombre: <input name="nombre"><br><br>
        Sucursal:
        <select name="sucursal">
    """

    for s in sucursales:
        html += f"<option value='{s[0]}'>{s[1]}</option>"

    html += "</select><br><br><button type='submit'>Guardar</button></form>"

    return html


# ---------- REGISTRAR LAVADO ----------
@app.route("/nuevo_lavado", methods=["POST"])
def nuevo_lavado():
    cliente = request.form["cliente"]
    auto = request.form["auto"]
    precio = float(request.form["precio"])
    empleado_id = int(request.form["empleado"])
    sucursal_id = int(request.form["sucursal"])
    fecha = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO lavados (cliente, auto, precio, fecha, empleado_id, sucursal_id)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (cliente, auto, precio, fecha, empleado_id, sucursal_id))

    conn.commit()
    conn.close()

    return redirect("/")


if __name__ == "__main__":
    app.run()
