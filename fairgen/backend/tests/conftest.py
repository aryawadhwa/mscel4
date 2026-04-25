"""pytest conftest — adds backend root to sys.path so all modules are importable."""
import sys
import os

# Insert backend root so `import pipeline`, `import schemas`, etc. work without
# installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
