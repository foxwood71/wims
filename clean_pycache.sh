#!/bin/bash

# --- 스크립트 설명 ---
# 프로젝트 내의 모든 Python 캐시 파일 및 폴더를 삭제합니다.
# (__pycache__, .pytest_cache 등)

echo "Python 캐시 파일 및 폴더를 삭제합니다..."

# __pycache__ 디렉토리 찾아서 삭제
find . -type d -name "__pycache__" -exec rm -rf {} +

# .pytest_cache 디렉토리 찾아서 삭제
find . -type d -name ".pytest_cache" -exec rm -rf {} +

echo "완료: 모든 캐시가 삭제되었습니다."