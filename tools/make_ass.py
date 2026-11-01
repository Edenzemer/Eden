import json,sys,math,os
src,out=sys.argv[1],sys.argv[2]
here=os.path.dirname(os.path.abspath(src))
GOLD,WHITE="&H00D7FF&","&HFFFFFF&"
segs=json.load(open(src))
def clean(w): return w.strip().rstrip(",.?!").replace("‏","")
def brk(w): return w.strip().endswith((",",".","?","!"))
# ---- tokens, phrases
phrases=[]
for s in segs:
    cur=[]
    for w,a,b in s["w"]:
        t=[clean(w),a,b,brk(w)]
        if t[0].startswith(("-","'")) and cur: cur[-1][0]+=t[0]; cur[-1][2]=t[2]; cur[-1][3]=t[3]
        elif t[0].startswith(",060") or t[0]=="060": cur[-1][0]+=",060"; cur[-1][2]=t[2]; cur[-1][3]=t[3]
        else: cur.append(t)
        if cur[-1][3]: phrases.append(cur); cur=[]
    if cur: phrases.append(cur)
def split2(t,w1,w2):
    mid=(t[1]+t[2])/2; return [[w1,t[1],mid,False],[w2,mid,t[2],t[3]]]
n_gova=0; fixed=[]
for m in phrases:
    o=[]; i=0
    while i<len(m):
        t=m[i]; w,a,b,e=t
        if w=="ה-GIFT":   # "gift with purchase" -> GWP
            end=m[i+1][2] if i+1<len(m) else b
            o.append(["GWP",a,end,False]); i+=2; continue
        if w=="ה-Cozy": w="Cozy"
        elif w=="דרגלו": o+=split2(t,"דרגון","בול"); i+=1; continue
        elif w=="1139": w="11390"
        elif w=="פסת": i+=1; continue           # unclear word, dropped
        elif w=="סגראדה": w="סגרדה"
        elif w=="חבוד": w="חמוד"
        elif w=="טיסני": w="דיסני"
        elif w=="וסטארוורס": o+=split2(t,"וסטאר","וורס"); i+=1; continue
        elif w=="סאל": w="סייל"
        elif w=="לרוקב": w="לרוחב"
        o.append([w,a,b,e]); i+=1
    if o: fixed.append(o)
# refine with forced alignment (tools/align.py) where it agrees with the transcription timing
al=os.path.join(here,"aligned.json")
if os.path.exists(al):
    A=json.load(open(al)); assert len(A)==len(fixed)
    for m,am in zip(fixed,A):
        prev_end=-1
        for t,x in zip(m,am):
            if abs(x[1]-t[1])<=0.5 and abs(x[2]-t[2])<=1.0 and x[1]>=prev_end-0.05: t[1],t[2]=x[1],x[2]
            prev_end=t[2]
# text merges: "50 %" -> "50%", "של לגו" -> "שלגו"
for mi,m in enumerate(fixed):
    o=[]
    for t in m:
        if o and t[0]=="%" : o[-1][0]+="%"; o[-1][2]=t[2]; continue
        if o and o[-1][0]=="של" and t[0]=="לגו" and 60<o[-1][1]<70: o[-1][0]="שלגו"; o[-1][2]=t[2]; continue
        o.append(t)
    fixed[mi]=o
for m in fixed:
    for k,t in enumerate(m):
        if t[2]<=t[1]: t[2]=t[1]+0.2
        if k+1<len(m) and t[2]>m[k+1][1]: t[2]=m[k+1][1]
# ---- speech map (captions only while speaking)
sp=json.load(open(os.path.join(here,"speech.json")))
mg=[]
for a,b in sp:
    if mg and a-mg[-1][1]<0.35: mg[-1][1]=b
    else: mg.append([a,b])
for m in fixed:
    st=m[0][1]
    if any(x-0.02<=st<=y for x,y in mg): continue
    nxt=[x for x,y in mg if 0<x-st<=0.6]
    if nxt:
        m[0][1]=nxt[0]; m[0][2]=max(m[0][2],nxt[0]+0.12)
        for k in range(1,len(m)):
            m[k][1]=max(m[k][1],m[k-1][2])
            if m[k][2]<=m[k][1]: m[k][2]=m[k][1]+0.12
def chunks(m):
    n=len(m); g=math.ceil(n/3); size=math.ceil(n/g); return [m[i:i+size] for i in range(0,n,size)]
def ts(t):
    t=max(t,0); h=int(t//3600); mi=int(t%3600//60); s=t%60; return f"{h}:{mi:02d}:{s:05.2f}"
ev=[]
for m in fixed:
    for line in chunks(m):
        for k,(w,a,b,_) in enumerate(line):
            end=min(line[k+1][1],b+0.35) if k+1<len(line) else b+0.12
            txt=" ".join(f"{{\\c{GOLD if j==k else WHITE}}}{x[0]}" for j,x in enumerate(line))
            ev.append((a,end,"Main","‏"+txt))
# ---- set info: (start,end) snapped to real scene cuts, each shown ~6s then leaves
INFO=[
 (12.24,18.8,"Icons: 11388","Venetian Neighborhood","5,682 חלקים"),
 (20.55,24.0,"Icons: 40898","Venetian Water Taxi GWP","322 חלקים"),
 (27.17,33.8,"Icons: 11390","Dragon Ball: Shenron & Goku","1,764 חלקים"),
 (37.52,41.8,"Icons: 11390","Dragon Ball: Shenron & Goku","1,764 חלקים"),
 (43.40,49.2,"Botanicals: 10371","Cozy Plants","248 חלקים"),
 (50.11,56.0,"Icons: 11388","Venetian Neighborhood","5,682 חלקים"),
 (76.65,82.9,"Architecture: 21065","Sagrada Família","12,060 חלקים"),
 (100.0,105.4,"Ideas: 40889","Build, Paint and Play GWP","158 חלקים"),
 (123.08,127.8,"Ideas: 40889","Build, Paint and Play GWP","158 חלקים"),
]
for a,b,l1,l2,l3 in INFO:
    for i,(txt,cy,fs,col) in enumerate([(l1,429,106,"&HFFFFFF&"),(l2,537,106,"&HFFFFFF&"),(l3,635,88,"&H00D7FF&")]):
        tag=f"{{\\an5\\fs{fs}\\c{col}\\fad(300,260)\\move(540,{cy+28},540,{cy},0,380)}}"
        ev.append((a+0.09*i,b,"Info",tag+txt))
json.dump([x[0] for x in INFO],open(os.path.join(here,"info_times.json"),"w"))
clipped=[]
for e in ev:
    if e[2]!="Main": clipped.append(e); continue
    for a,b in mg:
        lo,hi=max(e[0],a),min(e[1],b)
        if hi-lo>=0.04: clipped.append((lo,hi,e[2],e[3]))
ev=sorted(clipped,key=lambda e:(e[0],e[2]))
main=[i for i,e in enumerate(ev) if e[2]=="Main"]
for x,y in zip(main,main[1:]):
    if ev[x][1]>ev[y][0]: ev[x]=(ev[x][0],ev[y][0],ev[x][2],ev[x][3])
ev=[e for e in ev if e[2]!='Main' or e[1]-e[0]>=0.03]
hdr="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Heebo Black,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,6,3,2,70,70,360,-1
Style: Info,Heebo Black,106,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,8,2,8,10,10,380,-1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
with open(out,"w",encoding="utf-8") as f:
    f.write(hdr)
    for a,b,s,t in ev: f.write(f"Dialogue: 0,{ts(a)},{ts(b)},{s},,0,0,0,,{t}\n")
print(len(ev),"events")
