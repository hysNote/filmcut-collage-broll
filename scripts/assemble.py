"""Join valid approved silent clips and verify the combined preview."""
import argparse
from fractions import Fraction
import html
from pathlib import Path
import shutil
from local_tools import (read_json,write_json,check_source,check_still,find_tool,probe,run,
                         script_hash,scene_hash,sha256)
from render import validate


def assemble(project, ids=None, ffmpeg=None, ffprobe=None):
    manifest=read_json(project/'manifest.json')
    fps=validate(manifest)
    check_source(manifest)
    by_id={s['id']:s for s in manifest['shots']}
    chosen=ids or list(by_id)
    if not chosen or len(chosen)!=len(set(chosen)) or set(chosen)-set(by_id):
        raise ValueError('Choose unique existing shot IDs in playback order')
    ffmpeg=find_tool('ffmpeg',ffmpeg);ffprobe=find_tool('ffprobe',ffprobe)
    total_frames=0;chapters=[]
    for sid in chosen:
        s=by_id[sid]
        check_still(project,manifest,s)
        clip=project/'clips'/f'{sid}.mp4'
        record=read_json(clip.with_suffix('.render.json'))
        if (record['script_hash']!=script_hash(manifest,s) or record['scene_hash']!=scene_hash(project,manifest,s)
                or record['clip_hash']!=sha256(clip)):
            raise ValueError(f'{sid}: clip or approval is stale; render again')
        streams=probe(clip,ffprobe)['streams']
        frames=round(s['duration_s']*fps)
        v=streams[0]
        if (len(streams)!=1 or v['codec_type']!='video' or v['codec_name']!='h264'
                or (v['width'],v['height'])!=(manifest['output']['width'],manifest['output']['height'])
                or Fraction(v['avg_frame_rate'])!=Fraction(str(manifest['output']['fps']))
                or int(v['nb_frames'])!=frames):
            raise ValueError(f'{sid}: unexpected dimensions, fps, frames or audio')
        run([ffmpeg,'-hide_banner','-loglevel','error','-xerror','-i',clip,'-f','null','-'])
        chapters.append({'id':sid,'start_s':total_frames/fps,'end_s':(total_frames+frames)/fps,'quote':s['quote']})
        total_frames+=frames
    target=project/'clips/combined-preview.mp4'
    if target.exists():
        history=project/'clips/history';history.mkdir(exist_ok=True)
        shutil.copy2(target,history/f'combined-preview-{sha256(target)[:12]}.mp4')
    playlist=project/'clips/combined-playlist.txt'
    playlist.write_text(''.join(f"file '{sid}.mp4'\n" for sid in chosen),encoding='utf-8')
    run([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',playlist,
         '-c','copy','-movflags','+faststart',target])
    metadata=probe(target,ffprobe);streams=metadata['streams'];v=streams[0]
    if (len(streams)!=1 or int(v['nb_frames'])!=total_frames
            or abs(float(metadata['format']['duration'])-total_frames/fps)>.01
            or Fraction(v['avg_frame_rate'])!=Fraction(str(manifest['output']['fps']))
            or (v['width'],v['height'])!=(manifest['output']['width'],manifest['output']['height'])):
        raise ValueError('Combined preview failed stream or duration verification')
    run([ffmpeg,'-hide_banner','-loglevel','error','-xerror','-i',target,'-f','null','-'])
    write_json(project/'preview-chapters.json',{'timing_basis':'preview_only_not_source_timecodes',
        'duration_s':total_frames/fps,'frames':total_frames,'audio_streams':0,'decode_ok':True,
        'sha256':sha256(target),'chapters':chapters})
    items=''.join(f'<li>{c["start_s"]:g}–{c["end_s"]:g} 秒 · <a href="clips/{c["id"]}.mp4">{html.escape(c["quote"])}</a></li>' for c in chapters)
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>连续动画预览</title><style>body{{background:#17231f;color:#eee8d8;font:16px/1.8 system-ui,sans-serif;margin:28px auto;max-width:980px;padding:0 20px}}video{{display:block;max-height:75vh;max-width:100%;margin:auto}}a{{color:#e6c66b}}</style></head><body><h1>连续动画预览 · {total_frames/fps:g} 秒</h1><video controls playsinline preload="metadata" src="clips/combined-preview.mp4"></video><p>无声预览；以下时间仅指本预览内部位置，不是原口播时间码。</p><ul>{items}</ul><a href="review.html">四列脚本与最终结果图</a></body></html>'''
    (project/'watch.html').write_text(page,encoding='utf-8')
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True)
    parser.add_argument('--shots',nargs='+',help='Unique shot IDs in desired playback order')
    parser.add_argument('--ffmpeg');parser.add_argument('--ffprobe')
    args=parser.parse_args()
    print(assemble(Path(args.project).resolve(),args.shots,args.ffmpeg,args.ffprobe))
