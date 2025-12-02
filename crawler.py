import os
import time

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from auth import GmailAuth

load_dotenv()


class MediumCrawler:
    def __init__(self, email=None, headless=False):
        self.email = email or os.getenv('MEDIUM_EMAIL')
        self.headless = headless
        self.browser = None
        self.page = None
        self.gmail_auth = GmailAuth()
        
        if not self.email:
            raise ValueError("이메일 주소가 제공되지 않았습니다. MEDIUM_EMAIL 환경 변수를 설정하세요.")

    def start_browser(self):
        """Playwright 브라우저 시작"""
        self.playwright = sync_playwright().start()
        # JavaScript 활성화 및 실제 브라우저처럼 보이도록 설정
        # Chromium은 기본적으로 JavaScript가 활성화되어 있지만, 명시적으로 설정
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--enable-javascript',
                '--js-flags=--expose-gc',
                '--disable-blink-features=AutomationControlled'  # 자동화 감지 방지
            ]
        )
        # 실제 브라우저처럼 보이도록 최신 Chrome User-Agent 사용
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation', 'notifications']
        )
        self.page = self.context.new_page()
        
        # JavaScript가 활성화되어 있는지 확인
        try:
            js_enabled = self.page.evaluate('() => typeof window !== "undefined" && typeof document !== "undefined" && typeof window.navigator !== "undefined"')
            if js_enabled:
                print("✓ JavaScript 활성화 확인됨")
            else:
                print("경고: JavaScript가 활성화되지 않은 것 같습니다.")
        except Exception as e:
            print(f"경고: JavaScript 확인 중 오류: {e}")

    def close_browser(self):
        """브라우저 종료"""
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

    def _robust_click(self, locator, description="", timeout=10000, click_type='auto'):
        """
        견고한 클릭 메서드 - 여러 방법을 시도하여 확실히 클릭합니다.
        
        Args:
            locator: Playwright locator 객체
            description: 디버깅용 설명
            timeout: 타임아웃 (ms)
            click_type: 클릭 타입 ('normal', 'js', 'coordinate', 'force', 'auto')
                       - 'normal': 일반 클릭만 시도
                       - 'js': JavaScript 클릭만 시도
                       - 'coordinate': 좌표 클릭만 시도
                       - 'force': force 클릭만 시도
                       - 'auto': 모든 방법을 순차적으로 시도 (기본값)
        
        Returns:
            클릭 성공 여부
        """
        try:
            # 요소가 보이고 연결될 때까지 대기
            locator.wait_for(state='visible', timeout=timeout)
            locator.wait_for(state='attached', timeout=5000)
            
            # 스크롤하여 보이도록 함
            locator.scroll_into_view_if_needed()
            time.sleep(0.3)
            
            # 특정 클릭 타입이 지정된 경우 해당 방법만 시도
            if click_type == 'js':
                locator.evaluate('element => { element.scrollIntoView(); element.click(); }')
                print(f"✓ {description} 클릭 성공 (JavaScript 클릭)")
                time.sleep(0.5)
                return True
            elif click_type == 'coordinate':
                box = locator.bounding_box()
                if box:
                    self.page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    print(f"✓ {description} 클릭 성공 (좌표 클릭)")
                    time.sleep(0.5)
                    return True
                else:
                    raise Exception("요소의 bounding box를 가져올 수 없습니다.")
            elif click_type == 'force':
                locator.click(force=True, timeout=3000)
                print(f"✓ {description} 클릭 성공 (force 클릭)")
                time.sleep(0.5)
                return True
            elif click_type == 'normal':
                locator.click(timeout=3000)
                print(f"✓ {description} 클릭 성공 (일반 클릭)")
                time.sleep(0.5)
                return True
            
            # 'auto' 모드: 모든 방법을 순차적으로 시도 (일반 클릭은 건너뛰고 시작)
            # 방법 1: JavaScript로 직접 클릭 (일반 클릭이 실패하므로 먼저 시도)
            try:
                locator.evaluate('element => { element.scrollIntoView(); element.click(); }')
                print(f"✓ {description} 클릭 성공 (JavaScript 클릭)")
                time.sleep(0.5)
                return True
            except Exception as e1:
                print(f"  JavaScript 클릭 실패: {e1}, 좌표 클릭 시도...")
                
                # 방법 2: 좌표로 클릭
                try:
                    box = locator.bounding_box()
                    if box:
                        self.page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                        print(f"✓ {description} 클릭 성공 (좌표 클릭)")
                        time.sleep(0.5)
                        return True
                    else:
                        raise Exception("요소의 bounding box를 가져올 수 없습니다.")
                except Exception as e2:
                    print(f"  좌표 클릭 실패: {e2}, force 클릭 시도...")
                    
                    # 방법 3: force 옵션으로 클릭
                    try:
                        locator.click(force=True, timeout=3000)
                        print(f"✓ {description} 클릭 성공 (force 클릭)")
                        time.sleep(0.5)
                        return True
                    except Exception as e3:
                        print(f"  force 클릭 실패: {e3}, 일반 클릭 시도...")
                        
                        # 방법 4: 일반 클릭 (마지막 시도)
                        try:
                            locator.click(timeout=3000)
                            print(f"✓ {description} 클릭 성공 (일반 클릭)")
                            time.sleep(0.5)
                            return True
                        except Exception as e4:
                            print(f"  모든 클릭 방법 실패: {e4}")
                            return False
        except Exception as e:
            print(f"  {description} 클릭 중 오류: {e}")
            return False

    def _wait_and_click(self, selectors, timeout=10000, description=""):
        """
        여러 선택자를 시도하여 요소를 찾고 클릭합니다.
        
        Args:
            selectors: 시도할 선택자 리스트
            timeout: 타임아웃 (ms)
            description: 디버깅용 설명
        
        Returns:
            클릭 성공 여부
        """
        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                if self._robust_click(locator, f"{description} ({selector})", timeout):
                    return True
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                print(f"  선택자 {selector} 시도 중 오류: {e}")
                continue
        return False

    def login(self, max_retries=3):
        """
        Medium에 로그인합니다.
        
        Args:
            max_retries: 최대 재시도 횟수
        
        Returns:
            로그인 성공 여부
        """
        if not self.page:
            self.start_browser()
        
        try:
            # Medium 로그인 페이지로 이동
            print("Medium 로그인 페이지로 이동 중...")
            self.page.goto('https://medium.com', wait_until='load', timeout=30000)
            time.sleep(1)
            
            # 'Sign in' 링크 클릭 (a 태그) - JavaScript 클릭 사용
            print("'Sign in' 링크 찾는 중...")
            sign_in_link = self.page.locator('a:has-text("Sign in")').first
            try:
                if not self._robust_click(sign_in_link, "'Sign in' 링크", click_type='js'):
                    self.page.screenshot(path='debug_sign_in_link_not_found.png')
                    raise Exception("'Sign in' 링크를 클릭할 수 없습니다. 스크린샷: debug_sign_in_link_not_found.png")
                time.sleep(1)
            except PlaywrightTimeoutError:
                self.page.screenshot(path='debug_sign_in_link_not_found.png')
                raise Exception("'Sign in' 링크를 찾을 수 없습니다. 스크린샷: debug_sign_in_link_not_found.png")
            
            # 'Sign in with email' 버튼 찾기 (button 요소 중 하위에 'Sign in with email' 텍스트가 있는 것) - JavaScript 클릭 사용
            print("'Sign in with email' 버튼 찾는 중...")
            email_button = self.page.locator('button:has-text("Sign in with email")').first
            try:
                if not self._robust_click(email_button, "'Sign in with email' 버튼", click_type='js'):
                    self.page.screenshot(path='debug_email_button_not_found.png')
                    raise Exception("'Sign in with email' 버튼을 클릭할 수 없습니다. 스크린샷: debug_email_button_not_found.png")
                time.sleep(1)
            except PlaywrightTimeoutError:
                self.page.screenshot(path='debug_email_button_not_found.png')
                raise Exception("'Sign in with email' 버튼을 찾을 수 없습니다. 스크린샷: debug_email_button_not_found.png")
            
            # 이메일 입력 필드 찾기 (placeholder가 'Enter your email address'인 input)
            print(f"이메일 입력 필드 찾는 중...")
            email_input = self.page.locator('input[placeholder="Enter your email address"]').first
            try:
                email_input.wait_for(state='visible', timeout=10000)
                email_input.scroll_into_view_if_needed()
                time.sleep(0.5)
            except PlaywrightTimeoutError:
                self.page.screenshot(path='debug_email_input_not_found.png')
                raise Exception("이메일 입력 필드를 찾을 수 없습니다. 스크린샷: debug_email_input_not_found.png")
            
            # 이메일 입력
            print(f"이메일 입력 중: {self.email}")
            email_input.click()
            email_input.fill('')  # 기존 내용 지우기
            email_input.fill(self.email)
            time.sleep(0.5)
            
            # Continue 버튼 찾기 및 클릭
            print("Continue 버튼 찾는 중...")
            continue_button = self.page.locator('button:has-text("Continue")').first
            try:
                # 버튼이 비활성화되어 있지 않은지 확인
                try:
                    is_disabled = continue_button.get_attribute('disabled')
                    if is_disabled:
                        print("버튼이 비활성화되어 있습니다. 활성화될 때까지 대기...")
                        # 버튼이 활성화될 때까지 최대 5초 대기
                        for _ in range(10):
                            time.sleep(0.5)
                            is_disabled = continue_button.get_attribute('disabled')
                            if not is_disabled:
                                break
                except:
                    pass  # disabled 속성이 없을 수도 있음
                
                if not self._robust_click(continue_button, "Continue 버튼", click_type='auto'):
                    self.page.screenshot(path='debug_continue_button_not_found.png')
                    raise Exception("Continue 버튼을 클릭할 수 없습니다. 스크린샷: debug_continue_button_not_found.png")
                
                time.sleep(2)
                
            except PlaywrightTimeoutError:
                self.page.screenshot(path='debug_continue_button_not_found.png')
                raise Exception("Continue 버튼을 찾을 수 없습니다. 스크린샷: debug_continue_button_not_found.png")
            
            # 인증 코드 입력 대기 및 코드 가져오기
            print("Gmail에서 인증 코드 가져오는 중...")
            code = self.gmail_auth.get_medium_verification_code(self.email, max_retries=5, retry_interval=5)
            
            if not code:
                raise Exception("인증 코드를 받을 수 없습니다. 이메일을 확인하세요.")
            
            print(f"인증 코드 받음: {code}")
            
            # 인증 코드 입력 필드 대기 (6개의 입력 필드)
            print("인증 코드 입력 필드 대기 중...")
            code_input_selector = 'input[inputmode="numeric"]'
            
            # 6개의 입력 필드가 모두 나타날 때까지 대기
            code_inputs = self.page.locator(code_input_selector)
            try:
                code_inputs.first.wait_for(state='visible', timeout=10000)
                time.sleep(0.5)
            except PlaywrightTimeoutError:
                self.page.screenshot(path='debug_code_input_not_found.png')
                raise Exception("인증 코드 입력 필드를 찾을 수 없습니다. 스크린샷: debug_code_input_not_found.png")
            
            # 입력 필드 개수 확인
            input_count = code_inputs.count()
            print(f"  입력 필드 {input_count}개 발견")
            
            if input_count < len(code):
                print(f"  경고: 입력 필드 수({input_count})가 코드 길이({len(code)})보다 적습니다.")
            
            # 각 입력 필드에 코드의 각 자리를 하나씩 입력
            print(f"인증 코드 입력 중: {code}")
            for i, digit in enumerate(code):
                if i >= input_count:
                    print(f"  경고: 입력 필드가 부족합니다. ({i+1}번째 자리 입력 불가)")
                    break
                
                try:
                    input_field = code_inputs.nth(i)
                    input_field.scroll_into_view_if_needed()
                    time.sleep(0.1)
                    input_field.click()
                    time.sleep(0.1)
                    input_field.fill(digit)
                    time.sleep(0.1)
                    print(f"  {i+1}번째 자리 입력: {digit}")
                except Exception as e:
                    print(f"  {i+1}번째 자리 입력 실패: {e}")
                    # 다음 필드로 자동 이동할 수 있으므로 계속 진행
                    continue
            
            time.sleep(0.5)
            
            # Submit 또는 Continue 버튼 클릭
            print("인증 코드 제출 중...")
            submit_selectors = [
                'button:has-text("Continue")',
                'button:has-text("Submit")',
                'button:has-text("Verify")',
                'button[type="submit"]',
                'button[aria-label*="Continue" i]',
                'button[aria-label*="Verify" i]'
            ]
            
            if not self._wait_and_click(submit_selectors, timeout=1000, description="Submit 버튼"):
                print("Submit 버튼을 찾을 수 없습니다. Enter 키로 제출했을 수 있습니다.")
            
            # 로그인 완료 대기
            print("로그인 완료 대기 중...")
            time.sleep(5)
            
            # 로그인 성공 확인 (URL 변경 또는 특정 요소 확인)
            current_url = self.page.url
            if 'signin' not in current_url.lower() or self.page.locator('text=Home').count() > 0:
                print("로그인 성공!")
                return True
            else:
                print("로그인 상태 확인 중...")
                # 추가 대기 후 재확인
                time.sleep(1)
                return 'signin' not in self.page.url.lower()
                
        except Exception as e:
            print(f"로그인 중 오류 발생: {e}")
            return False

    def crawl_article(self, url):
        """
        단일 Medium 기사를 크롤링합니다.
        
        Args:
            url: 크롤링할 Medium 기사 URL
        
        Returns:
            크롤링한 데이터 딕셔너리
        """
        if not self.page:
            raise Exception("브라우저가 시작되지 않았습니다. 먼저 login()을 호출하세요.")
        
        try:
            print(f"기사 크롤링 중: {url}")
            # load를 사용하여 기본 페이지 로드 완료 대기
            self.page.goto(url, wait_until='load', timeout=60000)
            time.sleep(3)  # 초기 렌더링 대기
            
            # article.meteredContent가 나타날 때까지 대기
            print("  article.meteredContent 로드 대기 중...")
            try:
                self.page.wait_for_selector('article.meteredContent', state='visible', timeout=15000)
                print("  ✓ article.meteredContent 로드 완료")
            except PlaywrightTimeoutError:
                print("  경고: article.meteredContent를 찾을 수 없습니다. 일반 article로 진행...")
            
            # 페이지가 완전히 로드될 때까지 대기
            self.page.wait_for_load_state('networkidle', timeout=10000)
            time.sleep(2)
            
            # 여러 번 스크롤하여 모든 동적 콘텐츠 로드
            for i in range(3):
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
            
            # 천천히 위로 스크롤하여 모든 콘텐츠가 렌더링되도록 함
            self.page.evaluate("""
                (() => {
                    const scrollHeight = document.body.scrollHeight;
                    const scrollStep = scrollHeight / 10;
                    let currentPos = scrollHeight;
                    const scrollInterval = setInterval(() => {
                        currentPos -= scrollStep;
                        window.scrollTo(0, currentPos);
                        if (currentPos <= 0) {
                            clearInterval(scrollInterval);
                            window.scrollTo(0, 0);
                        }
                    }, 100);
                })();
            """)
            time.sleep(2)
            
            # 다시 맨 위로
            self.page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            
            article_data = {
                'url': url,
                'title': self._extract_title(),
                'author': self._extract_author(),
                'published_date': self._extract_published_date(),
                'tags': self._extract_tags(),
                'claps': self._extract_claps(),
                'reading_time': self._extract_reading_time(),
                'content': self._extract_content(),
                'metadata': self._extract_metadata()
            }
            
            return article_data
            
        except Exception as e:
            print(f"기사 크롤링 중 오류 발생 ({url}): {e}")
            return {
                'url': url,
                'error': str(e)
            }

    def _extract_title(self):
        """제목 추출"""
        # article.meteredContent 내에서 제목 찾기
        try:
            article = self.page.query_selector('article.meteredContent')
            if article:
                h1 = article.query_selector('h1')
                if h1:
                    return h1.inner_text().strip()
        except:
            pass
        
        # 대체 방법
        selectors = [
            'article.meteredContent h1',
            'h1',
            '[data-testid="storyTitle"]',
            'h1.pw-post-title',
            'article h1'
        ]
        
        for selector in selectors:
            try:
                element = self.page.query_selector(selector)
                if element:
                    return element.inner_text().strip()
            except:
                continue
        
        return None

    def _extract_author(self):
        """작성자 추출"""
        # article.meteredContent 내에서 작성자 찾기
        try:
            article = self.page.query_selector('article.meteredContent')
            if article:
                author_link = article.query_selector('a[href*="/@"]')
                if author_link:
                    return author_link.inner_text().strip()
        except:
            pass
        
        # 대체 방법
        selectors = [
            'article.meteredContent [data-testid="authorName"]',
            'article.meteredContent a[data-action="show-user-card"]',
            '[data-testid="authorName"]',
            'a[data-action="show-user-card"]',
            '.author-name',
            'article a[href*="/@"]'
        ]
        
        for selector in selectors:
            try:
                element = self.page.query_selector(selector)
                if element:
                    return element.inner_text().strip()
            except:
                continue
        
        return None

    def _extract_published_date(self):
        """발행일 추출"""
        selectors = [
            'time',
            '[data-testid="storyPublishDate"]',
            'time[datetime]',
            '.published-date'
        ]
        
        for selector in selectors:
            try:
                element = self.page.query_selector(selector)
                if element:
                    date_text = element.inner_text().strip()
                    datetime_attr = element.get_attribute('datetime')
                    return datetime_attr or date_text
            except:
                continue
        
        return None

    def _extract_tags(self):
        """태그 추출 - article.meteredContent 내에서만"""
        tags = []
        
        # article.meteredContent 내에서 태그 찾기
        try:
            article = self.page.query_selector('article.meteredContent')
            if article:
                tag_links = article.query_selector_all('a[href*="/tag/"]')
                for link in tag_links:
                    tag_text = link.inner_text().strip()
                    if tag_text and tag_text not in tags:
                        tags.append(tag_text)
        except:
            pass
        
        if tags:
            return tags
        
        # 대체 방법
        selectors = [
            'article.meteredContent [data-testid="tag"]',
            'article.meteredContent .tag',
            'a[href*="/tag/"]',
            '[data-testid="tag"]',
            '.tag'
        ]
        
        for selector in selectors:
            try:
                elements = self.page.query_selector_all(selector)
                for element in elements:
                    tag_text = element.inner_text().strip()
                    if tag_text and tag_text not in tags:
                        tags.append(tag_text)
                if tags:
                    break
            except:
                continue
        
        return tags

    def _extract_claps(self):
        """클랩 수 추출"""
        import re

        # 여러 선택자 시도
        selectors = [
            'button[data-testid="clap-button"]',
            'button[aria-label*="clap" i]',
            '[data-testid="clapCount"]',
            'button:has-text("clap")',
            '.clap-count',
            'button[aria-label*="applause" i]'
        ]
        
        for selector in selectors:
            try:
                elements = self.page.query_selector_all(selector)
                for element in elements:
                    # 텍스트에서 숫자 추출
                    clap_text = element.inner_text().strip()
                    if clap_text:
                        numbers = re.findall(r'\d+', clap_text.replace(',', '').replace('K', '000').replace('M', '000000'))
                        if numbers:
                            return int(numbers[0])
                    
                    # aria-label에서 숫자 추출
                    aria_label = element.get_attribute('aria-label') or ''
                    if aria_label:
                        numbers = re.findall(r'\d+', aria_label.replace(',', '').replace('K', '000').replace('M', '000000'))
                        if numbers:
                            return int(numbers[0])
                    
                    # data 속성에서 추출 시도
                    data_value = element.get_attribute('data-value')
                    if data_value:
                        try:
                            return int(data_value)
                        except:
                            pass
            except:
                continue
        
        # JavaScript로 직접 값 추출 시도
        try:
            clap_value = self.page.evaluate("""
                () => {
                    const clapButton = document.querySelector('button[data-testid="clap-button"]');
                    if (clapButton) {
                        const text = clapButton.innerText || clapButton.textContent || '';
                        const match = text.match(/\\d+/);
                        if (match) return parseInt(match[0]);
                    }
                    return null;
                }
            """)
            if clap_value:
                return clap_value
        except:
            pass
        
        return None

    def _extract_reading_time(self):
        """읽기 시간 추출"""
        selectors = [
            '[data-testid="storyReadingTime"]',
            'span:has-text("min read")',
            '.reading-time'
        ]
        
        for selector in selectors:
            try:
                element = self.page.query_selector(selector)
                if element:
                    time_text = element.inner_text().strip()
                    import re
                    numbers = re.findall(r'\d+', time_text)
                    if numbers:
                        return int(numbers[0])
            except:
                continue
        
        return None

    def _extract_content(self):
        """본문 내용 추출 - article.meteredContent만 수집"""
        content_parts = []
        
        # 방법 1: article.meteredContent 내의 모든 p 태그 수집 (가장 정확)
        try:
            article = self.page.query_selector('article.meteredContent')
            if article:
                # article.meteredContent 내의 모든 p 태그
                paragraphs = article.query_selector_all('p')
                seen_texts = set()  # 중복 제거
                
                for p in paragraphs:
                    text = p.inner_text().strip()
                    # 너무 짧은 텍스트나 중복 제외
                    if text and len(text) > 10 and text not in seen_texts:
                        # 광고나 관련 기사 추천 등 제외
                        if not any(exclude in text.lower() for exclude in ['sign up', 'subscribe', 'follow', 'member-only']):
                            content_parts.append(text)
                            seen_texts.add(text)
        except Exception as e:
            print(f"  단락 수집 중 오류: {e}")
        
        if content_parts:
            return '\n\n'.join(content_parts)
        
        # 방법 2: article.meteredContent 내의 storyBody에서 추출
        try:
            article = self.page.query_selector('article.meteredContent')
            if article:
                story_body = article.query_selector('[data-testid="storyBody"]')
                if story_body:
                    paragraphs = story_body.query_selector_all('p')
                    for p in paragraphs:
                        text = p.inner_text().strip()
                        if text and len(text) > 10:
                            content_parts.append(text)
                    if content_parts:
                        return '\n\n'.join(content_parts)
        except:
            pass
        
        # 방법 3: article.meteredContent 내의 postArticle-content에서 추출
        try:
            article = self.page.query_selector('article.meteredContent')
            if article:
                post_content = article.query_selector('.postArticle-content')
                if post_content:
                    paragraphs = post_content.query_selector_all('p')
                    for p in paragraphs:
                        text = p.inner_text().strip()
                        if text and len(text) > 10:
                            content_parts.append(text)
                    if content_parts:
                        return '\n\n'.join(content_parts)
        except:
            pass
        
        # 방법 4: article.meteredContent 내의 section에서 추출
        try:
            article = self.page.query_selector('article.meteredContent')
            if article:
                article_section = article.query_selector('section')
                if article_section:
                    paragraphs = article_section.query_selector_all('p')
                    for p in paragraphs:
                        text = p.inner_text().strip()
                        if text and len(text) > 10:
                            content_parts.append(text)
                    if content_parts:
                        return '\n\n'.join(content_parts)
        except:
            pass
        
        return None

    def _extract_metadata(self):
        """추가 메타데이터 추출"""
        import re
        metadata = {}
        
        # 댓글/응답 수
        try:
            comment_selectors = [
                '[data-testid="commentCount"]',
                'button[aria-label*="response" i]',
                'button[aria-label*="comment" i]',
                'button:has-text("responses")',
                'button:has-text("comments")',
                'button:has-text("response")'
            ]
            for selector in comment_selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    for element in elements:
                        comment_text = element.inner_text().strip()
                        if comment_text:
                            numbers = re.findall(r'\d+', comment_text.replace(',', '').replace('K', '000').replace('M', '000000'))
                            if numbers:
                                metadata['comments'] = int(numbers[0])
                                break
                        
                        # aria-label에서도 시도
                        aria_label = element.get_attribute('aria-label') or ''
                        if aria_label:
                            numbers = re.findall(r'\d+', aria_label.replace(',', '').replace('K', '000').replace('M', '000000'))
                            if numbers:
                                metadata['comments'] = int(numbers[0])
                                break
                    
                    if 'comments' in metadata:
                        break
                except:
                    continue
        except:
            pass
        
        # 조회수 (views) - 있는 경우
        try:
            view_selectors = [
                '[data-testid="viewCount"]',
                'span:has-text("views")',
                'span:has-text("view")'
            ]
            for selector in view_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        view_text = element.inner_text().strip()
                        numbers = re.findall(r'\d+', view_text.replace(',', '').replace('K', '000').replace('M', '000000'))
                        if numbers:
                            metadata['views'] = int(numbers[0])
                            break
                except:
                    continue
        except:
            pass
        
        # 작성자 프로필 링크
        try:
            author_link = self.page.query_selector('article a[href*="/@"]')
            if author_link:
                author_url = author_link.get_attribute('href')
                if author_url:
                    metadata['author_url'] = author_url
        except:
            pass
        
        return metadata

