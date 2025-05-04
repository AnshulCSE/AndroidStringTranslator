from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os
import tempfile
from pathlib import Path
import subprocess
import logging
import json
from werkzeug.utils import secure_filename

# This is the text comment.

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
RESULTS_FOLDER = Path("results")
RESULTS_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Supported translation methods
TRANSLATION_METHODS = {
    'free': 'Free Dictionary Translator',
    'dictionary': 'Basic Dictionary Lookup'
}

@app.route('/')
def index():
    return render_template('index.html', apis=TRANSLATION_METHODS)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if a file was uploaded
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    # Check if user submitted an empty form
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    # Check if file is an XML file
    if not file.filename.endswith('.xml'):
        flash('File must be an XML file', 'error')
        return redirect(url_for('index'))
    
    # Save the file
    filename = secure_filename(file.filename)
    file_path = Path(app.config['UPLOAD_FOLDER']) / filename
    file.save(file_path)
    
    # Get translation options from form
    languages = request.form.get('languages', '')
    api = request.form.get('api', 'free')
    skip_existing = 'skip_existing' in request.form
    preserve_comments = 'preserve_comments' in request.form
    
    # Store translation info in session
    session['translation_info'] = {
        'file_path': str(file_path),
        'languages': languages,
        'api': api,
        'skip_existing': skip_existing,
        'preserve_comments': preserve_comments
    }
    
    flash('File uploaded successfully', 'success')
    return redirect(url_for('confirm'))

@app.route('/confirm')
def confirm():
    if 'translation_info' not in session:
        flash('No translation information', 'error')
        return redirect(url_for('index'))
    
    translation_info = session['translation_info']
    languages = translation_info['languages'].split(',')
    language_count = len(languages)
    
    return render_template(
        'confirm.html', 
        translation_info=translation_info,
        language_count=language_count,
        languages=languages,
        api_name=TRANSLATION_METHODS[translation_info['api']]
    )

@app.route('/translate', methods=['POST'])
def translate():
    if 'translation_info' not in session:
        flash('No translation information', 'error')
        return redirect(url_for('index'))   
    
    translation_info = session['translation_info']
    
    # Create a directory for results
    result_dir = Path(app.config['RESULTS_FOLDER']) / f"result_{int(Path(translation_info['file_path']).stat().st_mtime)}"
    result_dir.mkdir(exist_ok=True)
    
    # Build command arguments
    args = [
        'python', 'android_string_translator.py', 'translate',
        '--source', translation_info['file_path'],
        '--output-dir', str(result_dir),
        '--languages', translation_info['languages'],
        '--api', translation_info['api']
    ]
    
    if translation_info['skip_existing']:
        args.append('--skip-existing')
    else:
        args.append('--overwrite-existing')
    
    if translation_info['preserve_comments']:
        args.append('--preserve-comments')
    else:
        args.append('--no-preserve-comments')
    
    try:
        # Run translation process
        logger.debug(f"Running command: {' '.join(args)}")
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        logger.debug(f"Command output: {result.stdout}")
        
        # Store result in session
        session['translation_result'] = {
            'stdout': result.stdout,
            'result_dir': str(result_dir),
            'languages': translation_info['languages'].split(',')
        }
        
        flash('Translation completed successfully', 'success')
        return redirect(url_for('results'))
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Translation failed: {e.stderr}")
        flash(f'Translation failed: {e.stderr}', 'error')
        return redirect(url_for('confirm'))

@app.route('/results')
def results():
    if 'translation_result' not in session:
        flash('No translation results', 'error')
        return redirect(url_for('index'))
    
    translation_result = session['translation_result']
    
    # Get file sizes for each language
    files_info = []
    for lang in translation_result['languages']:
        if lang == 'en':
            file_path = Path(translation_result['result_dir']) / "values" / "strings.xml"
        else:
            file_path = Path(translation_result['result_dir']) / f"values-{lang}" / "strings.xml"
        
        if file_path.exists():
            size = file_path.stat().st_size
            files_info.append({
                'language': lang,
                'size': f"{size / 1024:.1f} KB",
                'path': str(file_path)
            })
    
    return render_template(
        'results.html',
        result=translation_result,
        files_info=files_info
    )

@app.route('/download/<path:filename>')
def download(filename):
    filepath = Path(filename)
    if not filepath.exists():
        flash('File not found', 'error')
        return redirect(url_for('results'))
    
    return send_file(filepath, as_attachment=True)

@app.route('/supported-languages')
def supported_languages():
    try:
        result = subprocess.run(
            ['python', 'android_string_translator.py', 'list-languages'],
            capture_output=True, text=True, check=True
        )
        
        # Parse the output to get supported languages
        output = result.stdout
        supported_langs = []
        
        for line in output.splitlines():
            line = line.strip()
            if line and line.startswith('  '):
                lang_code = line.strip()
                supported_langs.append(lang_code)
        
        return render_template(
            'languages.html',
            supported_langs=supported_langs
        )
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get supported languages: {e.stderr}")
        flash(f'Failed to get supported languages: {e.stderr}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)