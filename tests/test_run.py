import subprocess
import sys

def test_pipeline_entrypoint():
    result=subprocess.run([sys.executable,'run.py','--help'],capture_output=True,text=True)
    assert result.returncode==0 and '--output' in result.stdout
