import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()


def read_urls_from_file(file_path=None):
  """
  텍스트 파일에서 URL 리스트를 읽습니다.

  Args:
      file_path: URL 리스트 파일 경로 (기본값: 환경 변수에서 읽음)

  Returns:
      URL 리스트
  """
  if not file_path:
    file_path = os.getenv('URLS_FILE', 'urls.txt')

  if not os.path.exists(file_path):
    raise FileNotFoundError(f"URL 리스트 파일을 찾을 수 없습니다: {file_path}")

  urls = []
  with open(file_path, 'r', encoding='utf-8') as f:
    for line in f:
      url = line.strip()
      if url and not url.startswith('#'):  # 빈 줄과 주석 제외
        urls.append(url)

  return urls


def save_crawled_data(data: Dict, output_dir=None, filename=None):
  """
  크롤링한 데이터를 JSON 파일로 저장합니다.

  Args:
      data: 저장할 데이터 딕셔너리
      output_dir: 출력 디렉토리 (기본값: 환경 변수에서 읽음)
      filename: 저장할 파일명 (기본값: URL 기반으로 자동 생성)

  Returns:
      저장된 파일 경로
  """
  if not output_dir:
    output_dir = os.getenv('OUTPUT_DIR', 'output')

  # 출력 디렉토리 생성
  Path(output_dir).mkdir(parents=True, exist_ok=True)

  # 파일명 생성
  if not filename:
    url = data.get('url', 'unknown')
    # URL에서 파일명으로 사용할 수 있는 부분 추출
    import re
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    if path_parts:
      # 마지막 경로 부분 사용
      base_name = path_parts[-1]
    else:
      base_name = 'article'

    # 파일명에 사용할 수 없는 문자 제거
    base_name = re.sub(r'[^\w\-_\.]', '_', base_name)
    filename = f"{base_name}.json"

  # 파일 경로 생성
  file_path = os.path.join(output_dir, filename)

  # JSON 파일로 저장
  with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

  return file_path


def save_all_crawled_data(data_list: List[Dict], output_dir=None, filename='all_articles.json'):
  """
  여러 크롤링 데이터를 하나의 JSON 파일에 저장합니다.

  Args:
      data_list: 저장할 데이터 딕셔너리 리스트
      output_dir: 출력 디렉토리 (기본값: 환경 변수에서 읽음)
      filename: 저장할 파일명

  Returns:
      저장된 파일 경로
  """
  if not output_dir:
    output_dir = os.getenv('OUTPUT_DIR', 'output')

  # 출력 디렉토리 생성
  Path(output_dir).mkdir(parents=True, exist_ok=True)

  # 파일 경로 생성
  file_path = os.path.join(output_dir, filename)

  # JSON 파일로 저장
  with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data_list, f, ensure_ascii=False, indent=2)

  return file_path
