"""Ujian asap: jalankan app.py dengan Streamlit palsu (tanpa pelayar).

Guna:  python smoke_test_app.py
Menyemak: app berjalan hingga habis selepas Generate, tiada expander bersarang,
tiada widget berkunci sama, dan memaparkan jadual pair yang telah disusun.
Tidak menggantikan ujian di Streamlit sebenar.
"""
import sys, types, functools, traceback, os
HERE=os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE); sys.path.insert(0,HERE)

LOG=[]  # (api, label)
DFS=[]; STACK=[]; PROBLEMS=[]; WIDGETS={}
def _widget(kind,label,key):
    ident=(kind,key if key else label)
    if ident in WIDGETS: PROBLEMS.append(f'DUPLIKAT WIDGET {ident}')
    WIDGETS[ident]=1
    LOG.append(('@'+'/'.join(STACK[-3:]),f'{kind}: {label}'))

class DG:
    def __init__(s,name='dg'): s._n=name
    def __enter__(s): STACK.append(s._n); LOG.append(('enter',s._n)); return s
    def __exit__(s,*a): STACK.pop(); LOG.append(('exit',s._n)); return False
    def __getattr__(s,name):
        if name.startswith('__'): raise AttributeError(name)
        return lambda *a,**k: (LOG.append((name,str(a[0])[:70] if a else '')), None)[1]
    def columns(s,spec,**k): n=spec if isinstance(spec,int) else len(spec); LOG.append(('columns',n)); return [DG('col') for _ in range(n)]
    def tabs(s,labels,**k): LOG.append(('tabs',list(labels))); return [DG('tab:'+l) for l in labels]
    def container(s,**k): LOG.append(('container','')); return DG('container')
    def expander(s,label,**k):
        if any(x.startswith('expander') for x in STACK): PROBLEMS.append(f'EXPANDER BERSARANG: {label} dalam {STACK}')
        LOG.append(('expander',label)); return DG('expander:'+label[:30])
    def form(s,key,**k): LOG.append(('form',key)); return DG('form')
    def spinner(s,*a,**k): return DG('spinner')
    def text_input(s,label,value='',**k): _widget('text_input',label,k.get('key')); return value
    def selectbox(s,label,options,index=0,**k): _widget('selectbox',label,k.get('key')); o=list(options); return o[index] if o else None
    def radio(s,label,options,index=0,**k): _widget('radio',label,k.get('key')); o=list(options); return o[index]
    def button(s,label,**k):
        _widget('button',label,k.get('key'))
        return k.get('key') in set(filter(None,os.environ.get('FORCE_BUTTONS','').split(',')))
    def form_submit_button(s,label='',**k): return label=='Generate'
    def checkbox(s,*a,**k): return False
    def toggle(s,*a,**k): return False
    def number_input(s,label,value=0,**k): return value
    def multiselect(s,label,options,default=None,**k): return default or []
    def file_uploader(s,*a,**k): return None
    def download_button(s,*a,**k): return False
    def text_area(s,label,value='',**k): return value
    def date_input(s,label,value=None,**k): return value
    def slider(s,label,min_value=0,max_value=100,value=None,**k): return value if value is not None else min_value
    def markdown(s,body,**k): LOG.append(('markdown',str(body)[:90]))
    def dataframe(s,df,**k):
        DFS.append(df); LOG.append(('dataframe',len(df) if hasattr(df,'__len__') else ''))

class State(dict):
    def __getattr__(s,k):
        try: return s[k]
        except KeyError: raise AttributeError(k)
    def __setattr__(s,k,v): s[k]=v
class Secrets(dict):
    def __getitem__(s,k): raise KeyError(k)
    def get(s,k,d=None): return d

st=types.ModuleType('streamlit'); root=DG('root')
for n in dir(DG):
    if not n.startswith('_'): setattr(st,n,getattr(root,n))
def __getattr__(name):
    if name.startswith('__'): raise AttributeError(name)
    return getattr(root,name)
st.__getattr__=__getattr__
st.session_state=State(); st.secrets=Secrets(); st.sidebar=DG('sidebar')
def cache_data(*a,**k):
    def deco(f):
        f.clear=lambda *x,**y:None; return f
    return deco(a[0]) if a and callable(a[0]) else deco
st.cache_data=cache_data; st.cache_resource=cache_data
st.set_page_config=lambda *a,**k:None
st.rerun=lambda *a,**k:LOG.append(('rerun',''))
def _stop(): raise SystemExit('st.stop')
st.stop=_stop
comp=types.ModuleType('streamlit.components'); v1=types.ModuleType('streamlit.components.v1')
v1.html=lambda *a,**k:LOG.append(('components.html','')); comp.v1=v1
st.components=comp
sys.modules.update({'streamlit':st,'streamlit.components':comp,'streamlit.components.v1':v1})

src=open(sys.argv[1] if len(sys.argv)>1 else 'app.py',encoding='utf-8').read()
g={'__name__':'__main__','__file__':'app.py'}
try:
    exec(compile(src,'app.py','exec'),g)
    print('RUN OK; ui calls:',len(LOG))
except SystemExit as e: print('stopped',e)
except Exception:
    traceback.print_exc(); print('RUN FAILED at ui call',len(LOG))
# ringkasan susunan
depth=0; out=[]
for api,label in LOG:
    if api in('tabs','container','expander','form') or api in ('metric','code','info','warning','success','subheader','selectbox') or (api=='markdown' and 'engine-head' in str(label)) or (api=='markdown' and 'panel-title' in str(label)):
        out.append(f'{api}: {label}')
import json; open(os.path.join(HERE,'ui_log.txt'),'w').write('\n'.join(f'{a}\t{b}' for a,b in LOG))
print('MASALAH:',PROBLEMS if PROBLEMS else 'tiada')
print('\n'.join(out[:60]))

import pandas as pd
pd.set_option('display.width',200,'display.max_columns',20)
for d in DFS:
    if hasattr(d,'columns') and '#' in list(d.columns): print(d.to_string(index=False)); print()
