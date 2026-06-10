import io
import zipfile

from app.packaging import build_zip


def test_zip_contains_json_and_graphs(tmp_path):
    (tmp_path / "training_data.json").write_text("{}")
    graphs = tmp_path / "graphs"
    graphs.mkdir()
    (graphs / "1_a.png").write_bytes(b"x")
    (graphs / "2_b.png").write_bytes(b"y")
    (graphs / "notes.txt").write_text("ignore me")

    with zipfile.ZipFile(io.BytesIO(build_zip(tmp_path))) as zf:
        names = set(zf.namelist())

    assert names == {"training_data.json", "graphs/1_a.png", "graphs/2_b.png"}


def test_zip_tolerates_missing_graphs(tmp_path):
    (tmp_path / "training_data.json").write_text("{}")
    with zipfile.ZipFile(io.BytesIO(build_zip(tmp_path))) as zf:
        assert zf.namelist() == ["training_data.json"]
