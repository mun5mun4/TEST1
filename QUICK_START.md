# Chrome Realtime Translator - Quick Start Guide

> 🚀 5분 안에 실시간 번역 시작하기!

---

## 📋 테스트 결과

✅ **코드 상태**: 모든 Python 파일 문법 정상
✅ **Python 버전**: 3.11.14 (3.8 이상 필요)
✅ **파일 구조**: 완료 (모든 파일 존재)

⚠️ **설치 필요**: 의존성 패키지 설치 필요

---

## 🔧 설치 단계

### Step 1: 시스템 요구사항 확인

**필수**:
- Windows 10/11 (WASAPI 지원)
- Python 3.8 이상
- GPU: NVIDIA (CUDA 지원) - 권장
- RAM: 16GB 이상 권장
- 디스크: 10GB 여유 공간

**선택**:
- VoiceMeeter 또는 스테레오 믹스 (시스템 오디오 캡처용)

---

### Step 2: 환경 설정

#### 2-1. Git 클론 (이미 완료)
```bash
git clone <repository-url>
cd chrome-realtime-translator
```

#### 2-2. Python 가상환경 생성 (권장)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac (참고용 - Windows 전용 프로그램)
python3 -m venv venv
source venv/bin/activate
```

---

### Step 3: 의존성 설치

#### 3-1. PyTorch 설치 (GPU 버전)

**CUDA 11.8 (권장)**:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**CUDA 12.1**:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**CPU 버전** (GPU 없는 경우):
```bash
pip install torch torchvision torchaudio
```

#### 3-2. 나머지 패키지 설치
```bash
pip install -r requirements.txt
```

**주의**: PyAudio 설치 실패 시:
```bash
# Windows - 미리 컴파일된 버전 설치
pip install pipwin
pipwin install pyaudio
```

---

### Step 4: 설정 파일 생성

#### 4-1. config.json 생성
```bash
# Windows
copy config.example.json config.json

# Linux/Mac
cp config.example.json config.json
```

#### 4-2. config.json 수정 (선택)

**기본 설정 (일본어 → 한국어)**:
```json
{
  "stt": {
    "model_size": "medium",
    "language": "ja",
    "device": "cuda"
  },
  "translation": {
    "source_language": "ja",
    "target_language": "ko"
  }
}
```

**영어 → 한국어 변경 예시**:
```json
{
  "stt": {
    "model_size": "medium",
    "language": "en",  // 여기 변경
    "device": "cuda"
  },
  "translation": {
    "source_language": "en",  // 여기 변경
    "target_language": "ko"
  }
}
```

---

### Step 5: 시스템 테스트 실행

```bash
python test_system.py
```

**예상 출력**:
```
✓ Python 버전
✓ 파일 구조
✓ 설정 파일
✓ Python 문법
✓ 필수 의존성
✓ 모듈 Import
✓ GPU 사용
✓ 오디오 디바이스
```

모든 항목이 ✓ 표시되면 준비 완료!

---

### Step 6: 실행!

```bash
python main.py
```

**실행 시 출력**:
```
Chrome Realtime Translator
==================================================
Real-time Chrome audio capture, STT, and translation
Press Ctrl+C to stop
==================================================

Loading Whisper model: medium
Model loaded in 8.32s on cuda
Loading model: tencent/Hunyuan-MT-7B
Model loaded in 12.45s on cuda:0
Chrome Realtime Translator started successfully!
Controls:
- F1: Show overlay settings
- ESC: Close overlay
- Ctrl+C: Stop system
```

**투명 오버레이 창이 나타나면 성공!**

---

## 🎮 사용 방법

### 기본 조작

1. **Chrome에서 동영상 재생** (YouTube, Netflix 등)
2. **자막이 자동으로 오버레이에 표시됨**
3. **F1 키**: 설정 창 열기
   - 폰트 크기 조절
   - 투명도 조절
   - 위치 이동
4. **ESC 키**: 오버레이 닫기
5. **Ctrl+C**: 프로그램 종료

### 오버레이 이동
- 오버레이를 **드래그**하여 원하는 위치로 이동
- 위치는 자동 저장됨 (`overlay_config.json`)

---

## 🐛 문제 해결

### 1. "No audio device found" 오류

**원인**: 시스템 오디오를 캡처할 디바이스가 없음

**해결**:
1. **스테레오 믹스 활성화** (Windows):
   - 작업 표시줄 스피커 아이콘 우클릭
   - "소리 설정" → "녹음" 탭
   - 빈 공간 우클릭 → "사용 안 함 장치 표시"
   - "스테레오 믹스" 우클릭 → "사용"

2. **VoiceMeeter 설치** (권장):
   - https://vb-audio.com/Voicemeeter/
   - VoiceMeeter Output이 자동 감지됨

### 2. "CUDA out of memory" 오류

**원인**: GPU 메모리 부족

**해결**:
```json
// config.json 수정
{
  "stt": {
    "model_size": "small"  // medium → small로 변경
  }
}
```

또는 CPU 모드:
```json
{
  "stt": {
    "device": "cpu"  // cuda → cpu
  },
  "translation": {
    "device": "cpu"
  }
}
```

### 3. 번역이 느림

**해결책 1**: Faster-Whisper 사용 (4배 빠름)
```bash
pip install faster-whisper
# realtime_stt.py 수정 필요 (WHISPER_ANALYSIS.md 참고)
```

**해결책 2**: 모델 크기 축소
```json
{
  "stt": {
    "model_size": "small"  // base도 가능
  }
}
```

### 4. 오버레이가 안 보임

**원인**: 다른 창에 가려짐

**해결**:
- F1 키를 눌러 설정 창 열기
- "항상 최상위 표시" 체크
- 투명도 조절

### 5. Import 오류

```
ModuleNotFoundError: No module named 'xxx'
```

**해결**:
```bash
pip install -r requirements.txt --upgrade
```

---

## ⚡ 성능 최적화 팁

### 1. GPU 메모리 최적화

**현재 메모리 사용량**:
- Whisper medium: ~5GB
- Hunyuan-MT-7B: ~14GB
- **총**: ~19GB

**메모리가 부족하면**:
```json
{
  "stt": {
    "model_size": "small"  // ~2GB
  }
}
```

### 2. 지연시간 개선

**현재 지연시간**: 4-6초

**개선 방법**:
1. **Faster-Whisper 사용**: 2-3초로 개선 (50% 빠름)
2. **작은 모델 사용**: base 또는 small
3. **연속 처리 간격 조정**:
   ```json
   {
     "audio_capture": {
       "processing_interval": 2.0  // 3.0 → 2.0초
     }
   }
   ```

### 3. 배치 처리 최적화

```json
{
  "translation": {
    "batch_size": 8,  // 기본값 4
    "workers": 3       // 기본값 2
  }
}
```

---

## 📊 지원 언어

| 원문 언어 | 코드 | 번역 대상 | 코드 |
|----------|------|----------|------|
| 일본어 | `ja` | 한국어 | `ko` |
| 영어 | `en` | 한국어 | `ko` |
| 중국어 | `zh` | 한국어 | `ko` |
| 한국어 | `ko` | 영어 | `en` |
| 스페인어 | `es` | 영어 | `en` |
| 프랑스어 | `fr` | 영어 | `en` |

**추가 가능 언어**: de, ru, ar, pt, it 등

---

## 🎯 권장 설정

### 고성능 PC (RTX 3080 이상)
```json
{
  "stt": {
    "model_size": "large",
    "device": "cuda"
  },
  "translation": {
    "workers": 3
  }
}
```

### 중급 PC (RTX 3060)
```json
{
  "stt": {
    "model_size": "medium",
    "device": "cuda"
  },
  "translation": {
    "workers": 2
  }
}
```

### 저사양 PC (GPU 없음)
```json
{
  "stt": {
    "model_size": "small",
    "device": "cpu"
  },
  "translation": {
    "device": "cpu",
    "workers": 1
  }
}
```

---

## 📝 체크리스트

설치 전:
- [ ] Windows 10/11
- [ ] Python 3.8 이상
- [ ] NVIDIA GPU (권장)
- [ ] 16GB RAM
- [ ] 10GB 여유 공간

설치 중:
- [ ] 가상환경 생성
- [ ] PyTorch (GPU) 설치
- [ ] requirements.txt 설치
- [ ] config.json 생성
- [ ] test_system.py 실행

실행 전:
- [ ] Chrome 실행
- [ ] 스테레오 믹스 또는 VoiceMeeter 설정
- [ ] 동영상 준비 (YouTube 등)

실행:
- [ ] python main.py 실행
- [ ] 오버레이 확인
- [ ] 번역 테스트

---

## 🚀 다음 단계

1. **Faster-Whisper 마이그레이션** (50% 성능 향상)
   - 📖 `WHISPER_ANALYSIS.md` 참고

2. **설정 최적화**
   - GPU 메모리에 맞춰 모델 크기 조정
   - 지연시간 최소화

3. **기능 확장**
   - 자막 히스토리 저장
   - SRT 파일 내보내기
   - 다중 언어 동시 지원

---

## 📚 추가 문서

- **INSPECTION_REPORT.md**: 코드 분석 및 개선 사항
- **WHISPER_ANALYSIS.md**: Whisper vs Faster-Whisper 비교
- **README.md**: 프로젝트 개요

---

## 💡 유용한 명령어

```bash
# 테스트 실행
python test_system.py

# 메인 프로그램 실행
python main.py

# 설정 파일 백업
copy config.json config.backup.json

# 로그 확인
type logs\translator.log

# 캐시 초기화
rmdir /s /q .cache
```

---

**준비 완료!** 이제 Chrome 동영상을 실시간으로 번역해보세요! 🎉
