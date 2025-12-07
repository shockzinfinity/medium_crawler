# Medium 리스트 다운로드 구현 리포트

## 문제 정의

Gmail 이메일에서 Medium 리스트 다운로드 링크를 추출하여 파일을 다운로드해야 함.

## 시도한 방법들과 결과

### 1. requests 라이브러리 사용 (실패)

**시도 내용:**

- `requests.get()`을 사용하여 직접 URL에서 파일 다운로드 시도
- User-Agent, Referer 등 브라우저 헤더 추가

**실패 원인:**

- 403 Forbidden 에러 발생
- Medium이 인증된 세션(쿠키)을 요구함
- `requests`는 브라우저 세션을 유지하지 못함

**에러 분석:**

- 응답 내용이 Medium 로그인 페이지로 리다이렉트됨
- `redirect` 파라미터에 원래 다운로드 URL이 포함되어 있음
- 인증된 브라우저 세션이 필요함을 확인

### 2. Playwright 엘리먼트 클릭 방식 (불필요하게 복잡)

**시도 내용:**

- Playwright로 URL 접근 후 다운로드 버튼/링크를 찾아 클릭

**문제점:**

- 링크 자체가 직접 다운로드 URL이므로 엘리먼트 클릭이 불필요
- 코드가 복잡해짐
- 실제로는 링크를 직접 접근하면 다운로드가 시작됨

### 3. Playwright 직접 URL 접근 (부분 성공)

**시도 내용:**

- `browser_page.goto(url)`로 직접 URL 접근
- `expect_download()`로 다운로드 이벤트 대기
- `wait_until='networkidle'` 사용

**발생한 문제:**

- `Page.goto: Download is starting` 에러 발생
- 다운로드가 시작되면 `goto()`가 네비게이션 완료를 기다리지 못함
- 실제로는 다운로드가 시작되었지만 에러로 처리됨

### 4. "Download is starting" 에러 정상 처리 (성공)

**해결 방법:**

- `wait_until='networkidle'` → `wait_until='load'`로 변경
- "Download is starting" 에러를 정상 케이스로 처리
- `expect_download()`가 이미 다운로드 객체를 받았으므로 에러를 무시하고 저장 진행

**최종 구현:**

```python
with browser_page.expect_download(timeout=60000) as download_info:
    try:
        browser_page.goto(url, wait_until='load', timeout=60000)
    except Exception as goto_error:
        if "Download is starting" in str(goto_error):
            # 정상 케이스: 다운로드가 시작됨
            pass
        else:
            raise
download = download_info.value
download.save_as(file_path)
```

## 핵심 인사이트

1. **인증 필요성**: Medium 리스트 다운로드는 인증된 세션이 필수
2. **리다이렉트 처리**: 이메일 링크는 SendGrid 추적 링크를 거쳐 Medium 다운로드 URL로 리다이렉트됨
3. **다운로드 시작 시점**: 다운로드가 시작되면 `goto()`는 네비게이션 완료를 기다리지 못함
4. **에러 처리**: "Download is starting" 에러는 실제로는 성공 케이스

## 최종 해결책

- **인증된 Playwright 세션 사용**: Medium 로그인 후 브라우저 페이지를 `gmail_checker`에 전달
- **다운로드 이벤트 선등록**: `expect_download()`를 `goto()` 전에 설정
- **에러 정상화**: 다운로드 시작으로 인한 `goto()` 에러를 정상 케이스로 처리
- **적절한 wait 조건**: `networkidle` 대신 `load` 사용

## 성능 및 안정성

- 타임아웃: 60초 (대용량 파일 다운로드 고려)
- 리다이렉트 자동 처리: Playwright가 자동으로 리다이렉트를 따라감
- 에러 복구: 다운로드 실패 시 명확한 에러 메시지 제공
