from flask import Flask, request, render_template, send_file
from pdf2docx import Converter
import os
import subprocess
from PyPDF2 import PdfWriter, PdfReader
from werkzeug.utils import secure_filename
from PyPDF2 import PdfMerger
import PyPDF2

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('home.html')  # Main page with information and links to both features

# Route for PDF-to-DOCX Conversion
@app.route('/pdf_to_docx')
def upload_form_docx():
    return render_template('upload_pdf_to_docx.html')  # Upload form specifically for PDF-to-DOCX

@app.route('/convert_to_docx', methods=['POST'])
def upload_file_docx():
    if 'file' not in request.files:
        return "No file part"
    
    file = request.files['file']
    
    if file.filename == '':
        return "No selected file"

    if file and file.filename.endswith('.pdf'):
        # Save the uploaded PDF file
        pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(pdf_path)

        # Convert PDF to DOCX
        docx_path = pdf_path.replace('.pdf', '.docx')
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()

        return send_file(docx_path, as_attachment=True)

    return "Invalid file format. Please upload a PDF file."

# Route for PDF Compression
# Route for Locking PDF
@app.route('/lock_pdf')
def upload_form_lock():
    return render_template('upload_lock_pdf.html')  # Upload form for locking a PDF

@app.route('/lock', methods=['POST'])
def lock_pdf():
    if 'file' not in request.files:
        return "No file part"
    
    file = request.files['file']
    
    if file.filename == '':
        return "No selected file"

    if file and file.filename.endswith('.pdf'):
        # Save the uploaded PDF file
        pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(pdf_path)

        # Define locked PDF path
        locked_pdf_path = pdf_path.replace('.pdf', '_locked.pdf')

        # Get password from the form
        password = request.form.get('password')

        # Lock the PDF
        writer = PdfWriter()
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)

        # Save the locked PDF
        with open(locked_pdf_path, 'wb') as f:
            writer.write(f)

        return send_file(locked_pdf_path, as_attachment=True)

    return "Invalid file format. Please upload a PDF file."

# Route for PDF-to-DOCX Conversion (GET & POST)
@app.route('/pdf_to_docx', methods=['GET', 'POST'])
def pdf_to_docx():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('upload_pdf_to_docx.html', error="No file uploaded.")
        
        file = request.files['file']
        
        if file.filename == '':
            return render_template('upload_pdf_to_docx.html', error="No file selected.")
        
        if file and file.filename.endswith('.pdf'):
            # Save the uploaded PDF file
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_path)

            try:
                # Convert PDF to DOCX
                docx_path = pdf_path.replace('.pdf', '.docx')
                cv = Converter(pdf_path)
                cv.convert(docx_path, start=0, end=None)
                cv.close()

                # Send the DOCX file as a download
                return send_file(docx_path, as_attachment=True, download_name=filename.replace('.pdf', '.docx'))

            except Exception as e:
                return render_template('upload_pdf_to_docx.html', error=f"Error converting file: {str(e)}")
        
        return render_template('upload_pdf_to_docx.html', error="Invalid file format. Please upload a PDF.")
    
    # For GET request, render the upload form
    return render_template('upload_pdf_to_docx.html')

@app.route('/unlock', methods=['POST','GET'])
def unlock_pdf():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return render_template('unlock_pdf.html', error="No file uploaded")
        
        pdf_file = request.files['pdf_file']
        password = request.form['password']
        
        if pdf_file.filename == '':
            return render_template('unlock_pdf.html', error="No file selected")
            
        if pdf_file and password:
            filename = secure_filename(pdf_file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'unlocked_' + filename)
            
            pdf_file.save(input_path)
            
            try:
                # Open the PDF with the password
                pdf_reader = PyPDF2.PdfReader(input_path)
                if pdf_reader.is_encrypted:
                    # Try to decrypt with provided password
                    if pdf_reader.decrypt(password):
                        # Create a new PDF writer and add all pages
                        pdf_writer = PyPDF2.PdfWriter()
                        for page in pdf_reader.pages:
                            pdf_writer.add_page(page)
                            
                        # Save the unlocked PDF
                        with open(output_path, 'wb') as output_file:
                            pdf_writer.write(output_file)
                            
                        # Clean up input file
                        os.remove(input_path)
                        
                        # Send the unlocked file
                        return send_file(output_path, as_attachment=True, 
                                      download_name='unlocked_' + filename)
                    else:
                        os.remove(input_path)
                        return render_template('unlock_pdf.html', 
                                            error="Incorrect password")
                else:
                    os.remove(input_path)
                    return render_template('unlock_pdf.html', 
                                        error="PDF is not encrypted")
                    
            except Exception as e:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
                return render_template('unlock_pdf.html', 
                                    error=f"Error processing PDF: {str(e)}")
                
    return render_template('unlock_pdf.html')



@app.route('/merge_pdf', methods=['GET', 'POST'])
def merge_pdfs():
    if request.method == 'POST':
        # Check if any file was uploaded
        if 'pdf_files[]' not in request.files:
            return render_template('merge_pdf.html', error="No files uploaded")
        
        files = request.files.getlist('pdf_files[]')
        
        # Filter out empty file inputs
        files = [f for f in files if f.filename != '']
        
        if not files:
            return render_template('merge_pdf.html', error="No files selected")
            
        if len(files) > 7:
            return render_template('merge_pdf.html', error="Maximum 7 files allowed")
        
        input_paths = []  # Initialize here

        try:
            merger = PdfMerger()
            
            # Save and merge PDFs
            for file in files:
                filename = secure_filename(file.filename)
                input_path = os.path.join(UPLOAD_FOLDER, filename)
                input_paths.append(input_path)
                file.save(input_path)
                merger.append(input_path)
            
            # Save merged PDF
            output_path = os.path.join(UPLOAD_FOLDER, 'merged_document.pdf')
            merger.write(output_path)
            merger.close()
            
            # Clean up input files
            for path in input_paths:
                if os.path.exists(path):
                    os.remove(path)
            
            # Send the merged file
            return send_file(
                output_path,
                as_attachment=True,
                download_name='merged_document.pdf',
                mimetype='application/pdf'
            )
                
        except Exception as e:
            # Clean up any files in case of error
            for path in input_paths:
                if os.path.exists(path):
                    os.remove(path)
            if 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
            return render_template('merge_pdf.html', 
                                error=f"Error processing PDFs: {str(e)}")
                
    return render_template('merge_pdf.html')

@app.route('/compress_pdf', methods=['GET', 'POST'])
def compress_pdf():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return render_template('compress_pdf.html', error="No file uploaded")
        
        pdf_file = request.files['pdf_file']
        compression_level = request.form.get('compression_level', 'medium')
        
        if pdf_file.filename == '':
            return render_template('compress_pdf.html', error="No file selected")
            
        if pdf_file:
            filename = secure_filename(pdf_file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'compressed_' + filename)
            
            pdf_file.save(input_path)
            
            try:
                # Open the PDF
                reader = PdfReader(input_path)
                writer = PdfWriter()

                # Copy pages and compress them
                for page in reader.pages:
                    writer.add_page(page)

                # Set compression parameters based on level
                if compression_level == 'high':
                    writer.compress_content_streams = True  # This compresses all content streams
                elif compression_level == 'medium':
                    writer.compress_content_streams = True
                # Low compression just copies the file
                
                # Save the compressed PDF
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                # Get file sizes for comparison
                original_size = os.path.getsize(input_path)
                compressed_size = os.path.getsize(output_path)
                
                # Clean up input file
                os.remove(input_path)
                
                # Send the compressed file
                return send_file(
                    output_path,
                    as_attachment=True,
                    download_name='compressed_' + filename,
                    mimetype='application/pdf'
                )
                    
            except Exception as e:
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
                return render_template('compress_pdf.html', 
                                    error=f"Error processing PDF: {str(e)}")
                
    return render_template('compress_pdf.html')



@app.route('/calculator', methods=['GET', 'POST'])
def calucate():
    return render_template('calculator.html')

@app.route('/b', methods=['GET', 'POST'])
def b():
    return render_template('b.html')
@app.route('/m', methods=['GET', 'POST'])
def m():
    return render_template('m.html')
@app.route('/t', methods=['GET', 'POST'])
def t():
    return render_template('t.html')
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    return render_template('upload.html')




if __name__ == '__main__':
    app.run(debug=True)
