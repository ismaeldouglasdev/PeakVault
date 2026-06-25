import streamlit as st
import pandas as pd
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
import logica

# ── CONFIG ──
st.set_page_config(page_title="PeakVault", page_icon="🗂️", layout="wide")
CORES = {"completo":"#4caf50","assistindo":"#03a9f4","planejado":"#ffa726","dropado":"#ef5350"}
PROJECT_DIR = Path(__file__).parent

# ── SESSION STATE ──
def init_session():
    for k,v in {"df":None,"df_name":None,"df_hash":None,"undo_stack":[],"undo_pos":-1,"gif_idx":0,
                "search":"","group_field":None,"show_add_dialog":False,"show_delete_dialog":False,
                "show_tags_dialog":False,"show_chart":False}.items():
        if k not in st.session_state: st.session_state[k]=v
init_session()

# ── HELPERS ──
def push_undo():
    if st.session_state.df is not None:
        snap = st.session_state.df.to_dict(orient="records")
        stack = st.session_state.undo_stack[:st.session_state.undo_pos+1]
        stack.append(snap)
        if len(stack)>50: stack.pop(0)
        st.session_state.undo_stack = stack
        st.session_state.undo_pos = len(stack)-1

def undo():
    if st.session_state.undo_pos>0:
        st.session_state.undo_pos-=1
        st.session_state.df = pd.DataFrame(st.session_state.undo_stack[st.session_state.undo_pos])
        return True
    return False

def redo():
    if st.session_state.undo_pos<len(st.session_state.undo_stack)-1:
        st.session_state.undo_pos+=1
        st.session_state.df = pd.DataFrame(st.session_state.undo_stack[st.session_state.undo_pos])
        return True
    return False

def obter_stats(df):
    if df is None or df.empty: return {"total":0,"media":None,"completo":0,"assistindo":0,"planejado":0,"dropado":0}
    s={"total":len(df)}
    if "nota" in df.columns:
        n=pd.to_numeric(df["nota"],errors="coerce")
        s["media"]=round(n.mean(),1) if not n.isna().all() else None
    if "status" in df.columns:
        for st_ in ("completo","assistindo","planejado","dropado"): s[st_]=int((df["status"]==st_).sum())
    return s

def get_filtered_df():
    df=st.session_state.df
    if df is None or df.empty: return df
    q=st.session_state.search.strip().lower()
    return df if not q else df[df.apply(lambda r:any(q in str(v).lower() for v in r.values),axis=1)]

def is_anime_like(df): return df is not None and {"nome","nota","status"}.issubset(set(df.columns))

# ═══════════════════════════════════════════════════════════════════
# CSS DESIGN SYSTEM
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    :root {
        --bg-primary: #0d0d1a;
        --bg-surface: #16162a;
        --bg-elevated: #1e1e38;
        --bg-hover: #282848;
        --border: #2a2a4a;
        --accent: #03a9f4;
        --accent-glow: #03a9f480;
        --text: #e8e8f0;
        --text-muted: #8888aa;
        --radius: 10px;
        --radius-sm: 6px;
    }
    .stApp { background: var(--bg-primary); }
    .stApp header { background: var(--bg-surface) !important; border-bottom: 1px solid var(--border); }
    section[data-testid="stSidebar"] > div:first-child {
        background: var(--bg-surface) !important;
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] .st-emotion-cache-1wbqy5s { gap: 4px; }

    /* Headers */
    h1, h2, h3, h4 { color: var(--text) !important; font-weight: 600 !important; }
    .stMarkdown, .stCaption, p, li { color: var(--text); }

    /* Cards */
    /* Stats cards custom (substitui st.metric) */
    .stat-card {
        background: var(--bg-elevated); border: 1px solid var(--border);
        border-radius: var(--radius); padding: 8px 12px 4px;
        text-align: center;
    }
    .stat-card .stat-emoji { font-size: 32px; line-height: 1.2; display: block; }
    .stat-card .stat-number {
        font-size: 22px; font-weight: 700; display: block;
        color: var(--text); margin-top: -2px;
    }

    /* Buttons */
    .stButton button {
        border-radius: var(--radius-sm);
        font-weight: 500;
        transition: all .15s;
        border: 1px solid var(--border);
    }
    .stButton button[kind="primary"] {
        background: var(--accent) !important;
        color: #000 !important;
        border: none;
        font-weight: 600;
    }
    .stButton button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(3,169,244,.15); }
    div[data-testid="stButton"] { gap: 4px; }

    /* Data editor */
    div[data-testid="stDataEditor"] {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        background: var(--bg-primary);
        font-size: 14px;
    }
    div[data-testid="stDataEditor"] table { background: var(--bg-primary); }
    div[data-testid="stDataEditor"] th {
        background: var(--bg-elevated) !important;
        color: var(--text) !important;
        font-weight: 600 !important;
        border-bottom: 1px solid var(--border) !important;
    }
    div[data-testid="stDataEditor"] td {
        background: var(--bg-primary) !important;
        color: var(--text) !important;
        border-bottom: 1px solid var(--border) !important;
    }
    div[data-testid="stDataEditor"] td:focus {
        background: var(--bg-hover) !important;
        box-shadow: inset 0 0 0 2px var(--accent);
    }
    div[data-testid="stDataEditor"] .dvn-scroller { background: var(--bg-primary); }

    /* Select boxes */
    div[data-testid="stSelectbox"] > label {
        color: var(--text-muted) !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }
    div[data-testid="stSelectbox"] > div > div {
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        color: var(--text);
    }
    div[data-testid="stSelectbox"] > div > div:focus { border-color: var(--accent); }
    .stSelectbox [data-baseweb="select"] { margin-top: 0 !important; }
    div[data-testid="stSelectbox"] { gap: 2px !important; }

    /* Text inputs */
    div[data-testid="stTextInput"] input {
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        color: var(--text);
    }
    div[data-testid="stTextInput"] input:focus { border-color: var(--accent); }

    /* File uploader */
    div[data-testid="stFileUploader"] section {
        background: var(--bg-elevated);
        border: 1px dashed var(--border);
        border-radius: var(--radius);
    }
    div[data-testid="stFileUploader"] section:hover { border-color: var(--accent); }

    /* Expander */
    div[data-testid="stExpander"] {
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
    }
    div[data-testid="stExpander"] summary { color: var(--text); font-weight: 500; }

    /* Dialog / Modal */
    div[data-testid="stDialog"] > div {
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
    }
    div[data-testid="stDialog"] div[role="dialog"] {
        background: var(--bg-surface);
    }

    /* Divider */
    hr { border-color: var(--border) !important; margin: 12px 0 !important; }

    /* Caption / helper text */
    .stCaption { color: var(--text-muted) !important; }

    /* Tabs (if any) */
    button[data-testid="stTab"] {
        color: var(--text-muted);
        border-bottom: 2px solid transparent;
    }
    button[data-testid="stTab"][aria-selected="true"] {
        color: var(--accent);
        border-bottom-color: var(--accent);
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: var(--bg-hover); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--border); }

    /* Status message banner */
    .stAlert { border-radius: var(--radius-sm); border: 1px solid var(--border); }
    div[data-testid="stNotification"] { border: 1px solid var(--border); }

    /* Download button */
    .stDownloadButton button {
        border-radius: var(--radius-sm);
        font-weight: 500;
    }

    /* Remove Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stAppDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🗂️ PeakVault")
    st.caption("Gerenciador de listas JSON")
    st.divider()

    uploaded = st.file_uploader("Carregar JSON", type=["json"], label_visibility="collapsed")

    uploaded_hash = hash(uploaded.read()) if uploaded else None
    if uploaded and uploaded_hash != st.session_state.df_hash:
        try:
            uploaded.seek(0)
            data = json.loads(uploaded.read())
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            if not df.empty:
                push_undo()
                st.session_state.df = df
                st.session_state.df_name = uploaded.name
                st.session_state.df_hash = uploaded_hash
                st.session_state.group_field = None
                st.session_state.show_chart = False
        except Exception as e:
            st.error(f"Erro: {e}")

    has_data = st.session_state.df is not None and not st.session_state.df.empty

    if has_data:
        st.caption(f"📄 {st.session_state.df_name} — {len(st.session_state.df)} itens")

        col_close, col_dl = st.columns(2)
        with col_close:
            if st.button("✕ Fechar", use_container_width=True, type="secondary"):
                for k in ["df","df_name","df_hash","undo_stack","undo_pos","group_field","show_chart"]:
                    st.session_state[k] = None if k in ("df","df_name","df_hash") else ([] if k=="undo_stack" else (False if k=="show_chart" else -1))
                st.rerun()
        with col_dl:
            if st.session_state.df is not None:
                jb = st.session_state.df.to_json(orient="records", indent=2, force_ascii=False).encode()
                st.download_button("💾 JSON", jb, file_name=st.session_state.df_name or "dados.json",
                    mime="application/json", width="stretch")

        st.divider()
        st.text_input("🔍", placeholder="Buscar na lista...", key="search", label_visibility="collapsed")

        st.markdown("##### Ações")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("➕ Novo", use_container_width=True): st.session_state.show_add_dialog=True
            if st.button("🏷️ Tags", use_container_width=True): st.session_state.show_tags_dialog=True
        with c2:
            if st.button("❌ Excluir", use_container_width=True): st.session_state.show_delete_dialog=True
            if st.button("📥 CSV", use_container_width=True):
                csv = st.session_state.df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button("📥 Download", csv,
                    file_name=(st.session_state.df_name or "dados").rsplit(".",1)[0]+".csv",
                    mime="text/csv", width="stretch")

        if is_anime_like(st.session_state.df):
            st.markdown("##### Status rápido")
            c1,c2 = st.columns(2)
            with c1:
                if st.button("💔 Dropado", use_container_width=True): st.session_state.show_add_dialog="dropado"
                if st.button("↩️ Desfazer", use_container_width=True):
                    if undo(): st.rerun()
            with c2:
                if st.button("⏳ Planejar", use_container_width=True): st.session_state.show_add_dialog="planejado"
                if st.button("↪️ Refazer", use_container_width=True):
                    if redo(): st.rerun()
        else:
            c1,c2 = st.columns(2)
            with c1:
                if st.button("↩️ Desfazer", use_container_width=True):
                    if undo(): st.rerun()
            with c2:
                if st.button("↪️ Refazer", use_container_width=True):
                    if redo(): st.rerun()

    # GIF aleatório (nova imagem a cada interação)
    import random
    st.divider()
    gif_dir = PROJECT_DIR / "gifs"
    gifs = sorted(gif_dir.glob("*.gif")) if gif_dir.is_dir() else []
    if gifs:
        gif_idx = random.randint(0, len(gifs)-1)
        st.image(str(gifs[gif_idx]), width=250)

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
if not has_data:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px;'>
            <div style='font-size:48px;margin-bottom:16px;'>🗂️</div>
            <h3 style='margin-bottom:8px;'>PeakVault</h3>
            <p style='color:#8888aa;margin-bottom:24px;'>Carregue um arquivo JSON no menu lateral para começar.</p>
            <div style='background:#1e1e38;border-radius:10px;padding:20px;text-align:left;border:1px solid #2a2a4a;'>
                <p style='color:#e8e8f0;margin:0 0 8px 0;font-weight:600;'>📖 Como usar</p>
                <ol style='color:#8888aa;margin:0;padding-left:20px;'>
                    <li>Faça upload de um JSON (array de objetos) no menu à esquerda</li>
                    <li>Edite os dados diretamente na tabela</li>
                    <li>Adicione, exclua e busque itens</li>
                    <li>Exporte em JSON ou CSV</li>
                </ol>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

df_current = st.session_state.df
stats = obter_stats(df_current)

# ── STATS ROW (HTML custom — st.metric é instável com emojis) ──
show_s = is_anime_like(df_current)
cols = st.columns(6)
cfg = [("📊","total","#fff"),("⭐","media","#03a9f4"),("✅","completo","#4caf50"),
       ("📺","assistindo","#03a9f4"),("⏳","planejado","#ffa726"),("💔","dropado","#ef5350")]
for col,(icon,key,c) in zip(cols,cfg):
    val = stats.get(key,0) if key!="media" else (stats.get("media","—") or "—")
    if key in ("completo","assistindo","planejado","dropado") and not show_s:
        col.empty(); continue
    col.markdown(f'<div class="stat-card"><span class="stat-emoji">{icon}</span><span class="stat-number" style="color:{c};">{val}</span></div>', unsafe_allow_html=True)

# ── GROUP + CHART ──
df_filtered = get_filtered_df()
cg, cc = st.columns([3,1])
with cg:
    if df_current is not None:
        opts = [""] + list(df_current.columns)
        idx = opts.index(st.session_state.group_field) if st.session_state.group_field in opts else 0
        sel = st.selectbox("📊 Agrupar por coluna", options=opts, index=idx)
        st.session_state.group_field = sel if sel else None
with cc:
    st.markdown("<br>",unsafe_allow_html=True)
    if st.button("📊 Gráfico", use_container_width=True):
        st.session_state.show_chart = not st.session_state.show_chart
        st.rerun()

# ── DATA EDITOR ──
if df_filtered is not None and not df_filtered.empty:
    display_df = df_filtered.copy().reset_index(drop=True)
    if st.session_state.group_field and st.session_state.group_field in display_df.columns:
        display_df[st.session_state.group_field] = display_df[st.session_state.group_field].astype(str)
        display_df = display_df.sort_values(by=st.session_state.group_field, na_position="last").reset_index(drop=True)

    edited = st.data_editor(display_df, width="stretch", num_rows="dynamic",
        key="data_editor",
        column_config={c: st.column_config.TextColumn(c, width="medium") for c in display_df.columns})

    if edited is not None and not edited.equals(display_df):
        push_undo()
        st.session_state.df = edited

    if st.session_state.search.strip():
        st.caption(f"{len(df_filtered)} resultado(s) para \"{st.session_state.search}\"")
else:
    st.markdown("<div style='text-align:center;padding:40px;color:#8888aa;'>📭 Nenhum item encontrado.</div>", unsafe_allow_html=True)

# ── CHART ──
if st.session_state.show_chart and df_current is not None and not df_current.empty:
    coluna = st.session_state.group_field
    if not coluna or coluna not in df_current.columns:
        for c in ("status","categoria","tag",df_current.columns[0]):
            if c in df_current.columns and df_current[c].dtype==object: coluna=c; break
    if coluna and coluna in df_current.columns:
        vc = df_current[coluna].astype(str).value_counts()
        if not vc.empty:
            fig,ax = plt.subplots(figsize=(10,4))
            bars = ax.bar(vc.index, vc.values, color="#03a9f4", width=0.55, edgecolor="#03a9f480", linewidth=0.5)
            ax.set_title(f"Distribuição por {coluna}", fontsize=14, color="#e8e8f0", pad=12)
            ax.set_ylabel("Contagem", color="#8888aa")
            ax.tick_params(colors="#8888aa")
            ax.set_facecolor("#0d0d1a")
            fig.patch.set_facecolor("#0d0d1a")
            for spine in ax.spines.values(): spine.set_visible(False)
            ax.grid(axis="y", alpha=0.1)
            plt.xticks(rotation=35, ha="right", color="#8888aa")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.caption("Dados insuficientes para o gráfico.")
    else:
        st.caption("Selecione uma coluna para agrupar.")

# ═══════════════════════════════════════════════════════════════════
# DIALOGS (inline forms — st.dialog com context manager é instável)
# ═══════════════════════════════════════════════════════════════════

if st.session_state.show_add_dialog:
    st.markdown("---")
    st.markdown("##### ➕ Novo Item")
    preset = st.session_state.show_add_dialog if isinstance(st.session_state.show_add_dialog,str) else None
    cols = list(st.session_state.df.columns) if st.session_state.df is not None else ["nome"]
    if "tags" not in cols: cols = list(cols)+["tags"]
    entries = {}
    for col in cols:
        entries[col] = st.text_input(col, value=(col=="status" and preset) or "", key=f"add_{col}", placeholder=col)
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Adicionar", use_container_width=True, type="primary"):
            push_undo()
            st.session_state.df = pd.concat(
                [st.session_state.df, pd.DataFrame([{c:entries[c] for c in cols}])],
                ignore_index=True)
            st.session_state.show_add_dialog = False
            st.rerun()
    with c2:
        if st.button("Cancelar", use_container_width=True): st.session_state.show_add_dialog=False; st.rerun()

if st.session_state.show_delete_dialog:
    st.markdown("---")
    st.markdown("##### ❌ Excluir Item")
    df = st.session_state.df
    if df is not None and not df.empty:
        nc = "nome" if "nome" in df.columns else df.columns[0]
        names = df[nc].astype(str).tolist()
        sel = st.selectbox("Selecione:", names)
        c1,c2 = st.columns(2)
        with c1:
            if st.button("Excluir", use_container_width=True, type="primary"):
                push_undo()
                st.session_state.df = df.drop(index=df.index[names.index(sel)]).reset_index(drop=True)
                st.session_state.show_delete_dialog = False
                st.rerun()
        with c2:
            if st.button("Cancelar", use_container_width=True): st.session_state.show_delete_dialog=False; st.rerun()
    else:
        st.write("Nada para excluir.")
        if st.button("Fechar"): st.session_state.show_delete_dialog=False; st.rerun()

if st.session_state.show_tags_dialog:
    st.markdown("---")
    st.markdown("##### 🏷️ Tags")
    df = st.session_state.df
    if df is not None and not df.empty and "tags" in df.columns:
        nc = "nome" if "nome" in df.columns else df.columns[0]
        names = df[nc].astype(str).tolist()
        si = st.selectbox("Selecione:", range(len(names)), format_func=lambda i: names[i])
        ts = {t.strip() for t in str(df.iloc[si].get("tags","")).split(",") if t.strip()}
        if ts:
            for i,tag in enumerate(sorted(ts)):
                c1,c2 = st.columns([3,1])
                c1.markdown(f"`{tag}`")
                if c2.button("✕", key=f"rt_{si}_{i}"):
                    ts.discard(tag); push_undo()
                    st.session_state.df.loc[df.index[si],"tags"] = ", ".join(sorted(ts))
                    st.rerun()
        else:
            st.caption("Nenhuma tag.")
        nt = st.text_input("Nova tag:", key="new_tag")
        if st.button("+ Adicionar", use_container_width=True):
            if nt.strip():
                ts.add(nt.strip().lower()); push_undo()
                if "tags" not in df.columns: st.session_state.df["tags"] = ""
                st.session_state.df.loc[df.index[si],"tags"] = ", ".join(sorted(ts))
                st.rerun()
        if st.button("Fechar", use_container_width=True): st.session_state.show_tags_dialog=False; st.rerun()
    else:
        st.write("Nenhuma coluna 'tags'." if df is not None and "tags" not in df.columns else "Vazio.")
        if st.button("Fechar"): st.session_state.show_tags_dialog=False; st.rerun()
