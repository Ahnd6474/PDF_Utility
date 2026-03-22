from __future__ import annotations
from zipfile import ZipFile
from pathlib import Path
import getpass

def open_hwpx_with_password(hwpx_path: str | Path, password: str | None = None) -> tuple[ZipFile, bytes | None]:
    """
    HWPX(=zip) 파일을 비밀번호로 열어 읽기 가능 여부를 검증한 뒤 ZipFile 객체를 반환.
    - password=None 이면 콘솔에서 안전 입력(getpass).
    - ZIP 레벨 암호가 아니거나 암호가 필요 없으면 password 없이도 열림.
    - 암호가 필요한데 틀리면 예외 발생.
    """
    p = Path(hwpx_path)

    if password is None:
        password = getpass.getpass("HWPX 비밀번호(없으면 Enter): ").strip() or None

    zf = ZipFile(p, "r")
    pwd_bytes = password.encode("utf-8") if password else None

    # “진짜로 열리는지” 1개 파일을 시험 읽기
    names = zf.namelist()
    if names:
        try:
            if pwd_bytes:
                zf.read(names[0], pwd=pwd_bytes)
            else:
                zf.read(names[0])  # 암호 없을 때
        except RuntimeError as e:
            zf.close()
            raise RuntimeError("암호가 필요하거나 암호가 틀렸습니다.") from e

    return zf, pwd_bytes


# 사용 예시
if __name__ == "__main__":
    zf, pwd = open_hwpx_with_password("sample.hwpx")  # 여기서 비밀번호 입력받음
    try:
        # 이제부터는 zf.read(name, pwd=pwd)로 동일 암호를 계속 사용
        print("열기 성공. 파일 수:", len(zf.namelist()))
    finally:
        zf.close()
