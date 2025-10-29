# Auto-imported by Python if present on sys.path.
# This runs extremely early, before most imports, to force quiet native logs.
import os
# Respect any value already set by the environment; else enforce strict silence.
os.environ.setdefault("GRPC_VERBOSITY", "NONE")   # DEBUG/INFO/ERROR/NONE
os.environ.setdefault("GLOG_minloglevel", "3")    # 3 -> FATAL only
os.environ.setdefault("GRPC_TRACE", "")
# If using dotenv later, those values can still override via override=True.
