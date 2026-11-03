# Base64 Transfer

안드로이드 파일을 Base64 텍스트로 전달하고 PC에서 원본 파일로 복원합니다.

## 다운로드

- [안드로이드 테스트 APK 다운로드](dist/base64-transfer-debug.apk?raw=true)
- [Windows 복원 EXE 다운로드](dist/Base64Restore.exe?raw=true)
- [PC 복원 프로그램 포함 ZIP 다운로드](dist/base64-transfer.zip?raw=true)

APK는 Android 8.0 이상용 테스트 서명 버전입니다. Gmail 작성 화면에서 사용자가 직접 전송합니다.

## 사용 방법

1. 안드로이드 앱에서 1MiB 미만 파일을 선택합니다.
2. 현재 조각을 **Gmail로 작성** 또는 **클립보드 복사**합니다.
3. 100KiB를 넘는 파일은 다음 조각도 전달합니다.
4. PC 프로그램에서 각 JSON 본문을 붙여 넣고 **조각 추가**를 누릅니다.
5. 모든 조각의 크기와 SHA-256 검증이 완료되면 **저장**합니다.

클립보드는 PC로 자동 전송되지 않습니다. Base64는 암호화가 아닙니다.
조각 크기는 앱의 설계 기준이며 모든 기기의 전달 성공을 보장하지 않습니다.

PC EXE 실행: `Base64Restore.exe`를 실행합니다. Python을 별도 설치할 필요가 없습니다.
PC 소스 실행: Python 3.9 이상과 Tk 설치 후 `pc/launch.cmd`를 실행합니다.
Windows EXE 빌드: PyInstaller가 설치된 Windows에서 `python pc/build_windows.py`를 실행합니다.

자세한 설명: [시작 안내](START-HERE.txt), [Android](android/README.txt), [PC](pc/README.txt).

## 검증

```sh
python3 -m unittest discover -s pc -v
```

Android 빌드 및 프로토콜 테스트는 `android/README.txt`를 참고하세요.
실제 휴대폰의 Gmail과 클립보드 연동은 기기별 확인이 필요합니다.
