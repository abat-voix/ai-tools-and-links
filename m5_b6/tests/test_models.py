async def test_list_models(client):
    resp = await client.get("/models")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = {m["id"] for m in data}
    assert ids == {"gpt-6-luna", "gpt-6.2-sol", "gpt-6.2-astra"}
    for m in data:
        assert m["provider"] in {"openai", "ollama", "anthropic"}
        assert m["input_per_1m"] >= 0
        assert m["output_per_1m"] >= 0
