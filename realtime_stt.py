#!/usr/bin/env python3
"""
실시간 STT 모듈 - Whisper 기반
기존 whisperwithgoogletrans2.py의 Whisper 로직을 실시간 처리에 최적화
"""

import whisper
import torch
import numpy as np
import threading
import queue
import time
import logging
from typing import Optional, Callable, Dict, Any
import tempfile
import wave
from pathlib import Path

class RealtimeSTTConfig:
    """실시간 STT 설정"""
    def __init__(self):
        # 기본값 설정
        self.model_size = "medium"  # medium 모델로 더 높은 정확도
        self.language = "ja"  # 일본어 (ISO 639-1 코드) - 기본값
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.sample_rate = 16000
        self.min_audio_length = 1.0  # 최소 오디오 길이 (초)
        self.max_audio_length = 10.0  # 최대 오디오 길이 (초)
        self.initial_prompt = None

        # 실시간 처리 최적화
        self.enable_vad = True  # Voice Activity Detection
        self.vad_threshold = 0.4
        self.beam_size = 1  # 빠른 처리를 위해 beam search 최소화
        self.patience = 1.0

        # 후처리 필터
        self.suppress_tokens = [
            "Thank you", "Thanks for", "ubscribe", "my channel",
            "for watching", "Amara", "視聴", "ご視聴"
        ]

        # config.json에서 설정 로드 시도
        self.load_from_config()

    def load_from_config(self):
        """config.json에서 STT 설정 로드"""
        try:
            from pathlib import Path
            import json

            config_file = Path("config.json")
            if not config_file.exists():
                return  # config.json이 없으면 기본값 사용

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # stt 섹션에서 설정 읽기
            if "stt" in config:
                stt_config = config["stt"]
                self.model_size = stt_config.get("model_size", self.model_size)
                self.language = stt_config.get("language", self.language)
                self.device = stt_config.get("device", self.device)
                self.min_audio_length = stt_config.get("min_audio_length", self.min_audio_length)
                self.max_audio_length = stt_config.get("max_audio_length", self.max_audio_length)
                self.initial_prompt = stt_config.get("initial_prompt", self.initial_prompt)

        except Exception:
            pass  # 로드 실패 시 기본값 사용

class RealtimeSTT:
    """실시간 Speech-to-Text 처리기"""
    
    def __init__(self, config: Optional[RealtimeSTTConfig] = None):
        self.config = config or RealtimeSTTConfig()
        self.model: Optional[whisper.Whisper] = None
        
        # 처리 큐
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # 상태 관리
        self.is_running = False
        self.processing_thread: Optional[threading.Thread] = None
        
        # 콜백
        self.on_transcription: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 성능 모니터링
        self.processing_times = []
        self.last_result = ""
        self.result_cache = {}
        
        # 로깅
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def load_model(self):
        """Whisper 모델 로딩"""
        if self.model is not None:
            return
            
        try:
            self.logger.info(f"Loading Whisper model: {self.config.model_size}")
            start_time = time.time()
            
            self.model = whisper.load_model(
                self.config.model_size,
                device=self.config.device
            )
            
            load_time = time.time() - start_time
            self.logger.info(f"Model loaded in {load_time:.2f}s on {self.config.device}")
            
            # 모델 워밍업
            self._warmup_model()
            
        except Exception as e:
            error_msg = f"Failed to load Whisper model: {e}"
            self.logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            raise
    
    def _warmup_model(self):
        """모델 워밍업 (첫 추론 지연 최소화)"""
        self.logger.info("Warming up model...")
        
        # 더미 오디오 생성 (1초, 무음)
        dummy_audio = np.zeros(self.config.sample_rate, dtype=np.float32)
        
        try:
            _ = self.model.transcribe(dummy_audio, language=self.config.language)
            self.logger.info("Model warmup completed")
        except Exception as e:
            self.logger.warning(f"Model warmup failed: {e}")
    
    def _save_temp_audio(self, audio_data: np.ndarray) -> str:
        """오디오 데이터를 임시 WAV 파일로 저장"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            with wave.open(tmp_file.name, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.config.sample_rate)
                
                # float32를 int16으로 변환
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wf.writeframes(audio_int16.tobytes())
            
            return tmp_file.name
    
    def _filter_transcription(self, text: str) -> str:
        """전사 결과 후처리"""
        if not text or len(text.strip()) < 2:
            return ""
            
        text = text.strip()
        
        # 억제할 토큰들 제거
        for suppress_token in self.config.suppress_tokens:
            if suppress_token.lower() in text.lower():
                return ""
        
        # 반복 제거 (간단한 중복 감지)
        if text == self.last_result:
            return ""
            
        self.last_result = text
        return text
    
    def _transcribe_audio(self, audio_data: np.ndarray) -> str:
        """오디오 데이터를 텍스트로 변환"""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        start_time = time.time()
        
        try:
            # 오디오 길이 검증
            duration = len(audio_data) / self.config.sample_rate
            if duration < self.config.min_audio_length:
                return ""
            if duration > self.config.max_audio_length:
                # 오디오를 최대 길이로 자르기
                max_samples = int(self.config.max_audio_length * self.config.sample_rate)
                audio_data = audio_data[-max_samples:]
            
            # Whisper 추론
            result = self.model.transcribe(
                audio_data,
                language=self.config.language,
                initial_prompt=self.config.initial_prompt,
                word_timestamps=False,
                verbose=False
            )
            
            text = result["text"].strip()
            
            # 성능 모니터링
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            if len(self.processing_times) > 10:
                self.processing_times.pop(0)
            
            avg_time = sum(self.processing_times) / len(self.processing_times)
            self.logger.debug(f"STT processing time: {processing_time:.2f}s (avg: {avg_time:.2f}s)")
            
            return self._filter_transcription(text)
            
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            return ""
    
    def _processing_worker(self):
        """백그라운드 처리 워커"""
        self.logger.info("STT processing worker started")
        
        while self.is_running or not self.audio_queue.empty():
            try:
                # 큐에서 오디오 데이터 가져오기
                audio_data = self.audio_queue.get(timeout=1.0)
                
                if audio_data is None:  # 종료 신호
                    break
                
                # 전사 수행
                text = self._transcribe_audio(audio_data)
                
                if text:
                    self.logger.debug(f"Transcribed: {text}")
                    
                    # 결과 큐에 추가
                    self.result_queue.put(text)
                    
                    # 콜백 호출
                    if self.on_transcription:
                        threading.Thread(
                            target=self.on_transcription,
                            args=(text,),
                            daemon=True
                        ).start()
                
                self.audio_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Processing worker error: {e}")
                if self.on_error:
                    self.on_error(f"STT processing error: {e}")
        
        self.logger.info("STT processing worker stopped")
    
    def start(self):
        """실시간 STT 시작"""
        if self.is_running:
            self.logger.warning("STT already running")
            return
        
        # 모델 로딩
        if self.model is None:
            self.load_model()
        
        # 처리 스레드 시작
        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._processing_worker,
            daemon=True
        )
        self.processing_thread.start()
        
        self.logger.info("Realtime STT started")
    
    def stop(self):
        """실시간 STT 중지"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping realtime STT...")
        
        # 종료 신호
        self.is_running = False
        self.audio_queue.put(None)  # 종료 신호
        
        # 스레드 종료 대기
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        self.logger.info("Realtime STT stopped")
    
    def process_audio(self, audio_data: np.ndarray):
        """오디오 데이터 처리 요청"""
        if not self.is_running:
            self.logger.warning("STT not running")
            return
        
        try:
            # 큐에 오디오 데이터 추가
            self.audio_queue.put(audio_data, timeout=1.0)
        except queue.Full:
            self.logger.warning("Audio queue full, dropping audio data")
    
    def get_result(self) -> Optional[str]:
        """결과 큐에서 텍스트 가져오기"""
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        if not self.processing_times:
            return {}
        
        return {
            "avg_processing_time": sum(self.processing_times) / len(self.processing_times),
            "queue_size": self.audio_queue.qsize(),
            "result_queue_size": self.result_queue.qsize(),
            "device": self.config.device,
            "model": self.config.model_size
        }

# 테스트 코드
if __name__ == "__main__":
    def on_transcription_callback(text):
        print(f"Transcribed: {text}")
    
    # STT 설정
    config = RealtimeSTTConfig()
    stt = RealtimeSTT(config)
    stt.on_transcription = on_transcription_callback
    
    # 테스트용 더미 오디오 (실제로는 audio_capture.py에서 받아옴)
    def generate_test_audio():
        # 1초 사인파 생성
        t = np.linspace(0, 1, 16000, False)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)  # 440Hz
        return audio
    
    print("Starting realtime STT test...")
    stt.start()
    
    try:
        # 5초간 테스트 오디오 전송
        for i in range(5):
            test_audio = generate_test_audio()
            stt.process_audio(test_audio)
            time.sleep(2)
            
            # 통계 출력
            stats = stt.get_stats()
            if stats:
                print(f"Stats: {stats}")
                
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stt.stop()
        print("STT test completed.")