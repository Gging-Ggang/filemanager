import os
import fitz  # PyMuPDF
import numpy as np
from extensions.model_loader import get_embedding

def process_pdf(path):
    """
    안정적인 PDF 텍스트 추출 및 지능형 청킹 분석 프로세서
    - fitz(PyMuPDF) 라이브러리 설정 오류를 안전하게 처리
    - CLIP 모델 한계를 극복하기 위해 텍스트 청킹 후 평균 임베딩 산출
    """
    try:
        # 1. 라이브러리 설정을 안전한 블록 내부로 이동 (AttributeError 방지)
        try:
            if hasattr(fitz, 'TOOLS'):
                fitz.TOOLS.mupdf_display_errors(False)
                fitz.TOOLS.mupdf_display_warnings(False)
        except:
            pass

        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        if not text.strip():
            return {
                "status": "failed", 
                "error": "텍스트를 추출할 수 없습니다 (이미지 위주의 PDF 등).", 
                "path": os.path.abspath(path),
                "filename": os.path.basename(path)
            }

        # 2. 텍스트 청킹 (Chunking) 전략
        # CLIP 모델의 실제 전처리 한계를 고려하여 약 200자 단위로 쪼개어 분석
        # 최대 3000자까지만 분석하여 성능 확보
        chunk_size = 200 
        max_chars = 3000
        processed_text = text[:max_chars]
        chunks = [processed_text[i:i+chunk_size] for i in range(0, len(processed_text), chunk_size)]
        
        embeddings = []
        for chunk in chunks:
            if chunk.strip():
                try:
                    emb = get_embedding(chunk)
                    embeddings.append(emb)
                except Exception as e:
                    print(f"Chunk embedding failed: {e}")
        
        if not embeddings:
            return {
                "status": "failed", 
                "error": "유효한 분석 벡터를 생성하지 못했습니다.", 
                "path": os.path.abspath(path),
                "filename": os.path.basename(path)
            }

        # 3. 평균 임베딩 산출 (Pooling)
        # 여러 구절의 의미를 종합하여 문서 전체를 대표하는 벡터 생성
        final_embedding = np.mean(embeddings, axis=0).tolist()

        return {
            "status": "success",
            "path": os.path.abspath(path),
            "filename": os.path.basename(path),
            "embedding": final_embedding,
            "char_count": len(text)
        }

    except Exception as e:
        return {
            "status": "failed", 
            "error": f"PDF 분석 실패: {str(e)}", 
            "path": os.path.abspath(path),
            "filename": os.path.basename(path)
        }
