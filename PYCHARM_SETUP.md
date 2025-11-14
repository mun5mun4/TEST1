# PyCharm에서 Chrome Realtime Translator 프로젝트 시작하기

> 🎯 PyCharm에서 5분 안에 프로젝트 설정 완료!

---

## 📋 방법 1: Git Clone (권장)

### Step 1: PyCharm에서 프로젝트 클론

1. **PyCharm 실행**

2. **Get from VCS 선택**
   - 시작 화면에서 `Get from VCS` 클릭
   - 또는 `File` → `New` → `Project from Version Control`

3. **Git URL 입력**
   ```
   Repository URL: https://github.com/<your-username>/TEST1
   Directory: C:\Users\<your-name>\PycharmProjects\chrome-realtime-translator
   ```

4. **Clone 클릭**

---

## 📋 방법 2: 기존 프로젝트 열기

이미 로컬에 클론되어 있다면:

1. **PyCharm 실행**

2. **Open 선택**
   - 시작 화면에서 `Open` 클릭
   - 또는 `File` → `Open`

3. **프로젝트 폴더 선택**
   - `chrome-realtime-translator` 폴더 선택
   - `OK` 클릭

---

## 🔧 Step 2: Python 인터프리터 설정

### 2-1. 가상환경 생성 (권장)

**방법 A: PyCharm 자동 생성**

1. PyCharm이 자동으로 venv 생성 여부를 물으면 `OK` 클릭
2. 또는 수동으로:
   - `File` → `Settings` (Windows/Linux)
   - `PyCharm` → `Preferences` (Mac)
   - `Project: chrome-realtime-translator` → `Python Interpreter`
   - 톱니바퀴 아이콘 → `Add...`
   - `Virtualenv Environment` → `New environment`
   - Location: `프로젝트폴더\venv`
   - Base interpreter: Python 3.8 이상
   - `OK` 클릭

**방법 B: 터미널에서 수동 생성**

PyCharm 하단의 `Terminal` 탭에서:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# 또는
source venv/bin/activate  # Linux/Mac
```

---

## 📦 Step 3: 패키지 설치

### 3-1. PyTorch 설치

**PyCharm Terminal에서**:

**GPU 버전 (CUDA 11.8 권장)**:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**GPU 버전 (CUDA 12.1)**:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**CPU 버전**:
```bash
pip install torch torchvision torchaudio
```

### 3-2. 나머지 패키지 설치

**requirements.txt 사용**:
```bash
pip install -r requirements.txt
```

**또는 PyCharm UI 사용**:
1. `requirements.txt` 파일 열기
2. 상단에 "Install requirements" 알림 나타남
3. `Install requirements` 클릭

**PyAudio 설치 실패 시**:
```bash
pip install pipwin
pipwin install pyaudio
```

---

## ⚙️ Step 4: 설정 파일 생성

### PyCharm Terminal에서:

```bash
# Windows
copy config.example.json config.json

# Linux/Mac
cp config.example.json config.json
```

### 또는 PyCharm UI에서:

1. `config.example.json` 우클릭
2. `Copy` 선택
3. 프로젝트 루트에 `Paste`
4. 이름을 `config.json`으로 변경

---

## 🚀 Step 5: 실행 구성 설정

### 방법 A: 직접 실행

1. `main.py` 파일 열기
2. 편집기 상단 우클릭 → `Run 'main'` 클릭
3. 또는 `Ctrl+Shift+F10` (Windows/Linux) / `Cmd+Shift+R` (Mac)

### 방법 B: Run Configuration 생성

1. **상단 툴바의 Run Configuration 선택**
   - `Edit Configurations...` 클릭

2. **새 Python 구성 추가**
   - `+` 아이콘 클릭
   - `Python` 선택

3. **설정 입력**:
   ```
   Name: Chrome Realtime Translator
   Script path: <프로젝트경로>\main.py
   Working directory: <프로젝트경로>
   Python interpreter: 프로젝트 인터프리터 (venv)
   ```

4. **저장**
   - `OK` 클릭

5. **실행**
   - 상단의 ▶️ 버튼 클릭
   - 또는 `Shift+F10` (Windows/Linux) / `Ctrl+R` (Mac)

---

## 🧪 Step 6: 테스트 실행

### 시스템 테스트

**PyCharm Terminal에서**:
```bash
python test_system.py
```

**또는 PyCharm에서**:
1. `test_system.py` 우클릭
2. `Run 'test_system'` 선택

**모든 항목이 ✓ 표시되면 준비 완료!**

---

## 🎨 PyCharm 추천 설정

### 1. 코드 스타일 설정

**File** → **Settings** → **Editor** → **Code Style** → **Python**
- Tab size: 4
- Indent: 4
- Continuation indent: 4

### 2. 유용한 플러그인

**File** → **Settings** → **Plugins**:
- **Requirements** (이미 설치됨)
- **.ignore** (`.gitignore` 관리)
- **Rainbow Brackets** (가독성 향상)
- **Key Promoter X** (단축키 학습)

### 3. 터미널 설정

**File** → **Settings** → **Tools** → **Terminal**:
- Shell path: `cmd.exe` (Windows)
- Activate virtualenv: ✓ 체크

---

## 🐛 PyCharm 관련 문제 해결

### 1. "No Python interpreter configured"

**해결**:
1. `File` → `Settings` → `Project` → `Python Interpreter`
2. 톱니바퀴 → `Add...`
3. `Virtualenv Environment` → `Existing environment`
4. Interpreter: `<프로젝트폴더>\venv\Scripts\python.exe` 선택

### 2. "Module not found" 오류

**해결**:
1. PyCharm Terminal에서:
   ```bash
   pip install -r requirements.txt
   ```
2. PyCharm 재시작

### 3. Import가 빨간 줄로 표시

**해결**:
1. `File` → `Invalidate Caches...`
2. `Invalidate and Restart` 클릭

### 4. 가상환경이 활성화 안 됨

**해결**:
1. Terminal에서 수동 활성화:
   ```bash
   venv\Scripts\activate
   ```
2. 또는 PyCharm 재시작

### 5. PyAudio 설치 실패 (Windows)

**해결**:
```bash
pip install pipwin
pipwin install pyaudio
```

---

## 🎯 PyCharm에서 효율적으로 작업하기

### 유용한 단축키

| 기능 | Windows/Linux | Mac |
|------|---------------|-----|
| 실행 | `Shift+F10` | `Ctrl+R` |
| 디버그 | `Shift+F9` | `Ctrl+D` |
| 터미널 열기 | `Alt+F12` | `Opt+F12` |
| 파일 검색 | `Ctrl+Shift+N` | `Cmd+Shift+O` |
| 전체 검색 | `Shift+Shift` | `Shift+Shift` |
| 코드 정리 | `Ctrl+Alt+L` | `Cmd+Opt+L` |
| Git 커밋 | `Ctrl+K` | `Cmd+K` |

### Run Configuration 추가 예시

**테스트 실행 구성**:
```
Name: System Test
Script path: <프로젝트경로>\test_system.py
Working directory: <프로젝트경로>
```

**디버그 모드 실행**:
```
Name: Chrome Translator (Debug)
Script path: <프로젝트경로>\main.py
Environment variables: LOG_LEVEL=DEBUG
```

---

## 📊 프로젝트 구조 (PyCharm Project View)

```
chrome-realtime-translator/
├── .git/                          # Git 저장소
├── .idea/                         # PyCharm 설정 (자동 생성)
├── venv/                          # 가상환경 (자동 생성)
├── .cache/                        # 번역 캐시 (실행 시 생성)
├── logs/                          # 로그 파일 (실행 시 생성)
├── main.py                        # 🚀 메인 실행 파일
├── audio_capture.py               # 오디오 캡처 모듈
├── realtime_stt.py                # 음성인식 모듈
├── realtime_translator.py         # 번역 모듈
├── overlay_ui.py                  # UI 오버레이
├── test_system.py                 # 🧪 시스템 테스트
├── config.json                    # ⚙️ 설정 파일 (생성 필요)
├── config.example.json            # 설정 예시
├── requirements.txt               # 의존성 목록
├── README.md                      # 프로젝트 개요
├── QUICK_START.md                 # 빠른 시작
├── INSPECTION_REPORT.md           # 코드 분석
└── WHISPER_ANALYSIS.md            # Whisper 비교
```

---

## 🔄 Git 작업 (PyCharm에서)

### 변경사항 커밋

1. **변경사항 확인**
   - `Alt+9` (Windows/Linux) / `Cmd+9` (Mac)
   - 또는 `VCS` → `Commit`

2. **커밋 메시지 작성**
   - 왼쪽 패널에서 변경 파일 선택
   - 커밋 메시지 입력
   - `Commit` 또는 `Commit and Push`

### Pull 받기

1. `VCS` → `Git` → `Pull`
2. 또는 `Ctrl+T` (Windows/Linux) / `Cmd+T` (Mac)

### Push 하기

1. `VCS` → `Git` → `Push`
2. 또는 `Ctrl+Shift+K` (Windows/Linux) / `Cmd+Shift+K` (Mac)

---

## ✅ 설치 확인 체크리스트

PyCharm에서 다음을 확인하세요:

- [ ] 프로젝트 열림
- [ ] Python 인터프리터 설정됨 (venv)
- [ ] 터미널에서 `(venv)` 표시됨
- [ ] `pip list`에서 torch, whisper, transformers 확인
- [ ] `config.json` 파일 존재
- [ ] `test_system.py` 실행 시 모든 항목 ✓
- [ ] `main.py` 실행 가능

---

## 🎉 완료!

이제 PyCharm에서 작업할 준비가 완료되었습니다!

**다음 단계**:
1. `main.py`를 열고 코드 확인
2. Chrome에서 동영상 재생
3. `▶️` 버튼 클릭하여 실행
4. 자막이 오버레이에 나타나는지 확인

**개발 팁**:
- `Ctrl+Click`: 함수/클래스 정의로 이동
- `Alt+Enter`: 자동 import 및 수정 제안
- `Ctrl+Space`: 코드 자동완성
- `Ctrl+/`: 주석 토글

---

**Happy Coding! 🚀**
