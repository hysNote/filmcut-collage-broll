"""Use synthetic approvals only in temporary test projects, never in user outputs."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/'scripts'))
from local_tools import script_hash,scene_hash,sha256,write_json,read_json,check_still,local_asset
from review import write_review
from render import validate


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.project=Path(self.temp.name)
        for name in ['stills','clips','assets','qa']:(self.project/name).mkdir()
        shutil.copy2(SKILL/'assets/canvas-template.html',self.project/'canvas-template.html')
        self.shot={'id':'01-test','quote':'Synthetic <script>alert(1)</script> | test',
                   'meaning':'test','visual_idea':'Paper enters frame','objects':['paper'],
                   'motion_plan':'enter and hold','duration_s':.5,
                   'timeline':{'in_s':None,'out_s':None,'verified':False,'method':''},
                   'background':'#174b40','approvals':{},
                   'layers':[{'type':'rect','x':64,'y':112,'width':80,'height':100,'fill':'#e4cb82',
                              'enter':{'start':.05,'duration':.1,'from_y':200}}]}
        self.manifest={'title':'Synthetic test','inputs':{},'output':{'width':128,'height':224,'fps':24},'shots':[self.shot]}
        self.save()

    def tearDown(self):self.temp.cleanup()

    def save(self):write_json(self.project/'manifest.json',self.manifest)

    def command(self,name,*args,ok=True):
        r=subprocess.run([sys.executable,'-X','utf8',str(SKILL/'scripts'/name),'--project',str(self.project),*args],
                         capture_output=True,text=True,encoding='utf-8',timeout=120)
        self.assertEqual(r.returncode==0,ok,r.stdout+r.stderr)
        return r

    def test_review_order_escaping_and_unverified_time(self):
        self.manifest['review_sequence']=[{'quote':'Opening','presentation':'talking-head'}, {'shot_id':'01-test'}]
        self.save();before=(self.project/'manifest.json').read_bytes()
        rows=write_review(self.project)
        self.assertEqual(rows[0][-1],'保留原片')
        self.assertIn('待对齐',rows[1][1])
        page=(self.project/'review.html').read_text(encoding='utf-8')
        self.assertEqual(page.count('<th scope="col">'),4)
        self.assertIn('&lt;script&gt;',page)
        self.assertNotIn('<script>alert',page)
        self.assertEqual(before,(self.project/'manifest.json').read_bytes())
        (self.project/'stills/01-test.png').write_bytes(b'synthetic fixture')
        write_review(self.project)
        self.assertIn('<img src="stills/01-test.png"', (self.project/'review.html').read_text(encoding='utf-8'))

    def test_real_time_requires_video_and_matching_duration(self):
        self.shot['timeline']={'in_s':1,'out_s':2,'verified':True,'method':'synthetic test'}
        with self.assertRaises(ValueError):validate(self.manifest)
        self.manifest['inputs']['video']={'duration_s':4}
        with self.assertRaises(ValueError):validate(self.manifest)
        self.shot['duration_s']=1
        self.assertEqual(validate(self.manifest),24)

    def test_approval_and_asset_changes_are_rejected(self):
        with self.assertRaises(ValueError):check_still(self.project,self.manifest,self.shot)
        self.shot['approvals']['script']={'hash':script_hash(self.manifest,self.shot),'user_message':'SYNTHETIC TEST ONLY'}
        image=self.project/'stills/01-test.png';image.write_bytes(b'synthetic image fixture')
        self.shot['approvals']['still']={'scene_hash':scene_hash(self.project,self.manifest,self.shot),
                                       'image_hash':sha256(image),'user_message':'SYNTHETIC TEST ONLY'}
        check_still(self.project,self.manifest,self.shot)
        self.shot['layers'][0]['x']+=1
        with self.assertRaises(ValueError):check_still(self.project,self.manifest,self.shot)
        with self.assertRaises(ValueError):local_asset(self.project,'https://example.com/image.png')
        with self.assertRaises(ValueError):local_asset(self.project,'../outside.png')

    @unittest.skipUnless(os.environ.get('FILMCUT_RUN_RENDER_TESTS')=='1','Opt-in local browser/FFmpeg test')
    def test_render_partial_approval_and_combined_preview(self):
        self.command('render.py','--stills',ok=False)
        self.shot['approvals']['script']={'hash':script_hash(self.manifest,self.shot),'user_message':'SYNTHETIC TEST ONLY'}
        self.save();self.command('render.py','--stills')
        self.command('render.py',ok=False)
        self.shot['approvals']['still']={'scene_hash':scene_hash(self.project,self.manifest,self.shot),
            'image_hash':sha256(self.project/'stills/01-test.png'),'user_message':'SYNTHETIC TEST ONLY'}
        pending=copy.deepcopy(self.shot);pending['id']='02-pending';pending['approvals']={}
        pending['layers']=[{'type':'image','src':'assets/missing.png'}]
        self.manifest['shots'].append(pending);self.save()
        self.command('render.py','--shots','01-test')
        self.command('deliver.py','--shots','01-test')
        self.command('assemble.py','--shots','01-test')
        report=read_json(self.project/'preview-chapters.json')
        self.assertEqual(report['frames'],12)
        self.assertEqual(report['duration_s'],.5)
        self.assertEqual(report['audio_streams'],0)
        self.assertTrue(report['decode_ok'])
        self.assertEqual(report['timing_basis'],'preview_only_not_source_timecodes')
        self.command('assemble.py',ok=False)
        with (self.project/'clips/01-test.mp4').open('ab') as f:f.write(b'changed')
        self.command('assemble.py','--shots','01-test',ok=False)


if __name__=='__main__':unittest.main()
