"""Render approved paper-collage layers locally; export only stills before still approval."""
import argparse
from fractions import Fraction
import math
from pathlib import Path
import re
import shutil
import sys
from local_tools import (SKILL, check_script, check_still, check_source, find_tool, read_json,
                         run, scene_hash, script_hash, sha256, write_json)


def validate(manifest):
    output = manifest['output']
    w, h = output['width'], output['height']
    if not isinstance(w, int) or not isinstance(h, int) or min(w, h) < 2 or w % 2 or h % 2:
        raise ValueError('Output width and height must be positive even integers')
    fps = float(Fraction(str(output['fps'])))
    if not 0 < fps <= 120:
        raise ValueError('Unsupported frame rate')
    ids = set()
    for shot in manifest['shots']:
        identity = shot['id']
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', identity) or identity in ids:
            raise ValueError('Shot IDs must be unique safe file names')
        ids.add(identity)
        if not math.isfinite(shot['duration_s']) or shot['duration_s'] <= 0:
            raise ValueError(f'{identity}: duration must be finite and positive')
        timeline = shot.get('timeline') or {}
        start, end = timeline.get('in_s'), timeline.get('out_s')
        if timeline.get('verified'):
            if not timeline.get('method') or start is None or end is None or not 0 <= start < end:
                raise ValueError(f'{identity}: invalid verified timeline')
            video = manifest.get('inputs', {}).get('video')
            if not video or end > video['duration_s'] + .001:
                raise ValueError(f'{identity}: verified interval exceeds actual source video')
            if abs(end - start - shot['duration_s']) > 1 / fps + .001:
                raise ValueError(f'{identity}: clip duration differs from verified source interval')
    return fps


def build_preview(project, manifest):
    import json
    template = (project / 'canvas-template.html')
    if not template.exists():
        template = SKILL / 'assets/canvas-template.html'
    data = json.dumps(manifest, ensure_ascii=False).replace('<', '\\u003c')
    path = project / 'preview.html'
    path.write_text(template.read_text(encoding='utf-8').replace('__FILMCUT_PROJECT_JSON__', data), encoding='utf-8')
    return path


def render_batches(project, manifest, shots, fps, args):
    """Bound each browser-driver session and resume only fingerprinted completed batches."""
    for shot in shots:
        sid = shot['id']
        frames = max(1, round(shot['duration_s'] * fps))
        folder = project / '.render-frames' / sid
        folder.mkdir(parents=True, exist_ok=True)
        signature = {'script_hash': script_hash(manifest, shot), 'scene_hash': scene_hash(project, manifest, shot),
                     'frames': frames, 'fps': str(manifest['output']['fps'])}
        stamp = folder / 'batches.json'
        state = read_json(stamp) if stamp.exists() else {}
        if state.get('signature') != signature:
            state = {'signature': signature, 'completed': []}
        write_json(stamp, state)
        for start in range(0, frames, args.batch_size):
            stop = min(frames, start + args.batch_size)
            if [start, stop] in state['completed'] and all((folder / f'{i:06d}.jpg').is_file() for i in range(start, stop)):
                continue
            command = [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), '--project', str(project),
                       '--shots', sid, '--frame-range', str(start), str(stop)]
            if args.chrome:
                command += ['--chrome', args.chrome]
            run(command)
            state['completed'].append([start, stop])
            write_json(stamp, state)
            print(f'FRAMES {sid}: {stop}/{frames}', flush=True)
        clips = project / 'clips'
        clips.mkdir(exist_ok=True)
        target = clips / f'{sid}.mp4'
        if target.exists():
            history = clips / 'history'
            history.mkdir(exist_ok=True)
            previous_id = f'{sid}-{sha256(target)[:12]}'
            shutil.copy2(target, history / f'{previous_id}.mp4')
            previous_record = clips / f'{sid}.render.json'
            if previous_record.exists():
                shutil.copy2(previous_record, history / f'{previous_id}.render.json')
        run([find_tool('ffmpeg', args.ffmpeg), '-hide_banner', '-loglevel', 'error', '-y', '-threads', '1', '-filter_threads', '1', '-framerate', str(manifest['output']['fps']),
             '-i', folder / '%06d.jpg', '-frames:v', str(frames), '-an', '-c:v', 'libx264', '-threads', '2', '-preset', 'fast',
             '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', target])
        write_json(clips / f'{sid}.render.json', {**signature, 'clip_hash': sha256(target)})
        print('CLIP', target, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--stills', action='store_true')
    parser.add_argument('--fingerprints', action='store_true', help='Print hashes for recording real user approvals; does not grant approval')
    parser.add_argument('--shots', nargs='+', help='Render selected IDs only')
    parser.add_argument('--chrome')
    parser.add_argument('--ffmpeg')
    parser.add_argument('--batch-size', type=int, default=32, help='Frames per fresh local browser process')
    parser.add_argument('--frame-range', nargs=2, type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    project = Path(args.project).resolve()
    manifest = read_json(project / 'manifest.json')
    fps = validate(manifest)
    shots = [s for s in manifest['shots'] if not args.shots or s['id'] in args.shots]
    if not shots or (args.shots and set(args.shots) - {s['id'] for s in shots}):
        raise ValueError('No matching shots or an unknown shot ID was supplied')
    check_source(manifest)
    if args.fingerprints:
        for shot in shots:
            result = {'id': shot['id'], 'script_hash': script_hash(manifest, shot)}
            if shot.get('layers'):
                result['scene_hash'] = scene_hash(project, manifest, shot)
            still = project / 'stills' / f"{shot['id']}.png"
            if still.exists():
                result['image_hash'] = sha256(still)
            print(__import__('json').dumps(result, ensure_ascii=False))
        return
    for shot in shots:
        check_script(manifest, shot)
        if not shot.get('layers'):
            raise ValueError(f"{shot['id']}: artwork layers are missing")
        scene_hash(project, manifest, shot)  # checks local asset existence
        if not args.stills:
            check_still(project, manifest, shot)
    if not args.stills and not args.frame_range:
        if args.batch_size < 1:
            raise ValueError('Batch size must be positive')
        render_batches(project, manifest, shots, fps, args)
        return
    preview = build_preview(project, {**manifest, 'shots': shots})
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=find_tool('chrome', args.chrome), headless=True)
        try:
            page = browser.new_page(viewport={'width': manifest['output']['width'], 'height': manifest['output']['height']}, device_scale_factor=1)
            page.goto(preview.as_uri() + '?render=1')
            page.wait_for_function('window.ready === true')
            errors = page.evaluate('window.assetErrors')
            if errors:
                raise ValueError(f'Artwork could not load: {errors}')
            canvas = page.locator('canvas')
            for shot in shots:
                sid = shot['id']
                frames = max(1, round(shot['duration_s'] * fps))
                if args.stills:
                    folder = project / 'stills'
                    folder.mkdir(exist_ok=True)
                    target = folder / f'{sid}.png'
                    if target.exists():
                        revision = folder / f'{sid}-{sha256(target)[:12]}.png'
                        if not revision.exists():
                            target.rename(revision)
                    page.evaluate('([id,t])=>window.drawFrame(id,t)', [sid, (frames - 1) / fps])
                    canvas.screenshot(path=str(target))
                    print('STILL', target, flush=True)
                    continue
                folder = project / '.render-frames' / sid
                folder.mkdir(parents=True, exist_ok=True)
                start, stop = args.frame_range
                if not 0 <= start < stop <= frames:
                    raise ValueError('Invalid frame range')
                for frame in range(start, stop):
                    page.evaluate('([id,t])=>window.drawFrame(id,t)', [sid, frame / fps])
                    canvas.screenshot(path=str(folder / f'{frame:06d}.jpg'), type='jpeg', quality=96)
        finally:
            browser.close()


if __name__ == '__main__':
    main()
