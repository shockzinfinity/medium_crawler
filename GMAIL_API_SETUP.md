# Gmail API 설정 가이드

Medium 크롤러에서 Gmail API를 사용하여 인증 코드를 자동으로 받기 위한 설정 방법입니다.

## 1. Google Cloud Console 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 상단의 프로젝트 선택 드롭다운 클릭
3. "새 프로젝트" 클릭
4. 프로젝트 이름 입력 (예: "medium-crawler")
5. "만들기" 클릭
6. 프로젝트가 생성되면 해당 프로젝트를 선택

## 2. Gmail API 활성화

1. 왼쪽 메뉴에서 "API 및 서비스" > "라이브러리" 클릭
2. 검색창에 "Gmail API" 입력
3. "Gmail API" 선택
4. "사용 설정" 버튼 클릭

## 3. OAuth 동의 화면 구성

1. 왼쪽 메뉴에서 "API 및 서비스" > "OAuth 동의 화면" 클릭
2. 사용자 유형 선택:
   - **외부** 선택 (개인 Google 계정 사용 시)
   - 또는 **내부** (Google Workspace 사용 시)
3. "만들기" 클릭
4. 앱 정보 입력:
   - **앱 이름**: Medium Crawler (또는 원하는 이름)
   - **사용자 지원 이메일**: 본인 이메일 선택
   - **앱 로고**: 선택 사항
5. "저장 후 계속" 클릭
6. 범위(Scopes) 설정:
   - "범위 추가 또는 삭제" 클릭
   - `https://www.googleapis.com/auth/gmail.readonly` 검색 및 선택
   - "업데이트" 클릭
   - "저장 후 계속" 클릭
7. 테스트 사용자 추가 (외부 앱인 경우):
   - "사용자 추가" 클릭
   - 본인 Gmail 주소 입력
   - "저장 후 계속" 클릭
8. 요약 화면에서 "대시보드로 돌아가기" 클릭

## 4. OAuth 2.0 클라이언트 ID 생성

1. 왼쪽 메뉴에서 "API 및 서비스" > "사용자 인증 정보" 클릭
2. 상단의 "+ 사용자 인증 정보 만들기" 클릭
3. "OAuth 클라이언트 ID" 선택
4. 애플리케이션 유형 선택:
   - **데스크톱 앱** 선택
5. 이름 입력 (예: "Medium Crawler Desktop")
6. "만들기" 클릭
7. 클라이언트 ID와 클라이언트 보안 비밀번호가 표시됨
8. **중요**: "JSON 다운로드" 버튼 클릭하여 `credentials.json` 파일 다운로드

## 5. credentials.json 파일 배치

1. 다운로드한 `credentials.json` 파일을 프로젝트 루트 디렉토리에 복사

   ```
   medium_crawler/
   ├── credentials.json  ← 여기에 배치
   ├── main.py
   ├── auth.py
   └── ...
   ```

2. `.gitignore`에 `credentials.json`이 포함되어 있는지 확인 (보안상 중요!)

## 6. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가:

```env
# Gmail API 인증 정보 파일 경로 (기본값: credentials.json)
GMAIL_CREDENTIALS_PATH=credentials.json

# Gmail API 토큰 저장 경로 (자동 생성됨)
GMAIL_TOKEN_PATH=token.json

# Medium 로그인에 사용할 이메일 주소
MEDIUM_EMAIL=your-email@gmail.com

# 크롤링할 URL 리스트 파일 경로
URLS_FILE=urls.txt

# 크롤링 결과 저장 디렉토리
OUTPUT_DIR=output
```

## 7. 첫 실행 및 인증

1. 프로그램을 처음 실행하면 브라우저가 자동으로 열립니다
2. Google 계정으로 로그인
3. "Medium Crawler가 다음 권한을 요청합니다" 화면에서:
   - "계속" 클릭
   - "허용" 클릭
4. 인증이 완료되면 `token.json` 파일이 자동으로 생성됩니다
5. 이후 실행 시에는 `token.json`을 사용하여 자동으로 인증됩니다

## 문제 해결

### "credentials.json을 찾을 수 없습니다" 오류

- `credentials.json` 파일이 프로젝트 루트에 있는지 확인
- 파일 경로가 올바른지 확인 (`.env`의 `GMAIL_CREDENTIALS_PATH` 설정 확인)

### "토큰이 만료되었습니다" 오류

- `token.json` 파일 삭제 후 재실행
- 또는 Google Cloud Console에서 클라이언트 ID를 재생성

### "액세스가 거부되었습니다" 오류

- OAuth 동의 화면에서 테스트 사용자로 본인 이메일이 추가되었는지 확인
- 앱이 검토 중인 경우, 테스트 사용자만 사용 가능합니다

### "Gmail API가 활성화되지 않았습니다" 오류

- Google Cloud Console에서 Gmail API가 활성화되었는지 확인
- 올바른 프로젝트를 선택했는지 확인

## 보안 주의사항

⚠️ **중요**:

- `credentials.json`과 `token.json` 파일은 절대 Git에 커밋하지 마세요
- `.gitignore`에 포함되어 있는지 확인하세요
- 이 파일들이 유출되면 다른 사람이 본인의 Gmail에 접근할 수 있습니다
