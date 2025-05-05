# test/conftest.py
import os
import sys
import json

test_dir_path = os.path.dirname(os.path.abspath(__file__))
project_root_path = os.path.dirname(test_dir_path)

if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)
src_path = os.path.join(project_root_path, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
