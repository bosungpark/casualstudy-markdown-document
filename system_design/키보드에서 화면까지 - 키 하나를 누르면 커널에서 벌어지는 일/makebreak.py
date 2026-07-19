#!/usr/bin/env python3
"""
§3 실증: make/break가 분리돼 있어서 조합키(모디파이어)가 성립한다.

키를 누를 때(press = make)와 뗄 때(release = break)가 따로 이벤트로 온다.
'Shift 누른 채로 A' 를 쳐보면 순서가 이렇게 찍힌다:
    press   Key.shift
    press   'a'
    release 'a'
    release Key.shift
Shift의 press와 release '사이'에 A가 들어오는 것 —
이게 바로 "Shift+A = 'A'"가 가능한 물리적 근거다.

※ macOS: 첫 실행 시 '입력 모니터링' 권한을 요구한다.
   시스템 설정 > 개인정보 보호 및 보안 > 입력 모니터링 에서 터미널(또는 iTerm)을 허용.
   ESC 를 누르면 종료.
"""
try:
    from pynput import keyboard
except ImportError:
    raise SystemExit("pynput이 없어요.  python3 -m pip install pynput  먼저 실행하세요.")


def fmt(key):
    try:
        return repr(key.char)      # 일반 문자 키
    except AttributeError:
        return str(key)            # Shift, Ctrl 등 특수키


def on_press(key):
    print(f"  press   {fmt(key)}      (make)")


def on_release(key):
    print(f"  release {fmt(key)}      (break)")
    if key == keyboard.Key.esc:
        print("\n종료합니다.")
        return False  # 리스너 중단


print("키를 눌러보세요.  'Shift 누른 채로 A' 를 쳐보면 make/break 분리가 보여요.")
print("(ESC = 종료)\n")
with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
    l.join()
