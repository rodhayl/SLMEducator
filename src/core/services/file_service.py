from fastapi import UploadFile
import io
import pypdf
import logging

logger = logging.getLogger(__name__)


class FileProcessingService:
    @staticmethod
    async def extract_text(file: UploadFile) -> str:
        """
        Extracts text from an uploaded file (PDF or Text).

        Args:
            file: The uploaded file object.

        Returns:
            Extracted text string.

        Raises:
            ValueError: If file type is not supported.
        """
        content_type = file.content_type or ""
        filename = (file.filename or "").lower()

        try:
            # Read file content
            content = await file.read()
            await file.seek(0)  # Reset cursor

            if "pdf" in content_type.lower() or filename.endswith(".pdf"):
                return FileProcessingService._extract_from_pdf(content)
            elif (
                "text" in content_type.lower()
                or filename.endswith(".txt")
                or filename.endswith(".md")
            ):
                return content.decode("utf-8")
            else:
                # Fallback: Try decoding as text
                try:
                    return content.decode("utf-8")
                except UnicodeDecodeError:
                    raise ValueError(f"Unsupported file type: {content_type}")

        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}")
            raise e

    @staticmethod
    def _extract_from_pdf(content: bytes) -> str:
        """Helper to extract text from PDF bytes."""
        text = ""
        try:
            pdf_file = io.BytesIO(content)
            reader = pypdf.PdfReader(pdf_file)

            for page in reader.pages:
                text += page.extract_text() + "\n\n"

            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            raise ValueError("Failed to process PDF content")
