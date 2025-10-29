# nixe/boot/early_env.py
# Apply as EARLY as possible (very top of main.py) to suppress native gRPC/absl noise.
def apply():
    import os
    # Load .env first so any GRPC_* you set there is respected early
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except Exception:
        pass

    # Suppress native logs from gRPC/abseil (set BEFORE any gRPC-backed import)
    os.environ.setdefault("GRPC_VERBOSITY", "ERROR")  # show only errors (INFO/WARN hidden)
    # Hide even 'ERROR' lines (like ALTS creds ignored) via glog level 3 (FATAL-only)
    os.environ.setdefault("GLOG_minloglevel", "3")

    # Optional: calm down other noisy stacks if present
    os.environ.setdefault("GRPC_TRACE", "")  # ensure tracing is off
    # Note: absl::InitializeLog() happens inside native libs; we can't call it here,
    # but minloglevel=3 ensures error-level messages are dropped.
