from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/greet', methods=['POST'])
def greet():
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name', 'World')
        return jsonify({'message': f'Hello {name}!', 'redirect': '/reservation'})
    else:
        return render_template('reservation.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)