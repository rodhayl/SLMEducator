"""Bounded source extraction from real synthetic PDF/text bytes, with no OCR."""

import io
from hashlib import sha256

import pypdf
import pytest
from fastapi import UploadFile
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from starlette.datastructures import Headers

from src.core.services.file_service import (
    FileProcessingService,
    MAX_PDF_PAGES,
    MAX_SOURCE_CHARACTERS,
)


def pdf_bytes(pages, encrypted=False):
    """Build a disposable real PDF with simple readable synthetic text pages."""
    writer = pypdf.PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        if text:
            font = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
            )
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode("ascii"))
            page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("synthetic-test-only-password")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.asyncio
async def test_pdf_reports_real_page_references_hash_and_unreadable_pages():
    payload = pdf_bytes(
        ["Numerators count selected parts.", "", "Denominators count total parts."]
    )
    file = UploadFile(io.BytesIO(payload), filename="synthetic.PDF")
    result = await FileProcessingService.extract_document(file)
    assert result["source_version"] == sha256(payload).hexdigest()
    assert result["total_pages"] == 3 and result["unreadable_pages"] == [2]
    assert result["coverage"] == "partial" and not result["truncated"]
    assert result["parser"] == f"pypdf-{pypdf.__version__}"
    assert [section["reference"] for section in result["sections"]] == [
        "page:1",
        "page:2",
        "page:3",
    ]
    assert result["sections"][0]["text"] == "Numerators count selected parts."
    assert result["sections"][2]["text"] == "Denominators count total parts."
    assert (
        result["extracted_text"]
        == "[page:1]\nNumerators count selected parts.\n\n[page:2]\n\n\n[page:3]\nDenominators count total parts."
    )
    assert file.file.tell() == 0


@pytest.mark.asyncio
async def test_pdf_page_limit_omits_excess_pages_without_claiming_full_coverage():
    payload = pdf_bytes(["Synthetic text"] * MAX_PDF_PAGES + ["MUST_NOT_BE_READ"])
    result = await FileProcessingService.extract_document(
        UploadFile(io.BytesIO(payload), filename="synthetic.pdf")
    )
    assert result["total_pages"] == MAX_PDF_PAGES + 1
    assert len(result["sections"]) == MAX_PDF_PAGES
    assert result["truncated"] is True and result["coverage"] == "partial"
    assert "MUST_NOT_BE_READ" not in result["extracted_text"]
    assert result["sections"][-1]["reference"] == f"page:{MAX_PDF_PAGES}"


@pytest.mark.asyncio
async def test_pdf_character_limit_includes_page_labels_and_separators():
    payload = pdf_bytes(["A" * (MAX_SOURCE_CHARACTERS + 1), "MUST_NOT_BE_READ"])
    result = await FileProcessingService.extract_document(
        UploadFile(io.BytesIO(payload), filename="synthetic.pdf")
    )
    assert len(result["extracted_text"]) == MAX_SOURCE_CHARACTERS
    assert result["extracted_text"].startswith("[page:1]\nAAA")
    assert len(result["sections"]) == 1
    assert result["total_pages"] == 2 and result["truncated"] is True
    assert (
        result["coverage"] == "partial"
        and "MUST_NOT_BE_READ" not in result["extracted_text"]
    )


@pytest.mark.asyncio
async def test_pdf_reference_overhead_can_omit_a_final_page_with_no_room():
    payload = pdf_bytes(["A" * (MAX_SOURCE_CHARACTERS - 10), "B"])
    result = await FileProcessingService.extract_document(
        UploadFile(io.BytesIO(payload), filename="synthetic.pdf")
    )
    assert len(result["sections"]) == 1
    assert len(result["extracted_text"]) == MAX_SOURCE_CHARACTERS - 1
    assert result["truncated"] is True and result["coverage"] == "partial"
    assert "[page:2]" not in result["extracted_text"]


@pytest.mark.asyncio
async def test_pdf_media_type_supports_extensionless_source_and_compatibility_reader():
    payload = pdf_bytes(["Synthetic source text"])
    file = UploadFile(
        io.BytesIO(payload),
        filename="source",
        headers=Headers({"content-type": "application/pdf"}),
    )
    assert (
        await FileProcessingService.extract_text(file)
        == "[page:1]\nSynthetic source text"
    )
    assert FileProcessingService._extract_from_pdf(payload) == "Synthetic source text"


@pytest.mark.asyncio
async def test_encrypted_pdf_requires_authorized_readable_copy():
    payload = pdf_bytes(["Synthetic protected content"], encrypted=True)
    with pytest.raises(ValueError, match="Encrypted PDFs are unsupported"):
        await FileProcessingService.extract_document(
            UploadFile(io.BytesIO(payload), filename="synthetic.pdf")
        )


@pytest.mark.asyncio
async def test_corrupt_pdf_reports_extraction_failure_instead_of_empty_success():
    with pytest.raises(ValueError, match="PDF text extraction failed"):
        await FileProcessingService.extract_document(
            UploadFile(io.BytesIO(b"not a PDF"), filename="corrupt.pdf")
        )


@pytest.mark.asyncio
async def test_invalid_utf8_is_rejected_and_upload_is_rewound():
    file = UploadFile(io.BytesIO(b"\xff\xfeinvalid"), filename="source.txt")
    with pytest.raises(ValueError, match="UTF-8"):
        await FileProcessingService.extract_document(file)
    assert file.file.tell() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,media_type",
    [
        ("synthetic.MD", "application/octet-stream"),
        (None, "text/markdown"),
        ("source", "text/plain"),
    ],
)
async def test_text_type_detection_preserves_unicode_and_provenance(
    filename, media_type
):
    payload = "# Fracciones\nNumerador: partes elegidas. π".encode("utf-8")
    file = UploadFile(
        io.BytesIO(payload),
        filename=filename,
        headers=Headers({"content-type": media_type}),
    )
    result = await FileProcessingService.extract_document(file)
    assert result["extracted_text"] == "[section:1]\n" + payload.decode("utf-8")
    assert result["source_version"] == sha256(payload).hexdigest()
    assert result["coverage"] == "complete" and not result["truncated"]
    assert result["total_pages"] is None and result["unreadable_pages"] == []
    assert result["parser"] == "utf8-text-v1"
    assert file.file.tell() == 0
