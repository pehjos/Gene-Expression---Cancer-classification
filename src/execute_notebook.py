"""Execute the tutorial with a project-local kernel and save real cell outputs."""
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
os.environ['JUPYTER_PATH']=str(ROOT/'.venv/share/jupyter')
os.environ['JUPYTER_RUNTIME_DIR']=str(ROOT/'tmp/jupyter_runtime')
os.environ['IPYTHONDIR']=str(ROOT/'tmp/ipython')
os.environ['MPLCONFIGDIR']=str(ROOT/'tmp/matplotlib')
os.environ['TEMP']=str(ROOT/'tmp')
os.environ['TMP']=str(ROOT/'tmp')
import nbformat
from nbclient import NotebookClient
path=ROOT/'notebooks/cancer_classification.ipynb'
notebook=nbformat.read(path,as_version=4)
client=NotebookClient(notebook,timeout=1800,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}})
def log_cell(cell_index,**kwargs):print(f'Executing notebook cell {cell_index}',flush=True)
client.on_cell_start=log_cell
client.execute()
nbformat.write(notebook,path)
print('Executed notebook saved:',path)
