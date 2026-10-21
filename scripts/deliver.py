"""Validate local exports, extract actual QA frames, and write insertion instructions."""
import argparse
import csv
from fractions import Fraction
import math
from pathlib import Path
from local_tools import (check_source, check_still, find_tool, probe, read_json, run,
                         scene_hash, script_hash, sha256, write_json)
from render import validate


def timestamp(seconds):
    if seconds is None:
        return ''
    ms = round(seconds * 1000)
    return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}.{ms % 1000:03}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--shots', nargs='+', help='Deliver a confirmed subset')
    parser.add_argument('--ffmpeg')
    parser.add_argument('--ffprobe')
    args = parser.parse_args()
    project = Path(args.project).resolve()
    manifest = read_json(project / 'manifest.json')
    fps = validate(manifest)
    check_source(manifest)
    shots = [s for s in manifest['shots'] if not args.shots or s['id'] in args.shots]
    if not shots or (args.shots and set(args.shots) - {s['id'] for s in shots}):
        raise ValueError('No matching shots or unknown IDs')
    ffmpeg, ffprobe = find_tool('ffmpeg', args.ffmpeg), find_tool('ffprobe', args.ffprobe)
    reports, rows = [], []
    for shot in shots:
        sid = shot['id']
        check_still(project, manifest, shot)
        clip = project / 'clips' / f'{sid}.mp4'
        record = read_json(clip.with_suffix('.render.json'))
        if (record['script_hash'] != script_hash(manifest, shot) or record['scene_hash'] != scene_hash(project, manifest, shot)
                or record['clip_hash'] != sha256(clip)):
            raise ValueError(f'{sid}: clip no longer matches approved layers or render record')
        metadata = probe(clip, ffprobe)
        streams = metadata['streams']
        videos = [s for s in streams if s['codec_type'] == 'video']
        if len(streams) != 1 or len(videos) != 1:
            raise ValueError(f'{sid}: expected exactly one video stream and zero audio')
        v = videos[0]
        frames = max(1, round(shot['duration_s'] * fps))
        expected = manifest['output']
        if (v['width'], v['height']) != (expected['width'], expected['height']):
            raise ValueError(f'{sid}: incorrect dimensions')
        if Fraction(v['avg_frame_rate']) != Fraction(str(expected['fps'])) or int(v['nb_frames']) != frames:
            raise ValueError(f'{sid}: incorrect frame rate or frame count')
        actual_duration = float(metadata['format']['duration'])
        if abs(actual_duration - frames / fps) > .01:
            raise ValueError(f'{sid}: incorrect duration')
        run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-xerror', '-i', clip, '-f', 'null', '-'])
        qa = project / 'qa' / sid
        qa.mkdir(parents=True, exist_ok=True)
        for name, frame in [('first', 0), ('last', frames - 1)]:
            run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-filter_threads', '1', '-i', clip,
                 '-vf', f'select=eq(n\\,{frame})', '-frames:v', '1', '-threads', '2', qa / f'{name}.png'])
        count = max(1, math.ceil(actual_duration))
        columns = min(5, count)
        thumb_height = max(2, round(200 * v['height'] / v['width']))
        run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-filter_threads', '1', '-i', clip,
             '-vf', f'fps=1,scale=200:{thumb_height},tile={columns}x{math.ceil(count / columns)}',
             '-frames:v', '1', '-threads', '2', qa / 'contact-sheet.jpg'])
        tl = shot.get('timeline') or {}
        verified = bool(tl.get('verified'))
        row = {'id': sid, 'file': f'clips/{sid}.mp4', 'quote': shot['quote'],
               'source_in': timestamp(tl.get('in_s')) if verified else '',
               'source_out': timestamp(tl.get('out_s')) if verified else '',
               'duration_s': round(frames / fps, 6), 'timing_status': '已核对' if verified else '待核对，不能视为精确对齐',
               'presentation': shot.get('presentation', 'full-screen'), 'notes': shot.get('edit_notes', '')}
        rows.append(row)
        reports.append({'id': sid, 'width': v['width'], 'height': v['height'], 'fps': v['avg_frame_rate'],
                        'frames': frames, 'duration_s': actual_duration, 'audio_streams': 0, 'decode_ok': True,
                        'timing_verified': verified, 'visual_review': 'pending manual review'})
    write_json(project / 'qa/technical.json', reports)
    with (project / 'insertion-guide.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# B-roll 插入说明', '', '片段均为无声 MP4，保留原口播音轨。已核验时间以所记录的初剪版本为准；未核验项留空。', '']
    for row in rows:
        position = f"{row['source_in']} → {row['source_out']}" if row['source_in'] else '待核对，暂无已核验的时间点'
        lines += [f"## {row['id']} · {row['file']}", '', f"- 对应原句：{row['quote']}",
                  f"- 初剪位置：{position}（{row['timing_status']}）",
                  f"- 动画长度：{row['duration_s']} 秒；呈现：{row['presentation']}",
                  f"- 剪辑提示：{row['notes'] or '按原句结束或语义停顿回到出镜画面。'}", '']
    lines += ['普通 MP4 不含透明通道；局部叠加需额外提供蒙版或约定透明交付格式。', '',
              '技术检查已完成；人工检查实际首尾帧与逐秒图，将结论写入 qa-review.md 后交付。']
    (project / 'insertion-guide.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Validated', len(rows), 'clips. Review QA images and write qa-review.md before delivery.')


if __name__ == '__main__':
    main()
