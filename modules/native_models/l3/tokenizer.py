"""UTF-8 byte tokenizer. Strict decoding never silently inserts replacement chars."""
import codecs

class ByteTokenizer:
    PAD, UNK, BOS, EOS = 0, 1, 2, 3
    BYTE_OFFSET = 4
    VOCAB_SIZE = 260

    def encode(self, text, add_bos=False, add_eos=False):
        if not isinstance(text, str):
            raise TypeError("text must be str")
        ids = [b + self.BYTE_OFFSET for b in text.encode("utf-8", errors="strict")]
        if add_bos:
            ids.insert(0, self.BOS)
        if add_eos:
            ids.append(self.EOS)
        return ids

    def decode(self, tokens, errors="strict"):
        if errors not in ("strict", "ignore"):
            raise ValueError("errors must be strict or ignore")
        data = bytearray()
        for token in tokens:
            token = int(token)
            if self.BYTE_OFFSET <= token < self.VOCAB_SIZE:
                data.append(token - self.BYTE_OFFSET)
            elif token in (self.PAD, self.UNK, self.BOS, self.EOS):
                continue
            else:
                raise ValueError(f"token id outside vocabulary: {token}")
        return data.decode("utf-8", errors=errors)

    def get_config(self):
        return {"type":"native_utf8_byte","vocab_size":self.VOCAB_SIZE,
                "pad_token":self.PAD,"unk_token":self.UNK,
                "bos_token":self.BOS,"eos_token":self.EOS}
