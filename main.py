import argparse
import os
import sys

from dotenv import load_dotenv

from config import get_logger, setup_logging
from crawler import MediumCrawler
from utils import read_urls_from_file, save_all_crawled_data, save_crawled_data

load_dotenv()


def main():
    """메인 실행 함수"""
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description='Medium Crawler with Gmail Auth')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 활성화')
    parser.add_argument('--login-only', action='store_true', help='로그인만 테스트하고 종료')
    args = parser.parse_args()
    
    # 로깅 설정
    setup_logging(debug=args.debug)
    logger = get_logger(__name__)
    
    logger.info("=" * 50)
    logger.info("Medium Crawler 시작")
    logger.info("=" * 50)
    
    # 환경 변수 확인 (필수: MEDIUM_EMAIL)
    email = os.getenv('MEDIUM_EMAIL')
    if not email:
        logger.error("MEDIUM_EMAIL 환경 변수가 설정되지 않았습니다.")
        logger.error(".env 파일에 MEDIUM_EMAIL을 설정하세요.")
        sys.exit(1)
    
    logger.debug(f"이메일: {email}")
    
    # 크롤러 초기화
    logger.info("크롤러 초기화 중...")
    try:
        crawler = MediumCrawler(email=email, headless=False)
        logger.debug("크롤러 초기화 완료")
    except Exception as e:
        logger.exception(f"크롤러 초기화 실패: {e}")
        sys.exit(1)
    
    # 로그인 (먼저 테스트)
    logger.info("Medium 로그인 시도 중...")
    logger.info("=" * 50)
    try:
        login_success = crawler.login()
        if not login_success:
            logger.error("로그인에 실패했습니다.")
            logger.error("로그인 상태를 확인하고 다시 시도하세요.")
            crawler.close_browser()
            sys.exit(1)
        logger.info("로그인 성공!")
    except Exception as e:
        logger.exception(f"로그인 실패: {e}")
        crawler.close_browser()
        sys.exit(1)
    
    # 로그인만 테스트하는 경우 종료
    if args.login_only:
        logger.info("로그인 테스트 완료. 종료합니다.")
        crawler.close_browser()
        sys.exit(0)
    
    # 로그인 성공 후 URL 리스트 확인 및 읽기
    urls_file = os.getenv('URLS_FILE', 'urls.txt')
    if not os.path.exists(urls_file):
        logger.warning(f"URL 리스트 파일을 찾을 수 없습니다: {urls_file}")
        logger.warning("로그인은 성공했지만 크롤링할 URL이 없습니다.")
        logger.warning(f"'{urls_file}' 파일을 생성하고 크롤링할 URL을 한 줄에 하나씩 입력하세요.")
        crawler.close_browser()
        sys.exit(0)
    
    # URL 리스트 읽기
    logger.info(f"URL 리스트 파일 읽는 중: {urls_file}")
    try:
        urls = read_urls_from_file(urls_file)
        logger.info(f"총 {len(urls)}개의 URL을 찾았습니다.")
        logger.debug(f"URL 목록: {urls}")
    except Exception as e:
        logger.exception(f"URL 리스트 파일 읽기 실패: {e}")
        crawler.close_browser()
        sys.exit(1)
    
    if not urls:
        logger.warning("크롤링할 URL이 없습니다.")
        crawler.close_browser()
        sys.exit(0)
    
    # 크롤링 실행
    logger.info("크롤링 시작...")
    logger.info("=" * 50)
    
    all_data = []
    success_count = 0
    error_count = 0
    
    for i, url in enumerate(urls, 1):
        logger.info(f"[{i}/{len(urls)}] 크롤링 중: {url}")
        
        try:
            article_data = crawler.crawl_article(url)
            
            if 'error' in article_data:
                logger.error(f"  오류: {article_data['error']}")
                error_count += 1
            else:
                # 개별 파일로 저장
                try:
                    saved_path = save_crawled_data(article_data)
                    logger.info(f"  저장 완료: {saved_path}")
                    logger.debug(f"  크롤링 데이터: {article_data.get('title', 'N/A')}")
                    all_data.append(article_data)
                    success_count += 1
                except Exception as e:
                    logger.exception(f"  저장 오류: {e}")
                    error_count += 1
            
        except Exception as e:
            logger.exception(f"  크롤링 오류: {e}")
            error_data = {
                'url': url,
                'error': str(e)
            }
            all_data.append(error_data)
            error_count += 1
        
        # 다음 URL 크롤링 전 잠시 대기 (서버 부하 방지)
        if i < len(urls):
            import time
            time.sleep(2)
    
    # 모든 데이터를 하나의 파일로도 저장
    if all_data:
        try:
            output_dir = os.getenv('OUTPUT_DIR', 'output')
            all_data_path = save_all_crawled_data(all_data, output_dir=output_dir)
            logger.info(f"전체 데이터 저장 완료: {all_data_path}")
        except Exception as e:
            logger.exception(f"전체 데이터 저장 오류: {e}")
    
    # 결과 요약
    logger.info("=" * 50)
    logger.info("크롤링 완료")
    logger.info("=" * 50)
    logger.info(f"성공: {success_count}개")
    logger.info(f"실패: {error_count}개")
    logger.info(f"전체: {len(urls)}개")
    
    # 브라우저 종료
    crawler.close_browser()
    logger.info("프로그램 종료.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger = get_logger(__name__)
        logger.warning("\n\n사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        logger = get_logger(__name__)
        logger.exception(f"\n예상치 못한 오류 발생: {e}")
        sys.exit(1)

