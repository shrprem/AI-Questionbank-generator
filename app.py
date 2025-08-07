import os
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import pandas as pd
import uuid
import time
import threading
from flask_cors import CORS
from dotenv import load_dotenv
import signal
import sys

# Import your OpenAI service
from openai_service import OpenAIService

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
GENERATED_FILES = 'generated'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_FILES'] = GENERATED_FILES

# Create directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FILES'], exist_ok=True)

# Global thread tracking
active_threads = []

# Initialize OpenAI service with better error handling
try:
    openai_service = OpenAIService()
    print("OpenAI service initialized successfully")
    
    # Only validate if we have sufficient quota
    try:
        if openai_service.validate_api_key():
            print("OpenAI API key is valid")
        else:
            print("WARNING: OpenAI API key validation failed")
    except Exception as quota_error:
        if "429" in str(quota_error) or "quota" in str(quota_error).lower():
            print("INFO: OpenAI quota exceeded - service will be available once quota is restored")
            print("The application will still work for testing, but question generation requires active quota")
        else:
            print(f"API validation error: {quota_error}")
            
except Exception as e:
    print(f"Failed to initialize OpenAI service: {e}")
    openai_service = None

# In-memory storage for job status
jobs = {}

# Static file serving
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path, max_pages=None):
    """Extract text from PDF with optimization for large files"""
    text = ""
    try:
        with fitz.open(file_path) as doc:
            total_pages = len(doc)
            print(f"Processing PDF: {file_path} with {total_pages} pages")
            
            # Limit pages for very large PDFs
            if max_pages and total_pages > max_pages:
                print(f"Large PDF detected ({total_pages} pages). Processing first {max_pages} pages only.")
                total_pages = max_pages
            
            for page_num in range(min(total_pages, 500)):  # Hard limit of 500 pages
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    text += page_text
                    
                    # Print progress less frequently for large files
                    if page_num % 50 == 0 or page_num < 10:
                        print(f"Page {page_num + 1}: extracted {len(page_text)} characters")
                    
                    # Memory management: break if we have enough content
                    if len(text) > 500000:  # 500KB of text should be sufficient
                        print(f"Sufficient text extracted ({len(text)} characters). Stopping at page {page_num + 1}")
                        break
                        
                except Exception as page_error:
                    print(f"Error processing page {page_num + 1}: {page_error}")
                    continue
        
        print(f"Total extracted text length: {len(text)}")
        if len(text) < 100:
            print("WARNING: Very little text extracted. PDF might be image-based.")
            print(f"Sample text: {text[:200]}")
        
        return text
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""

def generate_excel(questions_text, output_file):
    """Generate Excel file from the questions text"""
    print(f"Generated questions text: {questions_text[:500]}...")
    
    # Parse the text into sections
    sections = {
        "MCQ": [],
        "Short Answer": [],
        "Long Answer": []
    }

    lines = questions_text.split('\n')
    current_section = None
    current_question = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Identify sections (case insensitive)
        line_upper = line.upper()
        if "MULTIPLE CHOICE" in line_upper or line_upper.startswith("MCQ"):
            current_section = "MCQ"
            print(f"Found MCQ section: {line}")
            continue
        elif "SHORT ANSWER" in line_upper:
            current_section = "Short Answer"
            print(f"Found Short Answer section: {line}")
            continue
        elif "LONG ANSWER" in line_upper:
            current_section = "Long Answer"
            print(f"Found Long Answer section: {line}")
            continue

        if current_section is None:
            continue

        # Handle MCQs
        if current_section == "MCQ":
            if line.startswith(('Q', '1.', '2.', '3.', '4.', '5.')):
                if current_question and "Question" in current_question:
                    sections[current_section].append(current_question.copy())
                current_question = {"Question": line, "Options": [], "Answer": ""}
            elif line.startswith(('A)', 'B)', 'C)', 'D)', 'A.', 'B.', 'C.', 'D.')):
                if "Question" in current_question:
                    current_question["Options"].append(line)
            elif "ANSWER:" in line_upper or "CORRECT:" in line_upper:
                if "Question" in current_question:
                    current_question["Answer"] = line

        # Handle Short and Long Answer questions
        elif current_section in ["Short Answer", "Long Answer"]:
            if line.startswith(('Q', '1.', '2.', '3.', '4.', '5.')):
                if current_question and "Question" in current_question:
                    sections[current_section].append(current_question.copy())
                current_question = {"Question": line}

    # Don't forget to add the last question
    if current_question and "Question" in current_question and current_section:
        sections[current_section].append(current_question.copy())

    # Debug: Print what we parsed
    for section, questions in sections.items():
        print(f"{section}: {len(questions)} questions")
        if questions:
            print(f"First question: {questions[0]}")

    # Create Excel file with multiple sheets
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # MCQ sheet
            mcq_data = []
            for q in sections["MCQ"]:
                options = "\n".join(q.get("Options", []))
                mcq_data.append({
                    "Question": q.get("Question", ""),
                    "Options": options,
                    "Answer": q.get("Answer", "")
                })
            
            mcq_df = pd.DataFrame(mcq_data) if mcq_data else pd.DataFrame(columns=["Question", "Options", "Answer"])
            mcq_df.to_excel(writer, sheet_name="MCQs", index=False)

            # Short Answer sheet
            short_data = [{"Question": q.get("Question", "")} for q in sections["Short Answer"]]
            short_df = pd.DataFrame(short_data) if short_data else pd.DataFrame(columns=["Question"])
            short_df.to_excel(writer, sheet_name="Short Answer", index=False)

            # Long Answer sheet
            long_data = [{"Question": q.get("Question", "")} for q in sections["Long Answer"]]
            long_df = pd.DataFrame(long_data) if long_data else pd.DataFrame(columns=["Question"])
            long_df.to_excel(writer, sheet_name="Long Answer", index=False)
            
        print(f"Excel file created successfully: {output_file}")
        return True
    except Exception as e:
        print(f"Error creating Excel file: {e}")
        return False

def process_files(job_id, reference_file, syllabus_file, mcq_count, short_count, long_count, custom_instructions):
    """Process the uploaded files and generate questions with better error handling"""
    try:
        jobs[job_id]["status"] = "processing"
        print(f"Starting processing for job {job_id}")

        # Check if OpenAI service is available
        if not openai_service:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "OpenAI service is not available. Please check your API key configuration."
            return

        # Extract text from PDFs with limits for large files
        print("Extracting text from reference file...")
        reference_text = extract_text_from_pdf(reference_file, max_pages=1000)# Limit to 200 pages
        print("Extracting text from syllabus file...")
        syllabus_text = extract_text_from_pdf(syllabus_file, max_pages=50)   # Limit to 50 pages

        if not reference_text.strip():
            print("ERROR: No text extracted from reference file")
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "No text could be extracted from the reference PDF."
            return

        if not syllabus_text.strip():
            print("ERROR: No text extracted from syllabus file") 
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "No text could be extracted from the syllabus PDF."
            return

        jobs[job_id]["status"] = "generating_questions"
        print("Calling OpenAI API...")

        # Call OpenAI API using the service
        api_response = openai_service.generate_questions(
            reference_text,
            syllabus_text,
            mcq_count,
            short_count,
            long_count,
            custom_instructions
        )

        if not api_response["success"]:
            jobs[job_id]["status"] = "error"
            if "429" in str(api_response["error"]) or "quota" in str(api_response["error"]).lower():
                jobs[job_id]["error"] = "API quota exceeded. Please add credits to your OpenAI account and try again."
            else:
                jobs[job_id]["error"] = f"Failed to generate questions: {api_response['error']}"
            return

        questions_text = api_response["content"]
        print("Questions generated successfully, creating Excel file...")
        
        # Generate Excel file
        output_file = os.path.join(app.config['GENERATED_FILES'], f"{job_id}.xlsx")
        success = generate_excel(questions_text, output_file)
        
        if success:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result_file"] = output_file
            print(f"Processing completed successfully for job {job_id}")
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "Failed to create Excel file"

    except Exception as e:
        print(f"Error processing files for job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
    finally:
        # Clean up thread tracking
        current_thread = threading.current_thread()
        if current_thread in active_threads:
            active_threads.remove(current_thread)

# Your existing routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    if 'reference_book' not in request.files or 'syllabus' not in request.files:
        return jsonify({"error": "Missing required files"}), 400
    
    reference_file = request.files['reference_book']
    syllabus_file = request.files['syllabus']
    
    if reference_file.filename == '' or syllabus_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not (allowed_file(reference_file.filename) and allowed_file(syllabus_file.filename)):
        return jsonify({"error": "Invalid file type. Only PDF files are allowed"}), 400
    
    # Get form data
    mcq_count = int(request.form.get('mcq_count', 5))
    short_count = int(request.form.get('short_count', 3))
    long_count = int(request.form.get('long_count', 2))
    custom_instructions = request.form.get('custom_instructions', '')
    
    # Create unique job ID
    job_id = str(uuid.uuid4())
    
    # Save the files
    reference_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_reference.pdf")
    syllabus_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_syllabus.pdf")
    
    reference_file.save(reference_path)
    syllabus_file.save(syllabus_path)
    
    # Initialize job status
    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "created_at": time.time(),
        "result_file": None,
        "error": None
    }
    
    # Process files in background with proper thread management
    thread = threading.Thread(
        target=process_files,
        args=(job_id, reference_path, syllabus_path, mcq_count, short_count, long_count, custom_instructions),
        daemon=False  # Changed from daemon=True to prevent threading issues
    )
    active_threads.append(thread)
    thread.start()
    
    return jsonify({"job_id": job_id})

@app.route('/api/status/<job_id>', methods=['GET'])
def job_status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(jobs[job_id])

@app.route('/api/download/<job_id>', methods=['GET'])
def download_file(job_id):
    if job_id not in jobs or jobs[job_id]["status"] != "completed":
        return jsonify({"error": "File not ready or job not found"}), 404
    
    return send_file(
        jobs[job_id]["result_file"],
        as_attachment=True,
        download_name="question_bank.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def cleanup_threads():
    """Clean up any remaining threads"""
    print("Cleaning up threads...")
    for thread in active_threads:
        if thread.is_alive():
            print(f"Waiting for thread {thread.name} to complete...")
            thread.join(timeout=5)

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    print('Shutting down gracefully...')
    cleanup_threads()
    sys.exit(0)

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    import socket
    def find_available_port(start_port=8100, max_port=9000):
        for port in range(start_port, max_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('127.0.0.1', port))
                    return port
                except OSError:
                    continue
        raise OSError("No available ports found in range {}-{}".format(start_port, max_port))
    
    port = find_available_port()
    print(f"Starting server on port {port}")
    print("Access the application at: http://localhost:" + str(port))
    
    try:
        app.run(debug=True, port=port, host='0.0.0.0', threaded=True)
    except KeyboardInterrupt:
        print("Server interrupted by user")
    finally:
        cleanup_threads()
