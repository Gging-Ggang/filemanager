from sentence_transformers import SentenceTransformer
from PIL import Image
import numpy as np

# 모델 캐싱
_text_model = None
_vision_model = None

def get_text_model():
    global _text_model
    if _text_model is None:
        # 한국어 및 다국어 텍스트 지원용
        _text_model = SentenceTransformer('clip-ViT-B-32-multilingual-v1')
    return _text_model

def get_vision_model():
    global _vision_model
    if _vision_model is None:
        # 이미지 분석용 (시각 엔진 내장 모델)
        # clip-ViT-B-32 체계를 유지하면서 이미지 인코딩이 가능한 모델 로드
        _vision_model = SentenceTransformer('clip-ViT-B-32')
    return _vision_model

def get_embedding(content, is_image=False):
    """
    텍스트 또는 이미지로부터 임베딩 추출
    - 이미지: 시각 엔진이 포함된 모델 사용
    - 텍스트: 다국어(한국어) 지원 모델 사용
    """
    try:
        if is_image:
            model = get_vision_model()
            img = Image.open(content).convert("RGB")
            # 단일 이미지 인코딩
            embedding = model.encode(img)
            return embedding.tolist()
        else:
            model = get_text_model()
            # 단일 텍스트 인코딩
            embedding = model.encode(str(content))
            return embedding.tolist()
    except Exception as e:
        print(f"Embedding error: {e}")
        raise e
