import os
import json
import datetime
import tempfile
import traceback

class AnalyzerManager:
    def __init__(self, log_dir=None):
        if log_dir is None:
            self.log_dir = os.path.join(tempfile.gettempdir(), "ai_file_manager_logs")
        else:
            self.log_dir = os.path.abspath(log_dir)

        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except:
                self.log_dir = os.path.abspath(".logs_hidden")
                if not os.path.exists(self.log_dir):
                    os.makedirs(self.log_dir)
        
        print(f"Log location: {self.log_dir}")
        
        self.processors = {}
        self._load_processors()

    def _load_processors(self):
        """프로세서 로드 시 발생하는 상세 에러를 캡처하여 디버깅 지원"""
        # PDF
        try:
            from extensions.pdf_processor import process_pdf
            self.processors['.pdf'] = process_pdf
        except Exception as e:
            print(f"Error: PDF 프로세서 로드 실패 - {str(e)}")

        # Image (확장자 추가)
        try:
            from extensions.image_processor import process_image
            image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.gif']
            for ext in image_exts:
                self.processors[ext] = process_image
        except Exception as e:
            print(f"Error: 이미지 프로세서 로드 실패 - {str(e)}")

        # CSV
        try:
            from extensions.csv_processor import process_csv
            self.processors['.csv'] = process_csv
        except Exception as e:
            print(f"Error: CSV 프로세서 로드 실패 - {str(e)}")

    def analyze(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        processor = self.processors.get(ext)
        
        if not processor:
            # 지원하지 않는 파일도 'failed' 상태로 명확히 반환 (프론트엔드 실패 목록 이동용)
            return {
                "status": "failed", 
                "error": f"지원하지 않거나 설치되지 않은 프로세서: {ext}", 
                "path": os.path.abspath(file_path),
                "filename": os.path.basename(file_path)
            }
        
        try:
            result = processor(file_path)
            # 프로세서가 결과를 누락하거나 잘못된 형식을 반환할 경우 보정
            if not result:
                result = {"status": "failed", "error": "분석 결과 없음", "path": file_path}
            
            if "status" not in result:
                result["status"] = "success" # 임베딩이 있으면 성공으로 간주
            
            if result.get("status") == "success":
                self._log_result(result)
            return result
        except Exception as e:
            return {
                "status": "failed", 
                "error": f"분석 프로세스 내 치명적 오류: {str(e)}", 
                "path": os.path.abspath(file_path),
                "filename": os.path.basename(file_path)
            }

    def _log_result(self, result):
        try:
            log_file = os.path.join(self.log_dir, f"analysis_{datetime.date.today()}.jsonl")
            log_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "path": result.get("path"),
                "filename": result.get("filename"),
                "status": result.get("status")
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except:
            pass
