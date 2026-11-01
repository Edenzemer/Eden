"""CTC forced alignment (Hebrew wav2vec2) to refine word timings. Writes aligned.json: list of phrases [[word,start,end,aligned_bool],...]."""
import json,re,sys,numpy as np,torch,subprocess
import torchaudio.functional as AF
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
MODEL="imvladikon/wav2vec2-xls-r-300m-hebrew"
HEB=re.compile(r"^[א-ת]+$")
def emissions(wav):
    raw=subprocess.run(["ffmpeg","-v","error","-i",wav,"-f","s16le","-ac","1","-ar","16000","-"],capture_output=True).stdout
    a=np.frombuffer(raw,np.int16).astype(np.float32)/32768
    pr=Wav2Vec2Processor.from_pretrained(MODEL); m=Wav2Vec2ForCTC.from_pretrained(MODEL).eval()
    x=pr(a,sampling_rate=16000,return_tensors="pt").input_values
    out=[]; step=16000*20; hop=step   # 20s chunks, no overlap needed for CTC emissions at this scale
    with torch.no_grad():
        for i in range(0,x.shape[1],step):
            out.append(torch.log_softmax(m(x[:,i:i+step]).logits,-1)[0])
    return torch.cat(out),pr.tokenizer.get_vocab()
def refine(phrases,wav,pad=0.45):
    E,vocab=emissions(wav); T=E.shape[0]; fs=0.02; out=[]
    for ph in phrases:
        idx=[k for k,t in enumerate(ph) if HEB.match(t[0])]
        res=[list(t)+[False] for t in ph]
        if idx:
            f0=max(int((ph[0][1]-pad)/fs),0); f1=min(int((ph[-1][2]+pad)/fs)+1,T)
            tg=[]; spans=[]
            for n,k in enumerate(idx):
                if n: tg.append(vocab["|"])
                s=len(tg); tg+= [vocab[c] for c in ph[k][0]]; spans.append((s,len(tg)))
            try:
                al,_=AF.forced_align(E[f0:f1].unsqueeze(0),torch.tensor([tg],dtype=torch.int32),blank=vocab["[PAD]"])
                al=al[0].tolist()
                # map frames -> target positions
                pos=-1; first={}; last={}; prev=None
                for fr,tok in enumerate(al):
                    if tok==vocab["[PAD]"]: prev=None; continue
                    if tok!=prev: pos+=1
                    first.setdefault(pos,fr); last[pos]=fr; prev=tok
                # positions index the *non-blank-collapsed* tokens == target indices
                for n,k in enumerate(idx):
                    s,e=spans[n]; a=first[s]; b=last[e-1]
                    res[k][1]=(f0+a)*fs; res[k][2]=(f0+b+1)*fs; res[k][4]=True
            except Exception as ex: print("align fail",ph[0][:3],ex,file=sys.stderr)
        # non-aligned tokens (numbers/English): keep original timing, clamp between neighbours
        for k,t in enumerate(res):
            if t[4]: continue
            lo=res[k-1][2] if k and res[k-1][4] else t[1]
            hi=res[k+1][1] if k+1<len(res) and res[k+1][4] else t[2]
            t[1]=max(t[1],lo) if k else t[1]; t[2]=min(t[2],hi) if k+1<len(res) else t[2]
            if t[2]<=t[1]: t[2]=t[1]+0.15
        out.append([[t[0],t[1],t[2],t[3]] for t in res])
    return out
if __name__=="__main__":
    ph=json.load(open(sys.argv[1])); json.dump(refine(ph,sys.argv[2]),open(sys.argv[3],"w"),ensure_ascii=False)
