# Base64 Transfer

안드로이드 파일을 무손실 압축 후 텍스트로 전달하고 PC에서 원본 파일로 복원합니다.

## 다운로드

- [안드로이드 테스트 APK 다운로드](https://github.com/Hwangchulha/base64-transfer/releases/latest/download/base64-transfer-debug.apk)
- [Windows 복원 EXE 다운로드](https://github.com/Hwangchulha/base64-transfer/releases/latest/download/Base64Restore.exe)
- [APK·PC 복원 프로그램 전체 ZIP 다운로드](https://github.com/Hwangchulha/base64-transfer/releases/latest/download/base64-transfer.zip)
- [릴리스 안내](https://github.com/Hwangchulha/base64-transfer/releases/latest)

APK는 Android 8.0 이상용 테스트 서명 버전입니다. Gmail 작성 화면에서 사용자가 직접 전송합니다.

## PC에서 파일을 텍스트로 만들기

PC 1.5부터 상단 **파일 → 텍스트 만들기**에서 파일을 선택하면 전송용 본문을 생성합니다.
**전체 텍스트 복사** 또는 **텍스트 파일 저장**을 선택하세요. 원본은 1MiB 미만이며,
압축해서 더 짧아질 때만 압축합니다. 본문은 PC 복원 프로그램 1.4 이상에서 읽을 수 있습니다.
화면에는 앞부분만 표시하지만 복사/저장에는 전체 내용이 포함됩니다.
1.5.2는 Windows Unicode 클립보드를 직접 사용해 같은 프로그램 안에서 복사 후 붙여넣을 때 문자가 변하는 문제를 수정했습니다.
미리보기에서 Ctrl+C를 눌러도 전체 본문이 복사되고, 복사 직후 일치 여부를 확인합니다.
복원이 완료된 뒤 새 본문을 확인하면 새 파일로 검증하며, 실패 시 이전 검증 결과를 유지합니다.
현재 Android 앱은 파일 → 텍스트 변환용이며, 역방향 파일 복원 기능은 없습니다.
이번 배포의 PC는 1.5.2, Android APK는 기존 1.4입니다.

## 사용 방법

1. 안드로이드에서 파일을 선택합니다. 분할하지 않습니다.
2. **Gmail로 작성** 또는 **텍스트 복사**를 선택합니다.
3. 작은 본문은 자동 입력됩니다. 큰 본문은 복사 후 Gmail에서 **붙여넣기 한 번**을 합니다.
4. PC에서 본문 전체를 붙여넣고 **텍스트 확인 → 원본 파일 저장**을 누릅니다.

**1.4는 먼저 무손실 압축하고, 전체 본문이 더 짧아질 때만 압축 결과를 사용합니다. APK와 EXE를 함께 업데이트하세요.**
앱에 원본 → 압축 크기와 절감률을 표시하며, 효과가 없으면 원본 방식으로 전환합니다.
본문은 한자·한글처럼 보이는 CompactText15 문자열입니다.
사진·ZIP·XLSX 등 이미 압축된 파일은 거의 줄지 않을 수 있습니다.
텍스트 주소(URI), 첨부파일, 추가 Google 계정 연결은 사용하지 않습니다.
복사 후 클립보드에서 실제 텍스트를 다시 읽어 확인합니다.

앱은 실제 전달 크기를 측정해 800KiB 기준을 넘으면 거부합니다.
**1MiB 미만의 모든 파일이 복사 가능한 것은 아닙니다.**
기기 공유 버퍼와 키보드 정책에 따라 실패할 수 있으며 휴대폰/Gmail 실기기 호환성은 아직 미검증입니다.
키보드 기록 목록의 표시 여부는 키보드 앱이 결정합니다.

원본 크기와 SHA-256을 검증하며, PC는 이전 v1/v2/v3 형식도 읽습니다.
전체 본문은 보관하고 짧은 미리보기만 그립니다. [성능 검증 기록](docs/PERFORMANCE.txt)
CompactText15는 암호화가 아닙니다. 클립보드는 PC로 자동 전송되지 않습니다.

![PC 복원 프로그램](docs/pc-preview.png)

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
