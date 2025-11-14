#!/usr/bin/env python3
"""
실시간 오디오 캡처 모듈 - Chrome 브라우저 오디오를 실시간으로 캡처
Windows WASAPI를 사용하여 시스템 오디오(스피커 출력)를 모니터링
"""

import pyaudio
import numpy as np
import threading
import time
import wave
from collections import deque
from typing import Optional, Callable
import logging

class AudioCaptureConfig:
    """오디오 캡처 설정"""
    def __init__(self):
        self.sample_rate = 16000  # Whisper 최적화
        self.channels = 1  # 모노 오디오
        self.chunk_size = 1024  # 버퍼 크기
        self.format = pyaudio.paFloat32
        self.buffer_duration = 5.0  # 5초 버퍼 (더 긴 발화 대응)
        self.overlap_duration = 1.0  # 오디오 청크 간 겹침 시간 (연속성 보장)
        self.silence_threshold = 0.005  # 무음 감지 임계값 (낮춤 - 배경음악 고려)
        self.min_speech_duration = 0.3  # 최소 음성 지속시간 (짧게)
        self.max_silence_duration = 2.0  # 최대 지속 침묵 시간 (긴 발화 대응)
        self.background_noise_threshold = 0.008  # 배경 소음 임계값

class ChromeAudioCapture:
    """Chrome 오디오 실시간 캡처"""
    
    def __init__(self, config: Optional[AudioCaptureConfig] = None):
        self.config = config or AudioCaptureConfig()
        self.pyaudio = pyaudio.PyAudio()
        
        # 오디오 버퍼 (3초간)
        buffer_size = int(self.config.buffer_duration * self.config.sample_rate / self.config.chunk_size)
        self.audio_buffer = deque(maxlen=buffer_size)
        
        # 상태 관리
        self.is_recording = False
        self.is_speaking = False
        self.speech_start_time = None
        self.last_speech_time = None  # 마지막 음성 감지 시간
        self.silence_start_time = None  # 침묵 시작 시간

        # 배경 노이즈 적응형 감지
        self.noise_buffer = deque(maxlen=50)  # 배경 소음 레벨 저장
        self.adaptive_threshold = self.config.silence_threshold
        
        # 콜백 함수들
        self.on_speech_detected: Optional[Callable] = None
        self.on_speech_ended: Optional[Callable] = None
        self.on_continuous_audio: Optional[Callable] = None  # 연속 처리용 콜백
        
        # 스레드 관리
        self.capture_thread = None
        self.processing_thread = None
        self.continuous_thread = None

        # 연속 처리를 위한 상태
        self.continuous_mode = True  # 연속 처리 모드 활성화
        self.last_processing_time = 0
        self.processing_interval = 3.0  # 3초마다 연속 처리
        
        # 로깅
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def get_default_speaker_device(self) -> int:
        """기본 스피커 디바이스를 찾기 (시스템 오디오 캡처용)"""
        # 우선순위별 디바이스 검색
        priority_keywords = [
            # WASAPI loopback (최고 우선순위)
            ['WASAPI', 'loopback'],
            # Virtual Audio Cable 계열
            ['VoiceMeeter Output', 'VB-Audio'],
            ['CABLE Output', 'VB-Audio'],
            # 스테레오 믹스
            ['스테레오 믹스', 'Stereo Mix'],
            # 기타 가능한 시스템 오디오 소스
            ['Virtual Desktop Audio'],
            ['Steam Streaming Speakers', 'Input'],
            # 일반 입력 디바이스 (마지막 수단)
            ['Speakers', 'Input'],
            ['마이크', 'Microphone']
        ]
        
        for keywords in priority_keywords:
            for i in range(self.pyaudio.get_device_count()):
                try:
                    device_info = self.pyaudio.get_device_info_by_index(i)
                    device_name = device_info['name']
                    
                    # 입력 채널이 있는 디바이스만
                    if device_info['maxInputChannels'] == 0:
                        continue
                    
                    # 키워드 매칭 (대소문자 무시)
                    name_lower = device_name.lower()
                    if all(keyword.lower() in name_lower for keyword in keywords):
                        self.logger.info(f"Found audio capture device: {device_name}")
                        return i
                        
                except Exception as e:
                    continue
        
        # 기본 입력 디바이스 사용
        try:
            default_device = self.pyaudio.get_default_input_device_info()
            self.logger.warning(f"Using default input device: {default_device['name']}")
            return default_device['index']
        except Exception as e:
            self.logger.error(f"No suitable audio device found: {e}")
            return 0
    
    def detect_voice_activity(self, audio_data: np.ndarray) -> bool:
        """개선된 음성 활동 감지 (VAD) - 배경음악 대응"""
        # RMS 에너지 계산
        rms = np.sqrt(np.mean(audio_data ** 2))

        # 배경 노이즈 레벨 업데이트
        self.noise_buffer.append(rms)

        # 적응형 임계값 업데이트 (배경 노이즈의 2배)
        if len(self.noise_buffer) >= 10:
            avg_noise = sum(list(self.noise_buffer)[:10]) / 10  # 초기 10개 샘플의 평균
            self.adaptive_threshold = max(self.config.silence_threshold, avg_noise * 2.0)

        # 음성 감지: RMS가 적응형 임계값을 초과하고
        # 추가로 스펙트럼 기반 검증
        is_speech_rms = rms > self.adaptive_threshold

        if is_speech_rms:
            # 고주파 강도 검사 (음성의 특징)
            fft = np.fft.fft(audio_data)
            freqs = np.fft.fftfreq(len(audio_data), 1/self.config.sample_rate)

            # 300Hz - 3400Hz 대역의 에너지 (음성 주파수 대역)
            speech_band = (freqs >= 300) & (freqs <= 3400)
            speech_energy = np.sum(np.abs(fft[speech_band]) ** 2)

            # 전체 에너지 대비 음성 대역 에너지 비율
            total_energy = np.sum(np.abs(fft) ** 2)
            speech_ratio = speech_energy / (total_energy + 1e-10)

            # 음성으로 판단할 최소 비율
            return speech_ratio > 0.1

        return False
    
    def get_audio_segment(self, duration_seconds: float = 3.0) -> Optional[np.ndarray]:
        """지정된 길이의 오디오 세그먼트 반환"""
        if not self.audio_buffer:
            return None
            
        # 필요한 청크 수 계산
        chunks_needed = int(duration_seconds * self.config.sample_rate / self.config.chunk_size)
        chunks_needed = min(chunks_needed, len(self.audio_buffer))
        
        if chunks_needed == 0:
            return None
            
        # 최신 청크들을 가져와서 연결
        recent_chunks = list(self.audio_buffer)[-chunks_needed:]
        return np.concatenate(recent_chunks)
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio 콜백 함수"""
        try:
            # 바이트 데이터를 numpy 배열로 변환
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            
            # 스테레오를 모노로 변환 (필요시)
            if len(audio_data) == frame_count * 2:
                audio_data = audio_data.reshape(-1, 2).mean(axis=1)
            
            # 버퍼에 추가
            self.audio_buffer.append(audio_data)
            
            # 음성 활동 감지
            has_speech = self.detect_voice_activity(audio_data)
            
            current_time = time.time()
            
            # 음성 감지 상태 업데이트
            if has_speech:
                self.last_speech_time = current_time

                # 음성 시작 감지
                if not self.is_speaking:
                    self.is_speaking = True
                    self.speech_start_time = current_time
                    self.silence_start_time = None
                    self.logger.debug("Speech started")
            else:
                # 침묵 감지
                if self.is_speaking:
                    if self.silence_start_time is None:
                        self.silence_start_time = current_time

                    # 충분히 긴 침묵이 지속되면 음성 종료로 판단
                    silence_duration = current_time - self.silence_start_time
                    if silence_duration >= self.config.max_silence_duration:
                        # 최소 음성 지속 시간 체크
                        if current_time - self.speech_start_time >= self.config.min_speech_duration:
                            self.is_speaking = False
                            self.silence_start_time = None
                            self.logger.debug(f"Speech ended after {silence_duration:.1f}s silence")

                            # 음성 종료 콜백 호출
                            if self.on_speech_ended:
                                # 침묵 시작 이전까지의 오디오만 가져오기
                                audio_segment = self.get_audio_segment()
                                if audio_segment is not None:
                                    threading.Thread(
                                        target=self.on_speech_ended,
                                        args=(audio_segment,),
                                        daemon=True
                                    ).start()
                            
        except Exception as e:
            self.logger.error(f"Audio callback error: {e}")
            
        return (in_data, pyaudio.paContinue)
    
    def start_capture(self):
        """오디오 캡처 시작"""
        if self.is_recording:
            self.logger.warning("Already recording")
            return
            
        try:
            device_index = self.get_default_speaker_device()
            
            # 오디오 스트림 설정
            self.stream = self.pyaudio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self.audio_callback,
                start=False
            )
            
            self.is_recording = True
            self.stream.start_stream()

            # 연속 처리 워커 시작
            if self.continuous_mode:
                self.continuous_thread = threading.Thread(
                    target=self._continuous_processing_worker,
                    daemon=True
                )
                self.continuous_thread.start()

            self.logger.info(f"Audio capture started (device: {device_index}, continuous mode: {self.continuous_mode})")

        except Exception as e:
            self.logger.error(f"Failed to start audio capture: {e}")
            raise
    
    def stop_capture(self):
        """오디오 캡처 중지"""
        if not self.is_recording:
            return
            
        try:
            self.is_recording = False
            if hasattr(self, 'stream'):
                self.stream.stop_stream()
                self.stream.close()
            self.logger.info("Audio capture stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping audio capture: {e}")
    
    def save_audio_buffer_to_file(self, filename: str, duration: float = 3.0):
        """현재 오디오 버퍼를 WAV 파일로 저장 (디버깅용)"""
        audio_data = self.get_audio_segment(duration)
        if audio_data is None:
            self.logger.warning("No audio data to save")
            return
            
        # float32를 int16으로 변환
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        with wave.open(filename, 'w') as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(audio_int16.tobytes())
            
        self.logger.info(f"Audio saved to {filename}")

    def _continuous_processing_worker(self):
        """연속 처리 워커 - 배경음악이나 긴 발화 처리용"""
        self.logger.info("Continuous processing worker started")

        while self.is_recording:
            try:
                current_time = time.time()

                # 연속 처리 간격 체크
                if current_time - self.last_processing_time >= self.processing_interval:
                    # 최근 오디오 세그먼트 가져오기
                    audio_segment = self.get_audio_segment(duration_seconds=3.0)

                    if audio_segment is not None and self.on_continuous_audio:
                        # 연속 처리 콜백 호출
                        threading.Thread(
                            target=self.on_continuous_audio,
                            args=(audio_segment,),
                            daemon=True
                        ).start()

                        self.last_processing_time = current_time
                        self.logger.debug("Continuous processing triggered")

                time.sleep(0.5)  # 500ms마다 체크

            except Exception as e:
                self.logger.error(f"Continuous processing worker error: {e}")
                time.sleep(1.0)

        self.logger.info("Continuous processing worker stopped")

    def __del__(self):
        """소멸자"""
        self.stop_capture()
        if hasattr(self, 'pyaudio'):
            self.pyaudio.terminate()

# 테스트 코드
if __name__ == "__main__":
    def on_speech_callback(audio_data):
        print(f"Speech detected! Audio length: {len(audio_data)/16000:.2f}s")
    
    capture = ChromeAudioCapture()
    capture.on_speech_ended = on_speech_callback
    
    print("Starting audio capture... Speak something!")
    capture.start_capture()
    
    try:
        # 30초간 테스트
        time.sleep(30)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        capture.stop_capture()
        print("Audio capture test completed.")