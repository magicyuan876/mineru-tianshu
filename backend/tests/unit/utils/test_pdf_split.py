"""PDF 分片边界：尾部余数过小时并入上一个分片

简单的 range(0, n, chunk) 会让 41 页 + chunk=20 切成 20/20/1。那个 1 页分片
要走完整流程（任务认领、归一化、对象存储上传、参与父任务合并），固定开销与
满分片相同、有效工作只有 1/20。分片越激进（多卡部署下 chunk 会调得很小），
这种畸形尾巴出现得越频繁。
"""

import pytest

pikepdf = pytest.importorskip("pikepdf", reason="pikepdf 未安装")

from utils.pdf_utils import split_pdf_file  # noqa: E402


def make_pdf(path, pages):
    pdf = pikepdf.new()
    for _ in range(pages):
        pdf.add_blank_page(page_size=(200, 200))
    pdf.save(path)
    return path


def sizes(chunks):
    return [c["page_count"] for c in chunks]


class TestChunkBoundaries:
    @pytest.mark.parametrize(
        "total,chunk,expected",
        [
            (40, 20, [20, 20]),
            (41, 20, [20, 21]),  # 尾部 1 页并入上一片，而不是 20+20+1
            (50, 20, [20, 20, 10]),  # 尾部恰为半块：不合并（10 页仍是合理的工作量）
            (51, 20, [20, 20, 11]),  # 尾部超过半块：独立成片
            (49, 20, [20, 29]),  # 尾部 9 页不足半块：并入上一片
            (100, 20, [20, 20, 20, 20, 20]),
            (25, 20, [25]),  # 只有一片时不做任何合并
        ],
    )
    def test_trailing_remainder_merged(self, tmp_path, total, chunk, expected):
        src = make_pdf(tmp_path / "src.pdf", total)

        chunks = split_pdf_file(src, tmp_path / "out", chunk_size=chunk)

        assert sizes(chunks) == expected

    @pytest.mark.parametrize("total", [1, 7, 20, 21, 39, 41, 99, 120])
    def test_pages_are_fully_covered_and_contiguous(self, tmp_path, total):
        """不论怎么切，页码必须连续且不丢不重"""
        src = make_pdf(tmp_path / "src.pdf", total)

        chunks = split_pdf_file(src, tmp_path / "out", chunk_size=20)

        assert sum(sizes(chunks)) == total
        assert chunks[0]["start_page"] == 1
        assert chunks[-1]["end_page"] == total
        for prev, cur in zip(chunks, chunks[1:]):
            assert cur["start_page"] == prev["end_page"] + 1

    def test_chunk_files_have_declared_page_counts(self, tmp_path):
        """产出的分片文件页数必须与声明一致（合并尾部后尤其要验）"""
        src = make_pdf(tmp_path / "src.pdf", 41)

        chunks = split_pdf_file(src, tmp_path / "out", chunk_size=20)

        for c in chunks:
            with pikepdf.open(c["path"]) as f:
                assert len(f.pages) == c["page_count"]
