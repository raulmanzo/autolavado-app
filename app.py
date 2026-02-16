from flask import Flask, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Tabla de sucursales
    c.execute("""
    CREATE TABLE IF NOT EXISTS sucursales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    # Tabla de empleados
    c.execute("""
    CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        sucursal_id INTEGER
    )
    """)

    # Tabla de lavados
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

@app.route("/", methods=["GET", "POST"])
def home():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        cliente = request.form["cliente"]
        auto = request.form["auto"]
        precio = float(request.form["precio"])
        empleado_id = int(request.form["empleado"])
        sucursal_id = int(request.form["sucursal"])
        fecha = datetime.now().strftime("%Y-%m-%d")

        c.execute("""
        INSERT INTO lavados (cliente, auto, precio, fecha, empleado_id, sucursal_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (cliente, auto, precio, fecha, empleado_id, sucursal_id))

        conn.commit()
        return redirect("/")

    # Obtener datos
    c.execute("SELECT * FROM sucursales")
    sucursales = c.fetchall()

    c.execute("SELECT * FROM empleados")
    empleados = c.fetchall()

    c.execute("""
    SELECT lavados.cliente, lavados.auto, lavados.precio, empleados.nombre, sucursales.nombre
    FROM lavados
    JOIN empleados ON lavados.empleado_id = empleados.id
    JOIN sucursales ON lavados.sucursal_id = sucursales.id
    """)
    lavados = c.fetchall()

    total = sum(l[2] for l in lavados)

    conn.close()

    html = "<h1>Autolavado Pro 🚗</h1>"

    html += """
    <h2>Registrar lavado</h2>
    <form method="POST">
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

    html += "<h2>Historial</h2><ul>"

    for l in lavados:
        html += f"<li>{l[0]} - {l[1]} - ${l[2]} - {l[3]} - {l[4]}</li>"

    html += "</ul>"
    html += f"<h3>Total generado: ${total}</h3>"

    return html

if __name__ == "__main__":
    app.run()
