from langchain_core.messages import AIMessageChunk
from app.routers.agent import _format_event


def test_stream_emits_only_text_from_responses_blocks():
    chunk = AIMessageChunk(content=[
        {"type":"reasoning", "summary":[{"type":"summary_text", "text":"private"}]},
        {"type":"text", "text":"Answer"},
    ])
    assert _format_event("messages", (chunk, {})) == {"type":"token", "text":"Answer"}
    assert _format_event("messages", (AIMessageChunk(content=[
        {"type":"reasoning", "summary":[]}
    ]), {})) is None
