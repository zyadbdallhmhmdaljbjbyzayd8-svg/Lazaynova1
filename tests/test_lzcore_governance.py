import tempfile,unittest
from pathlib import Path
from model.lzcore.manifest import MIN_DATASET_BYTES,assess_training_evidence,verify_manifest
from model.lzcore.provenance import build_data_record,sha256_file
class GovernanceTests(unittest.TestCase):
 def rec(self,digest,license_id="CC0-1.0",**kw):
  a=dict(source="corpus",reference="source ref",rights_holder="holder",license_id=license_id,license_reference="license",attribution="credit",share_alike=False,sha256=digest); a.update(kw); return build_data_record(**a)
 def fixture(self,root,val_tokens=12000):
  data=root/"data.bin"; data.write_bytes(b"d"*MIN_DATASET_BYTES); ck=root/"weights.pt"; ck.write_bytes(b"checkpoint")
  tr=root/"train.txt"; tr.write_text(("train alpha beta gamma delta epsilon zeta eta theta. ")*80)
  va=root/"val.txt"; va.write_text(("validation iota kappa lambda mu nu xi omicron pi rho. ")*80)
  rec=self.rec(sha256_file(data))
  m=assess_training_evidence(dataset_path=data,dataset_sha256=sha256_file(data),provenance_records=[rec],train_tokens=50000,validation_tokens=val_tokens,initial_val_loss=6,best_val_loss=5,final_val_loss=5.1,steps_completed=1000,independent_validation=True,train_text_path=tr,validation_text_path=va,checkpoint_path=ck,checkpoint_sha256=sha256_file(ck),checkpoint_format="lzcore-ckpt-1",model_init="random (from scratch, no pretrained weights)")
  return data,ck,m
 def test_verified_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   data,ck,m=self.fixture(Path(d)); self.assertEqual(m["status"],"scratch-trained-verified"); self.assertTrue(verify_manifest(m,dataset_path=data,checkpoint_path=ck)["hashes_verified"])
 def test_small_validation_unverified(self):
  with tempfile.TemporaryDirectory() as d: self.assertEqual(self.fixture(Path(d),100)[2]["status"],"scratch-trained-unverified")
 def test_manifest_forgery_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   data,ck,m=self.fixture(Path(d)); m["dataset"]["bytes"]=1
   with self.assertRaises(ValueError): verify_manifest(m,dataset_path=data,checkpoint_path=ck)
 def test_real_overlap_detected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); data=root/"data"; data.write_bytes(b"x"*MIN_DATASET_BYTES); ck=root/"ck"; ck.write_bytes(b"ck")
   tr=root/"tr"; va=root/"va"; shared="one two three four five six seven eight nine ten "
   tr.write_text(shared*100); va.write_text(shared*100); rec=self.rec(sha256_file(data))
   m=assess_training_evidence(dataset_path=data,dataset_sha256=sha256_file(data),provenance_records=[rec],train_tokens=50000,validation_tokens=12000,initial_val_loss=6,best_val_loss=5,final_val_loss=5.1,steps_completed=100,independent_validation=True,train_text_path=tr,validation_text_path=va,checkpoint_path=ck,checkpoint_sha256=sha256_file(ck),checkpoint_format="lzcore-ckpt-1",model_init="random (from scratch, no pretrained weights)")
   self.assertEqual(m["status"],"scratch-trained-unverified")
 def test_sharealike_enforced(self):
  with self.assertRaises(ValueError): self.rec("a"*64,"CC-BY-SA-4.0")
if __name__=="__main__": unittest.main()
