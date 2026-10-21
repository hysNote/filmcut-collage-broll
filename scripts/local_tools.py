"""Local tool discovery and shared manifest utilities. No remote generation calls."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

SKILL = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def find_tool(name, explicit=None):
    specified = explicit or os.environ.get('FILMCUT_' + name.upper())
    if specified:
        path = Path(specified).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f'{name} override does not exist: {path}')
        return str(path)
    found = shutil.which(name)
    if found:
        return found
    roots = list(dict.fromkeys([Path.cwd(), *Path.cwd().parents, SKILL, *SKILL.parents]))
    if name in ('ffmpeg', 'ffprobe'):
        for root in roots:
            for pattern in (f'.runtime/media-tools/stable/*/bin/{name}.exe', f'.runtime/media-tools/*/bin/{name}.exe', f'.runtime/bin/{name}.exe', f'.runtime/bin/{name}'):
                matches = sorted(root.glob(pattern))
                if matches:
                    return str(matches[0])
    if name == 'chrome':
        paths = [Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Google/Chrome/Application/chrome.exe',
                 Path(os.environ.get('LOCALAPPDATA', 'C:/Users/Default/AppData/Local')) / 'Google/Chrome/Application/chrome.exe',
                 Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / 'Microsoft/Edge/Application/msedge.exe',
                 Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')]
        for path in paths:
            if path.is_file():
                return str(path)
        for candidate in ('chromium', 'chromium-browser', 'google-chrome', 'msedge'):
            found = shutil.which(candidate)
            if found:
                return found
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                path = Path(p.chromium.executable_path)
                if path.is_file():
                    return str(path)
        except ImportError:
            pass
    raise FileNotFoundError(f'Local {name} missing. Supply --{name} PATH or FILMCUT_{name.upper()}.')


def run(command):
    result = subprocess.run([str(x) for x in command], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(f'{Path(str(command[0])).name} failed (exit {result.returncode}): {result.stderr[-4000:]}')
    return result.stdout


def probe(path, ffprobe=None):
    return json.loads(run([ffprobe or find_tool('ffprobe'), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path]))


def local_asset(project, relative):
    # Project-owned assets make the skill portable and prevent HTTP image requests.
    if not isinstance(relative, str) or '://' in relative:
        raise ValueError(f'Asset must be a local project-relative path: {relative}')
    path = (project / relative).resolve()
    if not path.is_relative_to(project.resolve()) or not path.is_file():
        raise ValueError(f'Asset missing or outside project: {relative}')
    return path


def script_hash(manifest, shot):
    fields = ('id', 'quote', 'timeline', 'duration_s', 'meaning', 'visual_idea', 'objects', 'motion_plan')
    return digest({'source': manifest.get('inputs', {}).get('video', {}).get('sha256'),
                   'script': {key: shot.get(key) for key in fields}})


def scene_hash(project, manifest, shot):
    images = {}
    for layer in shot.get('layers', []):
        if layer.get('type') == 'image':
            images[layer['src']] = sha256(local_asset(project, layer['src']))
    template = project / 'canvas-template.html'
    if not template.exists():
        template = SKILL / 'assets/canvas-template.html'
    return digest({'script': script_hash(manifest, shot), 'output': manifest['output'], 'template': sha256(template),
                   'background': shot['background'], 'layers': shot['layers'],
                   'stop_motion_fps': shot.get('stop_motion_fps', 12), 'images': images})


def check_script(manifest, shot):
    record = shot.get('approvals', {}).get('script', {})
    if not record.get('user_message') or record.get('hash') != script_hash(manifest, shot):
        raise ValueError(f"{shot['id']}: current picture script has no valid user confirmation")


def check_still(project, manifest, shot):
    check_script(manifest, shot)
    record = shot.get('approvals', {}).get('still', {})
    image = project / 'stills' / f"{shot['id']}.png"
    if not record.get('user_message') or not image.is_file():
        raise ValueError(f"{shot['id']}: still confirmation missing")
    if record.get('scene_hash') != scene_hash(project, manifest, shot) or record.get('image_hash') != sha256(image):
        raise ValueError(f"{shot['id']}: approved still is stale; review the changed shot again")


def check_source(manifest):
    video = manifest.get('inputs', {}).get('video')
    if video and video.get('path'):
        path = Path(video['path'])
        if not path.is_file() or sha256(path) != video['sha256']:
            raise ValueError('Source video changed or moved. Recheck input records and timeline alignment.')


if __name__ == '__main__':
    print('Python:', sys.version.split()[0])
    failed = False
    for name in ('ffmpeg', 'ffprobe', 'chrome'):
        try:
            print('PASS', name, find_tool(name))
        except FileNotFoundError as error:
            print('MISSING', error)
            failed = True
    try:
        import playwright.sync_api
        print('PASS playwright')
    except ImportError:
        print('MISSING playwright: install into an isolated local Python environment')
        failed = True
    raise SystemExit(1 if failed else 0)
