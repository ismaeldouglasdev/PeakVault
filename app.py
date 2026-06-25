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
st.set_page_config(
    page_title="PeakVault",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CORES = {
    "completo": "#4caf50",
    "assistindo": "#03a9f4",
    "planejado": "#ffa726",
    "dropado": "#ef5350",
}

PROJECT_DIR = Path(__file__).parent

# ── SESSION STATE ──
def init_session():
    defaults = {
        "df": None, "df_name": None, "df_hash": None,
        "undo_stack": [], "undo_pos": -1,
        "search": "", "group_field": None,
        "show_add_dialog": False, "show_delete_dialog": False,
        "show_tags_dialog": False, "show_chart": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ── HELPERS ──
def push_undo():
    if st.session_state.df is not None:
        snap = st.session_state.df.to_dict(orient="records")
        stack = st.session_state.undo_stack[: st.session_state.undo_pos + 1]
        stack.append(snap)
        if len(stack) > 50:
            stack.pop(0)
        st.session_state.undo_stack = stack
        st.session_state.undo_pos = len(stack) - 1

def undo():
    if st.session_state.undo_pos > 0:
        st.session_state.undo_pos -= 1
        st.session_state.df = pd.DataFrame(st.session_state.undo_stack[st.session_state.undo_pos])
        st.toast("↩️ Desfeito", icon="↩️")
        return True
    st.toast("⚠️ Nada para desfazer", icon="⚠️")
    return False

def redo():
    if st.session_state.undo_pos < len(st.session_state.undo_stack) - 1:
        st.session_state.undo_pos += 1
        st.session_state.df = pd.DataFrame(st.session_state.undo_stack[st.session_state.undo_pos])
        st.toast("↪️ Refito", icon="↪️")
        return True
    st.toast("⚠️ Nada para refazer", icon="⚠️")
    return False

def obter_stats(df):
    if df is None or df.empty:
        return {"total": 0, "media": None, "completo": 0, "assistindo": 0, "planejado": 0, "dropado": 0}
    stats = {"total": len(df)}
    if "nota" in df.columns:
        notas = pd.to_numeric(df["nota"], errors="coerce")
        stats["media"] = round(notas.mean(), 1) if not notas.isna().all() else None
    else:
        stats["media"] = None
    if "status" in df.columns:
        for s in ("completo", "assistindo", "planejado", "dropado"):
            stats[s] = int((df["status"] == s).sum())
    return stats

def get_filtered_df():
    df = st.session_state.df
    if df is None or df.empty:
        return df
    q = st.session_state.search.strip().lower()
    if not q:
        return df
    return df[df.apply(lambda row: any(q in str(v).lower() for v in row.values), axis=1)]

def is_anime_like(df):
    return df is not None and {"nome", "nota", "status"}.issubset(set(df.columns))

# ── CSS ──
st.markdown("""
<style>
    .stat-card {
        background: #1a1a2e; border-radius: 8px; padding: 6px 12px;
        display: flex; align-items: center; gap: 6px; height: 42px;
    }
    .stat-icon { font-size: 16px; }
    .stat-value { font-size: 18px; font-weight: 700; }
    .stat-value.total { color: #ffffff; }
    .stat-value.media { color: #03a9f4; }
    .stat-value.completo { color: #4caf50; }
    .stat-value.assistindo { color: #03a9f4; }
    .stat-value.planejado { color: #ffa726; }
    .stat-value.dropado { color: #ef5350; }
    div[data-testid="stDataEditor"] { font-size: 14px; }
    button[kind="primary"] { font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗂️ PeakVault")
    st.divider()

    uploaded = st.file_uploader("Carregar lista JSON", type=["json"], label_visibility="collapsed")

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
                st.success(f"📂 Carregado: {uploaded.name}")
        except Exception as e:
            st.error(f"Erro ao ler JSON: {e}")

    has_data = st.session_state.df is not None and not st.session_state.df.empty

    if has_data:
        st.caption(f"📄 **{st.session_state.df_name}** ({len(st.session_state.df)} itens)")

        col_close, col_dl = st.columns(2)
        with col_close:
            if st.button("✕ Fechar", width="stretch", type="secondary"):
                st.session_state.df = None
                st.session_state.df_name = None
                st.session_state.undo_stack = []
                st.session_state.undo_pos = -1
                st.session_state.group_field = None
                st.session_state.show_chart = False
                st.rerun()
        with col_dl:
            if st.session_state.df is not None:
                json_bytes = st.session_state.df.to_json(orient="records", indent=2, force_ascii=False).encode("utf-8")
                st.download_button("💾 JSON", data=json_bytes,
                    file_name=st.session_state.df_name or "dados.json", mime="application/json",
                    width="stretch")

        st.divider()
        st.text_input("🔍 Buscar", placeholder="Filtrar...", key="search", label_visibility="collapsed")
        st.divider()

        # Ações em grupos com expander
        with st.expander("📋 Ações", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                if st.button("➕ Novo", width="stretch", key="btn_add"):
                    st.session_state.show_add_dialog = True
            with c2:
                if st.button("❌ Excluir", width="stretch", key="btn_del"):
                    st.session_state.show_delete_dialog = True

            c3, c4 = st.columns(2)
            with c3:
                if st.button("🏷️ Tags", width="stretch", key="btn_tags"):
                    st.session_state.show_tags_dialog = True
            with c4:
                if st.button("📥 CSV", width="stretch", key="btn_csv"):
                    csv = st.session_state.df.to_csv(index=False, encoding="utf-8-sig")
                    st.download_button("📥 Download", data=csv,
                        file_name=(st.session_state.df_name or "dados").rsplit(".", 1)[0] + ".csv",
                        mime="text/csv", width="stretch", key="csv_dl")

        if is_anime_like(st.session_state.df):
            with st.expander("🏷️ Status", expanded=False):
                c5, c6 = st.columns(2)
                with c5:
                    if st.button("💔 Dropado", width="stretch", key="btn_drop"):
                        st.session_state.show_add_dialog = "dropado"
                with c6:
                    if st.button("⏳ Planejar", width="stretch", key="btn_plan"):
                        st.session_state.show_add_dialog = "planejado"

        with st.expander("↩️ Histórico", expanded=False):
            c7, c8 = st.columns(2)
            with c7:
                if st.button("↩️ Desfazer", width="stretch", key="btn_undo"):
                    undo()
                    st.rerun()
            with c8:
                if st.button("↪️ Refazer", width="stretch", key="btn_redo"):
                    redo()
                    st.rerun()

    # GIF
    st.divider()
    gif_path = PROJECT_DIR / "gifs"
    gif_files = sorted(gif_path.glob("*.gif")) if gif_path.is_dir() else []
    if gif_files:
        gif_idx = st.session_state.get("gif_idx", 0) % len(gif_files)
        st.image(str(gif_files[gif_idx]))
        if st.button("⏭️ Próximo GIF", width="stretch", key="btn_gif"):
            st.session_state.gif_idx = (st.session_state.gif_idx + 1) % len(gif_files)

# ────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────
if not has_data:
    st.info("📂 Faça upload de um arquivo JSON na barra lateral.", icon="🗂️")
    st.markdown("""
    ### Como usar
    1. **Upload** — JSON no menu lateral
    2. **Edite** — tabela editável inline
    3. **Gerencie** — adicione, exclua, busque, agrupe, exporte

    Funciona com qualquer lista JSON plana (array de objetos).
    """)
    st.stop()

df_current = st.session_state.df
stats = obter_stats(df_current)

# Stats cards
cols_stat = st.columns(6)
show_status = is_anime_like(df_current)
stat_configs = [
    ("📊", "total", "total", "#ffffff"),
    ("⭐", "media", "media", "#03a9f4"),
    ("✅", "completo", "completo", "#4caf50"),
    ("📺", "assistindo", "assistindo", "#03a9f4"),
    ("⏳", "planejado", "planejado", "#ffa726"),
    ("💔", "dropado", "dropado", "#ef5350"),
]
for col, (icon, key, cls, color) in zip(cols_stat, stat_configs):
    val = stats.get(key, 0) if key != "media" else (stats.get("media", "—") or "—")
    if key in ("completo", "assistindo", "planejado", "dropado") and not show_status:
        col.empty()
        continue
    col.markdown(f"""<div class="stat-card"><span class="stat-icon">{icon}</span><span class="stat-value {cls}" style="color:{color};">{val}</span></div>""", unsafe_allow_html=True)

# Group by
df_filtered = get_filtered_df()
col_group, col_chart = st.columns([3, 1])
with col_group:
    if df_current is not None:
        all_cols = list(df_current.columns)
        opts = [""] + all_cols
        idx = opts.index(st.session_state.group_field) if st.session_state.group_field in opts else 0
        sel = st.selectbox("Agrupar por:", options=opts, index=idx, key="group_select",
                          label_visibility="collapsed", placeholder="Agrupar por...")
        st.session_state.group_field = sel if sel else None
with col_chart:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📊 Gráfico", width="stretch", key="btn_chart_main"):
        st.session_state.show_chart = not st.session_state.show_chart
        st.rerun()

# Data editor
if df_filtered is not None and not df_filtered.empty:
    display_df = df_filtered.copy().reset_index(drop=True)
    if st.session_state.group_field and st.session_state.group_field in display_df.columns:
        display_df[st.session_state.group_field] = display_df[st.session_state.group_field].astype(str)
        display_df = display_df.sort_values(by=st.session_state.group_field, na_position="last").reset_index(drop=True)

    edited = st.data_editor(
        display_df,
        width="stretch",
        num_rows="dynamic",
        key="data_editor",
        column_config={col: st.column_config.TextColumn(col, width="medium") for col in display_df.columns},
    )

    if edited is not None and not edited.equals(display_df):
        push_undo()
        st.session_state.df = edited

    if st.session_state.search.strip():
        st.caption(f"🔍 {len(df_filtered)} resultado(s) para '{st.session_state.search}'")
else:
    if st.session_state.search.strip():
        st.warning(f"Nenhum resultado para '{st.session_state.search}'")
    else:
        st.info("📭 Nenhum item. Adicione com '➕ Novo' na sidebar.")

# Chart
if st.session_state.show_chart and df_current is not None and not df_current.empty:
    coluna = st.session_state.group_field
    if not coluna or coluna not in df_current.columns:
        for cand in ("status", "categoria", "tag", st.session_state.df.columns[0]):
            if cand in df_current.columns and df_current[cand].dtype == object:
                coluna = cand
                break
    if coluna and coluna in df_current.columns:
        vc = df_current[coluna].astype(str).value_counts()
        if not vc.empty:
            fig, ax = plt.subplots(figsize=(9, 4))
            ax.bar(vc.index, vc.values, color="#03a9f4", width=0.6)
            ax.set_title(f"Distribuição por '{coluna}'", fontsize=13, color="white")
            ax.set_ylabel("Contagem", color="white")
            ax.tick_params(colors="white")
            ax.set_facecolor("#1a1a2e")
            fig.patch.set_facecolor("#101018")
            ax.spines["bottom"].set_color("#333")
            ax.spines["left"].set_color("#333")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            plt.xticks(rotation=45, ha="right", color="white")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("📊 Dados insuficientes.")
    else:
        st.info("📊 Selecione uma coluna para agrupar.")

# ────────────────────────────────────────────────────────────────────
# DIALOGS
# ────────────────────────────────────────────────────────────────────

if st.session_state.show_add_dialog:
    with st.dialog("➕ Novo Item"):
        preset = st.session_state.show_add_dialog if isinstance(st.session_state.show_add_dialog, str) else None
        cols = list(st.session_state.df.columns) if st.session_state.df is not None else ["nome"]
        if "tags" not in cols:
            cols = list(cols) + ["tags"]
        entries = {}
        for col in cols:
            entries[col] = st.text_input(f"{col}:", value=(col == "status" and preset) or "", key=f"add_{col}")
        c_a, c_c = st.columns(2)
        with c_a:
            if st.button("➕ ADICIONAR", width="stretch", type="primary"):
                push_undo()
                st.session_state.df = pd.concat(
                    [st.session_state.df, pd.DataFrame([{col: entries[col] for col in cols}])],
                    ignore_index=True,
                )
                st.session_state.show_add_dialog = False
                st.toast("➕ Item adicionado!", icon="➕")
                st.rerun()
        with c_c:
            if st.button("Cancelar", width="stretch"):
                st.session_state.show_add_dialog = False
                st.rerun()

if st.session_state.show_delete_dialog:
    with st.dialog("❌ Excluir Item"):
        df = st.session_state.df
        if df is not None and not df.empty:
            nome_col = "nome" if "nome" in df.columns else df.columns[0]
            names = df[nome_col].astype(str).tolist()
            sel_name = st.selectbox("Selecione:", names, key="del_select")
            c_d, c_c = st.columns(2)
            with c_d:
                if st.button("🗑️ EXCLUIR", width="stretch", type="primary"):
                    push_undo()
                    idx = names.index(sel_name)
                    st.session_state.df = df.drop(index=df.index[idx]).reset_index(drop=True)
                    st.session_state.show_delete_dialog = False
                    st.toast(f"🗑️ Excluído: {sel_name}", icon="🗑️")
                    st.rerun()
            with c_c:
                if st.button("Cancelar", width="stretch"):
                    st.session_state.show_delete_dialog = False
                    st.rerun()
        else:
            st.write("Nada para excluir.")
            if st.button("Fechar"):
                st.session_state.show_delete_dialog = False
                st.rerun()

if st.session_state.show_tags_dialog:
    with st.dialog("🏷️ Tags"):
        df = st.session_state.df
        if df is not None and not df.empty and "tags" in df.columns:
            nome_col = "nome" if "nome" in df.columns else df.columns[0]
            names = df[nome_col].astype(str).tolist()
            sel_idx = st.selectbox("Selecione:", range(len(names)), format_func=lambda i: names[i], key="tag_select")
            tags_str = str(df.iloc[sel_idx].get("tags", ""))
            tags_set = {t.strip() for t in tags_str.split(",") if t.strip()}
            if tags_set:
                st.markdown("**Tags:**")
                for i, tag in enumerate(sorted(tags_set)):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"`{tag}`")
                    if c2.button("✕", key=f"rm_tag_{sel_idx}_{i}"):
                        tags_set.discard(tag)
                        push_undo()
                        st.session_state.df.loc[df.index[sel_idx], "tags"] = ", ".join(sorted(tags_set))
                        st.rerun()
            else:
                st.caption("Sem tags.")
            new_tag = st.text_input("Nova tag:", key="new_tag")
            if st.button("+ Adicionar", width="stretch"):
                if new_tag.strip():
                    tags_set.add(new_tag.strip().lower())
                    push_undo()
                    if "tags" not in df.columns:
                        st.session_state.df["tags"] = ""
                    st.session_state.df.loc[df.index[sel_idx], "tags"] = ", ".join(sorted(tags_set))
                    st.rerun()
            if st.button("Fechar", width="stretch"):
                st.session_state.show_tags_dialog = False
                st.rerun()
        else:
            st.write(df is not None and "tags" not in df.columns and "Nenhuma coluna 'tags'." or "Vazio.")
            if st.button("Fechar"):
                st.session_state.show_tags_dialog = False
                st.rerun()
