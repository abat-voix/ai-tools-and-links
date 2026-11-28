"""Тесты конвертации медиа в content-part."""

import base64
import shutil
import subprocess
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
import httpx
from openai import AsyncOpenAI
from docx import Document as DocxDocument
from pypdf import PdfWriter

from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.chat.media import extract_docx_text, media_to_part


@pytest.fixture
def ogg_audio():
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required for the Ogg conversion check")
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
         "-t", "0.05", "-c:a", "libopus", "-f", "ogg", "pipe:1"],
        check=True, capture_output=True,
    ).stdout


async def test_ogg_is_converted_before_current_transcription_api(ogg_audio):
    requests = []

    async def handler(request):
        requests.append(request.content)
        return httpx.Response(200, json={"text": "heard"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with AsyncOpenAI(api_key="test-key", http_client=http) as llm:
            part = await media_to_part(FakeUploadFile("audio/ogg", ogg_audio, "voice.ogg"), llm)
    assert part["text"].endswith("heard")
    assert b"gpt-transcribe" in requests[0]
    assert b'filename="audio.wav"' in requests[0]
    assert b"WAVE" in requests[0]


class FakeUploadFile:
    """Минимальный двойник Starlette UploadFile."""

    def __init__(
        self, content_type: str, data: bytes, filename: str = "file"
    ):
        self.content_type = content_type
        self.filename = filename
        self.size = len(data)
        self._data = data

    async def read(self) -> bytes:
        return self._data


@pytest.mark.asyncio
async def test_image_to_part_returns_base64_data_uri():
    data = b"\x89PNG\r\n\x1a\nfake-bytes"
    f = FakeUploadFile("image/png", data, "test.png")
    llm = MagicMock()  # не должен дёргаться для image
    part = await media_to_part(f, llm)
    assert part["type"] == "image_url"
    assert part["image_url"]["url"].startswith("data:image/png;base64,")
    b64 = part["image_url"]["url"].split(",", 1)[1]
    assert base64.b64decode(b64) == data


@pytest.mark.asyncio
async def test_audio_to_part_calls_transcription(ogg_audio):
    data = ogg_audio
    f = FakeUploadFile("audio/ogg", data, "voice.ogg")

    llm = MagicMock()
    llm.audio.transcriptions.create = AsyncMock(
        return_value=MagicMock(text="Привет, как дела"),
    )

    part = await media_to_part(f, llm)
    assert part["type"] == "text"
    assert "пользователь сказал голосом" in part["text"]
    assert "Привет, как дела" in part["text"]
    llm.audio.transcriptions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_application_ogg_treated_as_audio(ogg_audio):
    """Telegram voice иногда летит как application/ogg, не audio/*."""
    data = ogg_audio
    f = FakeUploadFile("application/ogg", data, "v.ogg")
    llm = MagicMock()
    llm.audio.transcriptions.create = AsyncMock(
        return_value=MagicMock(text="Тест"),
    )
    part = await media_to_part(f, llm)
    assert part["type"] == "text"
    assert "Тест" in part["text"]


@pytest.mark.asyncio
async def test_pdf_to_part(tmp_path):
    writer = PdfWriter()
    page = writer.add_blank_page(width=72, height=72)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page["/Resources"][NameObject("/Font")] = DictionaryObject({NameObject("/F1"): font})
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 12 Tf 8 36 Td (Sample PDF text) Tj ET")
    page.replace_contents(content)
    pdf_path = tmp_path / "test.pdf"
    with open(pdf_path, "wb") as fp:
        writer.write(fp)

    data = pdf_path.read_bytes()
    f = FakeUploadFile("application/pdf", data, "test.pdf")
    llm = MagicMock()
    part = await media_to_part(f, llm)
    assert part["type"] == "text"
    assert part["text"] == "[документ PDF]:\nSample PDF text"


@pytest.mark.asyncio
async def test_docx_to_part(tmp_path):
    doc = DocxDocument()
    doc.add_paragraph("Hello world")
    doc.add_paragraph("Второй параграф")
    out = tmp_path / "test.docx"
    doc.save(out)

    data = out.read_bytes()
    mime = (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    )
    f = FakeUploadFile(mime, data, "test.docx")
    llm = MagicMock()
    part = await media_to_part(f, llm)
    assert part["type"] == "text"
    assert "документ DOCX" in part["text"]
    assert "Hello world" in part["text"]
    assert "Второй параграф" in part["text"]


@pytest.mark.asyncio
async def test_unknown_mime_raises():
    f = FakeUploadFile("application/octet-stream", b"\x00\x01\x02")
    llm = MagicMock()
    with pytest.raises(ValueError, match="Unsupported"):
        await media_to_part(f, llm)


async def test_pdf_without_text_is_rejected():
    writer = PdfWriter()
    for _ in range(5):
        writer.add_blank_page(width=72, height=72)
    buf = BytesIO()
    writer.write(buf)
    file = FakeUploadFile("application/pdf", buf.getvalue(), "empty.pdf")
    with pytest.raises(ValueError, match="Не удалось извлечь текст из PDF"):
        await media_to_part(file, MagicMock())


async def test_docx_without_text_is_rejected():
    buf = BytesIO()
    DocxDocument().save(buf)
    file = FakeUploadFile(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        buf.getvalue(), "empty.docx",
    )
    with pytest.raises(ValueError, match="Не удалось извлечь текст из DOCX"):
        await media_to_part(file, MagicMock())


def test_extract_docx_text_with_table(tmp_path):
    doc = DocxDocument()
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "A"
    table.cell(0, 1).text = "B"
    table.cell(1, 0).text = "C"
    table.cell(1, 1).text = "D"
    out = tmp_path / "t.docx"
    doc.save(out)

    text = extract_docx_text(out.read_bytes())
    assert "A | B" in text
    assert "C | D" in text
