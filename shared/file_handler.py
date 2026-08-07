import os
import PyPDF2
from werkzeug.utils import secure_filename
from shared.config import Config

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

def save_uploaded_file(file_obj) -> str:
    """Saves incoming werkzeug FileStorage object to ephemeral disk."""
    filename = secure_filename(file_obj.filename)
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    file_obj.save(filepath)
    return filepath

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts raw string content from a PDF document."""
    extracted_text = ""
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
    return extracted_text
