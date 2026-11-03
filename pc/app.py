"""Explicit-action Tk UI. Run with python app.py (Python with tkinter required)."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from decoder import DecodeError, MAX_TEXT_CHARS, Transfer


class App:
    def __init__(self, root):
        self.root = root
        self.transfer = Transfer()
        root.title('Base64 Transfer — 오프라인 복원')
        root.geometry('820x540')
        ttk.Label(root, text='완전한 JSON 조각을 붙여넣고 추가하세요. 한 번에 파일 하나를 복원합니다.').pack(padx=12, pady=10)
        self.text = tk.Text(root, wrap='char', undo=False)
        self.text.pack(fill='both', expand=True, padx=12)
        self.text.bind('<<Paste>>', self.paste)
        self.text.bind('<<PasteSelection>>', self.paste)
        self.text.bind('<<Modified>>', self.limit_text)
        controls = ttk.Frame(root)
        controls.pack(pady=10)
        for label, command in [('클립보드 붙여넣기', self.paste), ('조각 추가', self.add), ('초기화', self.clear), ('저장…', self.save)]:
            ttk.Button(controls, text=label, command=command).pack(side='left', padx=4)
        self.status = tk.StringVar(value=self.transfer.status)
        ttk.Label(root, textvariable=self.status, wraplength=780).pack(padx=12, pady=(0, 12))

    def limit_text(self, event=None):
        if self.text.edit_modified():
            # Also bounds keyboard input and platform-specific insertion paths.
            self.text.delete(f'1.0+{MAX_TEXT_CHARS}c', 'end-1c')
            self.text.edit_modified(False)

    def paste(self, event=None):
        try:
            value = self.root.clipboard_get()
            count = self.text.count('1.0', 'end-1c', 'chars')
            current = count[0] if count else 0
            if len(value) + current > MAX_TEXT_CHARS:
                raise DecodeError('Input limit exceeded. Add or clear the existing text first.')
            self.text.insert('insert', value)
        except (tk.TclError, DecodeError) as exc:
            messagebox.showerror('붙여넣기 실패', str(exc), parent=self.root)
        return 'break'

    def add(self):
        try:
            added = self.transfer.add(self.text.get('1.0', 'end-1c'))
            self.text.delete('1.0', 'end')
            self.status.set(f'새 조각 {added}개 추가. ' + self.transfer.status)
        except DecodeError as exc:
            messagebox.showerror('추가 실패', str(exc), parent=self.root)

    def clear(self):
        self.transfer.clear()
        self.text.delete('1.0', 'end')
        self.status.set(self.transfer.status)

    def save(self):
        try:
            raw = self.transfer.assemble()  # Validate before opening any save dialog.
        except DecodeError as exc:
            messagebox.showerror('저장 불가', str(exc), parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title='검증된 파일을 새 이름으로 저장', initialfile=self.transfer.filename)
        if not path:
            return
        try:
            # Exclusive creation prevents overwrites, including a race after the dialog.
            with open(path, 'xb') as destination:
                destination.write(raw)
        except OSError as exc:
            messagebox.showerror('저장 실패', '새 파일 이름을 선택하세요. 기존 파일은 덮어쓰지 않습니다.\n'
                                 '쓰기 실패 시 불완전한 새 파일이 남을 수 있습니다.\n' + str(exc), parent=self.root)
            return
        self.status.set('검증된 파일 저장 완료: ' + path)


if __name__ == '__main__':
    import sys
    root = tk.Tk()
    application = App(root)
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test-report':
        # Exercises bundled Tk and the real decoder in the packaged executable.
        import hashlib
        import json
        from pathlib import Path
        root.withdraw()
        digest = hashlib.sha256(b'').hexdigest()
        application.transfer.add(json.dumps(dict(format='base64-transfer-v1',
            id=digest, name='empty.bin', size=0, sha256=digest, part=1, parts=1, data='')))
        assert application.transfer.assemble() == b''
        root.update()
        root.destroy()
        Path(sys.argv[2]).write_text('PASS: bundled Tk UI and decoder\n', encoding='utf-8')
    else:
        root.mainloop()
