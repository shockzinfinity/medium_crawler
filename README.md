# Medium Crawler with Gmail Auth

Medium 크롤러는 Python과 Playwright를 사용하여 Medium 기사를 크롤링하는 도구입니다. Gmail API를 통해 인증 코드를 자동으로 받아 로그인합니다.

## 설치

1. 의존성 패키지 설치:

```bash
pip install -r requirements.txt
```

**Windows에서 `greenlet` 빌드 오류가 발생하는 경우:**

Python 3.13을 사용 중이라면 `greenlet`의 pre-built wheel이 없을 수 있습니다. 다음 중 하나를 선택하세요:

- **방법 1 (권장)**: Microsoft C++ Build Tools 설치

  - [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 다운로드 및 설치
  - "C++ build tools" 워크로드 선택
  - 설치 후 다시 `pip install -r requirements.txt` 실행

- **방법 2**: Python 3.13 사용

  - Python 3.13는 대부분의 패키지에 대해 pre-built wheel을 제공합니다
  - Python 3.13로 가상환경 생성 후 설치

- **방법 3**: Pre-built wheel 강제 사용 (Python 3.12 이하)
  ```bash
  pip install --upgrade pip setuptools wheel
  pip install --prefer-binary -r requirements.txt
  ```

2. Playwright 브라우저 설치:

```bash
playwright install
```

3. Gmail API 설정:

   **자세한 설정 방법은 [GMAIL_API_SETUP.md](GMAIL_API_SETUP.md)를 참조하세요.**

   간단 요약:

   - [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
   - Gmail API 활성화
   - OAuth 2.0 클라이언트 ID 생성 (Desktop app)
   - `credentials.json` 파일을 프로젝트 루트에 저장

4. 환경 변수 설정:
   - `.env.example`을 복사하여 `.env` 파일 생성
   - 필요한 값들을 입력

## 사용법

1. `urls.txt` 파일에 크롤링할 Medium URL 목록을 작성 (한 줄에 하나씩)

2. 스크립트 실행:

```bash
python main.py
```

## 출력

크롤링한 데이터는 `OUTPUT_DIR`에 지정된 디렉토리에 JSON 형식으로 저장됩니다.

## 크롤링 데이터

각 기사에서 다음 정보를 추출합니다:

- 제목
- 본문 내용
- 작성자
- 발행일
- 태그
- 클랩 수
- 읽기 시간
- 기타 메타데이터
