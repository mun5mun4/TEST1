# Chrome Realtime Translator

> 🎯 Chrome 브라우저의 오디오를 실시간으로 캡처하여 음성인식(STT)과 번역을 수행하고, 투명 오버레이로 자막을 표시하는 시스템

## 📋 목차
- [개요](#개요)
- [아키텍처 분석](#아키텍처-분석)
- [주요 기능](#주요-기능)
- [시스템 구조](#시스템-구조)
- [로드맵](#로드맵)
- [설치 및 실행](#설치-및-실행)

---

## 🎯 개요

Chrome Realtime Translator는 다음과 같은 워크플로우를 자동화합니다:

```
Chrome Audio → Audio Capture → STT (Speech-to-Text) → Translation → Overlay UI
```

실시간으로 Chrome에서 재생되는 오디오(동영상, 음악, 회의 등)를 캡처하여 텍스트로 변환하고, 즉시 번역하여 화면에 자막으로 표시합니다.

---

## 🏗️ 아키텍처 분석

### 코드 구조

#### 1. **ChromeRealtimeTranslatorConfig**
- **역할**: 시스템 전체 설정 관리
- **주요 기능**:
  - `config.json` 파일 로드
  - 각 컴포넌트 활성화/비활성화 제어
  - 성능 및 디버깅 옵션 설정
  - 워커 스레드 개수 설정

**강점**:
- ✅ 외부 설정 파일 지원으로 유연성 확보
- ✅ 기본값 제공으로 안정성 보장

**개선 필요**:
- ⚠️ 설정값 검증 로직 부족
- ⚠️ 환경변수 지원 필요

#### 2. **ChromeRealtimeTranslator**
- **역할**: 메인 시스템 통합 및 오케스트레이션
- **핵심 컴포넌트**:
  ```python
  - audio_capture: ChromeAudioCapture    # 오디오 캡처
  - stt: RealtimeSTT                     # 음성인식
  - translator: RealtimeTranslator       # 번역
  - overlay: TransparentOverlay          # UI 오버레이
  ```

**아키텍처 패턴**:
- 🎯 **이벤트 드리븐 아키텍처**: 콜백 기반 비동기 처리
- 🔄 **파이프라인 패턴**: 데이터가 컴포넌트를 순차적으로 통과
- 📊 **모니터링 패턴**: 통계 수집 및 주기적 리포팅

**강점**:
- ✅ 명확한 관심사 분리 (Separation of Concerns)
- ✅ 각 컴포넌트 독립적으로 활성화/비활성화 가능
- ✅ 통계 및 성능 모니터링 내장
- ✅ 시그널 핸들러로 안전한 종료 보장

**개선 필요**:
- ⚠️ 컴포넌트 간 의존성 명시적 관리 필요
- ⚠️ 에러 복구 메커니즘 강화 필요
- ⚠️ 메모리 관리 및 리소스 정리 개선

---

## 🚀 주요 기능

### 1. **오디오 캡처**
- Chrome 브라우저의 오디오 스트림 실시간 캡처
- VAD (Voice Activity Detection) 지원
- 연속 오디오 처리 (`on_continuous_audio`)

### 2. **음성인식 (STT)**
- Whisper 모델 기반 (medium 모델 사용)
- 실시간 스트리밍 처리
- 비동기 처리로 지연 최소화

### 3. **번역**
- Hunyuan-MT-7B 모델 기반
- 캐시 지원으로 중복 번역 방지
- 멀티 워커로 처리 속도 향상

### 4. **오버레이 UI**
- 투명 오버레이로 자막 표시
- 원문/번역문 동시 표시
- 단축키 지원 (F1, ESC)

### 5. **모니터링**
- 실시간 성능 통계
- 처리량 추적
- 에러율 모니터링

---

## 🔧 시스템 구조

### 의존성 모듈 (구현 필요)

| 모듈 | 역할 | 상태 |
|------|------|------|
| `audio_capture.py` | Chrome 오디오 캡처 | 🔴 미구현 |
| `realtime_stt.py` | 실시간 음성인식 | 🔴 미구현 |
| `realtime_translator.py` | 실시간 번역 | 🔴 미구현 |
| `overlay_ui.py` | 투명 오버레이 UI | 🔴 미구현 |

### 데이터 플로우

```
┌─────────────────┐
│  Chrome Audio   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Audio Capture   │ ◄── VAD, Segmentation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Realtime STT  │ ◄── Whisper Model
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Translator    │ ◄── Hunyuan-MT-7B
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Overlay UI    │ ◄── Transparent Subtitle
└─────────────────┘
```

---

## 🗺️ 로드맵

### 🔥 Phase 1: 핵심 모듈 구현 (현재)

**우선순위: 높음**

- [ ] `audio_capture.py` 구현
  - [ ] PulseAudio/WASAPI 연동
  - [ ] Chrome 프로세스 오디오 격리
  - [ ] VAD (Voice Activity Detection) 구현
  - [ ] 오디오 버퍼 관리

- [ ] `realtime_stt.py` 구현
  - [ ] Whisper 모델 로드 및 최적화
  - [ ] 스트리밍 처리 파이프라인
  - [ ] 비동기 큐 시스템
  - [ ] 에러 핸들링

- [ ] `realtime_translator.py` 구현
  - [ ] Hunyuan-MT-7B 모델 통합
  - [ ] 번역 캐시 시스템
  - [ ] 워커 풀 관리
  - [ ] 배치 처리 최적화

- [ ] `overlay_ui.py` 구현
  - [ ] Tkinter/PyQt 기반 투명 윈도우
  - [ ] 자막 렌더링 엔진
  - [ ] 위치 및 스타일 설정
  - [ ] 단축키 바인딩

### 📦 Phase 2: 테스트 및 문서화

**우선순위: 중간**

- [ ] 단위 테스트 작성
  - [ ] 각 컴포넌트별 테스트
  - [ ] 통합 테스트
  - [ ] 성능 테스트

- [ ] 문서화
  - [ ] API 문서
  - [ ] 사용자 가이드
  - [ ] 개발자 가이드
  - [ ] 아키텍처 다이어그램

- [ ] 설정 관리 개선
  - [ ] 설정값 검증
  - [ ] 환경변수 지원
  - [ ] 설정 UI 도구

### 🚀 Phase 3: 기능 확장

**우선순위: 낮음**

- [ ] 다중 STT 엔진 지원
  - [ ] Google Speech API
  - [ ] Azure Speech Service
  - [ ] 로컬 모델 선택 옵션

- [ ] 다중 번역 엔진 지원
  - [ ] Google Translate API
  - [ ] DeepL API
  - [ ] 다양한 로컬 모델

- [ ] 고급 기능
  - [ ] 자막 히스토리 관리
  - [ ] 자막 내보내기 (SRT, VTT)
  - [ ] 다중 언어 동시 지원
  - [ ] 화자 구분 (Speaker Diarization)

### 🌟 Phase 4: 최적화 및 배포

**우선순위: 낮음**

- [ ] 성능 최적화
  - [ ] GPU 가속 활용
  - [ ] 메모리 사용량 최적화
  - [ ] 지연시간 최소화
  - [ ] 모델 양자화

- [ ] 배포 및 패키징
  - [ ] PyInstaller/cx_Freeze로 실행파일 생성
  - [ ] Docker 컨테이너화
  - [ ] 자동 업데이트 시스템
  - [ ] 설치 마법사

- [ ] 모니터링 및 로깅
  - [ ] Prometheus 메트릭 연동
  - [ ] 구조화된 로깅
  - [ ] 에러 추적 시스템

---

## 📦 설치 및 실행

### 요구사항

```bash
Python 3.8+
CUDA (GPU 가속 사용 시)
PulseAudio (Linux) 또는 WASAPI (Windows)
```

### 설치

```bash
# 저장소 클론
git clone <repository-url>
cd chrome-realtime-translator

# 의존성 설치
pip install -r requirements.txt

# 설정 파일 생성
cp config.example.json config.json
# config.json 편집하여 설정 조정
```

### 실행

```bash
python main.py
```

### 단축키

- **F1**: 오버레이 설정 표시
- **ESC**: 오버레이 닫기
- **Ctrl+C**: 시스템 종료

---

## 🎯 개선 방향 요약

### 즉시 필요한 작업 (1-2주)
1. ✅ 핵심 모듈 4개 구현
2. ✅ 기본 통합 테스트
3. ✅ 최소 문서화

### 단기 개선 (1개월)
1. 🔧 에러 핸들링 강화
2. 🔧 성능 최적화
3. 🔧 설정 관리 개선
4. 🔧 단위 테스트 추가

### 중기 개선 (3개월)
1. 📈 다중 엔진 지원
2. 📈 고급 기능 추가
3. 📈 GUI 설정 도구
4. 📈 성능 모니터링 대시보드

### 장기 개선 (6개월+)
1. 🚀 클라우드 배포 지원
2. 🚀 플러그인 아키텍처
3. 🚀 모바일 앱 연동
4. 🚀 상용 서비스화

---

## 📊 현재 상태

```
전체 진행도: ███░░░░░░░ 30%

✅ 완료: 아키텍처 설계, 메인 시스템 구조
🔄 진행중: 핵심 모듈 구현
📋 예정: 테스트, 문서화, 배포
```

---

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 라이선스

TBD

---

## 📞 문의

프로젝트 관련 문의사항은 이슈 트래커를 이용해주세요.

---

**Made with ❤️ for real-time translation**
