#!/usr/bin/env python3
"""
Chrome 실시간 번역기 - 메인 시스템
모든 컴포넌트를 통합하여 실시간으로 Chrome 오디오를 캡처하고 번역하여 오버레이로 표시
"""

import threading
import time
import signal
import sys
import logging
from typing import Optional
from pathlib import Path
import json

# 로컬 모듈들
from audio_capture import ChromeAudioCapture, AudioCaptureConfig
from realtime_stt import RealtimeSTT, RealtimeSTTConfig
from realtime_translator import RealtimeTranslator, RealtimeTranslatorConfig
from overlay_ui import TransparentOverlay, OverlayConfig

class ChromeRealtimeTranslatorConfig:
    """메인 시스템 설정"""
    def __init__(self):
        # 기존 config.json 활용
        self.config_file = Path("config.json")
        self.load_base_config()

        # 실시간 처리 설정
        self.enable_audio_capture = True
        self.enable_stt = True
        self.enable_translation = True
        self.enable_overlay = True

        # 성능 설정
        self.stt_workers = 1
        self.translation_workers = 2
        self.max_concurrent_processing = 3

        # 디버깅 설정
        self.log_level = "INFO"
        self.save_debug_audio = False
        self.show_performance_stats = True
        self.stats_interval = 30.0  # 30초마다 통계 출력

    def load_base_config(self):
        """기존 config.json 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    base_config = json.load(f)

                # 기본 설정값들 적용
                self.model_name = base_config.get("model_name", "tencent/Hunyuan-MT-7B")
                self.max_new_tokens = base_config.get("max_new_tokens", 256)
                self.use_cache = base_config.get("use_cache", True)
                self.cache_dir = base_config.get("cache_dir", ".cache")
                self.log_level = base_config.get("log_level", "INFO")

            except Exception as e:
                logging.warning(f"Failed to load config.json: {e}")

class ChromeRealtimeTranslator:
    """Chrome 실시간 번역 시스템"""

    def __init__(self, config: Optional[ChromeRealtimeTranslatorConfig] = None):
        self.config = config or ChromeRealtimeTranslatorConfig()

        # 로깅 설정
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper(), logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # 컴포넌트들
        self.audio_capture: Optional[ChromeAudioCapture] = None
        self.stt: Optional[RealtimeSTT] = None
        self.translator: Optional[RealtimeTranslator] = None
        self.overlay: Optional[TransparentOverlay] = None

        # 상태 관리
        self.is_running = False
        self.start_time = time.time()

        # 통계
        self.stats = {
            'audio_segments_processed': 0,
            'texts_transcribed': 0,
            'translations_completed': 0,
            'errors': 0
        }

        # 통계 출력 타이머
        self.stats_timer: Optional[threading.Timer] = None

        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 등)"""
        self.logger.info("Received shutdown signal, stopping...")
        self.stop()
        sys.exit(0)

    def _initialize_components(self):
        """모든 컴포넌트 초기화"""
        self.logger.info("Initializing components...")

        try:
            # 오디오 캡처 초기화
            if self.config.enable_audio_capture:
                audio_config = AudioCaptureConfig()
                self.audio_capture = ChromeAudioCapture(audio_config)
                self.audio_capture.on_speech_ended = self._on_audio_segment
                self.audio_capture.on_continuous_audio = self._on_continuous_audio  # 연속 처리 콜백 추가
                self.logger.info("Audio capture initialized")

            # STT 초기화
            if self.config.enable_stt:
                stt_config = RealtimeSTTConfig()
                stt_config.model_size = "medium"  # medium 모델로 더 높은 정확도
                self.stt = RealtimeSTT(stt_config)
                self.stt.on_transcription = self._on_transcription
                self.stt.on_error = self._on_stt_error
                self.logger.info("STT initialized")

            # 번역기 초기화
            if self.config.enable_translation:
                translator_config = RealtimeTranslatorConfig()
                translator_config.model_name = self.config.model_name
                translator_config.use_cache = self.config.use_cache
                self.translator = RealtimeTranslator(translator_config)
                self.translator.on_translation = self._on_translation
                self.translator.on_error = self._on_translation_error
                self.logger.info("Translator initialized")

            # 오버레이 UI 초기화
            if self.config.enable_overlay:
                overlay_config = OverlayConfig()
                self.overlay = TransparentOverlay(overlay_config)
                self.logger.info("Overlay UI initialized")

            self.logger.info("All components initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise

    def _start_components(self):
        """모든 컴포넌트 시작"""
        self.logger.info("Starting components...")

        try:
            # STT 시작
            if self.stt:
                self.stt.start()
                self.logger.info("STT started")

            # 번역기 시작
            if self.translator:
                self.translator.start(self.config.translation_workers)
                self.logger.info("Translator started")

            # 오디오 캡처 시작 (마지막에 시작)
            if self.audio_capture:
                self.audio_capture.start_capture()
                self.logger.info("Audio capture started")

            self.logger.info("All components started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start components: {e}")
            self._stop_components()
            raise

    def _stop_components(self):
        """모든 컴포넌트 중지"""
        self.logger.info("Stopping components...")

        # 오디오 캡처 중지
        if self.audio_capture:
            self.audio_capture.stop_capture()
            self.logger.info("Audio capture stopped")

        # STT 중지
        if self.stt:
            self.stt.stop()
            self.logger.info("STT stopped")

        # 번역기 중지
        if self.translator:
            self.translator.stop()
            self.logger.info("Translator stopped")

        # 오버레이 닫기는 메인 스레드에서 처리
        self.logger.info("All components stopped")

    def _on_audio_segment(self, audio_data):
        """오디오 세그먼트 처리"""
        self.stats['audio_segments_processed'] += 1
        self.logger.debug(f"Audio segment received: {len(audio_data)} samples")

        if self.stt:
            try:
                self.stt.process_audio(audio_data)

                # 디버깅용 오디오 저장
                if self.config.save_debug_audio:
                    filename = f"debug_audio_{int(time.time())}.wav"
                    self.audio_capture.save_audio_buffer_to_file(filename)

            except Exception as e:
                self.logger.error(f"Failed to process audio: {e}")
                self.stats['errors'] += 1

    def _on_transcription(self, text: str):
        """STT 결과 처리"""
        if not text or len(text.strip()) < 2:
            return

        self.stats['texts_transcribed'] += 1
        self.logger.debug(f"Transcribed: {text}")

        if self.translator:
            try:
                self.translator.translate_async(text)
            except Exception as e:
                self.logger.error(f"Failed to request translation: {e}")
                self.stats['errors'] += 1

    def _on_translation(self, original: str, translated: str):
        """번역 결과 처리"""
        if not translated or len(translated.strip()) < 1:
            return

        self.stats['translations_completed'] += 1
        self.logger.debug(f"Translation: {original} -> {translated}")

        if self.overlay:
            try:
                self.overlay.update_subtitle(original, translated)
            except Exception as e:
                self.logger.error(f"Failed to update overlay: {e}")
                self.stats['errors'] += 1

    def _on_continuous_audio(self, audio_data):
        """연속 오디오 처리 콜백 - 배경음악이나 긴 발화 처리용"""
        self.logger.debug(f"Continuous audio processing: {len(audio_data)} samples")

        # 기존 오디오 세그먼트 처리와 동일하지만 연속 처리 전용
        if self.stt:
            try:
                self.stt.process_audio(audio_data)
            except Exception as e:
                self.logger.error(f"Failed to process continuous audio: {e}")
                self.stats['errors'] += 1

    def _on_stt_error(self, error: str):
        """STT 오류 처리"""
        self.logger.error(f"STT Error: {error}")
        self.stats['errors'] += 1

    def _on_translation_error(self, error: str):
        """번역 오류 처리"""
        self.logger.error(f"Translation Error: {error}")
        self.stats['errors'] += 1

    def _print_stats(self):
        """성능 통계 출력"""
        if not self.config.show_performance_stats:
            return

        uptime = time.time() - self.start_time

        self.logger.info("=== Performance Statistics ===")
        self.logger.info(f"Uptime: {uptime:.1f} seconds")
        self.logger.info(f"Audio segments processed: {self.stats['audio_segments_processed']}")
        self.logger.info(f"Texts transcribed: {self.stats['texts_transcribed']}")
        self.logger.info(f"Translations completed: {self.stats['translations_completed']}")
        self.logger.info(f"Errors: {self.stats['errors']}")

        # 컴포넌트별 통계
        if self.stt:
            stt_stats = self.stt.get_stats()
            if stt_stats:
                self.logger.info(f"STT avg processing time: {stt_stats.get('avg_processing_time', 0):.2f}s")

        if self.translator:
            trans_stats = self.translator.get_stats()
            if trans_stats:
                self.logger.info(f"Translation cache hit rate: {trans_stats.get('cache_hit_rate', 0)*100:.1f}%")
                self.logger.info(f"Translation avg time: {trans_stats.get('avg_translation_time', 0):.2f}s")

        self.logger.info("==============================")

        # 다음 통계 출력 예약
        if self.is_running:
            self.stats_timer = threading.Timer(self.config.stats_interval, self._print_stats)
            self.stats_timer.start()

    def start(self):
        """실시간 번역 시스템 시작"""
        if self.is_running:
            self.logger.warning("System already running")
            return

        try:
            self.logger.info("Starting Chrome Realtime Translator...")

            # 컴포넌트 초기화 및 시작
            self._initialize_components()
            self._start_components()

            self.is_running = True
            self.start_time = time.time()

            # 통계 출력 시작
            if self.config.show_performance_stats:
                self.stats_timer = threading.Timer(self.config.stats_interval, self._print_stats)
                self.stats_timer.start()

            self.logger.info("Chrome Realtime Translator started successfully!")
            self.logger.info("Controls:")
            self.logger.info("- F1: Show overlay settings")
            self.logger.info("- ESC: Close overlay")
            self.logger.info("- Ctrl+C: Stop system")

            # 오버레이 UI 실행 (메인 스레드에서)
            if self.overlay:
                self.overlay.run()
            else:
                # 오버레이가 없으면 무한 대기
                try:
                    while self.is_running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass

        except Exception as e:
            self.logger.error(f"Failed to start system: {e}")
            self.stop()
            raise
        finally:
            self.stop()

    def stop(self):
        """실시간 번역 시스템 중지"""
        if not self.is_running:
            return

        self.logger.info("Stopping Chrome Realtime Translator...")
        self.is_running = False

        # 통계 타이머 중지
        if self.stats_timer:
            self.stats_timer.cancel()

        # 컴포넌트 중지
        self._stop_components()

        # 오버레이 닫기
        if self.overlay:
            self.overlay.close()

        # 최종 통계 출력
        if self.config.show_performance_stats:
            self._print_stats()

        self.logger.info("Chrome Realtime Translator stopped")

def main():
    """메인 함수"""
    print("Chrome Realtime Translator")
    print("=" * 50)
    print("Real-time Chrome audio capture, STT, and translation")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    try:
        # 설정 로드
        config = ChromeRealtimeTranslatorConfig()

        # 시스템 생성 및 시작
        system = ChromeRealtimeTranslator(config)
        system.start()

    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
