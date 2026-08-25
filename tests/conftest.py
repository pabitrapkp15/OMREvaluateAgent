import os
import tempfile
from pathlib import Path


os.environ.setdefault("OMR_DB_PATH", str(Path(tempfile.gettempdir()) / f"omr-evaluate-tests-{os.getpid()}.db"))