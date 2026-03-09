import os
from extensions.model_loader import get_embedding

def process_image(path):
    """
    이미지 분석 프로세서
    - CLIP 모델을 사용하여 이미지 벡터 추출
    - 분석 성공 여부를 명확히 반환
    """
    try:
        embedding = get_embedding(path, is_image=True)
        return {
            "status": "success",
            "path": os.path.abspath(path),
            "filename": os.path.basename(path),
            "embedding": embedding
        }
    except Exception as e:
        return {
            "status": "failed", 
            "error": str(e), 
            "path": os.path.abspath(path),
            "filename": os.path.basename(path)
        }
