import os
import shutil
import numpy as np
from sklearn.cluster import AgglomerativeClustering

class Classifier:
    def __init__(self, output_dir="outputs"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def cluster_and_organize(self, analysis_results):
        """
        분석 결과를 기반으로 클러스터링을 수행합니다.
        분석에 실패했거나(status='failed') 유사도가 낮은 파일은 manual_list로 분류합니다.
        """
        if not analysis_results:
            return [], []

        # 1. 분석에 성공한 데이터와 실패한 데이터를 분리
        success_results = []
        manual_list = [] # 실패한 파일은 처음부터 수동 분류 리스트로

        for res in analysis_results:
            # error가 있거나 status가 failed인 경우 수동 분류로 바로 이동
            if "error" in res or res.get("status") == "failed":
                manual_list.append(res["path"])
            else:
                success_results.append(res)

        # 2. 분석 성공한 데이터가 너무 적으면 (1개 이하) 모두 수동 분류
        if len(success_results) < 2:
            for res in success_results:
                manual_list.append(res["path"])
            return [], manual_list

        # 3. 임베딩 벡터 추출 및 클러스터링
        embeddings = np.array([r["embedding"] for r in success_results])
        paths = [r["path"] for r in success_results]

        # AgglomerativeClustering: 유사하지 않은 데이터는 군집화하지 않음 (임계값 0.8)
        clustering = AgglomerativeClustering(
            n_clusters=None, 
            distance_threshold=0.8, # 코사인 거리가 0.8 이상(유사도 0.2 이하)이면 고립됨
            linkage='average',
            metric='cosine'
        ).fit(embeddings)

        labels = clustering.labels_
        unique_labels = set(labels)
        
        move_proposals = []

        # 4. 군집별로 결과 정리
        for label in unique_labels:
            indices = np.where(labels == label)[0]
            
            # 군집 크기가 1인 경우 (외톨이/유사한 파일 없음) 수동 분류로 할당
            if len(indices) <= 1:
                for idx in indices:
                    manual_list.append(paths[idx])
                continue

            # 군집 이름 (1, 2, 3...)
            folder_name = str(label + 1)
            target_dir = os.path.join(self.output_dir, folder_name)
            
            for idx in indices:
                move_proposals.append({
                    "original_path": paths[idx],
                    "target_folder": folder_name,
                    "target_full_path": os.path.join(target_dir, os.path.basename(paths[idx]))
                })

        return move_proposals, manual_list

    def execute_move(self, move_proposals):
        """실제 파일 이동 수행"""
        for move in move_proposals:
            target_dir = os.path.dirname(move["target_full_path"])
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            try:
                if os.path.exists(move["original_path"]):
                    # 동일 이름 파일이 있으면 이름 변경 (덮어쓰기 방지)
                    shutil.move(move["original_path"], move["target_full_path"])
            except Exception as e:
                print(f"Error moving {move['original_path']}: {e}")
