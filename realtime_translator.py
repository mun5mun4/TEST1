#!/usr/bin/env python3
"""
실시간 번역 모듈 - Hunyuan-MT-7B 기반
기존 h5.py의 번역 로직을 실시간 처리에 최적화
"""

import json
import re
import time
import threading
import queue
from pathlib import Path
from typing import Dict, Optional, Callable
from functools import lru_cache
import logging
import hashlib

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

class RealtimeTranslatorConfig:
    """실시간 번역 설정"""
    def __init__(self):
        # h5.py와 동일한 기본 설정
        self.model_name = "tencent/Hunyuan-MT-7B"
        self.max_new_tokens = 256
        self.gen_args = dict(
            top_k=20,
            top_p=0.6,
            temperature=0.7,
            repetition_penalty=1.05,
        )
        
        # 실시간 처리 최적화
        self.use_cache = True
        self.cache_dir = Path(".cache")
        self.batch_size = 4  # 배치 처리
        self.max_queue_size = 20
        self.translation_timeout = 10.0
        
        # 필터링
        self.min_text_length = 2
        self.max_text_length = 500
        self.skip_duplicates = True
        
        # 성능 최적화
        self.use_amp = True  # Mixed precision
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

class RealtimeTranslator:
    """실시간 번역기 - h5.py 로직 기반"""
    
    def __init__(self, config: Optional[RealtimeTranslatorConfig] = None):
        self.config = config or RealtimeTranslatorConfig()
        
        # 모델 및 토크나이저
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None
        
        # 캐싱 시스템 (h5.py와 동일)
        self.cache_dir = self.config.cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.translation_cache = self.load_cache() if self.config.use_cache else {}
        
        # 처리 큐
        self.translation_queue = queue.Queue(maxsize=self.config.max_queue_size)
        self.result_queue = queue.Queue()
        
        # 상태 관리
        self.is_running = False
        self.processing_threads = []
        self.last_translated_text = ""
        
        # 성능 모니터링
        self.translation_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        
        # 콜백
        self.on_translation: Optional[Callable[[str, str], None]] = None  # (original, translated)
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 로깅
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    @lru_cache(maxsize=1000)
    def get_cache_key(self, text: str) -> str:
        """캐시 키 생성 - h5.py와 동일"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def load_cache(self) -> Dict[str, str]:
        """캐시 로드 - h5.py와 동일"""
        cache_file = self.cache_dir / "realtime_translation_cache.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text(encoding='utf-8'))
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
                return {}
        return {}
    
    def save_cache(self):
        """캐시 저장 - h5.py와 동일"""
        if self.config.use_cache:
            try:
                cache_file = self.cache_dir / "realtime_translation_cache.json"
                cache_file.write_text(
                    json.dumps(self.translation_cache, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                self.logger.debug(f"Cache saved: {len(self.translation_cache)} entries")
            except Exception as e:
                self.logger.error(f"Failed to save cache: {e}")
    
    def load_model(self):
        """모델 로딩 - h5.py와 유사하지만 실시간 처리 최적화"""
        if self.model is not None:
            return
        
        try:
            self.logger.info(f"Loading model: {self.config.model_name}")
            start_time = time.time()
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                torch_dtype=self.config.torch_dtype,
                device_map="auto",
            )
            
            load_time = time.time() - start_time
            self.logger.info(f"Model loaded in {load_time:.2f}s on {self.model.device}")
            
            # 모델 워밍업
            self._warmup_model()
            
        except Exception as e:
            error_msg = f"Failed to load translation model: {e}"
            self.logger.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            raise
    
    def _warmup_model(self):
        """모델 워밍업"""
        self.logger.info("Warming up translation model...")
        try:
            dummy_text = "Hello world"
            _ = self.translate_text(dummy_text)
            self.logger.info("Translation model warmup completed")
        except Exception as e:
            self.logger.warning(f"Model warmup failed: {e}")
    
    def translate_text(self, text: str) -> str:
        """
        텍스트 번역 - h5.py의 translate_block_text와 100% 동일한 로직
        """
        if not text or len(text.strip()) < self.config.min_text_length:
            return ""
        
        text = text.strip()
        if len(text) > self.config.max_text_length:
            text = text[:self.config.max_text_length]
        
        # 중복 필터링
        if self.config.skip_duplicates and text == self.last_translated_text:
            return ""
        
        # 캐시 확인
        cache_key = None
        if self.config.use_cache:
            cache_key = self.get_cache_key(text)
            if cache_key in self.translation_cache:
                self.cache_hits += 1
                self.last_translated_text = text
                return self.translation_cache[cache_key]
        
        self.cache_misses += 1
        
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded")
        
        start_time = time.time()
        
        try:
            # 일본어→한국어 번역을 위한 최적화된 프롬프트
            prompt = (
                "Translate the following Japanese text into Korean. "
                "Provide natural and accurate Korean translation. "
                "Keep the original line breaks. Do not add any explanation.\n\n"
                f"{text}"
            )
            messages = [{"role": "user", "content": prompt}]
            
            inputs = self.tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=False,
                return_tensors="pt",
            )
            
            inputs = inputs.to(self.model.device)
            
            with torch.no_grad():
                if self.config.use_amp:
                    with torch.cuda.amp.autocast():
                        outputs = self.model.generate(
                            inputs,
                            max_new_tokens=self.config.max_new_tokens,
                            **self.config.gen_args,
                        )
                else:
                    outputs = self.model.generate(
                        inputs,
                        max_new_tokens=self.config.max_new_tokens,
                        **self.config.gen_args,
                    )
            
            out_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # h5.py와 동일한 후처리
            if text in out_text:
                out_text = out_text.split(text, 1)[-1].strip()
            
            out_text = out_text.strip().strip('"').strip()
            
            # 캐시 저장
            if self.config.use_cache and cache_key:
                self.translation_cache[cache_key] = out_text
            
            # 성능 모니터링
            processing_time = time.time() - start_time
            self.translation_times.append(processing_time)
            if len(self.translation_times) > 10:
                self.translation_times.pop(0)
            
            self.last_translated_text = text
            self.logger.debug(f"Translation time: {processing_time:.2f}s")
            
            return out_text
            
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            return text  # 번역 실패시 원문 반환
    
    def _translation_worker(self):
        """번역 워커 스레드"""
        self.logger.info("Translation worker started")
        
        while self.is_running or not self.translation_queue.empty():
            try:
                # 큐에서 텍스트 가져오기
                item = self.translation_queue.get(timeout=1.0)
                
                if item is None:  # 종료 신호
                    break
                
                original_text = item
                
                # 번역 수행
                translated_text = self.translate_text(original_text)
                
                if translated_text:
                    # 결과 큐에 추가
                    self.result_queue.put((original_text, translated_text))
                    
                    # 콜백 호출
                    if self.on_translation:
                        threading.Thread(
                            target=self.on_translation,
                            args=(original_text, translated_text),
                            daemon=True
                        ).start()
                
                self.translation_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Translation worker error: {e}")
                if self.on_error:
                    self.on_error(f"Translation error: {e}")
        
        self.logger.info("Translation worker stopped")
    
    def start(self, num_workers: int = 2):
        """실시간 번역 시작"""
        if self.is_running:
            self.logger.warning("Translator already running")
            return
        
        # 모델 로딩
        if self.model is None:
            self.load_model()
        
        # 워커 스레드 시작
        self.is_running = True
        for i in range(num_workers):
            worker = threading.Thread(
                target=self._translation_worker,
                name=f"TranslationWorker-{i}",
                daemon=True
            )
            worker.start()
            self.processing_threads.append(worker)
        
        self.logger.info(f"Realtime translator started with {num_workers} workers")
    
    def stop(self):
        """실시간 번역 중지"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping realtime translator...")
        
        # 종료 신호
        self.is_running = False
        for _ in self.processing_threads:
            self.translation_queue.put(None)
        
        # 스레드 종료 대기
        for thread in self.processing_threads:
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        self.processing_threads.clear()
        
        # 캐시 저장
        self.save_cache()
        
        self.logger.info("Realtime translator stopped")
    
    def translate_async(self, text: str):
        """비동기 번역 요청"""
        if not self.is_running:
            self.logger.warning("Translator not running")
            return
        
        if not text or len(text.strip()) < self.config.min_text_length:
            return
        
        try:
            self.translation_queue.put(text.strip(), timeout=1.0)
        except queue.Full:
            self.logger.warning("Translation queue full, dropping request")
    
    def get_result(self) -> Optional[tuple]:
        """결과 큐에서 번역 결과 가져오기"""
        try:
            return self.result_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_stats(self) -> Dict:
        """성능 통계 반환"""
        total_cache_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_cache_requests if total_cache_requests > 0 else 0
        
        avg_translation_time = 0
        if self.translation_times:
            avg_translation_time = sum(self.translation_times) / len(self.translation_times)
        
        return {
            "cache_hit_rate": cache_hit_rate,
            "cache_entries": len(self.translation_cache),
            "avg_translation_time": avg_translation_time,
            "queue_size": self.translation_queue.qsize(),
            "result_queue_size": self.result_queue.qsize(),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses
        }

# 테스트 코드
if __name__ == "__main__":
    def on_translation_callback(original, translated):
        print(f"Original: {original}")
        print(f"Translated: {translated}")
        print("-" * 50)
    
    # 번역기 설정
    config = RealtimeTranslatorConfig()
    translator = RealtimeTranslator(config)
    translator.on_translation = on_translation_callback
    
    # 테스트 텍스트
    test_texts = [
        "Hello, how are you?",
        "This is a test sentence.",
        "I love machine learning.",
        "Python is a great programming language.",
        "Real-time translation is amazing!"
    ]
    
    print("Starting realtime translator test...")
    translator.start()
    
    try:
        # 테스트 텍스트들 번역 요청
        for text in test_texts:
            translator.translate_async(text)
            time.sleep(2)
            
            # 통계 출력
            stats = translator.get_stats()
            print(f"Stats: {stats}")
        
        # 잠시 기다려서 모든 번역 완료
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        translator.stop()
        print("Translation test completed.")