import bench.bakeoff as bakeoff


def test_module_imports_without_llama_cpp_or_models():
    # If we got this far, the import at the top of this file already
    # succeeded with no llama_cpp/model dependency required.
    assert hasattr(bakeoff, "run_bakeoff")
    assert hasattr(bakeoff, "CANDIDATES")


def test_run_bakeoff_empty_list_returns_empty():
    assert bakeoff.run_bakeoff([]) == []


def test_run_bakeoff_skips_nonexistent_path():
    assert bakeoff.run_bakeoff(["models/does-not-exist.gguf"]) == []
