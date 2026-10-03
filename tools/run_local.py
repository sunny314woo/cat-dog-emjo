"""Run an isolated local demo without credentials or outbound paid API calls."""
from pathlib import Path
import os
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['EMJO_MODE']='demo'
os.environ.setdefault('EMJO_DATA_DIR',str(ROOT/'.local-data'))
os.environ.setdefault('EMJO_PUBLIC_URL','http://127.0.0.1:4173/sticker')
import uvicorn
uvicorn.run('server.main:app',host='127.0.0.1',port=4173,log_level='warning')
