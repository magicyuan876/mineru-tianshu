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
