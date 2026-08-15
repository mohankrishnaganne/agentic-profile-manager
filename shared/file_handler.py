import os
import boto3
import PyPDF2
from werkzeug.utils import secure_filename
from shared.config import Config

# Retrieve the bucket name we configured in your ECS task definition
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'agentic-profile-uploads-wichita')

def save_uploaded_file(file_obj) -> str:
    """Uploads incoming file directly to Amazon S3 and returns the object key."""
    filename = secure_filename(file_obj.filename)
    
    # Initialize the AWS S3 client
    s3_client = boto3.client('s3')
    print(f"Uploading file to S3 bucket '{S3_BUCKET_NAME}' with key '{filename}'")
    # Upload the file stream directly to S3 without saving it locally first
    s3_client.upload_fileobj(file_obj, S3_BUCKET_NAME, filename)
    
    # Return the S3 key (filename) so the worker knows exactly what to download
    return filename

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