from flask import Flask, render_template

app = Flask(__name__)

# Route untuk menampilkan peta
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return "Halaman Login (Belum dibuat)"

if __name__ == '__main__':
    app.run(debug=True)