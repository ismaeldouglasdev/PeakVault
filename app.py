import streamlit as st
import pandas as pd
import json
import os
import sys
import time
from pathlib import Path
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

# ── CORES ──
CORES = {
    "completo": "#4caf50",
    "assistindo": "#03a9f4",
    "planejado": "#ffa726",
    "dropado": "#ef5350",
}

GIF_LIST = [
    "gifs/pixel.gif",
    "gifs/cyberpunk-rain.gif",
    "gifs/ezgif.com-optimize (1).gif",
    "gifs/disc-resize.gif",
    "gifs/error-.gif",
]

PROJECT_DIR = Path(__file__).parent

# ── SESSION STATE ──
def init_session():
    if "df" not in st.session_state:
        st.session_state.df = None
    if "df_name" not in st.session_state:
        st.session_state.df_name = None
    if "undo_stack" not in st.session_state:
        st.session_state.undo_stack = []
    if "undo_pos" not in st.session_state:
        st.session_state.undo_pos = -1
    if "search" not in st.session_state:
        st.session_state.search = ""
    if "group_field" not in st.session_state:
        st.session_state.group_field = None
    if "gif_idx" not in st.session_state:
        st.session_state.gif_idx = 0
    if "status_msg" not in st.session_state:
        st.session_state.status_msg = "🔥 Pronto! Faça upload de um JSON"
    if "status_color" not in st.session_state:
        st.session_state.status_color = "#888888"
    if "show_add_dialog" not in st.session_state:
        st.session_state.show_add_dialog = False
    if "show_delete_dialog" not in st.session_state:
        st.session_state.show_delete_dialog = False
    if "show_tags_dialog" not in st.session_state:
        st.session_state.show_tags_dialog = False
    if "show_chart" not in st.session_state:
        st.session_state.show_chart = False


init_session()

# ── HELPERS ──
def push_undo():
    if st.session_state.df is not None:
        snap = st.session_state.df.to_dict(orient="records")
        st.session_state.undo_stack = st.session_state.undo_stack[: st.session_state.undo_pos + 1]
        st.session_state.undo_stack.append(snap)
        if len(st.session_state.undo_stack) > 50:
            st.session_state.undo_stack.pop(0)
        st.session_state.undo_pos = len(st.session_state.undo_stack) - 1


def undo():
    if st.session_state.undo_pos > 0:
        st.session_state.undo_pos -= 1
        st.session_state.df = pd.DataFrame(st.session_state.undo_stack[st.session_state.undo_pos])
        st.session_state.status_msg = "↩️ Desfeito"
        st.session_state.status_color = "#ffa726"
        return True
    st.session_state.status_msg = "⚠️ Nada para desfazer"
    st.session_state.status_color = "#ffa726"
    return False


def redo():
    if st.session_state.undo_pos < len(st.session_state.undo_stack) - 1:
        st.session_state.undo_pos += 1
        st.session_state.df = pd.DataFrame(st.session_state.undo_stack[st.session_state.undo_pos])
        st.session_state.status_msg = "↪️ Refito"
        st.session_state.status_color = "#03a9f4"
        return True
    st.session_state.status_msg = "⚠️ Nada para refazer"
    st.session_state.status_color = "#ffa726"
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
    else:
        for s in ("completo", "assistindo", "planejado", "dropado"):
            stats[s] = 0
    return stats


def get_filtered_df():
    df = st.session_state.df
    if df is None or df.empty:
        return df
    search = st.session_state.search.strip().lower()
    if not search:
        return df
    mask = df.apply(lambda row: any(search in str(v).lower() for v in row.values), axis=1)
    return df[mask]


def is_anime_like(df):
    if df is None:
        return False
    cols = set(df.columns)
    return {"nome", "nota", "status"}.issubset(cols)


# ── CSS CUSTOM ──
st.markdown(
    """
<style>
    /* stats cards */
    .stat-card {
        background: #1a1a2e;
        border-radius: 8px;
        padding: 6px 12px;
        display: flex;
        align-items: center;
        gap: 6px;
        height: 42px;
    }
    .stat-icon { font-size: 16px; }
    .stat-value { font-size: 18px; font-weight: 700; }
    .stat-value.total { color: #ffffff; }
    .stat-value.media { color: #03a9f4; }
    .stat-value.completo { color: #4caf50; }
    .stat-value.assistindo { color: #03a9f4; }
    .stat-value.planejado { color: #ffa726; }
    .stat-value.dropado { color: #ef5350; }

    /* sidebar */
    .sidebar-title {
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 2px;
    }
    .sidebar-accent {
        height: 2px;
        background: #03a9f4;
        margin: 0 24px 12px 24px;
    }
    .section-label {
        font-size: 10px;
        font-weight: 700;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 8px 0 4px 10px;
    }
    .status-bar {
        background: #1a1a2e;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 13px;
    }
    div[data-testid="stDataEditor"] { font-size: 14px; }
    button[kind="primary"] { font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)


# ────────────────────────────────────────────────────────────────────
# SIDEBAR
# ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">🗂️ PeakVault</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-accent"></div>', unsafe_allow_html=True)

    # ── Upload ──
    uploaded = st.file_uploader(
        "Carregar lista JSON",
        type=["json"],
        label_visibility="collapsed",
        key="file_uploader",
    )

    if uploaded:
        try:
            data = json.loads(uploaded.read())
            name = uploaded.name
            df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
            if not df.empty:
                push_undo()
                st.session_state.df = df
                st.session_state.df_name = name
                st.session_state.group_field = None
                st.session_state.show_chart = False
                st.session_state.status_msg = f"📂 Carregado: {name}"
                st.session_state.status_color = "#03a9f4"
        except Exception as e:
            st.error(f"Erro ao ler JSON: {e}")

    has_data = st.session_state.df is not None and not st.session_state.df.empty

    if has_data:
        st.caption(f"📄 **{st.session_state.df_name}** ({len(st.session_state.df)} itens)")

        col_close, col_dl = st.columns([1, 2])
        with col_close:
            if st.button("✕ Fechar", width="stretch", type="secondary"):
                st.session_state.df = None
                st.session_state.df_name = None
                st.session_state.undo_stack = []
                st.session_state.undo_pos = -1
                st.session_state.group_field = None
                st.session_state.show_chart = False
                st.session_state.status_msg = "📂 Arquivo fechado"
                st.session_state.status_color = "#888888"
                st.rerun()
        with col_dl:
            if st.session_state.df is not None:
                json_bytes = st.session_state.df.to_json(orient="records", indent=2, force_ascii=False).encode("utf-8")
                st.download_button(
                    "💾 Download JSON",
                    data=json_bytes,
                    file_name=st.session_state.df_name or "dados.json",
                    mime="application/json",
                    width="stretch",
                )

    st.divider()

    # ── Busca ──
    if has_data:
        st.text_input(
            "🔍 Buscar",
            placeholder="Digite para filtrar...",
            key="search",
            label_visibility="collapsed",
        )

        st.divider()

        # ── Botões de ação (como no desktop) ──
        st.markdown('<div class="section-label">GERAL</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📊  Listar", width="stretch", key="btn_listar"):
                st.session_state.status_msg = f"✅ {len(get_filtered_df())} item(ns) listados"
                st.session_state.status_color = "#4caf50"
        with c2:
            if st.button("➕  Novo Item", width="stretch", key="btn_add"):
                st.session_state.show_add_dialog = True

        c3, c4 = st.columns(2)
        with c3:
            if st.button("❌  Excluir", width="stretch", key="btn_del"):
                st.session_state.show_delete_dialog = True
        with c4:
            if st.button("📥  CSV", width="stretch", key="btn_csv"):
                if st.session_state.df is not None:
                    csv = st.session_state.df.to_csv(index=False, encoding="utf-8-sig")
                    st.download_button(
                        "📥 Download CSV",
                        data=csv,
                        file_name=(st.session_state.df_name or "dados").rsplit(".", 1)[0] + ".csv",
                        mime="text/csv",
                        width="stretch",
                        key="csv_dl_btn",
                    )

        if is_anime_like(st.session_state.df):
            st.markdown('<div class="section-label">STATUS</div>', unsafe_allow_html=True)
            c5, c6 = st.columns(2)
            with c5:
                if st.button("💔  Dropado", width="stretch", key="btn_drop"):
                    st.session_state.show_add_dialog = "dropado"
            with c6:
                if st.button("⏳  Planejar", width="stretch", key="btn_plan"):
                    st.session_state.show_add_dialog = "planejado"

        st.markdown('<div class="section-label">HISTÓRICO</div>', unsafe_allow_html=True)
        c7, c8 = st.columns(2)
        with c7:
            if st.button("↩️  Desfazer", width="stretch", key="btn_undo"):
                undo()
                st.rerun()
        with c8:
            if st.button("↪️  Refazer", width="stretch", key="btn_redo"):
                redo()
                st.rerun()

        st.markdown('<div class="section-label">AÇÕES</div>', unsafe_allow_html=True)
        c9, c10 = st.columns(2)
        with c9:
            if st.button("🏷️  Tags", width="stretch", key="btn_tags"):
                st.session_state.show_tags_dialog = True
        with c10:
            if st.button("📈  Gráfico", width="stretch", key="btn_chart"):
                st.session_state.show_chart = not st.session_state.show_chart

    # ── GIF ──
    st.divider()
    gif_path = PROJECT_DIR / GIF_LIST[st.session_state.gif_idx]
    if gif_path.exists():
        st.image(str(gif_path), width="stretch")
    if st.button("⏭️ Próximo GIF", width="stretch", key="btn_gif"):
        st.session_state.gif_idx = (st.session_state.gif_idx + 1) % len(GIF_LIST)
        st.rerun()


# ────────────────────────────────────────────────────────────────────
# MAIN AREA
# ────────────────────────────────────────────────────────────────────
if not has_data:
    st.info("📂 Faça upload de um arquivo JSON na barra lateral para começar.", icon="🗂️")
    st.markdown("""
    ### Como usar
    1. **Upload** — clique em "Carregar lista JSON" na sidebar
    2. **Visualize e edite** — a tabela aparece aqui, editável inline
    3. **Gerencie** — adicione, exclua, busque, agrupe, exporte

    O PeakVault funciona com qualquer JSON de lista (array de objetos).
    Animes, séries, projetos, tarefas — o que tiver `nome`, `nota`, `status`.
    """)
    st.stop()

# ── STATS CARDS ──
df_current = st.session_state.df
stats = obter_stats(df_current)

cols_stat = st.columns(6)
stat_configs = [
    ("📊", "total", "total", "#ffffff"),
    ("⭐", "media", "media", "#03a9f4"),
    ("✅", "completo", "completo", "#4caf50"),
    ("📺", "assistindo", "assistindo", "#03a9f4"),
    ("⏳", "planejado", "planejado", "#ffa726"),
    ("💔", "dropado", "dropado", "#ef5350"),
]

show_status_cards = is_anime_like(df_current)

for col, (icon, key, cls, color) in zip(cols_stat, stat_configs):
    val = stats.get(key, 0) if key != "media" else (stats.get("media", "—") or "—")
    if key in ("completo", "assistindo", "planejado", "dropado") and not show_status_cards:
        col.empty()
        continue
    col.markdown(
        f"""
        <div class="stat-card">
            <span class="stat-icon">{icon}</span>
            <span class="stat-value {cls}" style="color:{color};">{val}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── GROUP BY ──
df_filtered = get_filtered_df()
col_group, col_apply = st.columns([3, 1])
with col_group:
    if df_current is not None:
        all_cols = list(df_current.columns)
        group_opts = [""] + all_cols
        current_idx = group_opts.index(st.session_state.group_field) if st.session_state.group_field in group_opts else 0
        selected = st.selectbox(
            "Agrupar por:",
            options=group_opts,
            index=current_idx,
            key="group_select",
            label_visibility="collapsed",
            placeholder="Agrupar por...",
        )
        st.session_state.group_field = selected if selected else None
with col_apply:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📊  Gráfico", key="btn_chart_main", width="stretch"):
        st.session_state.show_chart = not st.session_state.show_chart
        st.rerun()

# ── DATA EDITOR ──
if df_filtered is not None and not df_filtered.empty:
    display_df = df_filtered.copy()
    if st.session_state.group_field and st.session_state.group_field in display_df.columns:
        display_df[st.session_state.group_field] = display_df[st.session_state.group_field].astype(str)
        display_df = display_df.sort_values(by=st.session_state.group_field, na_position="last")

    # Strip index from display — reset to range index first
    display_df = display_df.reset_index(drop=True)
    edited = st.data_editor(
        display_df,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        key="data_editor",
        column_config={
            col: st.column_config.TextColumn(col, width="medium")
            for col in display_df.columns
        },
    )

    # Detect changes and save to session state
    if edited is not None and not edited.equals(display_df):
        push_undo()
        st.session_state.df = edited.copy()
        st.session_state.status_msg = "✏️ Dados atualizados"
        st.session_state.status_color = "#4caf50"
        st.rerun()

    # Status message
    if st.session_state.search.strip():
        st.markdown(
            f"<span style='color:#03a9f4;font-size:13px;'>🔍 {len(df_filtered)} resultado(s) para '{st.session_state.search}'</span>",
            unsafe_allow_html=True,
        )
else:
    if st.session_state.search.strip():
        st.warning(f"Nenhum resultado para '{st.session_state.search}'")
    else:
        st.info("📭 Nenhum item. Adicione com '➕ Novo Item' na sidebar.")

# ── Status bar ──
st.markdown(
    f"<div class='status-bar' style='color:{st.session_state.status_color};'>{st.session_state.status_msg}</div>",
    unsafe_allow_html=True,
)

# ── CHART ──
if st.session_state.show_chart and df_current is not None and not df_current.empty:
    coluna = st.session_state.group_field
    if not coluna or coluna not in df_current.columns:
        for cand in ("status", "categoria", "tag"):
            if cand in df_current.columns:
                coluna = cand
                break
        if not coluna:
            for col in df_current.columns:
                if df_current[col].dtype == object:
                    coluna = col
                    break
    if coluna and coluna in df_current.columns:
        vc = df_current[coluna].astype(str).value_counts()
        if not vc.empty:
            fig, ax = plt.subplots(figsize=(9, 4))
            bars = ax.bar(vc.index, vc.values, color="#03a9f4", width=0.6)
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
            st.pyplot(fig)
        else:
            st.info("📊 Dados insuficientes para o gráfico.")
    else:
        st.info("📊 Selecione uma coluna para agrupar e gerar o gráfico.")

# ────────────────────────────────────────────────────────────────────
# DIALOGS
# ────────────────────────────────────────────────────────────────────

# ── Novo Item ──
if st.session_state.show_add_dialog:
    with st.dialog("➕ Novo Item"):
        preset_status = st.session_state.show_add_dialog if isinstance(st.session_state.show_add_dialog, str) else None
        cols = list(st.session_state.df.columns) if st.session_state.df is not None else ["nome"]
        if "tags" not in cols:
            cols = list(cols) + ["tags"]

        entries = {}
        for col in cols:
            val = ""
            if col == "status" and preset_status:
                val = preset_status
            entries[col] = st.text_input(f"{col}:", value=val, key=f"add_{col}")

        c_add, c_cancel = st.columns(2)
        with c_add:
            if st.button("➕ ADICIONAR", width="stretch", type="primary"):
                push_undo()
                new_row = {col: entries[col] for col in cols}
                st.session_state.df = pd.concat(
                    [st.session_state.df, pd.DataFrame([new_row])],
                    ignore_index=True,
                )
                st.session_state.status_msg = "➕ Item adicionado!"
                st.session_state.status_color = "#4caf50"
                st.session_state.show_add_dialog = False
                st.rerun()
        with c_cancel:
            if st.button("Cancelar", width="stretch"):
                st.session_state.show_add_dialog = False
                st.rerun()

# ── Excluir Item ──
if st.session_state.show_delete_dialog:
    with st.dialog("❌ Excluir Item"):
        df = st.session_state.df
        if df is not None and not df.empty:
            nome_col = "nome" if "nome" in df.columns else df.columns[0]
            names = df[nome_col].astype(str).tolist()
            selected_name = st.selectbox("Selecione o item:", names, key="del_select")

            c_del, c_cancel_del = st.columns(2)
            with c_del:
                if st.button("🗑️ EXCLUIR", width="stretch", type="primary"):
                    push_undo()
                    idx = names.index(selected_name)
                    st.session_state.df = st.session_state.df.drop(index=df.index[idx]).reset_index(drop=True)
                    st.session_state.status_msg = f"🗑️ Excluído: {selected_name}"
                    st.session_state.status_color = "#ef5350"
                    st.session_state.show_delete_dialog = False
                    st.rerun()
            with c_cancel_del:
                if st.button("Cancelar", width="stretch"):
                    st.session_state.show_delete_dialog = False
                    st.rerun()
        else:
            st.write("Nenhum item para excluir.")
            if st.button("Fechar"):
                st.session_state.show_delete_dialog = False
                st.rerun()

# ── Tags ──
if st.session_state.show_tags_dialog:
    with st.dialog("🏷️ Gerenciar Tags"):
        df = st.session_state.df
        if df is not None and not df.empty and "tags" in df.columns:
            nome_col = "nome" if "nome" in df.columns else df.columns[0]
            names = df[nome_col].astype(str).tolist()
            selected_tag_idx = st.selectbox("Selecione o item:", range(len(names)), format_func=lambda i: names[i], key="tag_select")

            current_tags_str = str(df.iloc[selected_tag_idx].get("tags", ""))
            current_tags = {t.strip() for t in current_tags_str.split(",") if t.strip()}

            if current_tags:
                st.markdown("**Tags atuais:**")
                cols_tags = st.columns(4)
                for i, tag in enumerate(sorted(current_tags)):
                    col_idx = i % 4
                    with cols_tags[col_idx]:
                        if st.button(f"✕ {tag}", key=f"rm_tag_{i}"):
                            current_tags.discard(tag)
                            new_tags_str = ", ".join(sorted(current_tags))
                            push_undo()
                            st.session_state.df.loc[df.index[selected_tag_idx], "tags"] = new_tags_str
                            st.rerun()
            else:
                st.caption("Nenhuma tag ainda.")

            new_tag = st.text_input("Nova tag:", placeholder="Digite e pressione Enter...", key="new_tag_input")
            c_tag_add, c_tag_close = st.columns(2)
            with c_tag_add:
                if st.button("+ Adicionar", width="stretch"):
                    if new_tag.strip():
                        current_tags.add(new_tag.strip().lower())
                        new_tags_str = ", ".join(sorted(current_tags))
                        push_undo()
                        if "tags" not in df.columns:
                            st.session_state.df["tags"] = ""
                        st.session_state.df.loc[df.index[selected_tag_idx], "tags"] = new_tags_str
                        st.rerun()
            with c_tag_close:
                if st.button("Fechar", width="stretch"):
                    st.session_state.show_tags_dialog = False
                    st.rerun()
        else:
            if "tags" not in df.columns:
                st.write("Nenhuma coluna 'tags' encontrada. Adicione tags a um item para criar a coluna.")
            else:
                st.write("Nenhum item disponível.")
            if st.button("Fechar", key="close_tags"):
                st.session_state.show_tags_dialog = False
                st.rerun()
