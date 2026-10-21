"""Prepare input records and local preview files; never modify the source video."""
import argparse
from pathlib import Path
import shutil
from local_tools import SKILL, find_tool, probe, sha256, write_json, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--transcript', required=True, help='UTF-8 text or Markdown transcript')
    parser.add_argument('--video', help='Rough-cut talking-head video; optional for untimed planning')
    parser.add_argument('--extract-audio', action='store_true')
    parser.add_argument('--ffprobe')
    parser.add_argument('--ffmpeg')
    args = parser.parse_args()
    project = Path(args.project).resolve()
    project.mkdir(parents=True, exist_ok=True)
    manifest_path = project / 'manifest.json'
    if manifest_path.exists():
        raise FileExistsError('Project already has manifest.json; keep its approved state and use a new revision.')
    transcript = Path(args.transcript).resolve()
    text = transcript.read_text(encoding='utf-8-sig')
    if not text.strip():
        raise ValueError('Transcript is empty')
    for folder in ('inputs', 'assets', 'stills', 'clips', 'qa'):
        (project / folder).mkdir(exist_ok=True)
    (project / 'inputs/transcript.txt').write_text(text, encoding='utf-8')
    inputs = {'transcript': {'path': str(transcript), 'sha256': sha256(transcript)}}
    output = {'width': 720, 'height': 1280, 'fps': 24}
    if args.video:
        video = Path(args.video).resolve()
        metadata = probe(video, find_tool('ffprobe', args.ffprobe))
        streams = [s for s in metadata['streams'] if s['codec_type'] == 'video']
        if not streams:
            raise ValueError('Input has no video stream')
        v = streams[0]
        fps = v.get('avg_frame_rate') or v['r_frame_rate']
        num, den = (int(p) for p in fps.split('/'))
        if den == 0 or num <= 0:
            raise ValueError('Cannot establish source frame rate; inspect video before choosing output fps')
        rotation = next((int(s.get('rotation', 0)) for s in v.get('side_data_list', []) if 'rotation' in s), int(v.get('tags', {}).get('rotate', 0)))
        w, h = v['width'], v['height']
        if rotation % 180:
            w, h = h, w
        output = {'width': w, 'height': h, 'fps': fps}
        inputs['video'] = {'path': str(video), 'sha256': sha256(video), 'duration_s': float(metadata['format']['duration']),
                           'width': w, 'height': h, 'fps': fps}
        write_json(project / 'inputs/video-probe.json', metadata)
        if args.extract_audio:
            if not any(s['codec_type'] == 'audio' for s in metadata['streams']):
                raise ValueError('Input video has no audio stream; timeline speech alignment is unavailable')
            run([find_tool('ffmpeg', args.ffmpeg), '-hide_banner', '-loglevel', 'error', '-y', '-i', video,
                 '-vn', '-ac', '1', '-ar', '16000', project / 'inputs/voice.wav'])
    write_json(manifest_path, {'schema_version': 1, 'title': project.name, 'inputs': inputs, 'output': output, 'shots': []})
    shutil.copy2(SKILL / 'assets/canvas-template.html', project / 'canvas-template.html')
    print('Prepared', project, '\nAdd and confirm picture-script shots in manifest.json before generating artwork.')


if __name__ == '__main__':
    main()
