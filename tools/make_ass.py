import json,sys,math
src,out=sys.argv[1],sys.argv[2]
GOLD,WHITE="&H00D7FF&","&HFFFFFF&"
segs=json.load(open(src))
def clean(w): return w.strip().rstrip(",.").replace("‏","")
seq=[]  # per sentence: list of [word,start,end]
for s in segs:
    toks=[[clean(w),a,b] for w,a,b in s["w"]]
    m=[]
    for t in toks:
        if t[0].startswith(("-","'")) and m: m[-1][0]+=t[0]; m[-1][2]=t[2]
        elif t[0].startswith("060") or t[0]==",060": m[-1][0]+=",060"; m[-1][2]=t[2]
        else: m.append(t)
    seq.append(m)
def split2(t,w1,w2):
    mid=(t[1]+t[2])/2; return [[w1,t[1],mid],[w2,mid,t[2]]]
fixed=[]; n_gova=0
for m in seq:
    o=[]; i=0
    while i<len(m):
        w,a,b=m[i]
        if w=="ה" and i+1<len(m) and "gift" in m[i+1][0]:
            g=m[i+1]; p=m[i+2]; i+=3; mid=(g[1]+g[2])/2
            o+= [["gift",g[1],g[2]],["with",p[1],p[1]+0.2],["purchase",p[1]+0.2,p[2]]]; continue
        if w=="ה" and i+1<len(m) and "cozy" in m[i+1][0].lower():
            c=m[i+1]; p=m[i+2]; i+=3
            o+= [["Cozy",c[1],c[2]],["Plants",p[1],p[2]]]; continue
        if w.startswith("צ'נרון"): w="שנרון"
        elif w=="מטחק": o+=split2([w,a,b],"דרגון","בול"); i+=1; continue
        elif w=="113900": w="11390"; b=a+1.0
        elif w=="מבנציה": w="מוונציה"
        elif w=="מטפסת": w="מדפסת"
        elif w=="לטממט": o+=split2([w,a,b],"תלת","מימד"); i+=1; continue
        elif w=="קצת": w="תלת"
        elif w=="מטוח": w="מטורף"
        elif w=="מהדגנים": w="מהדגמים"
        elif w=="וסטארו": o+=split2([w,a,b],"וסטאר","וורס"); i+=1; continue
        elif w=="סל": w="סייל"
        elif w=="לגובה":
            n_gova+=1
            if n_gova==2: w="לרוחב"; b=a+0.4
        elif w=="ומתנה" and a==b: b=a+0.2
        o.append([w,a,b]); i+=1
    fixed.append(o)
# fix zero/overlaps
for m in fixed:
    for k,t in enumerate(m):
        if t[2]<=t[1]: t[2]=t[1]+0.2
        if k+1<len(m) and t[2]>m[k+1][1]: t[2]=m[k+1][1]
# clip captions to real speech (no text during silence)
import os
sp=json.load(open(os.path.join(os.path.dirname(os.path.abspath(src)),"speech.json")))
mg=[]
for a,b in sp:
    if mg and a-mg[-1][1]<0.35: mg[-1][1]=b
    else: mg.append([a,b])
# first word starts in silence just before speech: start it at speech onset, keep later words as timed
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
    h=int(t//3600); mi=int(t%3600//60); s=t%60; return f"{h}:{mi:02d}:{s:05.2f}"
ev=[]
for m in fixed:
    for line in chunks(m):
        for k,(w,a,b) in enumerate(line):
            end=line[k+1][1] if k+1<len(line) else b+0.12
            end=min(end,b+0.35) if k+1<len(line) else end
            txt=" ".join(f"{{\\c{GOLD if j==k else WHITE}}}{x[0]}" for j,x in enumerate(line))
            ev.append((a,end,"Main",""+"‏"+txt))
# set info (box visible only)  (start,end,[lines])
INFO=[
 (37.6,42.6,"Icons: 11390","Dragon Ball: Shenron & Goku","1,764 חלקים"),
 (43.2,49.5,"Botanicals: 10371","Cozy Plants","248 חלקים"),
 (49.6,75.6,"Icons: 11388","Venetian Neighborhood","5,682 חלקים"),
 (76.3,96.0,"Architecture: 21065","Sagrada Família","12,060 חלקים"),
 (99.8,104.4,"Ideas: 40889","Build, Paint and Play GWP","158 חלקים"),
 (104.4,110.0,"Icons: 40898","Venetian Water Taxi GWP","322 חלקים"),
 (122.4,127.8,"Ideas: 40889","Build, Paint and Play GWP","158 חלקים"),
]
for a,b,l1,l2,l3 in INFO:
    ev.append((a,b,"Info",f"{l1}\\N{l2}\\N{{\\fs88\\c&H00D7FF&}}{l3}"))
clipped=[]
for e in ev:
    if e[2]!="Main": clipped.append(e); continue
    for a,b in mg:
        lo,hi=max(e[0],a),min(e[1],b)
        if hi-lo>=0.04: clipped.append((lo,hi,e[2],e[3]))
ev=clipped
ev.sort(key=lambda e:(e[0],e[2]))
main=[i for i,e in enumerate(ev) if e[2]=="Main"]
for x,y in zip(main,main[1:]):
    if ev[x][1]>ev[y][0]: ev[x]=(ev[x][0],ev[y][0],ev[x][2],ev[x][3])
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
