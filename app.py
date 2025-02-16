from flask import Flask

app = Flask(__name__)

@app.route("/", methods=['GET'])
def home():
    return """
    <html>
        <head>
            <title>Arpan's Flask App</title>
        </head>
        <body style="text-align: center; margin-top: 50px;">
            <h1>Arpan's Flask App</h1>
            <button onclick="alert('Button Clicked!')">Click Me</button>
        </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)
