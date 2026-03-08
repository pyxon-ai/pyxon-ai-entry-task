import os
import sqlite3
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from main import process_document
from src.storage import StorageManager
from src.benchmark import BenchmarkSuite

app = Flask(__name__)
# Configure uploads folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize storage for searching
storage = StorageManager()

@app.route('/')
def index():
    """Serve the main UI page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle document uploads and parsing."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        # We save the file temporarily to process it
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            # Re-use our existing logic!
            doc_id, stored_filename, chunks = process_document(file_path)
            # Clean up the temp file after its embedded
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return jsonify({
                'message': f'Successfully processed {stored_filename}',
                'doc_id': doc_id,
                'total_chunks': len(chunks)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/documents', methods=['GET'])
def get_documents_list():
    """Returns a list of all processed files."""
    try:
        docs = storage.get_all_documents()
        return jsonify({'documents': docs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['POST'])
def search_docs():
    """Handle semantic search queries."""
    data = request.json
    query = data.get('query')
    filter_file = data.get('filter_file') # We now accept the dropdown selection!
    
    # If the user selected 'All Files' or default, it will come through empty, so we pass None
    if not filter_file or filter_file.lower() == 'all files':
         filter_file = None
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
        
    try:
        # Search using our new mpnet-base model
        results = storage.search(query, top_k=5, filter_filename=filter_file)
        
        # We evaluate the quality just to show it
        suite = BenchmarkSuite(storage)
        chunks_only = [res['text'] for res in results]
        quality = 0
        if chunks_only:
             quality = suite.evaluate_chunk_quality(chunks_only)
             
        formatted_results = []
        for i, res in enumerate(results):
             metadata = res.get('metadata', {})
             formatted_results.append({
                 'text': res['text'],
                 'filename': metadata.get('filename', 'Unknown'),
                 'chunk_index': metadata.get('chunk_index', 'Unknown')
             })
             
        return jsonify({
            'results': formatted_results,
            'quality_score': round(quality * 100, 1)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Pyxon Web Server for Hugging Face Spaces...")
    print("Open http://0.0.0.0:7860 in your browser if running locally.")
    # Hugging Face Spaces REQUIRE the app to bind to 0.0.0.0 and port 7860
    app.run(host="0.0.0.0", port=7860, debug=False)
