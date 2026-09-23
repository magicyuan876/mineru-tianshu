r"""parse() 必须原样保留 MinerU 输出的 Markdown

曾经的 _clean_markdown 会全局替换 ~、剥掉 \mathrm{}、双重反转义 HTML，
并用 (\S+)\s+\1 去重：既删掉表格中相邻的同值单元格，又在长无空白文本上
退化成平方复杂度导致任务卡死。已移除，这里防止回归。
"""

import sys
import types
from pathlib import Path

import pytest

# 每一段都是旧清洗逻辑会改坏的真实内容
SEGMENTS = [
    "温度范围 10~20 ℃，路径 ~/data",
    r"$\mathrm{kg}\cdot\mathrm{m}$",
    "字面量写作 &amp;lt; 表示小于号",
    "<table>\n  <tr>\n    <td>a &lt; b</td>\n    <td>0</td>\n    <td>0</td>\n    <td>5</td>\n  </tr>\n</table>",
    "the the result",
]
RAW_MARKDOWN = "\n\n".join(SEGMENTS)


@pytest.fixture
def engine(monkeypatch):
    if "img2pdf" not in sys.modules:
        try:
            __import__("img2pdf")
        except ImportError:
            monkeypatch.setitem(sys.modules, "img2pdf", types.ModuleType("img2pdf"))
    from mineru_pipeline.engine import MinerUPipelineEngine

    instance = MinerUPipelineEngine.__new__(MinerUPipelineEngine)
    instance.vlm_api_base = None
    instance.is_offloaded = False
    instance.is_processing = False
    instance.last_active_time = 0

    def fake_do_parse(output_dir, pdf_file_names, **kwargs):
        result_dir = Path(output_dir) / "result" / "auto"
        result_dir.mkdir(parents=True)
        (result_dir / "result.md").write_text(RAW_MARKDOWN, encoding="utf-8")

    instance._load_pipeline = lambda: fake_do_parse
    return instance


def test_markdown_is_returned_and_written_unchanged(engine, tmp_path):
    source = tmp_path / "doc.pdf"
    source.write_bytes(b"%PDF-1.4")
    output = tmp_path / "out"

    result = engine.parse(str(source), str(output), options={})
    written = (output / "auto" / "result.md").read_text(encoding="utf-8")

    for segment in SEGMENTS:
        assert segment in result["markdown"]
        assert segment in written
    assert result["markdown"] == written == RAW_MARKDOWN
