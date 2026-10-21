"""Keep script and final-frame review in one four-column table; never grant approval."""
import argparse
import html
from pathlib import Path
from urllib.parse import quote
from local_tools import read_json
from render import validate


def timestamp(value):
    ms=round(value*1000)
    return f'{ms//60000:02}:{ms//1000%60:02}.{ms%1000:03}'


def build_rows(project, manifest):
    validate(manifest)
    shots={s['id']:s for s in manifest['shots']}
    sequence=manifest.get('review_sequence', [{'shot_id':s['id']} for s in manifest['shots']])
    rows=[]
    for entry in sequence:
        if 'shot_id' not in entry:
            if entry.get('presentation')!='talking-head':
                raise ValueError('Non-animation review rows must be talking-head entries')
            rows.append((entry['quote'],'随原片；待核对',entry.get('visual','保留本人出镜'),None,'保留原片'))
            continue
        s=shots[entry['shot_id']]
        tl=s.get('timeline') or {}
        if tl.get('verified'):
            timing=f"{timestamp(tl['in_s'])}–{timestamp(tl['out_s'])}；{s['duration_s']:g} 秒（已核对）"
        else:
            timing=f"待对齐；建议 {s.get('suggested_duration',str(s['duration_s'])+' 秒')}"
        path=project/'stills'/f"{s['id']}.png"
        relative=path.relative_to(project).as_posix() if path.is_file() else None
        rows.append((s['quote'],timing,s.get('review_visual',s['visual_idea']),relative,'待生成'))
    return rows


def write_review(project):
    manifest=read_json(project/'manifest.json')
    rows=build_rows(project,manifest)
    headers=['文案','时间/时长','预期画面呈现','最终结果图']
    title=manifest.get('title','拼贴 B-roll 审阅')
    esc=html.escape
    note='同一张表依次审阅脚本与最终结果图；确认结果图后实现动画过程。待对齐时间不代表实际口播入出点。'
    def md_cell(text):
        return esc(str(text)).replace('|','&#124;').replace('\n','<br>')
    markdown=f'# {md_cell(title)}\n\n{note}\n\n| '+' | '.join(headers)+' |\n|---|---|---|---|\n'
    table='<table><thead><tr>'+''.join(f'<th scope="col">{h}</th>' for h in headers)+'</tr></thead><tbody>'
    for text,timing,visual,image,placeholder in rows:
        cells=[text,timing,visual]
        md_image=f'![最终结果图]({quote(image,safe="/")})' if image else placeholder
        markdown+='| '+' | '.join(md_cell(c) for c in cells)+' | '+md_image+' |\n'
        table+='<tr>'+''.join('<td>'+esc(str(c)).replace('\n','<br>')+'</td>' for c in cells)
        if image:
            url=quote(image,safe='/')
            table+=f'<td><a href="{url}" target="_blank"><img src="{url}" alt="最终结果图"></a></td></tr>'
        else:
            table+='<td>'+esc(placeholder)+'</td></tr>'
    table+='</tbody></table>'
    style='''body{margin:0;background:#f6f5ef;color:#27342f;font:15px/1.85 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1450px;margin:auto;padding:28px}h1{font-size:25px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:900px;table-layout:fixed;background:white}td,th{padding:18px;border:1px solid #dfe3d8;text-align:left;vertical-align:top}th{background:#e6ebdf}th:nth-child(1){width:24%}th:nth-child(2){width:14%}th:nth-child(3){width:35%}th:nth-child(4){width:27%}img{display:block;width:100%;height:auto}p{color:#65705f}a{color:#2c654a}'''
    document=f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{style}</style></head><body><main><h1>{esc(title)}</h1><p>{note}</p><div class="scroll">{table}</div></main></body></html>'
    (project/'storyboard.md').write_text(markdown,encoding='utf-8')
    (project/'review.html').write_text(document,encoding='utf-8')
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True)
    args=parser.parse_args()
    rows=write_review(Path(args.project).resolve())
    print(f'Updated four-column review: {len(rows)} rows. No approval records changed.')
