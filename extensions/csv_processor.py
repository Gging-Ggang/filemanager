import os
import pandas as pd
from extensions.model_loader import get_embedding

def process_csv(path):
    """
    CSV 데이터 분석 프로세서
    - 상단 행 데이터를 텍스트로 변환하여 분석
    - CLIP 모델에 최적화된 길이로 데이터 주입
    """
    try:
        # 파일이 비어있거나 인코딩 문제가 있을 경우를 대비
        df = pd.read_csv(path, nrows=10, on_bad_lines='skip')
        
        if df.empty:
            return {
                "status": "failed", "error": "데이터가 없는 빈 CSV 파일입니다.", 
                "path": os.path.abspath(path), "filename": os.path.basename(path)
            }
            
        text_content = df.to_string(index=False)
        embedding = get_embedding(text_content[:1500]) # 모델 한계 고려
        
        return {
            "status": "success",
            "path": os.path.abspath(path),
            "filename": os.path.basename(path),
            "embedding": embedding
        }
    except Exception as e:
        return {
            "status": "failed", 
            "error": f"CSV 분석 오류: {str(e)}", 
            "path": os.path.abspath(path),
            "filename": os.path.basename(path)
        }
