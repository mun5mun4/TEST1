#!/usr/bin/env python3
"""
Chrome Realtime Translator - 시스템 테스트 스크립트
의존성, 설정, 모듈 로딩 등을 단계별로 검증합니다.
"""

import sys
import os
from pathlib import Path
import importlib.util

class Colors:
    """터미널 색상 코드"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """헤더 출력"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    """성공 메시지"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    """에러 메시지"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    """경고 메시지"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    """정보 메시지"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def check_python_version():
    """Python 버전 확인"""
    print_header("Python 버전 확인")

    version = sys.version_info
    print(f"Python 버전: {version.major}.{version.minor}.{version.micro}")

    if version.major >= 3 and version.minor >= 8:
        print_success("Python 3.8 이상 확인됨")
        return True
    else:
        print_error("Python 3.8 이상이 필요합니다")
        return False

def check_dependencies():
    """필수 의존성 확인"""
    print_header("필수 의존성 확인")

    required_packages = {
        'numpy': 'numpy',
        'torch': 'torch',
        'transformers': 'transformers',
        'whisper': 'openai-whisper',
        'pyaudio': 'pyaudio',
    }

    optional_packages = {
        'faster_whisper': 'faster-whisper',
    }

    all_ok = True

    print("필수 패키지:")
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
            print_success(f"{package_name} 설치됨")
        except ImportError:
            print_error(f"{package_name} 미설치 (필수)")
            all_ok = False

    print("\n선택 패키지:")
    for module_name, package_name in optional_packages.items():
        try:
            __import__(module_name)
            print_success(f"{package_name} 설치됨 (성능 향상)")
        except ImportError:
            print_warning(f"{package_name} 미설치 (선택사항)")

    return all_ok

def check_file_structure():
    """파일 구조 확인"""
    print_header("파일 구조 확인")

    required_files = [
        'main.py',
        'audio_capture.py',
        'realtime_stt.py',
        'realtime_translator.py',
        'overlay_ui.py',
        'config.example.json',
        'requirements.txt'
    ]

    all_ok = True

    for filename in required_files:
        filepath = Path(filename)
        if filepath.exists():
            size = filepath.stat().st_size / 1024  # KB
            print_success(f"{filename} ({size:.1f} KB)")
        else:
            print_error(f"{filename} 없음")
            all_ok = False

    # config.json 확인
    if Path("config.json").exists():
        print_success("config.json 존재")
    else:
        print_warning("config.json 없음 (config.example.json을 복사하세요)")

    return all_ok

def check_config_file():
    """설정 파일 확인"""
    print_header("설정 파일 확인")

    config_path = Path("config.json")

    if not config_path.exists():
        print_warning("config.json이 없습니다")
        print_info("config.example.json을 config.json으로 복사하세요:")
        print_info("  cp config.example.json config.json")
        return False

    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        print_success("config.json 파싱 성공")

        # 주요 섹션 확인
        sections = ['stt', 'translation', 'audio_capture', 'overlay']
        for section in sections:
            if section in config:
                print_success(f"  [{section}] 섹션 존재")
            else:
                print_warning(f"  [{section}] 섹션 없음")

        # 언어 설정 확인
        if 'stt' in config:
            stt_lang = config['stt'].get('language', 'N/A')
            print_info(f"  STT 언어: {stt_lang}")

        if 'translation' in config:
            src_lang = config['translation'].get('source_language', 'N/A')
            tgt_lang = config['translation'].get('target_language', 'N/A')
            print_info(f"  번역: {src_lang} → {tgt_lang}")

        return True

    except json.JSONDecodeError as e:
        print_error(f"config.json 파싱 실패: {e}")
        return False
    except Exception as e:
        print_error(f"config.json 읽기 실패: {e}")
        return False

def check_module_syntax():
    """모듈 문법 확인 (컴파일 테스트)"""
    print_header("Python 모듈 문법 확인")

    modules = [
        'main.py',
        'audio_capture.py',
        'realtime_stt.py',
        'realtime_translator.py',
        'overlay_ui.py'
    ]

    all_ok = True

    for module_path in modules:
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, module_path, 'exec')
            print_success(f"{module_path} 문법 OK")
        except SyntaxError as e:
            print_error(f"{module_path} 문법 오류: {e}")
            all_ok = False
        except FileNotFoundError:
            print_error(f"{module_path} 파일 없음")
            all_ok = False
        except Exception as e:
            print_error(f"{module_path} 오류: {e}")
            all_ok = False

    return all_ok

def test_module_imports():
    """모듈 import 테스트"""
    print_header("모듈 Import 테스트")

    all_ok = True

    # 1. audio_capture
    try:
        from audio_capture import AudioCaptureConfig, ChromeAudioCapture
        print_success("audio_capture 모듈 import 성공")

        # 설정 초기화 테스트
        config = AudioCaptureConfig()
        print_info(f"  - 샘플레이트: {config.sample_rate}Hz")
        print_info(f"  - 채널: {config.channels}")
    except Exception as e:
        print_error(f"audio_capture 모듈 import 실패: {e}")
        all_ok = False

    # 2. realtime_stt
    try:
        from realtime_stt import RealtimeSTTConfig, RealtimeSTT
        print_success("realtime_stt 모듈 import 성공")

        config = RealtimeSTTConfig()
        print_info(f"  - 모델: {config.model_size}")
        print_info(f"  - 언어: {config.language}")
        print_info(f"  - 디바이스: {config.device}")
    except Exception as e:
        print_error(f"realtime_stt 모듈 import 실패: {e}")
        all_ok = False

    # 3. realtime_translator
    try:
        from realtime_translator import RealtimeTranslatorConfig, RealtimeTranslator
        print_success("realtime_translator 모듈 import 성공")

        config = RealtimeTranslatorConfig()
        print_info(f"  - 모델: {config.model_name}")
        print_info(f"  - 언어 쌍: {config.source_language} → {config.target_language}")
    except Exception as e:
        print_error(f"realtime_translator 모듈 import 실패: {e}")
        all_ok = False

    # 4. overlay_ui
    try:
        from overlay_ui import OverlayConfig, TransparentOverlay
        print_success("overlay_ui 모듈 import 성공")

        config = OverlayConfig()
        print_info(f"  - 크기: {config.window_width}x{config.window_height}")
        print_info(f"  - 투명도: {config.alpha}")
    except Exception as e:
        print_error(f"overlay_ui 모듈 import 실패: {e}")
        all_ok = False

    # 5. main
    try:
        from main import ChromeRealtimeTranslatorConfig, ChromeRealtimeTranslator
        print_success("main 모듈 import 성공")

        config = ChromeRealtimeTranslatorConfig()
        print_info(f"  - 통계 표시: {config.show_performance_stats}")
    except Exception as e:
        print_error(f"main 모듈 import 실패: {e}")
        all_ok = False

    return all_ok

def check_gpu_availability():
    """GPU 사용 가능 여부 확인"""
    print_header("GPU 확인")

    try:
        import torch

        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            print_success(f"CUDA 사용 가능 ({device_count}개 GPU)")

            for i in range(device_count):
                device_name = torch.cuda.get_device_name(i)
                memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)  # GB
                print_info(f"  GPU {i}: {device_name} ({memory:.1f} GB)")

            return True
        else:
            print_warning("CUDA 사용 불가 (CPU 모드로 실행됨)")
            print_info("GPU 가속을 위해 CUDA를 설치하세요")
            return False

    except ImportError:
        print_error("PyTorch가 설치되지 않았습니다")
        return False

def check_audio_devices():
    """오디오 디바이스 확인"""
    print_header("오디오 디바이스 확인")

    try:
        import pyaudio

        pa = pyaudio.PyAudio()
        device_count = pa.get_device_count()

        print_info(f"총 {device_count}개의 오디오 디바이스 발견")

        # 입력 가능한 디바이스 찾기
        input_devices = []
        for i in range(device_count):
            try:
                info = pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    input_devices.append((i, info['name']))
            except:
                pass

        if input_devices:
            print_success(f"{len(input_devices)}개의 입력 디바이스 발견:")
            for idx, name in input_devices[:5]:  # 처음 5개만 표시
                print_info(f"  [{idx}] {name}")
        else:
            print_warning("입력 가능한 오디오 디바이스를 찾을 수 없습니다")

        pa.terminate()
        return len(input_devices) > 0

    except ImportError:
        print_error("PyAudio가 설치되지 않았습니다")
        return False
    except Exception as e:
        print_error(f"오디오 디바이스 확인 실패: {e}")
        return False

def print_summary(results):
    """테스트 결과 요약"""
    print_header("테스트 결과 요약")

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed

    print(f"총 테스트: {total}")
    print(f"{Colors.GREEN}성공: {passed}{Colors.END}")
    print(f"{Colors.RED}실패: {failed}{Colors.END}")
    print()

    for test_name, result in results.items():
        status = f"{Colors.GREEN}✓{Colors.END}" if result else f"{Colors.RED}✗{Colors.END}"
        print(f"{status} {test_name}")

    print()

    if failed == 0:
        print_success("모든 테스트 통과! 프로그램 실행 준비 완료")
        print()
        print_info("다음 단계:")
        print_info("  1. config.json 확인 및 수정")
        print_info("  2. python main.py 실행")
        return True
    else:
        print_error(f"{failed}개 테스트 실패")
        print()
        print_info("다음 조치:")
        print_info("  1. 실패한 항목을 확인하세요")
        print_info("  2. 필요한 패키지를 설치하세요:")
        print_info("     pip install -r requirements.txt")
        print_info("  3. config.json을 생성하세요:")
        print_info("     cp config.example.json config.json")
        return False

def main():
    """메인 테스트 실행"""
    print(f"\n{Colors.BOLD}Chrome Realtime Translator - 시스템 테스트{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

    results = {}

    # 테스트 실행
    results['Python 버전'] = check_python_version()
    results['파일 구조'] = check_file_structure()
    results['설정 파일'] = check_config_file()
    results['Python 문법'] = check_module_syntax()
    results['필수 의존성'] = check_dependencies()
    results['모듈 Import'] = test_module_imports()
    results['GPU 사용'] = check_gpu_availability()
    results['오디오 디바이스'] = check_audio_devices()

    # 결과 요약
    success = print_summary(results)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
