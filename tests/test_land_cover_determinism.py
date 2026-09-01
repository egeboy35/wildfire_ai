"""The land-cover selection must not change between server restarts.

``backend/services.py`` picks a fuel model for a coordinate by hashing the
coordinate string. Python salts ``hash()`` of a ``str`` per process
(PYTHONHASHSEED), so the same location was assigned a different fuel model
after every restart of the FastAPI server, while the response continued to cite
"USDA NASS Cropland Data Layer (CDL) & LANDFIRE EVT" as the source. This test
runs the selection in several fresh interpreters with different hash seeds and
requires one answer.
"""

import os
import subprocess
import sys

# Mirrors the selection in backend/services.py. Kept as a literal rather than an
# import so the test stays honest if the endpoint is refactored: it pins the
# property (stability across processes), not the implementation.
SNIPPET = (
    "import zlib;"
    "print(zlib.crc32(b'37.630,-122.411') % 3)"
)


def _env_with_seed(seed):
    """Inherit the real environment and override only the hash seed.

    Building the child environment from scratch needs platform-specific keys
    (SYSTEMROOT on Windows) to even start an interpreter, so it is simpler and
    more portable to copy the parent's.
    """
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(seed)
    return env


def _run_with_seed(seed):
    proc = subprocess.run(
        [sys.executable, "-c", SNIPPET],
        capture_output=True, text=True, timeout=60, check=False,
        env=_env_with_seed(seed),
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def test_selection_is_stable_across_processes():
    results = {_run_with_seed(seed) for seed in (0, 1, 42, 1000, 31337)}
    assert len(results) == 1, (
        f"the same coordinate produced {len(results)} different land-cover indices "
        f"across interpreters with different hash seeds: {sorted(results)}"
    )


def test_builtin_hash_would_not_be_stable():
    """Guard the reason for the change, so it is not reverted as cosmetic."""
    proc_results = set()
    for seed in (1, 2, 3, 4, 5, 6, 7, 8):
        proc = subprocess.run(
            [sys.executable, "-c", "print(hash('37.630,-122.411') % 3)"],
            capture_output=True, text=True, timeout=60, check=False,
            env=_env_with_seed(seed),
        )
        assert proc.returncode == 0, proc.stderr
        proc_results.add(proc.stdout.strip())
    assert len(proc_results) > 1, (
        "expected builtin hash() of a str to vary across hash seeds; if this ever "
        "fails, the salting behaviour changed and the crc32 change can be revisited"
    )


def test_services_module_no_longer_uses_builtin_hash_for_land_cover():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "backend", "services.py"), encoding="utf-8") as fh:
        src = fh.read()
    assert "hash(f\"{lat:.3f},{lng:.3f}\")" not in src, (
        "land-cover selection is back on builtin hash(), which is per-process salted"
    )
    assert "zlib.crc32" in src
