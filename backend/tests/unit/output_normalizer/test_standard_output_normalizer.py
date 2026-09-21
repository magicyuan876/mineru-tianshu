import json

import pytest

from output_normalizer.standard_output_normalizer import StandardOutputNormalizer


def test_normalize_output_preserves_result_contract_and_rewrites_local_image_references(runtime_paths, mocker):
    """只验证归一化契约（目录结构与本地图片引用改写），对象存储上传单独测试"""
    mocker.patch.object(StandardOutputNormalizer, "_process_rustfs_upload")
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


def test_image_processor_failure_does_not_break_normalization(runtime_paths, monkeypatch, mocker):
    """图片描述（可选能力）失败不应影响归一化主流程"""
    monkeypatch.setenv("RUSTFS_ENABLED", "true")
    output_dir = runtime_paths["output_path"] / "raw-output"
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True)
    (output_dir / "source.md").write_text("![page](page.png)", encoding="utf-8")
    (image_dir / "page.png").write_bytes(b"image")
    normalizer = StandardOutputNormalizer()
    mocker.patch.object(normalizer, "_upload_images_to_rustfs", return_value={"page.png": "http://host/s3/b/page.png"})

    result = normalizer.normalize(
        output_dir,
        image_processor=lambda *_: (_ for _ in ()).throw(RuntimeError("caption service unavailable")),
    )

    assert result["markdown_file"].exists()
    assert result["images_uploaded"] is True


def test_rustfs_upload_failure_fails_the_task(runtime_paths, monkeypatch, mocker):
    """对象存储是强制依赖：含图片的任务上传失败必须让任务失败

    此前这里是"失败也保留本地路径继续"，结果是任务显示 completed、
    但 Markdown 里留着相对路径 images/xxx.png，前端图片全部 404，
    用户完全看不出问题在哪。
    """
    monkeypatch.setenv("RUSTFS_ENABLED", "true")
    output_dir = runtime_paths["output_path"] / "raw-output"
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True)
    markdown_file = output_dir / "result.md"
    markdown_file.write_text("![page](images/page.png)", encoding="utf-8")
    (image_dir / "page.png").write_bytes(b"image")
    normalizer = StandardOutputNormalizer()
    mocker.patch.object(normalizer, "_upload_images_to_rustfs", side_effect=RuntimeError("storage unavailable"))

    with pytest.raises(RuntimeError, match="RUSTFS_ENDPOINT"):
        normalizer.normalize(output_dir)
