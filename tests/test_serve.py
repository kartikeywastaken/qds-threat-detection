import subprocess
import sys

def test_server_entrypoint():
    result=subprocess.run([sys.executable,'-m','presentation.serve','--help'],capture_output=True,text=True)
    assert result.returncode==0 and '--port' in result.stdout
