"""Bounded source extraction with explicit coverage and page provenance."""

import io
from hashlib import sha256

from fastapi import UploadFile
import pypdf
from starlette.concurrency import run_in_threadpool

MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_SOURCE_CHARACTERS = 100_000
MAX_PDF_PAGES = 100


class FileProcessingService:
    @staticmethod
    async def extract_document(file: UploadFile) -> dict:
        """Read a bounded text/PDF source and report omitted or unreadable pages."""
        content = await file.read(MAX_SOURCE_BYTES + 1)
        await file.seek(0)
        if len(content) > MAX_SOURCE_BYTES:
            raise ValueError("Source exceeds the 10 MiB limit")
        filename = (file.filename or "").lower()
        if filename.endswith(".pdf") or file.content_type == "application/pdf":
            result = await run_in_threadpool(
                FileProcessingService._extract_pdf_document, content
            )
        elif filename.endswith((".txt", ".md")) or file.content_type in (
            "text/plain",
            "text/markdown",
        ):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("Text sources must use UTF-8 encoding")
            result = {
                "sections": [
                    {"reference": "section:1", "text": text[:MAX_SOURCE_CHARACTERS]}
                ],
                "total_pages": None,
                "unreadable_pages": [],
                "truncated": len(text) > MAX_SOURCE_CHARACTERS,
            }
        else:
            raise ValueError("Supported sources are PDF, UTF-8 text and Markdown")
        result["source_version"] = sha256(content).hexdigest()
        result["extracted_text"] = "\n\n".join(
            f"[{section['reference']}]\n{section['text']}"
            for section in result["sections"]
        )
        result["coverage"] = (
            "partial"
            if result["truncated"] or result["unreadable_pages"]
            else "complete"
        )
        return result

    @staticmethod
    async def extract_text(file: UploadFile) -> str:
        """Compatibility entry point preserving bounded extraction."""
        return (await FileProcessingService.extract_document(file))["extracted_text"]

    @staticmethod
    def _extract_pdf_document(content: bytes) -> dict:
        try:
            reader = pypdf.PdfReader(io.BytesIO(content))
            if reader.is_encrypted:
                raise ValueError(
                    "Encrypted PDFs are unsupported; supply an authorized readable copy"
                )
            sections, unreadable, remaining = [], [], MAX_SOURCE_CHARACTERS
            truncated = len(reader.pages) > MAX_PDF_PAGES
            for index, page in enumerate(reader.pages[:MAX_PDF_PAGES]):
                text = page.extract_text() or ""
                if not text.strip():
                    unreadable.append(index + 1)
                if len(text) > remaining:
                    truncated = True
                sections.append(
                    {"reference": f"page:{index + 1}", "text": text[:remaining]}
                )
                remaining -= min(len(text), remaining)
                if remaining == 0:
                    truncated = truncated or index + 1 < len(reader.pages)
                    break
            return {
                "sections": sections,
                "total_pages": len(reader.pages),
                "unreadable_pages": unreadable,
                "truncated": truncated,
            }
        except ValueError:
            raise
        except Exception:
            raise ValueError(
                "PDF text extraction failed; scanned PDFs need OCR outside this application"
            )

    @staticmethod
    def _extract_from_pdf(content: bytes) -> str:
        """Legacy service entry point with the same page/character limits."""
        result = FileProcessingService._extract_pdf_document(content)
        return "\n\n".join(item["text"] for item in result["sections"]).strip()
