from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Mi App de Autolavado está funcionando 🚗✨"

if __name__ == "__main__":
    app.run()
