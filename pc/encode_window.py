"""Explicit file-to-text workflow; full payload never rendered by Tk."""
import json
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox
from encoder import encode_file
from clipboard_io import read_text, write_text, ClipboardError


class EncoderWindow:
    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.title('Text Transfer · 파일 → 텍스트')
        self.window.geometry('780x540')
        self.window.minsize(680, 480)
        self.window.configure(bg='#0b1018')
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.closed = self.busy = False
        self.payload = ''
        self.filename = 'transfer'
        self.future = self.poll_id = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='encode')
        panel = tk.Frame(self.window, bg='#121b27')
        panel.pack(fill='both', expand=True, padx=24, pady=24)
        app.label(panel, '파일에서, 전송용 텍스트로.', size=23, bold=True).pack(anchor='w', padx=20, pady=(20, 10))
        app.label(panel, '1 MiB 미만 · 무손실 압축 · 원본 파일은 그대로 유지됩니다.', color='#8c9bb0').pack(anchor='w', padx=20)
        self.pick = app.button(panel, '파일 선택하기', self.choose, primary=True)
        self.pick.pack(anchor='w', padx=20, pady=16)
        self.info = app.label(panel, '파일을 선택하면 전송용 본문을 만듭니다.', color='#8c9bb0')
        self.info.configure(wraplength=690)
        self.info.pack(anchor='w', padx=20, pady=(0, 12))
        self.preview = tk.Text(panel, height=6, width=30, wrap='none', state='disabled',
                               bg='#0d1520', fg='#bccddd', font=('Consolas', 10), relief='flat', padx=12, pady=12)
        self.preview.pack(fill='both', expand=True, padx=20)
        # Text's native copy would export only the shortened/wrapped preview.
        self.preview.bind('<<Copy>>', self.copy_payload)
        self.preview.bind('<Control-c>', self.copy_payload)
        self.preview.bind('<Control-C>', self.copy_payload)
        self.preview.bind('<Control-Insert>', self.copy_payload)
        actions = tk.Frame(panel, bg='#121b27')
        actions.pack(fill='x', padx=20, pady=16)
        self.copy_button = app.button(actions, '전체 텍스트 복사', self.copy_payload, primary=True)
        self.copy_button.pack(side='left')
        self.save_button = app.button(actions, '텍스트 파일 저장', self.save_payload)
        self.save_button.pack(side='right')
        self.status = tk.StringVar(value='한자·한글 모양의 본문이 만들어집니다. PC 복원 1.4 이상에서 읽을 수 있어요.')
        tk.Label(panel, textvariable=self.status, bg='#121b27', fg='#8c9bb0',
                 font=('맑은 고딕', 10), wraplength=690, justify='left').pack(anchor='w', padx=20, pady=(0, 18))
        self.controls()

    def controls(self):
        self.pick.configure(state='disabled' if self.busy else 'normal')
        state = 'normal' if self.payload and not self.busy else 'disabled'
        self.copy_button.configure(state=state)
        self.save_button.configure(state=state)

    def choose(self):
        if self.closed or self.busy:
            return
        path = filedialog.askopenfilename(parent=self.window, title='텍스트로 변환할 파일 선택')
        if path:
            self.start(path)

    def start(self, path):
        if self.closed or self.busy:
            return
        # Clear stale output before a new operation, including failures.
        self.payload = ''
        self.draw_preview('')
        self.busy = True
        self.controls()
        self.info.configure(text='파일을 읽고 압축·변환하는 중…')
        self.status.set('변환은 별도 작업으로 처리하고 있어요.')
        self.filename = Path(path).name
        try:
            self.future = self.executor.submit(encode_file, path)
            self.poll_id = self.window.after(20, self.poll)
        except Exception as exc:
            self.busy = False
            self.controls()
            self.fail(exc)

    def poll(self):
        self.poll_id = None
        if self.closed:
            return
        if not self.future.done():
            self.poll_id = self.window.after(20, self.poll)
            return
        self.busy = False
        try:
            self.payload = self.future.result()
            obj = json.loads(self.payload)
            self.draw_preview(self.payload)
            original = obj['size']
            packed = obj.get('packedSize', original)
            reduction = f'{100 * (original-packed) / original:.1f}%' if original else '0.0%'
            self.info.configure(text=f"{obj['name']}\n원본 {original:,} → {packed:,} 바이트 · {reduction} 감소 · 본문 {len(self.payload):,}자")
            self.status.set('변환 완료 · 전체 텍스트를 복사하거나 UTF-8 파일로 저장하세요. 암호화는 아닙니다.')
        except Exception as exc:
            self.payload = ''
            self.fail(exc)
        finally:
            self.future = None
            self.controls()

    def draw_preview(self, text):
        sample = text[:256]
        preview = '\n'.join(sample[i:i+64] for i in range(0, len(sample), 64))
        if len(text) > 256:
            preview += '\n… 앞부분 미리보기 · 복사/저장은 전체 본문입니다.'
        self.preview.configure(state='normal')
        self.preview.delete('1.0', 'end')
        self.preview.insert('1.0', preview)
        self.preview.configure(state='disabled')

    def fail(self, exc):
        self.info.configure(text='변환하지 못했어요. 1 MiB 미만의 읽을 수 있는 파일을 선택해주세요.')
        self.status.set('이전 변환 결과는 비웠습니다. 파일을 다시 선택해주세요.')
        messagebox.showerror('변환 실패', str(exc), parent=self.window)

    def copy_payload(self, event=None):
        if self.closed or self.busy or not self.payload:
            return 'break'
        try:
            write_text(self.window, self.payload)
            if read_text(self.window) != self.payload:
                raise tk.TclError('클립보드의 전체 본문이 일치하지 않습니다. 텍스트 파일 저장을 이용해주세요.')
            self.status.set('전체 텍스트 복사를 확인했어요. 원하는 곳에 붙여넣은 뒤 프로그램을 닫아주세요.')
        except (tk.TclError, ClipboardError) as exc:
            messagebox.showerror('복사 실패', str(exc), parent=self.window)
        return 'break'

    def save_payload(self):
        if self.closed or self.busy or not self.payload:
            return
        path = filedialog.asksaveasfilename(parent=self.window, title='전송용 텍스트 저장',
            initialfile=self.filename + '.transfer.txt', defaultextension='.txt', filetypes=[('텍스트 파일', '*.txt')])
        if not path:
            return
        try:
            with open(path, 'x', encoding='utf-8', newline='') as output:
                output.write(self.payload)
            self.status.set('전체 텍스트 저장 완료 · ' + path)
        except OSError as exc:
            messagebox.showerror('저장 실패', '기존 파일은 덮어쓰지 않습니다. 다른 이름을 선택해주세요.\n' + str(exc), parent=self.window)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.poll_id is not None:
            self.window.after_cancel(self.poll_id)
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.window.destroy()
