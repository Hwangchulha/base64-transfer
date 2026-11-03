"""Offline Base64 receiver: dark desktop interface, explicit clipboard actions."""
import tkinter as tk
import copy
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, messagebox, ttk
from decoder import DecodeError, MAX_TEXT_CHARS, Transfer

BG = '#0b1018'
PANEL = '#121b27'
INPUT = '#0d1520'
LINE = '#263344'
FG = '#edf3fa'
MUTED = '#8c9bb0'
ACCENT = '#64e4ce'
FONT = '맑은 고딕'


class App:
    def __init__(self, root):
        self.root, self.transfer = root, Transfer()
        self.input_text = ''
        self.busy = False
        self.closed = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='decode')
        self.future = None
        self.poll_id = None
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.title('Base64 Restore')
        root.geometry('1040x720')
        root.minsize(900, 650)
        root.configure(bg=BG)
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
            dark = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), 4)
        except (AttributeError, OSError):
            pass
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('Transfer.Horizontal.TProgressbar', troughcolor=LINE, background=ACCENT,
                        bordercolor=LINE, lightcolor=ACCENT, darkcolor=ACCENT)
        shell = tk.Frame(root, bg=BG)
        shell.pack(fill='both', expand=True, padx=32, pady=24)
        header = tk.Frame(shell, bg=BG)
        header.pack(fill='x')
        self.label(header, 'B64 / RESTORE', size=12, color=ACCENT, bold=True, bg=BG).pack(side='left')
        self.label(header, '●  OFFLINE', size=10, color=ACCENT, bg=BG).pack(side='right')
        self.label(shell, '텍스트에서, 원본으로.', size=27, bold=True, bg=BG).pack(anchor='w', pady=(18, 6))
        self.label(shell, '메일 본문을 한 번 붙여넣으면, 원본 파일로 돌아옵니다. 복원은 이 PC 안에서 처리돼요.',
                   size=11, color=MUTED, bg=BG).pack(anchor='w')
        body = tk.Frame(shell, bg=BG)
        body.pack(fill='both', expand=True, pady=(24, 18))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, minsize=290)
        body.rowconfigure(0, weight=1)
        editor = tk.Frame(body, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        editor.grid(row=0, column=0, sticky='nsew', padx=(0, 18))
        top = tk.Frame(editor, bg=PANEL)
        top.pack(fill='x', padx=20, pady=(18, 12))
        self.label(top, '01  텍스트 가져오기', size=12, bold=True).pack(side='left')
        self.count = self.label(top, '0 자', size=10, color=MUTED)
        self.count.pack(side='right')
        wrap = tk.Frame(editor, bg=INPUT)
        wrap.pack(fill='both', expand=True, padx=20)
        self.text = tk.Text(wrap, bg=INPUT, fg='#bccddd', insertbackground=ACCENT,
                            selectbackground='#245b60', selectforeground=FG,
                            relief='flat', bd=0, padx=14, pady=14, font=('Consolas', 10),
                            wrap='none', undo=False, width=30, height=8, highlightthickness=0, state='disabled')
        self.text.pack(side='left', fill='both', expand=True)
        scroll = tk.Scrollbar(wrap, command=self.text.yview, bg=LINE, troughcolor=INPUT,
                              activebackground=MUTED, relief='flat', bd=0, width=10)
        scroll.pack(side='right', fill='y')
        self.text.configure(yscrollcommand=scroll.set)
        self.placeholder = tk.Label(wrap, text='여기에 받은 텍스트를 붙여넣으세요\n\n메일 본문의 { } 전체를 복사하면 됩니다.',
                                    bg=INPUT, fg=MUTED, font=(FONT, 11), justify='center', cursor='xterm')
        self.placeholder.place(relx=.5, rely=.43, anchor='center')
        self.placeholder.bind('<Button-1>', lambda e: self.text.focus_set())
        self.text.bind('<<Paste>>', self.paste)
        self.text.bind('<<PasteSelection>>', self.paste)
        root.bind('<Control-v>', self.paste)
        root.bind('<Control-V>', self.paste)
        self.text.bind('<Control-Return>', lambda e: self.add())
        controls = tk.Frame(editor, bg=PANEL)
        controls.pack(fill='x', padx=20, pady=16)
        self.paste_button = self.button(controls, '클립보드 붙여넣기', self.paste)
        self.paste_button.pack(side='left')
        self.add_button = self.button(controls, '텍스트 확인  →', self.add, primary=True)
        self.add_button.pack(side='right')
        side = tk.Frame(body, bg=PANEL, highlightbackground=LINE, highlightthickness=1, width=290)
        side.grid(row=0, column=1, sticky='nsew')
        side.grid_propagate(False)
        inner = tk.Frame(side, bg=PANEL)
        inner.pack(fill='both', expand=True, padx=22, pady=20)
        self.label(inner, '02  파일 복원', size=12, bold=True).pack(anchor='w')
        self.stage = self.label(inner, '수신 대기', size=10, color=ACCENT)
        self.stage.pack(anchor='w', pady=(24, 8))
        self.file_label = self.label(inner, '아직 받은 파일이 없어요', size=15, bold=True)
        self.file_label.configure(wraplength=240)
        self.file_label.pack(anchor='w')
        self.detail = self.label(inner, '본문을 붙여넣고 확인을 눌러주세요.', size=10, color=MUTED)
        self.detail.pack(anchor='w', pady=(8, 28))
        self.progress_label = self.label(inner, 'READY', size=20, bold=True)
        self.progress_label.pack(anchor='w')
        self.progress = ttk.Progressbar(inner, style='Transfer.Horizontal.TProgressbar', maximum=100)
        self.progress.pack(fill='x', pady=(12, 14))
        self.missing = self.label(inner, '원본과 같은 파일인지 확인한 뒤\n안전하게 저장합니다.', size=10, color=MUTED)
        self.missing.configure(wraplength=240)
        self.missing.pack(anchor='w')
        self.save_button = self.button(inner, '원본 파일 저장  ↓', self.save, primary=True)
        self.save_button.pack(side='bottom', fill='x')
        self.save_button.configure(state='disabled')
        footer = tk.Frame(shell, bg=BG)
        footer.pack(fill='x')
        self.status = tk.StringVar(value='준비 완료 · 받은 텍스트를 붙여넣어 주세요.')
        tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED, font=(FONT, 10),
                 anchor='w', justify='left', wraplength=730).pack(side='left')
        self.clear_button = self.button(footer, '새 파일 시작', self.clear)
        self.clear_button.pack(side='right')

    def label(self, parent, text, size=11, color=FG, bold=False, bg=PANEL):
        return tk.Label(parent, text=text, bg=bg, fg=color, anchor='w', justify='left',
                        font=(FONT, size, 'bold' if bold else 'normal'))

    def button(self, parent, text, command, primary=False):
        bg, fg = (ACCENT, BG) if primary else ('#233144', FG)
        button = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                           activebackground='#91f0df' if primary else '#344960', activeforeground=fg,
                           disabledforeground='#607584', relief='flat', bd=0, padx=16, pady=11,
                           font=(FONT, 10, 'bold'), cursor='hand2', highlightthickness=1,
                           highlightbackground=LINE, highlightcolor=ACCENT)
        button.bind('<Enter>', lambda e: button.configure(bg='#91f0df' if primary else '#344960') if button['state'] != 'disabled' else None)
        button.bind('<Leave>', lambda e: button.configure(bg=bg))
        return button

    def refresh(self):
        total, received = self.transfer.total_parts, self.transfer.received_parts
        ready = total > 0 and not self.transfer.missing
        self.stage.configure(text='새 본문 확인 대기' if self.input_text else '검증 완료' if ready else '수신 중' if total else '수신 대기')
        self.file_label.configure(text=self.transfer.filename if total else '아직 받은 파일이 없어요')
        self.detail.configure(text=f'{self.transfer.file_size:,} 바이트 · 원본 크기' if total else '본문을 붙여넣고 확인을 눌러주세요.')
        self.progress_label.configure(text='100%' if ready else f'{received} / {total} 조각' if total else 'READY')
        self.progress['value'] = received / total * 100 if total else 0
        self.missing.configure(text='가져온 본문의 확인이 필요해요.\n텍스트 확인 버튼을 눌러주세요.' if self.input_text else
                               '원본 일치 확인 완료.\n이제 파일을 저장할 수 있어요.' if ready else
                               '필요한 조각: ' + ', '.join(map(str, self.transfer.missing)) if total else
                               '원본과 같은 파일인지 확인한 뒤\n안전하게 저장합니다.', fg=ACCENT if ready else MUTED)
        self.save_button.configure(state='normal' if ready and not self.busy and not self.input_text else 'disabled')

    def set_input(self, value):
        """Keep complete input out of Tk: only a bounded, short-line preview is drawn."""
        if self.busy or self.closed:
            return
        if not isinstance(value, str) or len(value) > MAX_TEXT_CHARS:
            raise DecodeError('본문이 너무 큽니다. 2,097,152자 이하의 텍스트를 가져와 주세요.')
        self.input_text = value
        sample = value[:4096]
        # Hard-wrap the preview so even an unbroken Base64 string is cheap to draw.
        lines = []
        for line in sample.splitlines():
            lines.extend(line[i:i + 72] for i in range(0, len(line), 72))
        preview = '\n'.join(lines)
        if len(value) > 4096:
            preview += '\n\n… 미리보기만 줄였습니다. 원본 본문은 모두 보관하고 있어요.'
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', preview)
        self.text.configure(state='disabled')
        self.count.configure(text=f'{len(value):,} 자 · 전체 보관' if value else '0 자')
        if value:
            self.placeholder.place_forget()
            self.status.set('본문을 가져왔어요. 텍스트 확인을 누르면 전체 내용을 검증합니다.')
        else:
            self.placeholder.place(relx=.5, rely=.43, anchor='center')
        self.refresh()

    def paste(self, event=None):
        if self.busy or self.closed:
            return 'break'
        try:
            self.set_input(self.root.clipboard_get())
            self.text.focus_set()
        except (tk.TclError, DecodeError) as exc:
            messagebox.showerror('붙여넣기 실패', str(exc), parent=self.root)
        return 'break'

    @staticmethod
    def decode_input(candidate, value):
        candidate.add(value)
        return candidate

    def add(self):
        if self.busy or self.closed:
            return
        if not self.input_text.strip():
            self.status.set('먼저 메일 본문을 붙여넣어 주세요.')
            return
        self.busy = True
        for button in (self.paste_button, self.add_button, self.clear_button, self.save_button):
            button.configure(state='disabled')
        self.stage.configure(text='원본 확인 중')
        self.status.set('전체 본문을 확인하고 있어요…')
        self.progress.configure(mode='indeterminate')
        self.progress.start(15)
        # A candidate prevents a failed batch from changing the active transfer.
        try:
            self.future = self.executor.submit(self.decode_input, copy.deepcopy(self.transfer), self.input_text)
        except Exception as exc:
            self.busy = False
            self.future = None
            self.progress.stop()
            self.progress.configure(mode='determinate')
            for button in (self.paste_button, self.add_button, self.clear_button):
                button.configure(state='normal')
            self.refresh()
            self.status.set('본문 확인을 시작하지 못했어요. 입력은 그대로 보관됩니다.')
            messagebox.showerror('확인 실패', str(exc), parent=self.root)
            return
        self.poll_id = self.root.after(20, self.poll_decode)

    def poll_decode(self):
        self.poll_id = None
        if self.closed:
            return
        if not self.future.done():
            self.poll_id = self.root.after(20, self.poll_decode)
            return
        self.busy = False
        self.progress.stop()
        self.progress.configure(mode='determinate')
        for button in (self.paste_button, self.add_button, self.clear_button):
            button.configure(state='normal')
        try:
            self.transfer = self.future.result()
            self.set_input('')
            self.status.set(self.transfer.status)
        except Exception as exc:
            self.status.set('본문 확인에 실패했어요. 입력 내용은 그대로 보관됩니다.')
            messagebox.showerror('확인 실패', str(exc), parent=self.root)
        finally:
            self.future = None
            self.refresh()

    def clear(self):
        if self.busy or self.closed:
            return
        if (self.transfer.received_parts or self.input_text) and not messagebox.askyesno(
                '새 파일 시작', '현재 입력과 복원 데이터를 비우고 새 파일을 시작할까요?', parent=self.root):
            return
        self.transfer.clear()
        self.set_input('')
        self.status.set('준비 완료 · 받은 텍스트를 붙여넣어 주세요.')

    def close(self):
        self.closed = True
        if self.poll_id is not None:
            self.root.after_cancel(self.poll_id)
        self.progress.stop()
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.root.update_idletasks()
        self.root.destroy()

    def save(self):
        if self.busy or self.input_text or self.closed:
            return
        try:
            raw = self.transfer.assemble()
        except DecodeError as exc:
            messagebox.showerror('저장 불가', str(exc), parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title='원본 파일 저장', initialfile=self.transfer.filename)
        if not path: return
        try:
            with open(path, 'xb') as destination: destination.write(raw)
        except OSError as exc:
            messagebox.showerror('저장 실패', '다른 파일 이름을 선택해 주세요. 기존 파일은 덮어쓰지 않습니다.\n'
                                 '쓰기 실패 시 불완전한 새 파일이 남을 수 있습니다.\n' + str(exc), parent=self.root)
            return
        self.status.set('저장 완료 · ' + path)


if __name__ == '__main__':
    import sys
    root = tk.Tk()
    application = App(root)
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test-report':
        # Exercises bundled Tk and the real decoder in the packaged executable.
        import hashlib
        import base64
        import json
        from pathlib import Path
        root.withdraw()
        raw = bytes(range(256)) * 1400
        digest = hashlib.sha256(raw).hexdigest()
        assert str(application.save_button['state']) == 'disabled'
        application.set_input(json.dumps(dict(format='base64-transfer-v2',
            id=digest, name='한번에.bin', size=len(raw), sha256=digest, part=1, parts=1,
            data=base64.b64encode(raw).decode('ascii'))))
        assert len(application.text.get('1.0', 'end-1c')) < 5000
        application.add()
        import time
        deadline = time.monotonic() + 15
        while application.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(.005)
        assert not application.busy
        assert application.transfer.assemble() == raw
        assert str(application.save_button['state']) == 'normal'
        root.update()
        application.close()
        Path(sys.argv[2]).write_text('PASS: bundled Tk UI and decoder\n', encoding='utf-8')
    else:
        root.mainloop()
