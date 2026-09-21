"""MinerU content_list 的 v1 / v2 兼容

对应线上故障：engine.py 的「MD 为空时从 JSON 恢复」逻辑按 v1 的扁平结构写，
而 MinerU 3.x 的 *_content_list_v2.json 是按页分组的嵌套数组，于是抛出
`AttributeError: 'list' object has no attribute 'get'`（线上 106 次）。
前端 TaskDetail.vue 早已正确处理 v2，这里与之对齐。
"""

import sys
import types

import pytest


@pytest.fixture
def engine_cls(monkeypatch):
    # engine 模块依赖 img2pdf 等三方包，测试环境不一定有
    for name in ("img2pdf",):
        if name not in sys.modules:
            try:
                __import__(name)
            except ImportError:
                monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    from mineru_pipeline.engine import MinerUPipelineEngine

    return MinerUPipelineEngine


class TestFlatten:
    def test_v2_nested_by_page(self, engine_cls):
        """v2：外层按页分组"""
        data = [
            [{"type": "title"}, {"type": "paragraph"}],
            [{"type": "table"}],
        ]

        assert len(engine_cls._flatten_content_blocks(data)) == 3

    def test_v1_flat(self, engine_cls):
        data = [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]

        assert len(engine_cls._flatten_content_blocks(data)) == 2

    def test_page_objects(self, engine_cls):
        data = [{"page_index": 0, "parsing_res_list": [{"text": "x"}, {"text": "y"}]}]

        assert len(engine_cls._flatten_content_blocks(data)) == 2

    @pytest.mark.parametrize("bad", [None, {}, "string", 123, [None, 1, "x"], [[None, 2]]])
    def test_malformed_input_never_raises(self, engine_cls, bad):
        assert isinstance(engine_cls._flatten_content_blocks(bad), list)


class TestExtractText:
    def test_v1_text_field(self, engine_cls):
        assert engine_cls._extract_block_text({"text": "旧版内容"}) == "旧版内容"

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("title_content", "第一章"),
            ("paragraph_content", "第一章"),
            ("table_content", "第一章"),
            ("list_content", "第一章"),
        ],
    )
    def test_v2_content_variants(self, engine_cls, key, expected):
        block = {"type": "x", "content": {key: [{"content": expected}]}}

        assert engine_cls._extract_block_text(block) == expected

    def test_v2_multi_segment_joined(self, engine_cls):
        block = {"content": {"paragraph_content": [{"content": "正文"}, {"content": "续写"}]}}

        assert engine_cls._extract_block_text(block) == "正文续写"

    def test_production_empty_block(self, engine_cls):
        """线上真实数据：paragraph_content 为空，必须返回空串而不是抛异常"""
        block = {"type": "paragraph", "content": {"paragraph_content": []}, "bbox": [0, 0, 996, 998]}

        assert engine_cls._extract_block_text(block) == ""

    @pytest.mark.parametrize("bad", [None, [], "string", {"content": 42}, {"content": None}])
    def test_malformed_block_never_raises(self, engine_cls, bad):
        assert engine_cls._extract_block_text(bad) == ""

    def test_production_regression_end_to_end(self, engine_cls):
        """线上那条 AttributeError 的完整复现数据"""
        json_content = [[{"type": "paragraph", "content": {"paragraph_content": []}, "bbox": [0, 0, 996, 998]}]]

        texts = [engine_cls._extract_block_text(b) for b in engine_cls._flatten_content_blocks(json_content)]

        assert texts == [""]
