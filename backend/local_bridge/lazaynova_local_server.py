"""Threaded loopback REST bridge for LAZAYNOVA native L3 V2."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json, logging, sys
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from lz_core.ai_gateway.gateway import InternalAIGateway
logging.basicConfig(level=logging.INFO)
gateway=InternalAIGateway()
MAX_BODY=256*1024

class LazaynovaHandler(BaseHTTPRequestHandler):
    server_version="LAZAYNOVA-Local/2.0"
    def _send(self,status,payload):
        body=json.dumps(payload,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(body)
    def _body(self):
        try: length=int(self.headers.get("Content-Length","0"))
        except ValueError: raise ValueError("invalid Content-Length")
        if length<1 or length>MAX_BODY: raise ValueError("request body must be 1..262144 bytes")
        data=json.loads(self.rfile.read(length).decode("utf-8","strict"))
        if not isinstance(data,dict): raise ValueError("JSON body must be an object")
        return data
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/health":
            return self._send(200,{"status":"healthy","service":"LAZAYNOVA","mode":"LOCAL_ONLY"})
        if path=="/v1/models":
            return self._send(200,{"object":"list","data":[{"id":"LAZAYNOVA-L3-native-v2","object":"model","owned_by":"LAZAYNOVA"}]})
        if path=="/api/model/status":
            return self._send(200,gateway.model_status_report())
        return self._send(404,{"error":{"message":"not found"}})
    def do_POST(self):
        path=urlparse(self.path).path
        if path not in ("/v1/chat/completions","/api/chat"):
            return self._send(404,{"error":{"message":"not found"}})
        try:
            data=self._body()
            if path=="/api/chat":
                prompt=data.get("message")
                if not isinstance(prompt,str): raise ValueError("message must be text")
                out=gateway.generate(prompt,data.get("max_tokens",96),data.get("temperature",0.0))
                return self._send(200,{"brand":"LAZAYNOVA","model":"L3-V2","response":out})
            return self._send(200,gateway.chat_completion(data.get("messages"),data.get("max_tokens",96),data.get("temperature",0.0)))
        except FileNotFoundError as exc:
            return self._send(503,{"error":{"message":str(exc),"type":"model_not_ready"}})
        except (ValueError,TypeError,json.JSONDecodeError) as exc:
            return self._send(400,{"error":{"message":str(exc),"type":"invalid_request"}})
        except Exception:
            logging.exception("local inference failed")
            return self._send(500,{"error":{"message":"local inference failed"}})
    def log_message(self,fmt,*args):
        logging.info("%s - %s",self.address_string(),fmt%args)

if __name__=="__main__":
    host,port="127.0.0.1",8787
    print(f"LAZAYNOVA local API: http://{host}:{port}",flush=True)
    ThreadingHTTPServer((host,port),LazaynovaHandler).serve_forever()
