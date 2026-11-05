import os
import tempfile

# Keep test runs out of the real hub log (logs/citadel.log)
os.environ.setdefault("CITADEL_LOG_DIR", tempfile.mkdtemp(prefix="citadel-test-logs-"))
