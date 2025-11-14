#!/usr/bin/env python3
"""
투명 오버레이 UI 모듈
실시간 자막을 화면에 반투명 오버레이로 표시
"""

import tkinter as tk
from tkinter import ttk, font, messagebox
import threading
import queue
import time
from typing import Optional, Dict, Any
import json
from pathlib import Path
import sys

# Windows에서만 사용가능한 모듈들
try:
    import win32gui
    import win32con
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

class OverlayConfig:
    """오버레이 UI 설정"""
    def __init__(self):
        # 기본 위치 및 크기
        self.window_width = 800
        self.window_height = 200
        self.x_position = 100
        self.y_position = 100
        
        # 투명도 및 외관
        self.alpha = 0.8  # 투명도 (0.0 ~ 1.0)
        self.bg_color = "#000000"  # 배경색
        self.original_text_color = "#FFFFFF"  # 원문 색상
        self.translated_text_color = "#00FF00"  # 번역문 색상
        
        # 폰트 설정
        self.font_family = "맑은 고딕"
        self.original_font_size = 14
        self.translated_font_size = 16
        self.font_weight = "normal"  # "normal" or "bold"
        
        # 동작 설정
        self.always_on_top = True
        self.click_through = False  # 클릭 투과 여부
        self.auto_hide_enabled = True  # 자동 숨김 활성화 여부
        self.auto_hide_delay = 10.0  # 자동 숨김 지연 (초) - 증가
        self.fade_duration = 0.5  # 페이드 애니메이션 시간
        self.resizable = True  # 윈도우 크기 조절 가능 여부
        self.subtitle_alpha = 1.0  # 자막 투명도 (별도 조절)

        # 가사 스타일 스크롤 설정
        self.lyrics_style = True  # 위로 밀리는 가사 스타일 활성화
        self.max_history_lines = 5  # 표시할 최대 이력 줄 수
        self.scroll_animation_speed = 300  # 스크롤 애니메이션 속도 (ms)
        
        # 텍스트 표시 설정
        self.show_original = True
        self.show_translated = True
        self.max_line_length = 80
        self.max_lines = 3
        
        # 설정 파일
        self.config_file = Path("overlay_config.json")
    
    def save(self):
        """설정을 파일로 저장"""
        config_dict = {
            "window_width": self.window_width,
            "window_height": self.window_height,
            "x_position": self.x_position,
            "y_position": self.y_position,
            "alpha": self.alpha,
            "bg_color": self.bg_color,
            "original_text_color": self.original_text_color,
            "translated_text_color": self.translated_text_color,
            "font_family": self.font_family,
            "original_font_size": self.original_font_size,
            "translated_font_size": self.translated_font_size,
            "font_weight": self.font_weight,
            "always_on_top": self.always_on_top,
            "click_through": self.click_through,
            "auto_hide_delay": self.auto_hide_delay,
            "show_original": self.show_original,
            "show_translated": self.show_translated,
            "lyrics_style": self.lyrics_style,
            "max_history_lines": self.max_history_lines,
            "scroll_animation_speed": self.scroll_animation_speed,
            "auto_hide_enabled": self.auto_hide_enabled,
            "resizable": self.resizable,
            "subtitle_alpha": self.subtitle_alpha,
        }
        
        try:
            self.config_file.write_text(
                json.dumps(config_dict, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception:
            pass
    
    def load(self):
        """파일에서 설정 로드"""
        if not self.config_file.exists():
            return
        
        try:
            config_dict = json.loads(self.config_file.read_text(encoding='utf-8'))
            for key, value in config_dict.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        except Exception:
            pass

class TransparentOverlay:
    """투명 오버레이 UI"""
    
    def __init__(self, config: Optional[OverlayConfig] = None):
        self.config = config or OverlayConfig()
        self.config.load()
        
        # UI 요소
        self.root: Optional[tk.Tk] = None
        self.original_label: Optional[tk.Label] = None
        self.translated_label: Optional[tk.Label] = None
        self.settings_window: Optional[tk.Toplevel] = None
        
        # 상태 관리
        self.is_visible = True
        self.current_original = ""
        self.current_translated = ""
        self.last_update_time = time.time()

        # 가사 스타일을 위한 이력 관리
        self.translation_history = []  # (original, translated) 튜플 리스트
        self.history_labels = []  # 이력 표시용 라벨들
        
        # 자동 숨김 타이머
        self.hide_timer: Optional[threading.Timer] = None
        
        # 업데이트 큐 (스레드 안전)
        self.update_queue = queue.Queue()
        
        # 드래그 관련
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False
    
    def create_ui(self):
        """UI 생성"""
        self.root = tk.Tk()
        self.root.title("Real-time Translation Overlay")
        
        # 윈도우 설정
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}+"
                          f"{self.config.x_position}+{self.config.y_position}")
        self.root.configure(bg=self.config.bg_color)
        
        # 투명도 설정
        self.root.wm_attributes('-alpha', self.config.alpha)
        
        # 항상 최상위
        if self.config.always_on_top:
            self.root.wm_attributes('-topmost', True)
        
        # 윈도우 경계 설정 (크기 조절 가능하도록)
        if self.config.resizable:
            self.root.overrideredirect(False)
            self.root.resizable(True, True)
            # 타이틀바는 숨기고 경계만 표시하도록 설정
            try:
                self.root.wm_attributes('-toolwindow', True)
            except:
                pass
        else:
            self.root.overrideredirect(True)
        
        # Windows 클릭 투과 설정
        if WINDOWS_AVAILABLE and self.config.click_through:
            self._setup_click_through()
        
        # 폰트 설정
        original_font = font.Font(
            family=self.config.font_family,
            size=self.config.original_font_size,
            weight=self.config.font_weight
        )

        translated_font = font.Font(
            family=self.config.font_family,
            size=self.config.translated_font_size,
            weight="bold"
        )

        # 자막 투명도 적용된 색상 계산
        original_color = self._blend_color_alpha(self.config.original_text_color, self.config.subtitle_alpha)
        translated_color = self._blend_color_alpha(self.config.translated_text_color, self.config.subtitle_alpha)
        
        # 메인 프레임 (스크롤 가능하도록 Canvas 사용)
        if self.config.lyrics_style:
            # 가사 스타일: Canvas로 스크롤 구현
            self.canvas = tk.Canvas(self.root, bg=self.config.bg_color, highlightthickness=0)
            self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            main_frame = tk.Frame(self.canvas, bg=self.config.bg_color)
            # Canvas 중앙에 프레임 배치
            self.canvas_window = self.canvas.create_window(
                self.config.window_width // 2, 0,
                anchor="n", window=main_frame
            )
        else:
            # 기본 스타일
            main_frame = tk.Frame(self.root, bg=self.config.bg_color)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 가사 스타일 vs 기본 스타일 구분
        if self.config.lyrics_style:
            self._create_lyrics_style_ui(main_frame, original_font, translated_font)
        else:
            self._create_default_style_ui(main_frame, original_font, translated_font)
        
        # 마우스 이벤트 바인딩 (드래그 이동)
        if not self.config.click_through:
            self._setup_drag_events()
        
        # 키보드 이벤트 바인딩
        self.root.bind('<Escape>', self._on_escape)
        self.root.bind('<F1>', self._show_settings)
        self.root.focus_set()
        
        # 업데이트 체크 타이머
        self.root.after(100, self._check_updates)

        # Canvas 크기 조정 바인딩 (가사 스타일인 경우)
        if self.config.lyrics_style and hasattr(self, 'canvas'):
            self.root.bind('<Configure>', self._on_window_resize)
    
    def _setup_click_through(self):
        """Windows 클릭 투과 설정"""
        if not WINDOWS_AVAILABLE:
            return
        
        def setup():
            try:
                hwnd = self.root.winfo_id()
                # WS_EX_TRANSPARENT: 클릭 투과
                # WS_EX_LAYERED: 투명도 적용을 위해 필요
                extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                                     extended_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
            except Exception:
                pass
        
        # 윈도우가 완전히 생성된 후 설정
        self.root.after(100, setup)
    
    def _create_lyrics_style_ui(self, parent, original_font, translated_font):
        """가사 스타일 UI 생성"""
        # 자막 투명도 적용된 색상 계산
        original_color = self._blend_color_alpha(self.config.original_text_color, self.config.subtitle_alpha)
        translated_color = self._blend_color_alpha(self.config.translated_text_color, self.config.subtitle_alpha)
        # 현재 번역 표시용 (맨 아래)
        if self.config.show_translated:
            self.translated_label = tk.Label(
                parent,
                text="실시간 번역을 기다리는 중...",
                font=translated_font,
                fg=translated_color,
                bg=self.config.bg_color,
                justify=tk.CENTER,
                wraplength=self.config.window_width - 20,
                anchor=tk.CENTER
            )
            self.translated_label.pack(side=tk.BOTTOM, pady=(2, 5))

        # 현재 원문 표시용 (번역문 위)
        if self.config.show_original:
            self.original_label = tk.Label(
                parent,
                text="",
                font=original_font,
                fg=original_color,
                bg=self.config.bg_color,
                justify=tk.CENTER,
                wraplength=self.config.window_width - 20,
                anchor=tk.CENTER
            )
            self.original_label.pack(side=tk.BOTTOM, pady=(5, 2))

        # 이력 표시용 프레임 (맨 위)
        self.history_frame = tk.Frame(parent, bg=self.config.bg_color)
        self.history_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)

    def _create_default_style_ui(self, parent, original_font, translated_font):
        """기본 스타일 UI 생성"""
        # 자막 투명도 적용된 색상 계산
        original_color = self._blend_color_alpha(self.config.original_text_color, self.config.subtitle_alpha)
        translated_color = self._blend_color_alpha(self.config.translated_text_color, self.config.subtitle_alpha)
        # 원문 라벨
        if self.config.show_original:
            self.original_label = tk.Label(
                parent,
                text="",
                font=original_font,
                fg=original_color,
                bg=self.config.bg_color,
                justify=tk.CENTER,
                wraplength=self.config.window_width - 20,
                anchor=tk.CENTER
            )
            self.original_label.pack(pady=(5, 2))

        # 번역문 라벨
        if self.config.show_translated:
            self.translated_label = tk.Label(
                parent,
                text="실시간 번역을 기다리는 중...",
                font=translated_font,
                fg=translated_color,
                bg=self.config.bg_color,
                justify=tk.CENTER,
                wraplength=self.config.window_width - 20,
                anchor=tk.CENTER
            )
            self.translated_label.pack(pady=(2, 5))

    def _on_window_resize(self, event):
        """윈도우 크기 변경 시 Canvas 업데이트"""
        if hasattr(self, 'canvas') and event.widget == self.root:
            canvas_width = event.width - 20  # 패딩 고려
            canvas_height = event.height - 10  # 패딩 고려
            self.canvas.configure(width=canvas_width, height=canvas_height)
            # Canvas 중앙에 프레임 위치 업데이트
            self.canvas.coords(self.canvas_window, canvas_width // 2, 0)

    def _setup_drag_events(self):
        """드래그 이벤트 설정"""
        def start_drag(event):
            self.is_dragging = True
            self.drag_start_x = event.x
            self.drag_start_y = event.y
        
        def on_drag(event):
            if self.is_dragging:
                x = self.root.winfo_x() + (event.x - self.drag_start_x)
                y = self.root.winfo_y() + (event.y - self.drag_start_y)
                self.root.geometry(f"+{x}+{y}")
                
                # 설정 업데이트
                self.config.x_position = x
                self.config.y_position = y
        
        def end_drag(event):
            self.is_dragging = False
            self.config.save()  # 위치 저장
        
        # 모든 위젯에 드래그 이벤트 바인딩
        widgets = [self.root]
        if self.original_label:
            widgets.append(self.original_label)
        if self.translated_label:
            widgets.append(self.translated_label)
        
        for widget in widgets:
            widget.bind('<Button-1>', start_drag)
            widget.bind('<B1-Motion>', on_drag)
            widget.bind('<ButtonRelease-1>', end_drag)
    
    def _check_updates(self):
        """업데이트 큐 확인 및 UI 업데이트"""
        try:
            while True:
                update = self.update_queue.get_nowait()
                if update['type'] == 'subtitle':
                    self._update_subtitle_display(update['original'], update['translated'])
                elif update['type'] == 'hide':
                    self._hide_overlay()
                elif update['type'] == 'show':
                    self._show_overlay()
        except queue.Empty:
            pass
        
        # 자동 숨김 체크
        if (self.config.auto_hide_enabled and self.config.auto_hide_delay > 0 and
            time.time() - self.last_update_time > self.config.auto_hide_delay):
            if self.is_visible:
                self._hide_overlay()
        
        # 다음 업데이트 스케줄
        if self.root:
            self.root.after(100, self._check_updates)
    
    def _update_subtitle_display(self, original: str, translated: str):
        """자막 표시 업데이트"""
        self.current_original = original
        self.current_translated = translated
        self.last_update_time = time.time()

        # 오버레이 표시
        if not self.is_visible:
            self._show_overlay()

        # 텍스트 길이 제한
        if len(original) > self.config.max_line_length:
            original = original[:self.config.max_line_length] + "..."
        if len(translated) > self.config.max_line_length:
            translated = translated[:self.config.max_line_length] + "..."

        if self.config.lyrics_style:
            self._update_lyrics_style(original, translated)
        else:
            self._update_default_style(original, translated)

        # 자동 숨김 타이머 재설정
        if self.hide_timer:
            self.hide_timer.cancel()

        if self.config.auto_hide_enabled and self.config.auto_hide_delay > 0:
            self.hide_timer = threading.Timer(
                self.config.auto_hide_delay,
                lambda: self.update_queue.put({'type': 'hide'})
            )
            self.hide_timer.start()

    def _update_default_style(self, original: str, translated: str):
        """기본 스타일 업데이트"""
        # 라벨 업데이트
        if self.original_label and self.config.show_original:
            self.original_label.config(text=original)

        if self.translated_label and self.config.show_translated:
            self.translated_label.config(text=translated)

    def _update_lyrics_style(self, original: str, translated: str):
        """가사 스타일 업데이트 (위로 밀려 올라감)"""
        # 현재 번역을 이력에 추가
        if self.current_translated and self.current_translated != "실시간 번역을 기다리는 중...":
            self.translation_history.append((self.current_original, self.current_translated))

            # 최대 이력 수 제한
            if len(self.translation_history) > self.config.max_history_lines:
                self.translation_history.pop(0)

        # 현재 라벨 업데이트
        if self.original_label and self.config.show_original:
            self.original_label.config(text=original)

        if self.translated_label and self.config.show_translated:
            self.translated_label.config(text=translated)

        # 이력 라벨들 업데이트
        self._update_history_labels()
    
    def _show_overlay(self):
        """오버레이 표시"""
        if self.is_visible:
            return
        
        self.is_visible = True
        if self.root:
            self.root.deiconify()
    
    def _hide_overlay(self):
        """오버레이 숨김"""
        if not self.is_visible:
            return
        
        self.is_visible = False
        if self.root:
            self.root.withdraw()
    
    def _on_escape(self, event):
        """ESC 키 처리"""
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        else:
            self.close()
    
    def _show_settings(self, event):
        """설정 창 표시 (F1)"""
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
        
        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("오버레이 설정")
        self.settings_window.geometry("400x500")
        self.settings_window.resizable(False, False)
        
        # 설정 UI 생성
        self._create_settings_ui()
    
    def _create_settings_ui(self):
        """설정 UI 생성"""
        if not self.settings_window:
            return
        
        notebook = ttk.Notebook(self.settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 외관 탭
        appearance_frame = ttk.Frame(notebook)
        notebook.add(appearance_frame, text="외관")

        # 동작 탭
        behavior_frame = ttk.Frame(notebook)
        notebook.add(behavior_frame, text="동작")

        # 크기 조절 탭
        size_frame = ttk.Frame(notebook)
        notebook.add(size_frame, text="크기")

        # 윈도우 탭
        window_frame = ttk.Frame(notebook)
        notebook.add(window_frame, text="윈도우")

        self._create_appearance_settings(appearance_frame)
        self._create_behavior_settings(behavior_frame)
        self._create_size_settings(size_frame)
        self._create_window_settings(window_frame)

    def _create_appearance_settings(self, parent):
        """외관 설정 UI"""

        # 창 투명도
        ttk.Label(parent, text="창 투명도:").grid(row=0, column=0, sticky=tk.W, pady=5)
        alpha_var = tk.DoubleVar(value=self.config.alpha)
        alpha_scale = ttk.Scale(parent, from_=0.1, to=1.0, variable=alpha_var,
                               command=lambda v: self._update_alpha(float(v)))
        alpha_scale.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5)

        # 자막 투명도
        ttk.Label(parent, text="자막 투명도:").grid(row=1, column=0, sticky=tk.W, pady=5)
        subtitle_alpha_var = tk.DoubleVar(value=self.config.subtitle_alpha)
        subtitle_alpha_scale = ttk.Scale(parent, from_=0.1, to=1.0, variable=subtitle_alpha_var,
                                        command=lambda v: self._update_subtitle_alpha(float(v)))
        subtitle_alpha_scale.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=5)

        # 폰트 크기
        ttk.Label(parent, text="번역문 폰트 크기:").grid(row=2, column=0, sticky=tk.W, pady=5)
        font_size_var = tk.IntVar(value=self.config.translated_font_size)
        font_size_spinbox = ttk.Spinbox(parent, from_=8, to=72, textvariable=font_size_var,
                                       command=lambda: self._update_font_size(font_size_var.get()))
        font_size_spinbox.grid(row=2, column=1, sticky=tk.EW, padx=5)

        # 원문 폰트 크기
        ttk.Label(parent, text="원문 폰트 크기:").grid(row=3, column=0, sticky=tk.W, pady=5)
        orig_font_size_var = tk.IntVar(value=self.config.original_font_size)
        orig_font_size_spinbox = ttk.Spinbox(parent, from_=8, to=72, textvariable=orig_font_size_var,
                                            command=lambda: self._update_original_font_size(orig_font_size_var.get()))
        orig_font_size_spinbox.grid(row=3, column=1, sticky=tk.EW, padx=5)

    def _create_behavior_settings(self, parent):
        """동작 설정 UI"""
        # 원문 표시 토글
        show_original_var = tk.BooleanVar(value=self.config.show_original)
        ttk.Checkbutton(parent, text="원문 표시", variable=show_original_var,
                       command=lambda: self._toggle_original_display(show_original_var.get())).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 가사 스타일 토글
        lyrics_style_var = tk.BooleanVar(value=self.config.lyrics_style)
        ttk.Checkbutton(parent, text="가사 스타일 (위로 스크롤)", variable=lyrics_style_var,
                       command=lambda: self._toggle_lyrics_style(lyrics_style_var.get())).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 자동 숨김 활성화
        auto_hide_enabled_var = tk.BooleanVar(value=self.config.auto_hide_enabled)
        ttk.Checkbutton(parent, text="자동 숨김 활성화", variable=auto_hide_enabled_var,
                       command=lambda: self._toggle_auto_hide(auto_hide_enabled_var.get())).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 자동 숨김 시간
        ttk.Label(parent, text="자동 숨김 시간 (초):").grid(row=3, column=0, sticky=tk.W, pady=5)
        hide_delay_var = tk.DoubleVar(value=self.config.auto_hide_delay)
        hide_delay_scale = ttk.Scale(parent, from_=3.0, to=20.0, variable=hide_delay_var,
                                    command=lambda v: self._update_hide_delay(float(v)))
        hide_delay_scale.grid(row=3, column=1, columnspan=2, sticky=tk.EW, padx=5)

        # 이력 줄 수 (가사 스타일용)
        ttk.Label(parent, text="이력 표시 줄 수:").grid(row=4, column=0, sticky=tk.W, pady=5)
        history_lines_var = tk.IntVar(value=self.config.max_history_lines)
        history_lines_spinbox = ttk.Spinbox(parent, from_=1, to=10, textvariable=history_lines_var,
                                           command=lambda: self._update_history_lines(history_lines_var.get()))
        history_lines_spinbox.grid(row=4, column=1, sticky=tk.EW, padx=5)

    def _create_size_settings(self, parent):
        """크기 설정 UI"""
        # 윈도우 너비
        ttk.Label(parent, text="오버레이 너비:").grid(row=0, column=0, sticky=tk.W, pady=5)
        width_var = tk.IntVar(value=self.config.window_width)
        width_scale = ttk.Scale(parent, from_=400, to=1200, variable=width_var,
                               command=lambda v: self._update_window_width(int(float(v))))
        width_scale.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5)

        # 윈도우 높이
        ttk.Label(parent, text="오버레이 높이:").grid(row=1, column=0, sticky=tk.W, pady=5)
        height_var = tk.IntVar(value=self.config.window_height)
        height_scale = ttk.Scale(parent, from_=100, to=600, variable=height_var,
                                command=lambda v: self._update_window_height(int(float(v))))
        height_scale.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=5)
        
        # 버튼 프레임
        button_frame = ttk.Frame(self.settings_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="저장", command=self._save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="닫기", command=lambda: self.settings_window.destroy()).pack(side=tk.RIGHT, padx=5)

    def _create_window_settings(self, parent):
        """윈도우 설정 UI"""
        # 크기 조절 가능 토글
        resizable_var = tk.BooleanVar(value=self.config.resizable)
        ttk.Checkbutton(parent, text="창 테두리로 크기 조절 가능", variable=resizable_var,
                       command=lambda: self._toggle_resizable(resizable_var.get())).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 클릭 투과 토글
        click_through_var = tk.BooleanVar(value=self.config.click_through)
        ttk.Checkbutton(parent, text="클릭 투과 모드", variable=click_through_var,
                       command=lambda: self._toggle_click_through(click_through_var.get())).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 항상 최상위 토글
        always_on_top_var = tk.BooleanVar(value=self.config.always_on_top)
        ttk.Checkbutton(parent, text="항상 최상위 표시", variable=always_on_top_var,
                       command=lambda: self._toggle_always_on_top(always_on_top_var.get())).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
    
    def _update_alpha(self, value: float):
        """창 투명도 실시간 업데이트"""
        self.config.alpha = value
        if self.root:
            self.root.wm_attributes('-alpha', value)

    def _update_subtitle_alpha(self, value: float):
        """자막 투명도 실시간 업데이트"""
        self.config.subtitle_alpha = value
        # 모든 텍스트 라벨의 색상 업데이트
        self._apply_subtitle_alpha()
    
    def _update_font_size(self, size: int):
        """폰트 크기 실시간 업데이트"""
        self.config.translated_font_size = size
        if self.translated_label:
            current_font = self.translated_label.cget("font")
            new_font = font.Font(font=current_font)
            new_font.config(size=size)
            self.translated_label.config(font=new_font)

    def _update_original_font_size(self, size: int):
        """원문 폰트 크기 실시간 업데이트"""
        self.config.original_font_size = size
        if self.original_label:
            current_font = self.original_label.cget("font")
            new_font = font.Font(font=current_font)
            new_font.config(size=size)
            self.original_label.config(font=new_font)

    def _toggle_original_display(self, show: bool):
        """원문 표시 토글"""
        self.config.show_original = show
        if self.original_label:
            if show:
                self.original_label.pack()
            else:
                self.original_label.pack_forget()

    def _toggle_lyrics_style(self, enable: bool):
        """가사 스타일 토글 (재시작 필요)"""
        self.config.lyrics_style = enable
        # 설정 저장하고 재시작 안내
        self.config.save()
        if hasattr(self, 'settings_window') and self.settings_window:
            tk.messagebox.showinfo("알림", "가사 스타일 변경은 오버레이를 재시작한 후 적용됩니다.")

    def _toggle_auto_hide(self, enabled: bool):
        """자동 숨김 기능 토글"""
        self.config.auto_hide_enabled = enabled
        if not enabled and self.hide_timer:
            self.hide_timer.cancel()

    def _update_hide_delay(self, delay: float):
        """자동 숨김 시간 업데이트"""
        self.config.auto_hide_delay = delay

    def _update_history_lines(self, lines: int):
        """이력 줄 수 업데이트"""
        self.config.max_history_lines = lines
        # 현재 이력이 새 제한을 초과하면 줄임
        while len(self.translation_history) > lines:
            self.translation_history.pop(0)
        self._update_history_labels()

    def _update_window_width(self, width: int):
        """오버레이 너비 실시간 업데이트"""
        self.config.window_width = width
        if self.root:
            current_geometry = self.root.geometry()
            parts = current_geometry.split('+')
            height = parts[0].split('x')[1]
            x, y = parts[1], parts[2]
            self.root.geometry(f"{width}x{height}+{x}+{y}")

            # 텍스트 wraplength도 업데이트
            wrap_length = width - 40  # 여유 공간 증가
            if self.original_label:
                self.original_label.config(wraplength=wrap_length)
            if self.translated_label:
                self.translated_label.config(wraplength=wrap_length)

            # Canvas 윈도우 위치도 업데이트 (가사 스타일인 경우)
            if self.config.lyrics_style and hasattr(self, 'canvas'):
                self.canvas.coords(self.canvas_window, width // 2, 0)

    def _update_window_height(self, height: int):
        """오버레이 높이 실시간 업데이트"""
        self.config.window_height = height
        if self.root:
            current_geometry = self.root.geometry()
            parts = current_geometry.split('+')
            width = parts[0].split('x')[0]
            x, y = parts[1], parts[2]
            self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _update_history_labels(self):
        """가사 스타일을 위한 이력 라벨 업데이트"""
        if not self.config.lyrics_style or not hasattr(self, 'history_frame'):
            return

        # 기존 이력 라벨들 제거
        for label in self.history_labels:
            label.destroy()
        self.history_labels.clear()

        # 새 이력 라벨들 생성 (오래된 것부터 위에, 투명도 점진적 감소)
        for i, (orig, trans) in enumerate(self.translation_history):
            # 투명도 계산 (오래된 것일수록 투명)
            alpha_factor = (i + 1) / len(self.translation_history)
            alpha_color = self._blend_color_alpha(self.config.translated_text_color, alpha_factor * 0.7 * self.config.subtitle_alpha)

            # 이력 번역문 라벨
            history_label = tk.Label(
                self.history_frame,
                text=trans,
                font=(self.config.font_family, max(8, self.config.translated_font_size - 4)),
                fg=alpha_color,
                bg=self.config.bg_color,
                justify=tk.CENTER,
                wraplength=self.config.window_width - 40,
                anchor=tk.CENTER
            )
            history_label.pack(side=tk.TOP, pady=1, fill=tk.X)
            self.history_labels.append(history_label)

            # 원문도 표시하는 경우
            if self.config.show_original and orig:
                orig_alpha_color = self._blend_color_alpha(self.config.original_text_color, alpha_factor * 0.5 * self.config.subtitle_alpha)
                orig_history_label = tk.Label(
                    self.history_frame,
                    text=orig,
                    font=(self.config.font_family, max(6, self.config.original_font_size - 6)),
                    fg=orig_alpha_color,
                    bg=self.config.bg_color,
                    justify=tk.CENTER,
                    wraplength=self.config.window_width - 40,
                    anchor=tk.CENTER
                )
                orig_history_label.pack(side=tk.TOP, pady=(0, 3), fill=tk.X)
                self.history_labels.append(orig_history_label)

    def _blend_color_alpha(self, color: str, alpha: float) -> str:
        """색상에 투명도 적용 (어두운 배경 기준)"""
        if color.startswith('#'):
            # RGB 값 추출
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            # 알파 적용 (검은 배경과 블렌딩)
            r = int(r * alpha)
            g = int(g * alpha)
            b = int(b * alpha)

            return f"#{r:02x}{g:02x}{b:02x}"
        return color

    def _apply_subtitle_alpha(self):
        """모든 자막 요소에 투명도 적용"""
        # 현재 라벨들에 자막 투명도 적용
        if self.original_label:
            original_color = self._blend_color_alpha(self.config.original_text_color, self.config.subtitle_alpha)
            self.original_label.config(fg=original_color)

        if self.translated_label:
            translated_color = self._blend_color_alpha(self.config.translated_text_color, self.config.subtitle_alpha)
            self.translated_label.config(fg=translated_color)

        # 히스토리 라벨들도 업데이트 (가사 스타일인 경우)
        if hasattr(self, 'history_labels'):
            for i, label in enumerate(self.history_labels):
                if i % 2 == 0:  # 번역문 라벨
                    color = self._blend_color_alpha(self.config.translated_text_color,
                                                  self.config.subtitle_alpha * 0.7 * ((i//2 + 1) / max(1, len(self.history_labels)//2)))
                else:  # 원문 라벨
                    color = self._blend_color_alpha(self.config.original_text_color,
                                                  self.config.subtitle_alpha * 0.5 * ((i//2 + 1) / max(1, len(self.history_labels)//2)))
                label.config(fg=color)

    def _toggle_resizable(self, enabled: bool):
        """크기 조절 가능 토글 (재시작 필요)"""
        self.config.resizable = enabled
        self.config.save()
        if hasattr(self, 'settings_window') and self.settings_window:
            tk.messagebox.showinfo("알림", "윈도우 테두리 변경은 오버레이를 재시작한 후 적용됩니다.")

    def _toggle_click_through(self, enabled: bool):
        """클릭 투과 모드 토글 (재시작 필요)"""
        self.config.click_through = enabled
        self.config.save()
        if hasattr(self, 'settings_window') and self.settings_window:
            tk.messagebox.showinfo("알림", "클릭 투과 모드 변경은 오버레이를 재시작한 후 적용됩니다.")

    def _toggle_always_on_top(self, enabled: bool):
        """항상 최상위 토글"""
        self.config.always_on_top = enabled
        if self.root:
            self.root.wm_attributes('-topmost', enabled)

    def _save_settings(self):
        """설정 저장"""
        self.config.save()
        if self.settings_window:
            self.settings_window.destroy()
    
    def update_subtitle(self, original_text: str, translated_text: str):
        """자막 업데이트 (외부 호출용)"""
        self.update_queue.put({
            'type': 'subtitle',
            'original': original_text,
            'translated': translated_text
        })
    
    def show(self):
        """오버레이 표시"""
        self.update_queue.put({'type': 'show'})
    
    def hide(self):
        """오버레이 숨김"""
        self.update_queue.put({'type': 'hide'})
    
    def run(self):
        """UI 메인 루프 시작"""
        self.create_ui()
        
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.close()
    
    def close(self):
        """오버레이 종료"""
        if self.hide_timer:
            self.hide_timer.cancel()
        
        if self.root:
            self.root.quit()
            self.root.destroy()
        
        self.config.save()

# 테스트 코드
if __name__ == "__main__":
    def test_overlay():
        overlay = TransparentOverlay()
        
        # 테스트용 자막 업데이트
        def update_test_subtitles():
            test_data = [
                ("Hello, how are you?", "안녕하세요, 어떻게 지내세요?"),
                ("This is a test.", "이것은 테스트입니다."),
                ("Real-time translation works!", "실시간 번역이 작동합니다!"),
                ("Press F1 for settings.", "F1을 눌러 설정을 열어보세요."),
                ("Press Escape to exit.", "ESC를 눌러 종료하세요.")
            ]
            
            def update_loop(index=0):
                if index < len(test_data):
                    original, translated = test_data[index]
                    overlay.update_subtitle(original, translated)
                    
                    # 다음 업데이트 스케줄
                    if overlay.root:
                        overlay.root.after(4000, lambda: update_loop(index + 1))
            
            # 3초 후 시작
            if overlay.root:
                overlay.root.after(3000, update_loop)
        
        # 테스트 스레드 시작
        import threading
        threading.Thread(target=update_test_subtitles, daemon=True).start()
        
        # UI 실행
        overlay.run()
    
    print("Testing overlay UI...")
    print("Controls:")
    print("- F1: Show settings")
    print("- ESC: Close")
    print("- Drag to move")
    
    test_overlay()