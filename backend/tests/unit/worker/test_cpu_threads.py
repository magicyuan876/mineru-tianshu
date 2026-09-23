import pytest

from tests.unit.worker.test_routing import load_worker_module


@pytest.mark.parametrize(
    ("override", "total", "cpus", "expected"),
    [
        (None, "16", 128, 8),  # 线上：128 核、8 卡 x 2 进程
        ("", "16", 128, 8),  # compose 传入空字符串 = 自动
        ("4", "16", 128, 4),  # 显式指定优先
        ("0", "16", 128, 8),  # 0 视为自动
        ("abc", "16", 128, 8),  # 非法值回落自动
        (None, None, 128, 128),  # 进程总数未知（本地单进程）按 1 算
        (None, "16", 8, 1),  # 核数少于进程数时至少 1
        (None, "bad", 12, 12),
    ],
)
def test_resolve_cpu_threads(monkeypatch, override, total, cpus, expected):
    worker_module = load_worker_module(monkeypatch)

    assert worker_module.resolve_cpu_threads(override, total, cpus) == expected


def test_configure_cpu_threads_sets_defaults_but_keeps_explicit_vars(monkeypatch):
    worker_module = load_worker_module(monkeypatch)
    for var in worker_module.CPU_THREAD_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("WORKER_CPU_THREADS", raising=False)
    monkeypatch.setenv(worker_module.TOTAL_WORKERS_ENV, "16")
    monkeypatch.setenv("OMP_NUM_THREADS", "3")
    monkeypatch.setattr(worker_module, "_available_cpus", lambda: 128)

    threads = worker_module.configure_cpu_threads()

    assert threads == 8
    assert worker_module.os.environ["OMP_NUM_THREADS"] == "3"
    assert worker_module.os.environ["MKL_NUM_THREADS"] == "8"
    assert worker_module.os.environ["OPENBLAS_NUM_THREADS"] == "8"
    assert worker_module.os.environ["NUMEXPR_NUM_THREADS"] == "8"


def test_configure_cpu_threads_covers_mineru_onnx_env(monkeypatch):
    worker_module = load_worker_module(monkeypatch)
    for var in (*worker_module.CPU_THREAD_ENV_VARS, "MINERU_INTER_OP_NUM_THREADS", "WORKER_CPU_THREADS"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv(worker_module.TOTAL_WORKERS_ENV, "16")
    monkeypatch.setattr(worker_module, "_available_cpus", lambda: 128)

    worker_module.configure_cpu_threads()

    assert worker_module.os.environ["MINERU_INTRA_OP_NUM_THREADS"] == "8"
    assert worker_module.os.environ["MINERU_INTER_OP_NUM_THREADS"] == "1"


@pytest.fixture
def identity_model(tmp_path):
    onnx = pytest.importorskip("onnx")
    from onnx import TensorProto, helper

    graph = helper.make_graph(
        [helper.make_node("Identity", ["x"], ["y"])],
        "identity",
        [helper.make_tensor_value_info("x", TensorProto.FLOAT, [1])],
        [helper.make_tensor_value_info("y", TensorProto.FLOAT, [1])],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    path = tmp_path / "identity.onnx"
    onnx.save(model, str(path))
    return str(path)


def test_onnxruntime_sessions_without_options_get_threads_and_providers(monkeypatch, identity_model):
    ort = pytest.importorskip("onnxruntime")
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setattr(ort, "InferenceSession", ort.InferenceSession)  # 测试结束后还原

    # 本地为 CPU 版 onnxruntime：即使 use_cuda=True 也只能回落 CPU，不能因缺 CUDA provider 报错
    assert worker_module.configure_onnxruntime_sessions(3, use_cuda=True) == ["CPUExecutionProvider"]
    worker_module.configure_onnxruntime_sessions(3, use_cuda=True)  # 重复调用不叠加包装
    assert ort.InferenceSession.__mro__[1] is ort.InferenceSession._tianshu_original

    # 与 MinerU PaddleTableClsModel 相同：既不传 SessionOptions 也不传 providers
    bare = ort.InferenceSession(identity_model)
    assert bare.get_session_options().intra_op_num_threads == 3
    assert bare.get_session_options().inter_op_num_threads == 1
    assert bare.get_providers() == ["CPUExecutionProvider"]

    # 显式配置的线程数与 providers 保持不动
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 5
    explicit = ort.InferenceSession(identity_model, sess_options=opts, providers=["CPUExecutionProvider"])
    assert explicit.get_session_options().intra_op_num_threads == 5

    # 包装后仍能正常推理
    import numpy as np

    out = bare.run(None, {"x": np.array([1.5], dtype=np.float32)})[0]
    assert out.tolist() == [1.5]


def test_onnxruntime_cuda_provider_injected_when_available(monkeypatch, identity_model):
    ort = pytest.importorskip("onnxruntime")
    worker_module = load_worker_module(monkeypatch)
    monkeypatch.setattr(ort, "InferenceSession", ort.InferenceSession)
    monkeypatch.setattr(ort, "get_available_providers", lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"])

    assert worker_module.configure_onnxruntime_sessions(4, use_cuda=True) == [
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    assert worker_module.configure_onnxruntime_sessions(4, use_cuda=False) == ["CPUExecutionProvider"]


def test_onnxruntime_session_passes_cuda_first_to_base(monkeypatch):
    ort = pytest.importorskip("onnxruntime")
    worker_module = load_worker_module(monkeypatch)
    captured = {}

    class FakeBase:
        def __init__(self, path_or_bytes, sess_options=None, providers=None, provider_options=None, **kwargs):
            captured.update(providers=providers, threads=sess_options.intra_op_num_threads)

    monkeypatch.setattr(ort, "InferenceSession", FakeBase)
    monkeypatch.setattr(ort, "get_available_providers", lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"])
    worker_module.configure_onnxruntime_sessions(4, use_cuda=True)

    ort.InferenceSession("model.onnx")
    assert captured["threads"] == 4
    assert captured["providers"][0][0] == "CUDAExecutionProvider"
    assert captured["providers"][0][1]["device_id"] == 0
    assert captured["providers"][1] == "CPUExecutionProvider"

    ort.InferenceSession("model.onnx", providers=["CPUExecutionProvider"])
    assert captured["providers"] == ["CPUExecutionProvider"]
