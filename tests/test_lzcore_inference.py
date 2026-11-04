import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import torch
from model.lzcore.config import LZConfig
from model.lzcore.inference import InferenceError,LZCoreInference
from model.lzcore.model import LZCore
from model.lzcore.provenance import sha256_file
from model.lzcore.tokenizer import LZTokenizer
class InferenceTests(unittest.TestCase):
 def fixture(self,root):
  data=root/"dataset.txt"; data.write_bytes(b"x"*(1024*1024)); cfg=LZConfig(name="tiny",vocab_size=260,block_size=8,n_layer=1,n_head=1,n_embd=8,batch_size=1,max_steps=1,eval_interval=1,eval_batches=1)
  tok=LZTokenizer(); model=LZCore(cfg); ck=root/"checkpoint.pt"
  torch.save({"format":"lzcore-ckpt-1","model_version":"0.1.0","model_state":model.state_dict(),"optimizer_state":None,"step":0,"config":cfg.to_dict(),"tokenizer":tok.to_dict(),"tokenizer_hash":tok.hash(),"history":[],"best_val_loss":6.0,"initial_val_loss":6.0,"dataset_sha256":sha256_file(data)},ck)
  m={"format":"lzcore-governance-2","status":"scratch-initialized","verified":False,"reasons":["synthetic test only"],"model_init":"random (from scratch, no pretrained weights)","dataset":{"path_name":data.name,"bytes":data.stat().st_size,"sha256":sha256_file(data),"train_tokens":1,"validation_tokens":1,"provenance":[{"source":"fixture","reference":"test fixture","rights_holder":"test","license_id":"CC0-1.0","license_reference":"CC0-1.0","attribution":"none","share_alike":False,"sha256":sha256_file(data),"owner_verified":False,"owner_attestation":None}]},"checkpoint":{"path_name":ck.name,"bytes":ck.stat().st_size,"sha256":sha256_file(ck),"format":"lzcore-ckpt-1"},"evaluation":{}}
  mp=root/"manifest.json"; mp.write_text(json.dumps(m)); return ck,mp
 def test_default_rejects_untrained(self):
  with tempfile.TemporaryDirectory() as d:
   ck,mp=self.fixture(Path(d))
   with self.assertRaises(InferenceError): LZCoreInference.load(ck,mp)
 def test_bypass_requires_test_env(self):
  with tempfile.TemporaryDirectory() as d:
   ck,mp=self.fixture(Path(d))
   with patch.dict(os.environ,{},clear=True):
    with self.assertRaises(InferenceError): LZCoreInference.load(ck,mp,allow_untrained=True)
   with patch.dict(os.environ,{"LZCORE_TEST_MODE":"1"}):
    engine=LZCoreInference.load(ck,mp,allow_untrained=True); self.assertEqual(engine.status,"scratch-initialized"); self.assertIsInstance(engine.generate("hello",max_new_tokens=2),str)
 def test_tamper_rejected(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"LZCORE_TEST_MODE":"1"}):
   ck,mp=self.fixture(Path(d)); ck.write_bytes(ck.read_bytes()+b"tamper")
   with self.assertRaises(InferenceError): LZCoreInference.load(ck,mp,allow_untrained=True)
 def test_limits(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{"LZCORE_TEST_MODE":"1"}):
   ck,mp=self.fixture(Path(d)); e=LZCoreInference.load(ck,mp,allow_untrained=True)
   with self.assertRaises(ValueError): e.generate(" ")
   with self.assertRaises(ValueError): e.generate("ok",max_new_tokens=0)
if __name__=="__main__": unittest.main()
