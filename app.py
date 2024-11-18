import os
import uuid
from flask import Flask, request, jsonify, render_template, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'shared'  # Folder where the files will be stored
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'zip', 'mp4'}
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Max file size 500 MB

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Check if the file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')  # Serve the index.html page

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())  # Generate a unique file ID
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        
        # Save the file incrementally in chunks to avoid memory overload
        with open(file_path, 'wb') as f:
            while True:
                chunk = file.stream.read(4096)  # Read in chunks of 4KB
                if not chunk:
                    break
                f.write(chunk)

        # Respond with file_id and filename
        return jsonify({"file_id": file_id, "filename": filename})

    return jsonify({"error": "Invalid file type"}), 400

@app.route('/transfer/<file_id>/<filename>', methods=['GET'])
def transfer_file(file_id, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")

    if os.path.exists(file_path):
        def generate():
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):  # Read in 8KB chunks
                    yield chunk
        
        # Handle range requests for partial file download
        byte_range = request.headers.get('Range', None)
        if byte_range:
            start_byte, end_byte = byte_range.strip().split('=')[1].split('-')
            start_byte = int(start_byte)
            end_byte = int(end_byte) if end_byte else None

            with open(file_path, 'rb') as f:
                f.seek(start_byte)
                data = f.read(end_byte - start_byte if end_byte else None)
                return Response(data, status=206, mimetype='application/octet-stream', 
                                content_type='application/octet-stream',
                                headers={'Content-Range': f"bytes {start_byte}-{end_byte or ''}/{os.path.getsize(file_path)}"})

        return Response(generate(), mimetype='application/octet-stream')

    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
