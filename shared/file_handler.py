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
    print(f"Uploading file to S3 bucket '{S3_BUCKET_NAME}' with key '{filename}'", flush=True)
    
    # Upload the file stream directly to S3 without saving it locally first
    s3_client.upload_fileobj(file_obj, S3_BUCKET_NAME, filename)
    
    # Return the S3 key (filename) so the worker knows exactly what to download
    return filename

def extract_text_from_pdf(filename: str) -> str:
    """Downloads the PDF from S3 to the worker container, then extracts the text."""
    print(f"Downloading '{filename}' from S3 to worker...", flush=True)
    s3_client = boto3.client('s3')
    
    # Define a temporary path inside the Fargate container
    local_tmp_path = f"/tmp/{filename}"
    
    # 1. Download the file from S3 to the worker
    s3_client.download_file(S3_BUCKET_NAME, filename, local_tmp_path)
    
    # 2. Extract the text
    extracted_text = ""
    with open(local_tmp_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
                
    # 3. Delete the temporary file to keep the container clean
    os.remove(local_tmp_path)
    print("Text successfully extracted and temporary file cleaned up.", flush=True)
            
    return extracted_text