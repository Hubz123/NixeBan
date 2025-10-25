import io
from typing import List, Set
try:
    from PIL import Image, ImageSequence
except Exception:
    Image=None; ImageSequence=None
try:
    import imagehash
except Exception:
    imagehash=None

def dhash_list_from_bytes(data:bytes,max_frames:int=6)->List[str]:
    out=[]
    if not data or not Image: return out
    def _d(img):
        g=img.convert('L').resize((9,8)); px=list(g.getdata()); w,h=g.size; bits=[]
        for y in range(h):
            row=px[y*w:(y+1)*w]
            for x in range(w-1): bits.append(1 if row[x]<row[x+1] else 0)
        v=0
        for b in bits: v=(v<<1)|b
        return f"{v:0{len(bits)//4}x}"
    im=Image.open(io.BytesIO(data))
    frames=ImageSequence.Iterator(im) if getattr(im,'is_animated',False) else [im]
    seen=set(); c=0
    for fr in frames:
        hs=_d(fr.copy())
        if hs and hs not in seen: seen.add(hs); out.append(hs)
        c+=1
        if c>=max_frames: break
    return out

def phash_list_from_bytes(data:bytes,max_frames:int=6)->List[str]:
    out=[]
    if not data or not Image or not imagehash: return out
    im=Image.open(io.BytesIO(data))
    frames=ImageSequence.Iterator(im) if getattr(im,'is_animated',False) else [im]
    seen=set(); c=0
    for fr in frames:
        h=str(imagehash.phash(fr.copy().convert('RGB')))
        if h not in seen: seen.add(h); out.append(h)
        c+=1
        if c>=max_frames: break
    return out
