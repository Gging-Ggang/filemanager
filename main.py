import os
import sys
import subprocess
import json
import uvicorn
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from analyzer_manager import AnalyzerManager
from classifier import Classifier

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 초기화
manager = AnalyzerManager()
classifier = Classifier()

# 마지막으로 선택한 경로 저장 (초기값은 사용자 홈 디렉토리)
last_dir = os.path.expanduser("~")

def run_tk_dialog(script: str):
    try:
        full_script = f"""
import tkinter as tk
from tkinter import filedialog
import json
import ctypes
import os
try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except: pass
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
{script}
"""
        cmd = [sys.executable, "-c", full_script]
        result = subprocess.check_output(cmd, text=True, encoding='utf-8')
        return json.loads(result.strip())
    except: return []

@app.get("/dialog/file")
def open_file_dialog():
    global last_dir
    script = f"files = filedialog.askopenfilenames(initialdir=r'{last_dir}'); print(json.dumps(list(files)))"
    files = run_tk_dialog(script)
    if files:
        last_dir = os.path.dirname(files[0])
    return {"paths": [os.path.normpath(f) for f in files if f]}

@app.get("/dialog/folder")
def open_folder_dialog():
    global last_dir
    script = f"folder = filedialog.askdirectory(initialdir=r'{last_dir}'); print(json.dumps([folder] if folder else []))"
    folder_list = run_tk_dialog(script)
    if not folder_list: return {"paths": []}
    
    selected_path = folder_list[0]
    last_dir = os.path.dirname(selected_path)
    return {"paths": [os.path.normpath(selected_path)]}

@app.get("/list/directory")
def list_directory(path: str):
    try:
        if not os.path.isdir(path):
            return {"items": None, "is_file": True}
        items = []
        with os.scandir(path) as it:
            for entry in it:
                items.append({
                    "name": entry.name,
                    "path": os.path.normpath(entry.path),
                    "is_dir": entry.is_dir()
                })
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"items": items, "is_file": False}
    except Exception as e:
        return {"items": [], "error": str(e), "is_file": False}

@app.get("/analyze/file")
async def analyze_file(path: str):
    """
    범용 분석 API (PDF, 이미지, CSV 대응)
    - run_in_threadpool을 사용하여 모델 로드/분석 중에도 서버가 멈추지 않도록 함
    """
    result = await run_in_threadpool(manager.analyze, path)
    if result:
        return result
    return {"status": "failed", "error": "지원하지 않는 확장자이거나 분석 실패", "path": path}

@app.post("/classify")
def classify_files(analysis_results: list = Body(...)):
    """분석 결과를 바탕으로 클러스터링 및 분류 제안"""
    move_proposals, manual_list = classifier.cluster_and_organize(analysis_results)
    return {
        "move_proposals": move_proposals,
        "manual_list": manual_list
    }

@app.post("/execute_move")
def execute_move(move_proposals: list = Body(...)):
    """확정된 이동 실행"""
    classifier.execute_move(move_proposals)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
