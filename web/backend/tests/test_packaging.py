from app.packaging import read_output


def test_read_output_returns_json_bytes(tmp_path):
    (tmp_path / "training_data.json").write_bytes(b'{"meta": {}}')
    assert read_output(tmp_path) == b'{"meta": {}}'
