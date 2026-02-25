from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
from PyPDF2 import PdfMerger
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
MERGED_FOLDER = 'merged'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MERGED_FOLDER'] = MERGED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MERGED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files[]')
        
        if len(files) < 2:
            return jsonify({'error': 'Please upload at least 2 PDF files'}), 400
        
        uploaded_files = []
        session_id = str(uuid.uuid4())
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        os.makedirs(session_folder, exist_ok=True)
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(session_folder, filename)
                file.save(filepath)
                uploaded_files.append({
                    'name': filename,
                    'path': filepath,
                    'size': os.path.getsize(filepath)
                })
            else:
                return jsonify({'error': f'Invalid file: {file.filename}. Only PDF files are allowed'}), 400
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'files': uploaded_files,
            'count': len(uploaded_files)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/merge', methods=['POST'])
def merge_pdfs():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        if not os.path.exists(session_folder):
            return jsonify({'error': 'Session not found'}), 404
        
        # Get all PDF files in session folder
        pdf_files = sorted([f for f in os.listdir(session_folder) if f.endswith('.pdf')])
        
        if len(pdf_files) < 2:
            return jsonify({'error': 'At least 2 PDF files required'}), 400
        
        # Merge PDFs
        merger = PdfMerger()
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(session_folder, pdf_file)
            merger.append(pdf_path)
        
        # Save merged PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        merged_filename = f'merged_{timestamp}.pdf'
        merged_path = os.path.join(app.config['MERGED_FOLDER'], merged_filename)
        
        merger.write(merged_path)
        merger.close()
        
        return jsonify({
            'success': True,
            'merged_file': merged_filename,
            'download_url': f'/api/download/{merged_filename}'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Merge failed: {str(e)}'}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        file_path = os.path.join(app.config['MERGED_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup/<session_id>', methods=['DELETE'])
def cleanup_session(session_id):
    try:
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        if os.path.exists(session_folder):
            for file in os.listdir(session_folder):
                os.remove(os.path.join(session_folder, file))
            os.rmdir(session_folder)
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)