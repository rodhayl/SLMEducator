from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from src.core.services.file_service import FileProcessingService
from src.api.security import require_teacher_or_admin

from src.core.models.models import User
import logging

router = APIRouter(prefix="/api/upload", tags=["upload"])
logger = logging.getLogger(__name__)


@router.post("/source-material")
async def upload_source_material(
    file: UploadFile = File(...), current_user: User = Depends(require_teacher_or_admin)
):
    """
    Upload a source material file (PDF/Text) and extract its text content.
    Returns the extracted text ID (or just the text for now/temp storage).

    In a real system, we'd save the file and return an ID.
    For this MVP, we return the extracted text directly to be used in the next form step,
    or a temporary reference ID if we implemented a cache.
    """
    try:
        text_content = await FileProcessingService.extract_text(file)

        # Validation: Ensure we have meaningful content
        if not text_content or len(text_content.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Could not extract usable text from file. Please upload a file with more content.",
            )

        return {
            "filename": file.filename,
            "char_count": len(text_content),
            "preview": (
                text_content[:200] + "..." if len(text_content) > 200 else text_content
            ),
            "extracted_text": text_content,
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Internal server error parsing file"
        )
