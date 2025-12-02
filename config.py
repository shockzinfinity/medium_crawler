import logging
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
    
    # 파일 핸들러 설정
    file_handler = logging.FileHandler(
        log_dir / 'medium_crawler.log',
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
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

