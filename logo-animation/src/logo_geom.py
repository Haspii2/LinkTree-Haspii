"""Vector reconstruction of logo.png: fitted straight edges + circular fillets.
Coordinates: source-pixel-centre space of the 256x256 PNG."""
import numpy as np, json, os
_HERE=os.path.dirname(os.path.abspath(__file__))

def _intersect(m1,d1,m2,d2):
    A=np.array([d1,-d2]).T; t=np.linalg.solve(A,m2-m1); return m1+t[0]*d1

def build(fit_path=os.path.join(_HERE,'fit.json'), arc_step_deg=1.0, sharp_below=1.2):
    fit=json.load(open(fit_path))
    polys=[]
    for pc in fit:
        lines=[(np.array(m),np.array(d)) for m,d in pc['lines']]
        k=len(lines); pts=[]
        for j in range(k):
            m1,d1=lines[j]; m2,d2=lines[(j+1)%k]
            P=_intersect(m1,d1,m2,d2)
            cn=pc['corners'][j]
            r=cn['r_ls'] if cn['rms']<1.0 else cn['r_d']
            if r<sharp_below:
                pts.append(P); continue
            if cn.get('bez'):
                a,b,h1,h2=cn['bez']
                P0=P-d1*a; P3=P+d2*b; P1=P0+d1*a*h1; P2=P3-d2*b*h2
                for t in np.linspace(0,1,max(24,int((a+b)*2))+1):
                    pts.append((1-t)**3*P0+3*(1-t)**2*t*P1+3*(1-t)*t**2*P2+t**3*P3)
                continue
            th=np.arccos(np.clip((-d1)@d2,-1,1))
            bis=(-d1+d2); bis/=np.linalg.norm(bis)
            ctr=P+bis*r/np.sin(th/2)
            tl=r/np.tan(th/2)
            T1=P-d1*tl; T2=P+d2*tl
            a1=np.arctan2(*(T1-ctr)[::-1]); a2=np.arctan2(*(T2-ctr)[::-1])
            da=(a2-a1+np.pi)%(2*np.pi)-np.pi
            nseg=max(4,int(np.ceil(abs(np.degrees(da))/arc_step_deg)))
            for s in np.linspace(0,1,nseg+1):
                a=a1+da*s; pts.append(ctr+r*np.array([np.cos(a),np.sin(a)]))
        polys.append(np.array(pts))
    return polys
