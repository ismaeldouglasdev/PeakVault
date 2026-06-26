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
CORES = {"completo":"#4caf50","assistindo":"#8d5a97","planejado":"#ffa726","dropado":"#ef5350"}
PROJECT_DIR = Path(__file__).parent

# ── SESSION STATE ──
def init_session():
    for k,v in {"df":None,"df_name":None,"df_hash":None,"undo_stack":[],"undo_pos":-1,"gif_idx":0,
                "search":"","group_field":None,"show_chart":False,"upload_key":0}.items():
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
        --bg-primary: #1f1210;
        --bg-surface: #2a1a17;
        --bg-elevated: #35231f;
        --bg-hover: #40302b;
        --border: #6a505e;
        --accent: #8d5a97;
        --accent-glow: #8d5a9760;
        --text: #ffedac;
        --text-muted: #a4a5ae;
        --radius: 10px;
        --radius-sm: 6px;
    }
    /* ── Animações ── */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(20px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50%      { transform: translateY(-8px); }
    }
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 4px var(--accent-glow); }
        50%      { box-shadow: 0 0 16px var(--accent-glow); }
    }
    .hero-icon    { animation: float 3s ease-in-out infinite; }
    .hero-title   { animation: fadeUp 0.6s ease-out both; }
    .hero-sub     { animation: fadeUp 0.6s ease-out 0.15s both; }
    .hero-badges  { animation: fadeUp 0.6s ease-out 0.3s both; }
    .hero-features { animation: fadeUp 0.6s ease-out 0.45s both; }
    .hero-hint    { animation: fadeUp 0.6s ease-out 0.6s both; }
    .hero-features > div {
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .hero-features > div:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(141,90,151,.12);
    }
    .hero-badge {
        transition: transform 0.2s, box-shadow 0.2s, background 0.2s;
        cursor: default;
    }
    .hero-badge:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(141,90,151,.2);
        background: var(--bg-hover) !important;
    }
    .hero-card     { background: var(--bg-surface) !important; border: 1px solid var(--border) !important; }
    .hero-card-title { color: var(--text) !important; }
    .hero-card-desc  { color: var(--text-muted) !important; }
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

    /* Sidebar buttons full width */
    section[data-testid="stSidebar"] .stButton button { width: 100% !important; }
    /* Popover — mais largo/retangular */
    div[data-testid="stPopover"] > div[data-testid="stPopoverBody"] {
        min-width: 320px !important;
        max-width: 420px !important;
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 8px;
    }
    div[data-testid="stPopover"] button[kind="primary"] { width: 100% !important; }
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
    /* File upload chip */
    div[data-testid="stFileChip"] {
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
    }
    div[data-testid="stFileChip"] .stFileChipName {
        color: var(--text) !important;
    }
    div[data-testid="stFileChip"] small {
        color: var(--text-muted) !important;
    }
    div[data-testid="stFileUploaderDropzone"] {
        background: var(--bg-elevated) !important;
        border-color: var(--border) !important;
    }
    /* Stats cards — flex row com label */
    .stat-card {
        padding: 6px 8px !important;
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        min-height: 40px !important;
    }
    .stat-card .stat-emoji {
        font-size: 22px !important;
        line-height: 1 !important;
        flex-shrink: 0 !important;
    }
    .stat-card .stat-info {
        display: flex !important;
        flex-direction: column !important;
        line-height: 1.2 !important;
    }
    .stat-card .stat-number {
        font-size: 17px !important;
        font-weight: 700 !important;
    }
    .stat-card .stat-label {
        font-size: 10px !important;
        color: var(--text-muted) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.3px !important;
    }
    /* Select box — visivel */
    div[data-testid="stSelectbox"] > div > div {
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        min-height: 36px;
    }
    div[data-testid="stSelectbox"] > div > div:focus-within {
        border-color: var(--accent) !important;
    }
    div[data-testid="stSelectbox"] input,
    div[data-testid="stSelectbox"] [role="combobox"] {
        color: var(--text) !important;
    }
    div[role="listbox"] {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border) !important;
    }
    div[role="option"]:hover {
        background: var(--bg-hover) !important;
    }
    div[role="option"][aria-selected="true"] {
        background: rgba(141,90,151,.3) !important;
    }
    /* Group by + stats row spacing */
    .stSelectbox {
        margin-bottom: 8px !important;
        margin-top: 8px !important;
    }
    div[data-testid="column"] {
        gap: 4px !important;
    }
    section[data-testid="stMain"] div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        gap: 8px !important;
    }
    .stButton button[kind="primary"] {
        background: var(--accent) !important;
        color: #000 !important;
        border: none;
        font-weight: 600;
    }
    .stButton button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(141,90,151,.2); }
    div[data-testid="stButton"] { gap: 4px; }

    /* Data editor — escuro forçado */
    div[data-testid="stDataEditor"] {
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        background: #1a0e0c !important;
        font-size: 14px;
    }
    div[data-testid="stDataEditor"] table,
    div[data-testid="stDataEditor"] thead,
    div[data-testid="stDataEditor"] tbody,
    div[data-testid="stDataEditor"] tr,
    div[data-testid="stDataEditor"] td {
        background: transparent !important;
        color: var(--text) !important;
        border-color: rgba(106,80,94,.25) !important;
    }
    div[data-testid="stDataEditor"] thead,
    div[data-testid="stDataEditor"] th {
        background: #1f1210 !important;
        color: #a4a5ae !important;
        font-weight: 600 !important;
        border-bottom: 1px solid var(--border) !important;
    }
    div[data-testid="stDataEditor"] th:hover {
        background: #2a1a17 !important;
    }
    div[data-testid="stDataEditor"] td {
        background: #1a0e0c !important;
        border-bottom: 1px solid rgba(106,80,94,.15) !important;
    }
    div[data-testid="stDataEditor"] tr:nth-child(even) td {
        background: #1f1210 !important;
    }
    div[data-testid="stDataEditor"] input[type="checkbox"] {
        accent-color: #8d5a97 !important;
    }
    div[data-testid="stDataEditor"] input,
    div[data-testid="stDataEditor"] textarea {
        background: transparent !important;
        color: var(--text) !important;
    }
    div[data-testid="stDataEditor"] td:focus,
    div[data-testid="stDataEditor"] td:focus-within {
        background: #2a1a17 !important;
        outline: 2px solid var(--accent) !important;
        outline-offset: -2px;
    }
    div[data-testid="stDataEditor"] td.selected {
        background: rgba(141,90,151,.15) !important;
    }
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

    uploaded = st.file_uploader("Carregar JSON", type=["json"], label_visibility="collapsed",
        key=f"upload_{st.session_state.upload_key}")

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
            if st.button("✕ Fechar", key="btn_close", type="secondary"):
                for k in ["df","df_name","df_hash","undo_stack","undo_pos","group_field","show_chart"]:
                    st.session_state[k] = None if k in ("df","df_name","df_hash") else ([] if k=="undo_stack" else (False if k=="show_chart" else -1))
                st.session_state.upload_key += 1
                st.rerun()
        with col_dl:
            if st.session_state.df is not None:
                jb = st.session_state.df.to_json(orient="records", indent=2, force_ascii=False).encode()
                st.download_button("💾 JSON", jb, file_name=st.session_state.df_name or "dados.json",
                    mime="application/json", width="stretch")

        st.divider()
        st.text_input("🔍", placeholder="Buscar na lista... (filtra ao digitar)", key="search")

        st.markdown("##### Ações")
        c1,c2 = st.columns(2)
        with c1:
            with st.popover("➕ Novo", width="stretch"):
                cols = list(st.session_state.df.columns) if st.session_state.df is not None else ["nome"]
                if "tags" not in cols: cols = list(cols)+["tags"]
                entries = {}
                for col in cols:
                    entries[col] = st.text_input(col, key=f"add_{col}", placeholder=col)
                if st.button("Adicionar", type="primary"):
                    push_undo()
                    st.session_state.df = pd.concat(
                        [st.session_state.df, pd.DataFrame([{c:entries[c] for c in cols}])],
                        ignore_index=True)
                    st.rerun()
            with st.popover("🏷️ Tags", width="stretch"):
                df = st.session_state.df
                if df is not None and not df.empty and "tags" in df.columns:
                    nc = "nome" if "nome" in df.columns else df.columns[0]
                    names = df[nc].astype(str).tolist()
                    si = st.selectbox("Selecione:", range(len(names)), format_func=lambda i: names[i], key="tag_sel")
                    ts = {t.strip() for t in str(df.iloc[si].get("tags","")).split(",") if t.strip()}
                    if ts:
                        for i,tag in enumerate(sorted(ts)):
                            ca,cb = st.columns([3,1])
                            ca.markdown(f"`{tag}`")
                            if cb.button("✕", key=f"rt_{si}_{i}"):
                                ts.discard(tag); push_undo()
                                st.session_state.df.loc[df.index[si],"tags"] = ", ".join(sorted(ts))
                                st.rerun()
                    else:
                        st.caption("Nenhuma tag.")
                    nt = st.text_input("Nova tag:", key="new_tag")
                    if st.button("+ Adicionar"):
                        if nt.strip():
                            ts.add(nt.strip().lower()); push_undo()
                            if "tags" not in df.columns: st.session_state.df["tags"] = ""
                            st.session_state.df.loc[df.index[si],"tags"] = ", ".join(sorted(ts))
                            st.rerun()
                else:
                    st.caption("Nenhuma coluna 'tags'." if df is not None and "tags" not in df.columns else "Vazio.")
        with c2:
            with st.popover("❌ Excluir", width="stretch"):
                df = st.session_state.df
                if df is not None and not df.empty:
                    nc = "nome" if "nome" in df.columns else df.columns[0]
                    names = df[nc].astype(str).tolist()
                    sel = st.selectbox("Selecione:", names, key="del_sel")
                    if st.button("Excluir", type="primary"):
                        push_undo()
                        st.session_state.df = df.drop(index=df.index[names.index(sel)]).reset_index(drop=True)
                        st.rerun()
                else:
                    st.write("Nada para excluir.")
            if st.button("📥 CSV", key="btn_csv"):
                csv = st.session_state.df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button("📥 Download", csv,
                    file_name=(st.session_state.df_name or "dados").rsplit(".",1)[0]+".csv",
                    mime="text/csv", width="stretch")

        if is_anime_like(st.session_state.df):
            st.markdown("##### Status rápido")
            c1,c2 = st.columns(2)
            with c1:
                with st.popover("💔 Dropado", width="stretch"):
                    nome_drop = st.text_input("Nome:", key="drop_nome")
                    if st.button("Marcar como Dropado"):
                        push_undo()
                        nc = "nome" if "nome" in st.session_state.df.columns else st.session_state.df.columns[0]
                        nr = {c:"" for c in st.session_state.df.columns}
                        nr[nc] = nome_drop
                        if "nota" in nr: nr["nota"] = "--"
                        if "status" in nr: nr["status"] = "dropado"
                        st.session_state.df = pd.concat(
                            [st.session_state.df, pd.DataFrame([nr])], ignore_index=True)
                        st.rerun()
                if st.button("↩️ Desfazer", key="btn_undo"):
                    if undo(): st.rerun()
            with c2:
                with st.popover("⏳ Planejar", width="stretch"):
                    nome_plan = st.text_input("Nome:", key="plan_nome")
                    if st.button("Adicionar aos Planejados"):
                        push_undo()
                        nc = "nome" if "nome" in st.session_state.df.columns else st.session_state.df.columns[0]
                        nr = {c:"" for c in st.session_state.df.columns}
                        nr[nc] = nome_plan
                        if "nota" in nr: nr["nota"] = "--"
                        if "status" in nr: nr["status"] = "planejado"
                        st.session_state.df = pd.concat(
                            [st.session_state.df, pd.DataFrame([nr])], ignore_index=True)
                        st.rerun()
                if st.button("↪️ Refazer", key="btn_redo"):
                    if redo(): st.rerun()
        else:
            c1,c2 = st.columns(2)
            with c1:
                if st.button("↩️ Desfazer", key="btn_undo2"):
                    if undo(): st.rerun()
            with c2:
                if st.button("↪️ Refazer", key="btn_redo2"):
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
    col1, col2, col3 = st.columns([1,2.5,1])
    with col2:
        st.markdown("""
        <div style='text-align:center;padding:60px 10px;'>
            <div class='hero-icon' style='font-size:56px;margin-bottom:8px;'>🗂️</div>
            <h1 class='hero-title' style='margin:0 0 4px;font-size:32px;'>PeakVault</h1>
            <p class='hero-sub' style='color:var(--text-muted);margin:0 0 24px;font-size:16px;'>
                Gerenciador de listas JSON — edição, CRUD, busca, gráficos
            </p>
            <div class='hero-badges' style='display:flex;gap:8px;justify-content:center;margin-bottom:28px;flex-wrap:wrap;'>
                <span class='hero-badge' style='background:var(--bg-elevated);padding:4px 14px;border-radius:20px;font-size:13px;border:1px solid var(--border);'>🐍 Python</span>
                <span class='hero-badge' style='background:var(--bg-elevated);padding:4px 14px;border-radius:20px;font-size:13px;border:1px solid var(--border);'>📊 Streamlit</span>
                <span class='hero-badge' style='background:var(--bg-elevated);padding:4px 14px;border-radius:20px;font-size:13px;border:1px solid var(--border);'>🐼 Pandas</span>
                <span class='hero-badge' style='background:var(--bg-elevated);padding:4px 14px;border-radius:20px;font-size:13px;border:1px solid var(--border);'>📈 Matplotlib</span>
            </div>
            <div class='hero-features' style='background:var(--bg-elevated);border-radius:12px;padding:24px;border:1px solid var(--border);text-align:left;'>
                <p style='color:var(--text);margin:0 0 16px;font-weight:600;font-size:15px;'>📖 Como usar</p>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;'>
                    <div class='hero-card' style='border-radius:8px;padding:12px;'>
                        <div style='font-size:20px;margin-bottom:4px;'>📂</div>
                        <div class='hero-card-title' style='font-weight:600;font-size:13px;'>Upload</div>
                        <div class='hero-card-desc' style='font-size:12px;'>Carregue qualquer JSON</div>
                    </div>
                    <div class='hero-card' style='border-radius:8px;padding:12px;'>
                        <div style='font-size:20px;margin-bottom:4px;'>✏️</div>
                        <div class='hero-card-title' style='font-weight:600;font-size:13px;'>Edição</div>
                        <div class='hero-card-desc' style='font-size:12px;'>Edite inline na tabela</div>
                    </div>
                    <div class='hero-card' style='border-radius:8px;padding:12px;'>
                        <div style='font-size:20px;margin-bottom:4px;'>🔍</div>
                        <div class='hero-card-title' style='font-weight:600;font-size:13px;'>Busca</div>
                        <div class='hero-card-desc' style='font-size:12px;'>Filtro em tempo real</div>
                    </div>
                    <div class='hero-card' style='border-radius:8px;padding:12px;'>
                        <div style='font-size:20px;margin-bottom:4px;'>📊</div>
                        <div class='hero-card-title' style='font-weight:600;font-size:13px;'>Gráficos</div>
                        <div class='hero-card-desc' style='font-size:12px;'>Visualize agrupamentos</div>
                    </div>
                    <div class='hero-card' style='border-radius:8px;padding:12px;'>
                        <div style='font-size:20px;margin-bottom:4px;'>🏷️</div>
                        <div class='hero-card-title' style='font-weight:600;font-size:13px;'>Tags</div>
                        <div class='hero-card-desc' style='font-size:12px;'>Organize com etiquetas</div>
                    </div>
                    <div class='hero-card' style='border-radius:8px;padding:12px;'>
                        <div style='font-size:20px;margin-bottom:4px;'>📥</div>
                        <div class='hero-card-title' style='font-weight:600;font-size:13px;'>Exportar</div>
                        <div class='hero-card-desc' style='font-size:12px;'>JSON ou CSV</div>
                    </div>
                </div>
            </div>
            <p class='hero-hint' style='color:var(--text-muted);margin-top:20px;font-size:12px;'>
                Faça upload de um JSON na barra lateral para começar
            </p>
        </div>
""", unsafe_allow_html=True)

# Forcar cores do Glide Data Grid via componente HTML (script permitido)
st.components.v1.html("""
<script>
const s = document.createElement('style');
s.textContent = `
  :root {
    --gdg-accent-color: #8d5a97 !important;
    --gdg-accent-fg: #1f1210 !important;
    --gdg-bg-color: #1a0e0c !important;
    --gdg-header-bg-color: #1f1210 !important;
    --gdg-text-dark: #ffedac !important;
    --gdg-text-light: #a4a5ae !important;
    --gdg-border-color: rgba(106,80,94,.25) !important;
    --gdg-selection-color: rgba(141,90,151,.3) !important;
  }
`;
document.head.appendChild(s);
</script>
""", height=0, width=0)
st.stop()

df_current = st.session_state.df
stats = obter_stats(df_current)

# ── STATS ROW (HTML custom — st.metric é instável com emojis) ──
show_s = is_anime_like(df_current)
cols = st.columns(6)
cfg = [("📊","total","#ffedac","TOTAL"),("⭐","media","#8d5a97","MÉDIA"),("✅","completo","#4caf50","COMPLETO"),
       ("📺","assistindo","#907f9f","ASSISTINDO"),("⏳","planejado","#ffa726","PLANEJADO"),("💔","dropado","#ef5350","DROPADO")]
for col,(icon,key,c,label) in zip(cols,cfg):
    val = stats.get(key,0) if key!="media" else (stats.get("media","—") or "—")
    if key in ("completo","assistindo","planejado","dropado") and not show_s:
        col.empty(); continue
    col.markdown(f'<div class="stat-card"><span class="stat-emoji">{icon}</span><div class="stat-info"><span class="stat-number" style="color:{c};">{val}</span><span class="stat-label">{label}</span></div></div>', unsafe_allow_html=True)

# ── GROUP + CHART ──
df_filtered = get_filtered_df()
cg, cc = st.columns([3,1])
with cg:
    if df_current is not None:
        opts = [""] + list(df_current.columns)
        idx = opts.index(st.session_state.group_field) if st.session_state.group_field in opts else 0
        sel = st.selectbox("🗂️ Agrupar por coluna", options=opts, index=idx)
        st.session_state.group_field = sel if sel else None
with cc:
    st.markdown("<br>",unsafe_allow_html=True)
    if st.button("📊 Gráfico", key="btn_chart"):
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
    st.markdown("<div style='text-align:center;padding:40px;color:var(--text-muted);'>📭 Nenhum item encontrado.</div>", unsafe_allow_html=True)

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
            bars =             ax.bar(vc.index, vc.values, color="#8d5a97", width=0.55, edgecolor="#8d5a9780", linewidth=0.5)
            ax.set_title(f"Distribuição por {coluna}", fontsize=14, color="#ffedac", pad=12)
            ax.set_ylabel("Contagem", color="#a4a5ae")
            ax.tick_params(colors="#a4a5ae")
            ax.set_facecolor("#3e2723")
            fig.patch.set_facecolor("#3e2723")
            for spine in ax.spines.values(): spine.set_visible(False)
            ax.grid(axis="y", alpha=0.1)
            plt.xticks(rotation=35, ha="right", color="#a4a5ae")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.caption("Dados insuficientes para o gráfico.")
    else:
        st.caption("Selecione uma coluna para agrupar.")


