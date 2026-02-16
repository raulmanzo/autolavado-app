from flask import Flask, request, render_template_string

app = Flask(__name__)

lavados = []

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        cliente = request.form["cliente"]
        auto = request.form["auto"]
        precio = float(request.form["precio"])
        
        lavados.append({
            "cliente": cliente,
            "auto": auto,
            "precio": precio
        })

    total = sum(l["precio"] for l in lavados)

    return render_template_string("""
        <h1>Control de Autolavado 🚗✨</h1>

        <h2>Registrar nuevo lavado</h2>
        <form method="POST">
            Cliente: <input name="cliente"><br><br>
            Auto: <input name="auto"><br><br>
            Precio: <input name="precio" type="number" step="0.01"><br><br>
            <button type="submit">Guardar</button>
        </form>

        <h2>Lavados registrados</h2>
        <ul>
            {% for lavado in lavados %}
                <li>{{ lavado.cliente }} - {{ lavado.auto }} - ${{ lavado.precio }}</li>
            {% endfor %}
        </ul>

        <h3>Total generado: ${{ total }}</h3>
    """, lavados=lavados, total=total)

if __name__ == "__main__":
    app.run()
