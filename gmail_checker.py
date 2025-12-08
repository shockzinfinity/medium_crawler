import base64
import logging
import os
import re
import time
from io import StringIO

import requests
from dotenv import load_dotenv
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from lxml import etree

load_dotenv()

logger = logging.getLogger(__name__)

# Gmail API 스코프 (읽기 및 수정 권한 필요)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]


class GmailChecker:
  def __init__(self, credentials_path=None, token_path=None, sender_email=None):
    self.credentials_path = credentials_path or os.getenv(
        'GMAIL_CREDENTIALS_PATH', 'credentials.json')
    self.token_path = token_path or os.getenv('GMAIL_TOKEN_PATH', 'token.json')
    self.service = None
    self._authenticate()

  def _authenticate(self):
    """Gmail API 인증 및 서비스 초기화"""
    creds = None

    # 기존 토큰이 있는지 확인
    if os.path.exists(self.token_path):
      creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

    # 토큰이 없거나 만료된 경우 새로 인증
    if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
        try:
          # refresh token으로 새 access token 발급 시도
          creds.refresh(Request())
          logger.debug("토큰이 성공적으로 갱신되었습니다.")
        except RefreshError as e:
          # refresh token이 만료되었거나 취소된 경우
          logger.warning(f"토큰 갱신 실패: {e}")
          logger.info("기존 토큰이 만료되었거나 취소되었습니다. 재인증이 필요합니다.")
          # 기존 토큰 파일 삭제
          if os.path.exists(self.token_path):
            os.remove(self.token_path)
            logger.debug(f"기존 토큰 파일 삭제: {self.token_path}")
          # creds를 None으로 설정하여 재인증 진행
          creds = None

      # 토큰이 없거나 refresh 실패한 경우 재인증
      if not creds or not creds.valid:
        if not os.path.exists(self.credentials_path):
          raise FileNotFoundError(
              f"Gmail API 인증 정보 파일을 찾을 수 없습니다: {self.credentials_path}\n"
              "Google Cloud Console에서 credentials.json 파일을 다운로드하세요."
          )
        logger.info("새로운 인증을 시작합니다. 브라우저가 열리면 Google 계정으로 로그인하세요.")
        flow = InstalledAppFlow.from_client_secrets_file(
            self.credentials_path, SCOPES
        )
        creds = flow.run_local_server(port=0)

      # 토큰 저장
      with open(self.token_path, 'w') as token:
        token.write(creds.to_json())

    self.service = build('gmail', 'v1', credentials=creds)

  def get_medium_verification_code(self, email=None, sender_email=None, max_retries=5, retry_interval=5):
    """
    Medium에서 보낸 인증 코드 이메일을 찾아 코드를 추출합니다.
    안 읽은 새로운 이메일만 확인합니다.

    Args:
        email: Medium 로그인에 사용한 이메일 주소
        max_retries: 최대 재시도 횟수
        retry_interval: 재시도 간격 (초)

    Returns:
        인증 코드 문자열, 없으면 None
    """
    if not email:
      email = os.getenv('MEDIUM_EMAIL')

    if not email:
      raise ValueError("이메일 주소가 제공되지 않았습니다.")

    # Medium 인증 코드 이메일 검색 쿼리 (안 읽은 메일만 검색, 'Your login code is' 포함)
    query = f'from:{sender_email} to:{email} is:unread "Your login code is"'

    logger.info(f"Gmail에서 인증 코드 이메일 검색 중... (최대 {max_retries}회)")

    for attempt in range(1, max_retries + 1):
      try:
        logger.debug(f"시도 {attempt}/{max_retries}...")

        # 안 읽은 이메일 검색
        results = self.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()

        messages = results.get('messages', [])

        if not messages:
          if attempt < max_retries:
            logger.debug(f"안 읽은 이메일을 찾을 수 없습니다. {retry_interval}초 후 재시도...")
            time.sleep(retry_interval)
            continue
          else:
            logger.warning("안 읽은 이메일을 찾을 수 없습니다.")
            return None

        # 가장 최근 이메일부터 확인
        for message in messages:
          try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message['id']
            ).execute()

            # 이메일 본문 추출
            code = self._extract_code_from_message(msg)
            if code:
              # 인증 코드를 찾았으면 이메일을 읽음 처리
              try:
                self.service.users().messages().modify(
                    userId='me',
                    id=message['id'],
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                logger.info(f"인증 코드 찾음: {code}")
              except Exception as e:
                logger.warning(f"인증 코드 찾음: {code} (읽음 처리 실패: {e})")

              return code
          except Exception as e:
            logger.debug(f"이메일 처리 중 오류 (메시지 ID: {message.get('id', 'unknown')}): {e}")
            continue  # 다음 이메일로 계속 진행

        # 코드를 찾지 못한 경우 재시도
        if attempt < max_retries:
          logger.debug(f"인증 코드를 찾을 수 없습니다. {retry_interval}초 후 재시도...")
          time.sleep(retry_interval)

      except HttpError as error:
        logger.error(f'Gmail API 오류 발생: {error}')
        if attempt < max_retries:
          time.sleep(retry_interval)
        else:
          return None

    return None

  def _extract_code_from_message(self, message):
    """이메일 메시지에서 인증 코드 추출"""
    try:
      payload = message['payload']
      body = ""

      # 이메일 본문 추출
      if 'parts' in payload:
        for part in payload['parts']:
          if part['mimeType'] == 'text/plain' or part['mimeType'] == 'text/html':
            data = part['body']['data']
            body += base64.urlsafe_b64decode(data).decode('utf-8')
      else:
        if payload['body'].get('data'):
          data = payload['body']['data']
          body = base64.urlsafe_b64decode(data).decode('utf-8')

      # 'Your login code is '로 시작하는 이메일인지 확인
      if 'Your login code is' not in body and 'Your code is' not in body:
        return None

      # 'Your code is xxxxxx' 형식으로 코드 찾기
      # 패턴: "Your code is " 뒤에 오는 숫자 코드
      pattern = r'Your code is\s+(\d{4,8})'
      matches = re.findall(pattern, body, re.IGNORECASE)

      if matches:
        # 첫 번째 매치 반환
        code = matches[0]
        if len(code) >= 4:  # 최소 4자리 이상
          return code

      # 대체 패턴: "Your login code is " 형식
      pattern2 = r'Your login code is\s+(\d{4,8})'
      matches2 = re.findall(pattern2, body, re.IGNORECASE)

      if matches2:
        code = matches2[0]
        if len(code) >= 4:
          return code

      return None

    except Exception as e:
      logger.debug(f'이메일 파싱 오류: {e}')
      return None

  def _extract_body_from_message(self, message):
    """이메일 메시지에서 텍스트 본문 추출"""
    try:
      payload = message['payload']
      body = ""

      # 이메일 본문 추출
      if 'parts' in payload:
        for part in payload['parts']:
          if part['mimeType'] == 'text/plain':
            if part['body'].get('data'):
              data = part['body']['data']
              body += base64.urlsafe_b64decode(data).decode('utf-8')
      else:
        if payload.get('mimeType') == 'text/plain' and payload['body'].get('data'):
          data = payload['body']['data']
          body = base64.urlsafe_b64decode(data).decode('utf-8')

      return body
    except Exception as e:
      logger.debug(f'이메일 본문 추출 오류: {e}')
      return ""

  def _extract_html_from_message(self, message):
    """이메일 메시지에서 HTML 본문 추출"""
    try:
      payload = message['payload']
      html = ""

      # 이메일 본문 추출
      if 'parts' in payload:
        for part in payload['parts']:
          if part['mimeType'] == 'text/html':
            if part['body'].get('data'):
              data = part['body']['data']
              html += base64.urlsafe_b64decode(data).decode('utf-8')
      else:
        if payload.get('mimeType') == 'text/html' and payload['body'].get('data'):
          data = payload['body']['data']
          html = base64.urlsafe_b64decode(data).decode('utf-8')

      return html
    except Exception as e:
      logger.debug(f'이메일 HTML 추출 오류: {e}')
      return ""

  def _extract_links_from_message(self, body_text, body_html):
    """이메일 본문에서 'Download my archive' 링크 추출"""
    links = set()

    # HTML에서 XPath를 사용해 링크 추출
    if body_html:
      try:
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(body_html), parser)
        # XPath: email-button 클래스를 가진 <a> 태그 또는 'Download my archive' 텍스트를 가진 <a> 태그의 href 속성
        hrefs = tree.xpath(
            "//a[contains(@class, 'email-button') or contains(text(), 'Download my archive')]/@href")
        for href in hrefs:
          if href.startswith('http://') or href.startswith('https://'):
            links.add(href)
      except Exception as e:
        logger.debug(f"HTML 파싱 중 오류: {e}")

    if body_text:
      pattern = r'(?i)download\s+my\s+archive[^\n]*?(https?://[^\s<>"{}|\\^`\[\]]+)'
      matches = re.findall(pattern, body_text)
      for url in matches:
        url = url.rstrip('.,;:!?)')
        if url.startswith('http://') or url.startswith('https://'):
          links.add(url)

    return list(links)

  def _download_from_url(self, url, download_path, browser_page=None):
    """URL에서 파일 다운로드"""
    try:
      logger.info(f"다운로드 요청: {url}")

      # 브라우저 페이지가 있으면 브라우저로 다운로드 (로그인된 세션 사용)
      if browser_page:
        logger.debug("브라우저를 통해 다운로드 중...")
        try:
          # 다운로드 이벤트를 먼저 대기 시작 (리다이렉트 전에 시작)
          with browser_page.expect_download(timeout=60000) as download_info:
            try:
              # 리다이렉트를 따라가면서 최종 다운로드 URL까지 이동
              browser_page.goto(url, wait_until='load', timeout=60000)
            except Exception as goto_error:
              # "Download is starting" 에러는 정상적인 경우 (다운로드가 시작됨)
              error_msg = str(goto_error)
              if "Download is starting" in error_msg:
                logger.debug("다운로드가 시작되었습니다")
              else:
                raise
          download = download_info.value
          file_name = download.suggested_filename
          if file_name:
            file_path = os.path.join(download_path, file_name)
          download.save_as(file_path)
          logger.info(f"파일 다운로드 완료: {file_path}")
          return file_path
        except Exception as e:
          logger.error(f"브라우저 다운로드 실패: {e}")
          return None

      # requests 사용 (fallback, 인증이 필요 없는 경우에만)
      logger.warning("브라우저 페이지가 없어 requests로 시도합니다 (인증이 필요할 수 있습니다)")
      headers = {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
          'Referer': 'https://medium.com/',
          'Accept': '*/*'
      }

      response = requests.get(url, stream=True, headers=headers, allow_redirects=True, timeout=60)
      response.raise_for_status()

      # 파일 저장
      with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
          if chunk:
            f.write(chunk)

      logger.info(f"파일 다운로드 완료: {file_path}")
      return file_path

    except requests.exceptions.RequestException as e:
      logger.error(f"파일 다운로드 실패: {e}")
      if hasattr(e, 'response') and e.response is not None:
        logger.debug(f"에러 Response 상태 코드: {e.response.status_code}")
      return None
    except Exception as e:
      logger.error(f"파일 다운로드 실패: {e}")
      return None

  def get_medium_list(self, email=None, sender_email=None, download_path="", search_query="", max_retries=5, retry_interval=5, browser_page=None):
    if not email:
      email = os.getenv('MEDIUM_EMAIL')

    if not email:
      raise ValueError("이메일 주소가 제공되지 않았습니다.")

    if not os.path.exists(download_path):
      os.makedirs(download_path, exist_ok=True)

    # 기본 쿼리 구성
    query_parts = [f'from:{sender_email}', f'to:{email}', 'is:unread']

    # search_query가 있으면 추가
    if search_query:
      query_parts.append(search_query)

    query = ' '.join(query_parts)

    logger.info(f"Gmail에서 Medium 리스트 이메일 검색 중... (최대 {max_retries}회)")

    for attempt in range(1, max_retries + 1):
      try:
        logger.debug(f"시도 {attempt}/{max_retries}...")

        # 안 읽은 이메일 검색
        results = self.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()

        messages = results.get('messages', [])

        if not messages:
          if attempt < max_retries:
            logger.debug(f"안 읽은 이메일을 찾을 수 없습니다. {retry_interval}초 후 재시도...")
            time.sleep(retry_interval)
            continue
          else:
            logger.warning("안 읽은 이메일을 찾을 수 없습니다.")
            return None

        for message in messages:
          msg = self.service.users().messages().get(
              userId='me',
              id=message['id'],
              format='full'
          ).execute()

          # 이메일 본문에서 링크 추출
          body_text = self._extract_body_from_message(msg)
          body_html = self._extract_html_from_message(msg)
          links = self._extract_links_from_message(body_text, body_html)

          if links:
            # 첫 번째 링크 다운로드
            link = links[0]
            logger.info(f"다운로드 링크 발견: {link}")
            file_path = self._download_from_url(link, download_path, browser_page=browser_page)
            if file_path:
              # 이메일 읽음 처리
              self.service.users().messages().modify(
                  userId='me',
                  id=message['id'],
                  body={'removeLabelIds': ['UNREAD']}
              ).execute()
              logger.info(f"Medium 리스트 다운로드 완료: {file_path}")
              return [file_path]

        # 링크를 찾지 못한 경우 재시도
        if attempt < max_retries:
          logger.debug(f"링크를 찾을 수 없습니다. {retry_interval}초 후 재시도...")
          time.sleep(retry_interval)

      except HttpError as error:
        logger.error(f'Gmail API 오류 발생: {error}')
        if attempt < max_retries:
          time.sleep(retry_interval)
        else:
          return None

    return None
