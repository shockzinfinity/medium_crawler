import argparse
import os
import sys

from dotenv import load_dotenv

from config import get_logger, setup_logging
from crawler import MediumCrawler
from gmail_checker import GmailChecker
from utils import read_urls_from_file, save_all_crawled_data, save_crawled_data

load_dotenv()


def show_menu():
  """메뉴 표시 및 선택"""
  print("\n" + "=" * 50)
  print("Medium Crawler - 작업 선택")
  print("=" * 50)
  print("1. Medium 로그인만 테스트")
  print("2. Medium 로그인 후 urls.txt 크롤링 진행")
  print("3. Gmail을 통해 Medium 리스트 다운로드")
  print("=" * 50)

  while True:
    try:
      choice = input("\n선택하세요 (1-3): ").strip()
      if choice in ['1', '2', '3']:
        return int(choice)
      else:
        print("잘못된 선택입니다. 1, 2, 또는 3을 입력하세요.")
    except KeyboardInterrupt:
      print("\n\n사용자에 의해 중단되었습니다.")
      sys.exit(0)
    except Exception as e:
      print(f"입력 오류: {e}")


def main():
  """메인 실행 함수"""
  # 명령줄 인자 파싱
  parser = argparse.ArgumentParser(description='Medium Crawler with Gmail Auth')
  parser.add_argument('--debug', action='store_true', help='디버그 모드 활성화')
  parser.add_argument('--mode', type=int, choices=[1, 2, 3],
                      help='작업 모드: 1=로그인만, 2=로그인+크롤링, 3=Gmail 리스트 다운로드')
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

  # 메뉴 선택 (명령줄 인자가 없으면 대화형 메뉴 표시)
  if args.mode:
    mode = args.mode
  else:
    mode = show_menu()

  logger.info(f"선택된 모드: {mode}")

  # 모드 3: Gmail을 통해 Medium 리스트 다운로드 (로그인 필요)
  if mode == 3:
    logger.info("Gmail을 통해 Medium 리스트 다운로드 시작...")
    logger.info("=" * 50)

    # 크롤러 초기화 및 로그인 (다운로드 링크 접근을 위해)
    logger.info("크롤러 초기화 중...")
    try:
      crawler = MediumCrawler(email=email, headless=False)
      logger.debug("크롤러 초기화 완료")
    except Exception as e:
      logger.exception(f"크롤러 초기화 실패: {e}")
      sys.exit(1)

    # 로그인
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

    try:
      gmail_checker = GmailChecker()
      sender_email = os.getenv('SENDER_EMAIL', 'noreply@medium.com')
      download_path = os.getenv('DOWNLOAD_PATH', 'downloads')
      search_query = 'subject:"Medium download request"'

      # 로그인된 브라우저 페이지를 전달하여 다운로드
      result = gmail_checker.get_medium_list(
          email=email,
          sender_email=sender_email,
          download_path=download_path,
          search_query=search_query,
          browser_page=crawler.page
      )
      if result:
        logger.info(f"다운로드 완료: {result}")
      else:
        logger.warning("다운로드할 항목을 찾을 수 없습니다.")
    except Exception as e:
      logger.exception(f"Gmail 리스트 다운로드 실패: {e}")
      crawler.close_browser()
      sys.exit(1)
    finally:
      crawler.close_browser()
    logger.info("프로그램 종료.")
    return

  # 모드 1, 2: Medium 로그인 필요
  # 크롤러 초기화
  logger.info("크롤러 초기화 중...")
  try:
    crawler = MediumCrawler(email=email, headless=False)
    logger.debug("크롤러 초기화 완료")
  except Exception as e:
    logger.exception(f"크롤러 초기화 실패: {e}")
    sys.exit(1)

  # 로그인
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

  # 모드 1: 로그인만 테스트하고 종료
  if mode == 1:
    logger.info("로그인 테스트 완료. 종료합니다.")
    crawler.close_browser()
    return

  # 모드 2: 로그인 성공 후 URL 리스트 확인 및 읽기
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
