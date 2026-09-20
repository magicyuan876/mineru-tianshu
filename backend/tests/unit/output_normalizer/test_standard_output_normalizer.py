import json

from output_normalizer.standard_output_normalizer import StandardOutputNormalizer


def test_normalize_output_preserves_result_contract_and_rewrites_local_image_references(runtime_paths, monkeypatch):
    monkeypatch.setenv("RUSTFS_ENABLED", "false")
    output_dir = runtime_paths["output_path"] / "raw-output"
    nested = output_dir / "nested"
    image_dir = output_dir / "imgs"
    nested.mkdir(parents=True)
    image_dir.mkdir()
    (nested / "document.md").write_text('![page](../imgs/page.png)\n<img src="../imgs/page.png">', encoding="utf-8")
    (nested / "content_list.json").write_text(json.dumps({"image": "images/page.png"}), encoding="utf-8")
    (image_dir / "page.png").write_bytes(b"image")

    result = StandardOutputNormalizer().normalize(output_dir)

    assert result["markdown_file"] == output_dir / "result.md"
    assert result["json_file"] == output_dir / "result.json"
    assert result["image_dir"] == output_dir / "images"
    assert result["image_count"] == 1
    assert result["images_uploaded"] is False
    assert (output_dir / "images" / "page.png").exists()
    markdown = (output_dir / "result.md").read_text(encoding="utf-8")
    assert "![page](images/page.png)" in markdown
    assert '<img src="images/page.png">' in markdown


def test_image_processor_failure_does_not_break_normalization(runtime_paths, monkeypatch):
    monkeypatch.setenv("RUSTFS_ENABLED", "false")
    output_dir = runtime_paths["output_path"] / "raw-output"
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True)
    (output_dir / "source.md").write_text("![page](page.png)", encoding="utf-8")
    (image_dir / "page.png").write_bytes(b"image")

    result = StandardOutputNormalizer().normalize(
        output_dir,
        image_processor=lambda *_: (_ for _ in ()).throw(RuntimeError("caption service unavailable")),
    )

    assert result["markdown_file"].exists()
    assert result["images_uploaded"] is False


def test_rustfs_upload_failure_keeps_local_output(runtime_paths, monkeypatch, mocker):
    monkeypatch.setenv("RUSTFS_ENABLED", "true")
    output_dir = runtime_paths["output_path"] / "raw-output"
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True)
    markdown_file = output_dir / "result.md"
    markdown_file.write_text("![page](images/page.png)", encoding="utf-8")
    (image_dir / "page.png").write_bytes(b"image")
    normalizer = StandardOutputNormalizer()
    mocker.patch.object(normalizer, "_upload_images_to_rustfs", side_effect=RuntimeError("storage unavailable"))

    result = normalizer.normalize(output_dir)

    assert result["images_uploaded"] is False
    assert markdown_file.exists()
    assert "images/page.png" in markdown_file.read_text(encoding="utf-8")
