import base64
import os
import re
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# Gmail API 스코프 (읽기 및 수정 권한 필요)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]


class GmailAuth:
    def __init__(self, credentials_path=None, token_path=None):
        self.credentials_path = credentials_path or os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')
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
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail API 인증 정보 파일을 찾을 수 없습니다: {self.credentials_path}\n"
                        "Google Cloud Console에서 credentials.json 파일을 다운로드하세요."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # 토큰 저장
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)

    def get_medium_verification_code(self, email=None, max_retries=5, retry_interval=5):
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
        
        # Medium 인증 코드 이메일 검색 쿼리 (안 읽은 메일만 검색)
        query = f'from:noreply@medium.com to:{email} is:unread'
        
        print(f"Gmail에서 안 읽은 인증 코드 이메일 검색 중... (최대 {max_retries}회, {retry_interval}초 간격)")
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"  시도 {attempt}/{max_retries}...")
                
                # 안 읽은 이메일 검색
                results = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=10
                ).execute()
                
                messages = results.get('messages', [])
                
                if not messages:
                    if attempt < max_retries:
                        print(f"  안 읽은 이메일을 찾을 수 없습니다. {retry_interval}초 후 재시도...")
                        time.sleep(retry_interval)
                        continue
                    else:
                        print("  안 읽은 이메일을 찾을 수 없습니다.")
                        return None
                
                # 가장 최근 이메일부터 확인
                for message in messages:
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
                            print(f"  인증 코드 찾음! (이메일 읽음 처리 완료)")
                        except Exception as e:
                            print(f"  인증 코드 찾음! (읽음 처리 실패: {e})")
                        return code
                
                # 코드를 찾지 못한 경우 재시도
                if attempt < max_retries:
                    print(f"  인증 코드를 찾을 수 없습니다. {retry_interval}초 후 재시도...")
                    time.sleep(retry_interval)
                
            except HttpError as error:
                print(f'Gmail API 오류 발생: {error}')
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
            print(f'이메일 파싱 오류: {e}')
            return None

