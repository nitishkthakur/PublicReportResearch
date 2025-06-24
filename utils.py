import os
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

def concatenate_pdfs_in_folder(folder_path: str) -> BytesIO:
    """
    Reads all PDF files in the given folder, concatenates them, and returns a BytesIO object.
    This can be used as input for LangChain document loaders.
    """
    pdf_writer = PdfWriter()
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    pdf_files.sort()  # Optional: sort files alphabetically

    for pdf_file in pdf_files:
        file_path = os.path.join(folder_path, pdf_file)
        try:
            pdf_reader = PdfReader(file_path)
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")



    output_stream = BytesIO()
    pdf_writer.write(output_stream)
    output_stream.seek(0)
    return output_stream