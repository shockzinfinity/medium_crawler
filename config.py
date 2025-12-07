import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def setup_logging(debug=False):
  """
  로깅 설정

  Args:
      debug: 디버그 모드 활성화 여부
  """
  log_level = logging.DEBUG if debug else logging.INFO

  # 로그 디렉토리 생성
  log_dir = Path('logs')
  log_dir.mkdir(exist_ok=True)

  # 로그 포맷 설정
  log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  date_format = '%Y-%m-%d %H:%M:%S'

  # 로그 파일명에 날짜/시간 포함 (예: medium_crawler_2024-01-15_14-30-00.log)
  timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
  log_filename = log_dir / f'{timestamp}.log'

  # 파일 핸들러 설정 (TimedRotatingFileHandler 사용)
  # 매일 자정에 rolling, 최대 30일 보관, 백업 파일명에 날짜 포함
  file_handler = TimedRotatingFileHandler(
      filename=str(log_filename),
      when='midnight',  # 매일 자정에 rolling
      interval=1,  # 1일마다
      backupCount=30,  # 최대 30개 파일 보관
      encoding='utf-8',
      delay=False
  )
  file_handler.setLevel(log_level)
  file_handler.setFormatter(logging.Formatter(log_format, date_format))

  # 백업 파일명에 날짜 포함하도록 suffix 설정
  file_handler.suffix = '%Y-%m-%d'

  # 콘솔 핸들러 설정
  console_handler = logging.StreamHandler()
  console_handler.setLevel(log_level)
  console_handler.setFormatter(logging.Formatter(log_format, date_format))

  # 루트 로거 설정
  root_logger = logging.getLogger()
  root_logger.setLevel(log_level)
  root_logger.addHandler(file_handler)
  root_logger.addHandler(console_handler)

  # 외부 라이브러리 로그 레벨 조정
  logging.getLogger('urllib3').setLevel(logging.WARNING)
  logging.getLogger('googleapiclient').setLevel(logging.WARNING)
  logging.getLogger('playwright').setLevel(logging.INFO)

  return root_logger


def get_logger(name):
  """로거 인스턴스 반환"""
  return logging.getLogger(name)
