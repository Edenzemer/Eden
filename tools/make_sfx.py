import json,sys,numpy as np,wave
times=json.load(open(sys.argv[1])); out=sys.argv[2]; dur=float(sys.argv[3])
sr=44100; rng=np.random.default_rng(7)
def env(n,a,d): 
    t=np.arange(n)/sr; return np.minimum(t/a,1)*np.exp(-t/d)
def swoosh():
    n=int(0.32*sr); x=rng.standard_normal(n); X=np.fft.rfft(x); f=np.fft.rfftfreq(n,1/sr)
    X*=((f>700)&(f<4500))*np.exp(-((f-2200)/1800)**2); x=np.fft.irfft(X,n)
    e=np.sin(np.pi*np.arange(n)/n)**2; x=x*e; return 0.9*x/np.abs(x).max()*0.16
def bell(f0,n=int(1.1*sr)):
    t=np.arange(n)/sr; y=0
    for k,(m,a,d) in enumerate([(1,1,0.55),(2.0,0.28,0.30),(3.01,0.12,0.18),(4.2,0.05,0.10)]):
        y=y+a*np.sin(2*np.pi*f0*m*t)*np.exp(-t/d)
    y*=np.minimum(t/0.004,1); return y/np.abs(y).max()*0.13
def snd():
    n=int(1.6*sr); y=np.zeros(n)
    s=swoosh(); y[:len(s)]+=s
    for off,f in [(0.12,659.25),(0.21,987.77)]:
        b=bell(f); i=int(off*sr); y[i:i+len(b)]+=b
    for dly,g in [(0.11,0.30),(0.23,0.14)]:  # soft room tail
        i=int(dly*sr); y[i:]+=g*y[:n-i]
    # gentle lowpass for warmth
    Y=np.fft.rfft(y); f=np.fft.rfftfreq(n,1/sr); Y*=1/(1+(f/6500)**4); return np.fft.irfft(Y,n)
s=snd(); L=int(dur*sr)+sr; mix=np.zeros(L)
for t in times:
    i=int(t*sr); mix[i:i+len(s)]+=s[:L-i]
mix=np.clip(mix*0.6,-0.9,0.9); pcm=(np.stack([mix,mix],1)*32767).astype('<i2')
w=wave.open(out,"wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes()); w.close()
print("ok",len(times),"hits, peak",np.abs(mix).max())
