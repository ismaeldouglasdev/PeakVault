import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import logica
import importlib
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import json
import os

importlib.reload(logica)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CAELESTIA_SCHEME = os.path.expanduser(
    "~/.local/state/caelestia/scheme.json"
)


class ThemeWatcher:
    def __init__(self, root, on_theme_change):
        self.root = root
        self.on_theme_change = on_theme_change
        self._active = True
        self._last_mtime = 0
        self._current_name = None
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()

    def _watch(self):
        while self._active:
            try:
                if os.path.exists(CAELESTIA_SCHEME):
                    mtime = os.path.getmtime(CAELESTIA_SCHEME)
                    if mtime != self._last_mtime:
                        self._last_mtime = mtime
                        self._on_file_change()
            except Exception:
                pass
            time.sleep(2)

    def _on_file_change(self):
        try:
            with open(CAELESTIA_SCHEME, "r") as f:
                data = json.load(f)
            self._current_name = data.get("name", "")
            self.root.after(0, self.on_theme_change, data)
        except Exception:
            pass

    def stop(self):
        self._active = False


class ItemTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🗂️ PeakVault")
        self.root.geometry("900x700")
        self.root.configure(fg_color="#101018")

        self.current_file = None
        logica.set_ranking_file(None)

        self.items = []
        self.columns = []

        self.is_anime_like = False
        self.group_field = None

        self.left_gif_label = None
        self.left_gif_sets = []
        self.left_gif_index = 0
        self.left_gif_frame_index = 0

        # inline editing state
        self._edit_entry = None
        self._edit_item_id = None
        self._edit_column = None

        # cached data
        self._df_cache = None
        self._filtered_df = None

        # tabs
        self._tabs = {}           # tab_name -> {file, tree, tree_container, df_cache, filtered_df}
        self._active_tab = None
        self.tabview = None
        self.tree = None
        self.tree_container = None

        self._theme_watcher = ThemeWatcher(root, self._on_caelestia_theme_change)

        self.criar_interface()

        # apply initial Caelestia scheme after UI is built
        self._apply_current_scheme()

    def _apply_current_scheme(self):
        """Read the current Caelestia scheme file and apply colours to the UI."""
        try:
            with open(CAELESTIA_SCHEME, "r") as f:
                data = json.load(f)
            colours = data.get("colours", {})
            if colours:
                self._theme_colours = colours
                self._apply_scheme_colours(colours)
        except Exception:
            pass

    # ── THEME REACTIVITY ─────────────────────────────────────────

    def _on_caelestia_theme_change(self, scheme):
        colours = scheme.get("colours", {})
        if not colours:
            return
        self._theme_colours = colours
        self._apply_scheme_colours(colours)
        name = scheme.get("name", "?")
        mode = scheme.get("mode", "dark")
        self.atualizar_status(f"🎨 Tema: {name} ({mode})", cor="#03a9f4")

    def _apply_scheme_colours(self, colours):
        def _hex(key, fallback):
            return f"#{colours.get(key, fallback)}"

        bg = _hex("background", "101018")
        surface = _hex("surface", "14141f")
        surface_container = _hex("surfaceContainer", "151525")
        surface_high = _hex("surfaceContainerHigh", "202035")
        surface_highest = _hex("surfaceContainerHighest", "313150")
        primary = _hex("primary", "4488ff")
        on_surface = _hex("onSurface", "ffffff")
        on_surface_var = _hex("onSurfaceVariant", "888888")
        green = _hex("green", "4caf50")
        red = _hex("red", "ef5350")
        orange = _hex("peach", "ffa726")
        blue = _hex("sky", "03a9f4")

        # ── Root ──
        self.root.configure(fg_color=bg)

        # ── Main frames ──
        if hasattr(self, "main_frame"):
            self.main_frame.configure(fg_color=surface_container)
        if hasattr(self, "left_frame"):
            self.left_frame.configure(fg_color=surface)
        if hasattr(self, "right_frame"):
            self.right_frame.configure(fg_color=surface)
        if hasattr(self, "right_gif_frame"):
            self.right_gif_frame.configure(fg_color=surface_high)
        if hasattr(self, "left_gif_label"):
            try:
                self.left_gif_label.configure(bg=surface)
            except Exception:
                pass
        if hasattr(self, "group_frame"):
            self.group_frame.configure(fg_color=surface_high)
        if hasattr(self, "stats_frame"):
            for child in self.stats_frame.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    child.configure(fg_color=surface_highest)
        # iterate all tab tree containers so non-active tabs also get themed
        for tname, tinfo in self._tabs.items():
            tc = tinfo.get("tree_container")
            if tc:
                try:
                    tc.configure(fg_color=surface)
                except Exception:
                    pass
        if hasattr(self, "tree_container"):
            self.tree_container.configure(fg_color=surface)

        # ── Status bar ──
        if hasattr(self, "status_bar"):
            self.status_bar.configure(fg_color=surface_high, text_color=on_surface_var)

        # ── Botões do painel esquerdo ──
        accent = primary
        for btn in getattr(self, "botao_defs", []):
            try:
                btn.configure(fg_color=surface_high, hover_color=surface_highest)
            except Exception:
                pass

        # ── Stats labels ──
        if hasattr(self, "_stats_labels"):
            self._stats_labels["total"].configure(text_color=on_surface)
            self._stats_labels["media"].configure(text_color=blue)
            self._stats_labels["completo"].configure(text_color=green)
            self._stats_labels["assistindo"].configure(text_color=blue)
            self._stats_labels["planejado"].configure(text_color=orange)
            self._stats_labels["dropado"].configure(text_color=red)

        # ── Group combobox ──
        if hasattr(self, "group_combo"):
            try:
                self.group_combo.configure(fg_color=surface_highest)
            except Exception:
                pass

        # ── Treeview ──
        if hasattr(self, "tree"):
            try:
                style = ttk.Style()
                style.configure(
                    "Peak.Treeview",
                    background=surface,
                    fieldbackground=surface,
                    foreground=on_surface,
                )
                style.map(
                    "Peak.Treeview",
                    background=[("selected", surface_highest)],
                )
            except Exception:
                pass

    # ── INTERFACE LAYOUT ──────────────────────────────────────────

    def criar_interface(self):
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=12, fg_color="#151525")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=14)

        # ── LEFT SIDEBAR ───────────────────────────────────────────
        self.left_frame = ctk.CTkFrame(
            self.main_frame, width=260, corner_radius=10, fg_color="#14141f"
        )
        self.left_frame.pack(side="left", fill="y", padx=(0, 8))
        self.left_frame.pack_propagate(False)

        # ── Title ──
        titulo = ctk.CTkLabel(
            self.left_frame, text="PeakVault",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        titulo.pack(pady=(14, 2))

        # subtle accent line
        ctk.CTkFrame(self.left_frame, height=2, fg_color="#03a9f4").pack(
            fill="x", padx=24, pady=(0, 8)
        )

        # ── Search row (inline) ──
        search_row = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        search_row.pack(fill="x", padx=10, pady=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._ao_digitar_busca)
        ctk.CTkEntry(
            search_row, textvariable=self.search_var,
            placeholder_text="Buscar...", height=28, corner_radius=6,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            search_row, text="🔍", command=self.pesquisar_item,
            width=36, height=28, corner_radius=6,
            fg_color="#202840", font=ctk.CTkFont(size=12),
        ).pack(side="right")

        # ── Scrollable buttons ──
        self.left_scroll = ctk.CTkScrollableFrame(
            self.left_frame, fg_color="transparent",
            scrollbar_button_hover_color="#404065",
            corner_radius=0,
        )
        self.left_scroll.pack(fill="both", expand=True)

        self.botao_defs = []

        def _grupo(titulo_grupo):
            """Add a small group header label inside the scroll area."""
            ctk.CTkLabel(
                self.left_scroll, text=titulo_grupo,
                font=ctk.CTkFont(size=8, weight="bold"),
                text_color="#666",
            ).pack(anchor="w", padx=14, pady=(6, 1))

        def add_botao(texto, comando, attr_name=None):
            btn = ctk.CTkButton(
                self.left_scroll,
                text=texto,
                command=lambda c=comando, b=None: None,
                height=24,
                corner_radius=6,
                font=ctk.CTkFont(size=10),
                fg_color="transparent",
                text_color="#cccccc",
                hover_color="#1e1e35",
                anchor="w",
            )
            btn.configure(
                command=lambda c=comando, b=btn: self.animar_botao_click(b, c)
            )
            btn.pack(pady=1, padx=8, fill="x")
            if attr_name:
                setattr(self, attr_name, btn)
            self.botao_defs.append(btn)

        _grupo("GERAL")
        add_botao("📊  Listar Items", self.listar_items)
        add_botao("➕  Novo Item", self.adicionar_item)
        add_botao("❌  Excluir Item", self.excluir_items)

        _grupo("STATUS")
        add_botao("💔  Dropado", self.add_dropado, attr_name="btn_dropado")
        add_botao("⏳  Planejar", self.add_planejado, attr_name="btn_planejado")
        add_botao("🏷️  Tags", self.gerenciar_tags)

        _grupo("HISTÓRICO")
        add_botao("↩️  Desfazer", self.desfazer)
        add_botao("↪️  Refazer", self.refazer)

        _grupo("ARQUIVO")
        add_botao("📂  Carregar lista", self.carregar_lista)
        add_botao("❌  Fechar aba", self._fechar_tab_btn)
        add_botao("💾  Salvar", self.salvar_items)
        add_botao("📥  Exportar CSV", self.exportar_csv)
        add_botao("📈  Estatísticas", self.mostrar_stats)

        if not self.is_anime_like:
            self.btn_dropado.pack_forget()
            self.btn_planejado.pack_forget()

        # ── RIGHT PANEL ────────────────────────────────────────────
        self.right_frame = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color="#181828")
        self.right_frame.pack(side="right", fill="both", expand=True)
        self.right_frame.grid_rowconfigure(3, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        # ── Stats + Group bar (row 0) ──
        top_bar = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))

        self.stats_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        self.stats_frame.pack(side="left", fill="x", expand=True)

        self._criar_stats_cards()

        # ── Group bar (row 1) ──
        self.group_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.group_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 0))

        ctk.CTkLabel(
            self.group_frame, text="Agrupar:", font=ctk.CTkFont(size=10),
        ).pack(side="left", padx=(0, 4))

        self.group_var = ctk.StringVar(value="")
        self.group_combo = ctk.CTkComboBox(
            self.group_frame, variable=self.group_var,
            width=130, height=24, corner_radius=6,
            state="readonly", values=self.columns or [],
            font=ctk.CTkFont(size=10),
        )
        self.group_combo.pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            self.group_frame, text="Aplicar",
            width=60, height=24, corner_radius=6,
            fg_color="#313150", font=ctk.CTkFont(size=10),
            command=self.aplicar_agrupamento,
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            self.group_frame, text="📊 Gráfico",
            width=70, height=24, corner_radius=6,
            fg_color="#313150", font=ctk.CTkFont(size=10),
            command=self.mostrar_grafico_stats,
        ).pack(side="left")

        # ── GIF banner (row 2, ~170px) ──
        self.right_gif_frame = ctk.CTkFrame(
            self.right_frame, fg_color="transparent", height=170
        )
        self.right_gif_frame.grid(row=2, column=0, sticky="ew", padx=6, pady=(2, 0))
        self.right_gif_frame.grid_propagate(False)

        try:
            gif_paths = [
                "gifs/pixel.gif",
                "gifs/cyberpunk-rain.gif",
                "gifs/ezgif.com-optimize (1).gif",
                "gifs/disc-resize.gif",
                "gifs/error-.gif",
            ]
            self.left_gif_sets = []
            for path in gif_paths:
                frames = []
                for i in range(300):
                    try:
                        frame = tk.PhotoImage(file=path, format=f"gif -index {i}")
                        frames.append(frame)
                    except tk.TclError:
                        break
                if frames:
                    self.left_gif_sets.append(frames)

            if self.left_gif_sets:
                self.left_gif_label = tk.Label(
                    self.right_gif_frame,
                    image=self.left_gif_sets[0][0],
                    bg="#181828",
                    borderwidth=0,
                    highlightthickness=0,
                )
                self.left_gif_label.pack(expand=True)
                self.animar_gifs_left()
        except Exception as e:
            print("Erro ao carregar GIF:", e)
            self.left_gif_sets = []
            self.left_gif_label = None

        # ── Tabview (row 3, fills remaining) ──
        self._criar_tabview(self.right_frame)
        self.tabview.grid(row=3, column=0, sticky="nsew", padx=6, pady=(4, 0))

        # ── Status bar (row 4) ──
        self.status_var = ctk.StringVar()
        self.status_var.set("🔥 Pronto! Clique em Listar Items")
        self.status_bar = ctk.CTkLabel(
            self.right_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11),
            anchor="w", fg_color="#1a1a2e",
            corner_radius=6,
        )
        self.status_bar.grid(row=4, column=0, sticky="ew", padx=8, pady=(4, 6))

    # ── STATS CARDS ────────────────────────────────────────────────

    def _criar_stats_cards(self):
        cards_data = [
            ("📊", "total", "#888888"),
            ("⭐", "media", "#03a9f4"),
            ("✅", "completo", "#4caf50"),
            ("📺", "assistindo", "#03a9f4"),
            ("⏳", "planejado", "#ffa726"),
            ("💔", "dropado", "#ef5350"),
        ]

        self._stats_labels = {}
        for icon, key, cor in cards_data:
            card = ctk.CTkFrame(
                self.stats_frame, fg_color="#1a1a2e", corner_radius=6, height=36
            )
            card.pack(side="left", padx=1, fill="x", expand=True)
            card.pack_propagate(False)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(expand=True, padx=4)

            ctk.CTkLabel(
                row, text=icon, font=ctk.CTkFont(size=10),
            ).pack(side="left")

            lbl = ctk.CTkLabel(
                row, text="—",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=cor,
            )
            lbl.pack(side="left", padx=(2, 0))
            self._stats_labels[key] = lbl

    def _atualizar_stats_cards(self):
        """Atualiza os valores dos cards de estatísticas."""
        stats = logica.obter_stats()
        self._stats_labels["total"].configure(text=str(stats.get("total", 0)))
        media = stats.get("media")
        self._stats_labels["media"].configure(
            text=str(media) if media is not None else "—"
        )
        for s in ("completo", "assistindo", "planejado", "dropado"):
            self._stats_labels[s].configure(text=str(stats.get(s, 0)))

        # Mostra/esconde cards de status se não for anime-like
        if self.is_anime_like:
            for s in ("completo", "assistindo", "planejado", "dropado"):
                self._stats_labels[s].master.pack(side="left", padx=2, fill="x", expand=True)
        else:
            for s in ("completo", "assistindo", "planejado", "dropado"):
                self._stats_labels[s].master.pack_forget()

    # ── TREEVIEW ──────────────────────────────────────────────────

    def _criar_treeview(self, parent):
        """Create a treeview inside `parent` and return it."""
        container = ctk.CTkFrame(parent, fg_color="#14141f", corner_radius=10)
        container.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Peak.Treeview",
            background="#14141f",
            foreground="#cccccc",
            fieldbackground="#14141f",
            rowheight=30,
            font=("Segoe UI", 11),
            borderwidth=0,
        )
        style.configure(
            "Peak.Treeview.Heading",
            background="#202840",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            borderwidth=0,
        )
        style.map(
            "Peak.Treeview",
            background=[("selected", "#264f73")],
            foreground=[("selected", "#ffffff")],
        )
        style.layout("Peak.Treeview", [("Peak.Treeview.treearea", {"sticky": "nswe"})])

        tree = ttk.Treeview(
            container,
            style="Peak.Treeview",
            show="headings",
            selectmode="browse",
        )

        v_scroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        tree.tag_configure("completo", foreground="#4caf50")
        tree.tag_configure("assistindo", foreground="#03a9f4")
        tree.tag_configure("planejado", foreground="#ffa726")
        tree.tag_configure("dropado", foreground="#ef5350")

        tree.bind("<Double-1>", self._treeview_double_click)
        tree.bind("<ButtonRelease-1>", self._treeview_single_click)
        tree.bind("<Control-C>", self._copiar_selecao)

        return tree

    def _criar_tabview(self, parent):
        """Create a CTkTabview for multiple file tabs."""
        self.tabview = ctk.CTkTabview(
            parent,
            corner_radius=8,
            fg_color="#181828",
            segmented_button_fg_color="#202035",
            segmented_button_selected_color="#313150",
            segmented_button_selected_hover_color="#404065",
            segmented_button_unselected_color="#202035",
            segmented_button_unselected_hover_color="#2a2a45",
            text_color="#ffffff",
        )

        # default tab
        self.tabview.add("Início")

        tab_frame = self.tabview.tab("Início")
        tree = self._criar_treeview(tab_frame)

        self._tabs["Início"] = {
            "file": None,
            "tree": tree,
            "tree_container": tree.master,
            "df_cache": None,
            "filtered_df": None,
            "columns": [],
            "is_anime_like": False,
            "group_field": None,
        }
        self._active_tab = "Início"
        self.tree = tree
        self.tree_container = tree.master

        # bind tab switch
        self.tabview.configure(command=self._on_tab_switch)

    def _on_tab_switch(self, tab_name):
        """Save/restore state when switching tabs."""
        if self._active_tab and self._active_tab in self._tabs:
            old = self._tabs[self._active_tab]
            old["df_cache"] = self._df_cache
            old["filtered_df"] = self._filtered_df
            old["group_field"] = self.group_field
            old["columns"] = self.columns

        self._active_tab = tab_name
        tab = self._tabs.get(tab_name)
        if tab:
            self.tree = tab["tree"]
            self.tree_container = tab["tree_container"]
            self._df_cache = tab["df_cache"]
            self._filtered_df = tab["filtered_df"]
            self.current_file = tab["file"]
            self.columns = tab["columns"]
            self.is_anime_like = tab.get("is_anime_like", False)
            if tab["file"]:
                logica.set_ranking_file(tab["file"])

            self.group_field = tab.get("group_field") or None
            if hasattr(self, "group_combo"):
                self.group_combo.configure(values=self.columns)
                if self.group_field and self.group_field in self.columns:
                    self.group_var.set(self.group_field)
                else:
                    self.group_var.set("")

            if hasattr(self, "btn_dropado") and hasattr(self, "btn_planejado"):
                if self.is_anime_like:
                    self.btn_dropado.pack(pady=3, padx=10)
                    self.btn_planejado.pack(pady=3, padx=10)
                else:
                    self.btn_dropado.pack_forget()
                    self.btn_planejado.pack_forget()

            self.listar_items()

    def _add_file_tab(self, caminho):
        """Open a file in a new tab (or switch to existing one)."""
        nome_curto = caminho.split("/")[-1].split("\\")[-1]

        # if already open, just switch
        for tname, tdata in self._tabs.items():
            if tdata.get("file") == caminho:
                self.tabview.set(tname)
                self._on_tab_switch(tname)
                return tname

        # create unique tab name
        base = nome_curto.rsplit(".", 1)[0][:20]
        tab_name = base
        i = 1
        while tab_name in self._tabs:
            tab_name = f"{base}_{i}"
            i += 1

        self.tabview.add(tab_name)
        tab_frame = self.tabview.tab(tab_name)
        tree = self._criar_treeview(tab_frame)

        logica.set_ranking_file(caminho)
        df = logica.carregar_dataframe()
        colunas = list(df.columns) if not df.empty else []

        is_anime = {"nome", "nota", "status"}.issubset(set(colunas))
        self._tabs[tab_name] = {
            "file": caminho,
            "tree": tree,
            "tree_container": tree.master,
            "df_cache": df if not df.empty else None,
            "filtered_df": None,
            "columns": colunas,
            "is_anime_like": is_anime,
            "group_field": None,
        }

        self.tabview.set(tab_name)
        self._on_tab_switch(tab_name)
        return tab_name

    def _fechar_tab_btn(self):
        self._fechar_tab(self._active_tab)

    def _fechar_tab(self, tab_name=None):
        """Close a tab (not the last one)."""
        if tab_name is None:
            tab_name = self._active_tab
        if len(self._tabs) <= 1 or tab_name == "Início":
            return
        if tab_name not in self._tabs:
            return

        del self._tabs[tab_name]
        self.tabview.delete(tab_name)

        # switch to first remaining tab
        remaining = list(self._tabs.keys())
        self.tabview.set(remaining[0])
        self._on_tab_switch(remaining[0])

    def _popular_treeview(self, registros=None):
        """Popula a Treeview com dados. Se registros=None, usa o cache."""
        self.tree.delete(*self.tree.get_children())

        if registros is None:
            registros = self._get_dados_exibir()

        if not registros:
            return

        colunas = list(registros[0].keys()) if registros else []

        # Configura colunas
        self.tree["columns"] = colunas
        for col in colunas:
            # Largura adaptativa
            max_len = len(str(col))
            for r in registros:
                max_len = max(max_len, len(str(r.get(col, ""))))
            width = min(max(max_len * 9, 60), 400)
            self.tree.heading(
                col, text=col.upper(),
                command=lambda c=col: self._ordenar_por(c),
            )
            self.tree.column(col, width=width, minwidth=50, anchor="w")

        # Insere linhas
        for i, item in enumerate(registros):
            values = [item.get(c, "") for c in colunas]
            status = str(item.get("status", "")).lower()
            tag = status if status in ("completo", "assistindo", "planejado", "dropado") else ""
            self.tree.insert("", "end", iid=str(i), values=values, tags=(tag,) if tag else ())

        # Garante que alguma linha apareça selecionada
        if self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])

    def _get_dados_exibir(self):
        """Retorna a lista de dicts a exibir (filtrada/agrupada)."""
        if self._filtered_df is not None and not self._filtered_df.empty:
            df = self._filtered_df
        elif self._df_cache is not None and not self._df_cache.empty:
            df = self._df_cache
        else:
            df = logica.carregar_dataframe()
            if df.empty:
                return []
            self._df_cache = df

        if self.group_field and self.group_field in df.columns:
            # convert to string to avoid mixed-type sort errors (str vs float/NaN)
            df = df.copy()
            df[self.group_field] = df[self.group_field].astype(str)
            df = df.sort_values(by=self.group_field, na_position="last")

        return df.to_dict(orient="records")

    def _ordenar_por(self, coluna):
        """Ordena a Treeview pela coluna clicada (alterna ordem)."""
        registros = self._get_dados_exibir()
        if not registros:
            return
        # Alterna direção
        if not hasattr(self, "_sort_col") or self._sort_col != coluna:
            self._sort_reverse = False
        else:
            self._sort_reverse = not self._sort_reverse
        self._sort_col = coluna

        def chave(r):
            v = r.get(coluna, "")
            try:
                return (0, float(v))
            except (ValueError, TypeError):
                return (1, str(v).lower())

        registros.sort(key=chave, reverse=self._sort_reverse)
        self._popular_treeview(registros)

    # ── LIVE FILTER ───────────────────────────────────────────────

    def _ao_digitar_busca(self, *_):
        """Dispara o filtro ao vivo com debounce de 200ms."""
        if hasattr(self, "_filter_timer") and self._filter_timer is not None:
            self.root.after_cancel(self._filter_timer)
        self._filter_timer = self.root.after(200, self._aplicar_filtro_vivo)

    def _aplicar_filtro_vivo(self):
        """Filtra a Treeview conforme o texto digitado."""
        consulta = self.search_var.get().strip().lower()
        self._filter_timer = None

        df = logica.carregar_dataframe()
        if df.empty:
            self._df_cache = df
            self._filtered_df = None
            self._popular_treeview([])
            return

        self._df_cache = df

        if not consulta:
            self._filtered_df = None
            self._popular_treeview()
            self._atualizar_stats_cards()
            self.atualizar_status(f"📋 Mostrando todos ({len(df)} itens)", cor="#4caf50")
            return

        # Filtra registros onde qualquer campo contém a consulta
        mask = df.apply(
            lambda row: any(consulta in str(v).lower() for v in row.values), axis=1
        )
        self._filtered_df = df[mask]
        total = len(self._filtered_df)
        self._popular_treeview(self._filtered_df.to_dict(orient="records"))
        self._atualizar_stats_cards()
        self.atualizar_status(f"🔍 {total} resultado(s) para '{consulta}'", cor="#03a9f4")

    # ── INLINE EDITING ────────────────────────────────────────────

    def _treeview_double_click(self, event):
        """Inicia edição inline ao dar duplo clique numa célula."""
        if self._edit_entry:
            self._salvar_edicao_inline()

        region = self.tree.identify_region(event.x, event.y)
        if region not in ("cell", "tree"):
            return

        col_id = self.tree.identify_column(event.x)
        item_id = self.tree.identify_row(event.y)
        if not col_id or not item_id:
            return

        col_index = int(col_id.replace("#", "")) - 1
        cols = self.tree["columns"]
        if col_index < 0 or col_index >= len(cols):
            return

        col_name = cols[col_index]
        # Impede editar colunas que não fazem sentido
        if col_name.lower() == "status":
            # Status é editável via botões, mas permitimos edição
            pass

        x, y, w, h = self.tree.bbox(item_id, col_id)
        # Ajusta para coordenadas absolutas do container
        x += self.tree.winfo_x() + self.tree.master.winfo_x()
        y += self.tree.winfo_y() + self.tree.master.winfo_y()

        valor_atual = self.tree.set(item_id, col_name)

        self._edit_item_id = item_id
        self._edit_column = col_name

        self._edit_entry = ctk.CTkEntry(
            self.tree.master.master,
            width=w + 10,
            height=h + 6,
            font=("Segoe UI", 11),
            fg_color="#1a1a2e",
            border_color="#03a9f4",
        )
        self._edit_entry.place(x=x - 4, y=y - 2)
        self._edit_entry.insert(0, valor_atual)
        self._edit_entry.select_range(0, "end")
        self._edit_entry.focus()

        self._edit_entry.bind("<Return>", lambda e: self._salvar_edicao_inline())
        self._edit_entry.bind("<Escape>", lambda e: self._cancelar_edicao_inline())

    def _salvar_edicao_inline(self):
        """Salva o valor editado e fecha o entry."""
        if not self._edit_entry or self._edit_item_id is None:
            return

        novo_valor = self._edit_entry.get().strip()
        item_id = self._edit_item_id
        col_name = self._edit_column

        self._cancelar_edicao_inline()

        idx = int(item_id)
        logica.push_undo()
        if logica.atualizar_item(idx, col_name, novo_valor):
            self._df_cache = None
            self._filtered_df = None
            self.listar_items()
            self.atualizar_status(f"✏️ {col_name} atualizado!", cor="#4caf50")
        else:
            self.atualizar_status("❌ Erro ao salvar edição", cor="#ef5350")

    def _cancelar_edicao_inline(self):
        """Fecha o entry de edição sem salvar."""
        if self._edit_entry:
            self._edit_entry.destroy()
            self._edit_entry = None
        self._edit_item_id = None
        self._edit_column = None

    def _treeview_single_click(self, event):
        """Foca a Treeview (fecha edição inline se clicar fora)."""
        if self._edit_entry:
            region = self.tree.identify_region(event.x, event.y)
            if region not in ("cell", "tree"):
                self._salvar_edicao_inline()

    def _copiar_selecao(self, event):
        """Copia célula selecionada com Ctrl+C."""
        selection = self.tree.selection()
        if not selection:
            return
        col_id = self.tree.identify_column(event.x)
        col_index = int(col_id.replace("#", "")) - 1
        cols = self.tree["columns"]
        if 0 <= col_index < len(cols):
            valor = self.tree.set(selection[0], cols[col_index])
            self.root.clipboard_clear()
            self.root.clipboard_append(str(valor))

    # ── CORE OPERATIONS ───────────────────────────────────────────

    def aplicar_agrupamento(self):
        valor = self.group_var.get().strip()
        if valor:
            self.group_field = valor
            self.atualizar_status(f"📊 Agrupando por: {valor}", cor="#03a9f4")
        else:
            self.group_field = None
            self.atualizar_status("📊 Agrupamento removido.", cor="#03a9f4")
        if self._active_tab in self._tabs:
            self._tabs[self._active_tab]["group_field"] = self.group_field
        self._df_cache = None
        self._filtered_df = None
        self.listar_items()

    def carregar_lista(self):
        from tkinter import filedialog

        caminho = filedialog.askopenfilename(
            title="Escolha o arquivo de lista (JSON)",
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            self.atualizar_status("📂 Carregamento cancelado.")
            return

        try:
            tab_name = self._add_file_tab(caminho)

            # update columns and group combo from the tab's data
            tab = self._tabs.get(tab_name)
            if tab:
                df = logica.carregar_dataframe()
                self.columns = list(df.columns) if not df.empty else []
                self.is_anime_like = {"nome", "nota", "status"}.issubset(set(self.columns))

                if hasattr(self, "group_combo"):
                    self.group_combo.configure(values=self.columns)
                    self.group_field = None
                    self.group_var.set("")

                if hasattr(self, "btn_dropado") and hasattr(self, "btn_planejado"):
                    if self.is_anime_like:
                        self.btn_dropado.pack(pady=3, padx=10)
                        self.btn_planejado.pack(pady=3, padx=10)
                    else:
                        self.btn_dropado.pack_forget()
                        self.btn_planejado.pack_forget()

                nome_curto = caminho.split("/")[-1].split("\\")[-1]
                self.atualizar_status(f"📂 Lista Carregada: {nome_curto}", cor="#03a9f4")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar lista:\n{e}")
            self.atualizar_status("❌ Erro ao carregar lista.", cor="#ff5252")

    def pesquisar_item(self):
        """Pesquisa manual pelo botão (já temos filtro ao vivo, mas mantemos compatibilidade)."""
        self._aplicar_filtro_vivo()

    def limpar_area(self):
        self.tree.delete(*self.tree.get_children())

    def listar_items(self):
        """Carrega dados e popula a Treeview."""
        df = logica.carregar_dataframe()
        self._df_cache = df
        self._filtered_df = None

        if df.empty:
            self.limpar_area()
            msg = (
                "📂 Nenhum arquivo de lista carregado.\nUse '📂 Carregar lista' para abrir um JSON."
                if self.current_file is None
                else "📭 Nenhum item cadastrado ainda!\nAdicione items com '➕ Novo Item'."
            )
            self.atualizar_status(msg)
            self._atualizar_stats_cards()
            return

        registros = self._get_dados_exibir()
        self._popular_treeview(registros)
        self._atualizar_stats_cards()
        self.atualizar_status(f"✅ {len(registros)} item(ns) listados!", cor="#4caf50")

    # ── CRUD ──────────────────────────────────────────────────────

    def adicionar_item(self):
        janela = ctk.CTkToplevel(self.root)
        janela.title("➕ Novo Item")
        janela.geometry("450x500")
        janela.configure(fg_color="#14141f")
        janela.transient(self.root)
        janela.grab_set()

        # Container interno com grid pra garantir renderização
        container = ctk.CTkFrame(janela, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=10)
        container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            container,
            text="Novo Item",
            font=("Arial", 18, "bold"),
            text_color="#00d4ff",
            fg_color="#1a1a2e",
        ).grid(row=0, column=0, pady=(5, 15), sticky="ew")

        if not getattr(self, "columns", None):
            self.columns = ["nome"]

        entries = {}
        campos = self.columns[:]
        if "tags" not in campos:
            campos.append("tags")

        row = 1
        for col in campos:
            ctk.CTkLabel(container, text=f"{col}:", anchor="w").grid(
                row=row, column=0, pady=(5, 0), sticky="ew"
            )
            row += 1
            ent = ctk.CTkEntry(container, height=30, corner_radius=8)
            ent.grid(row=row, column=0, pady=(0, 5), sticky="ew")
            entries[col] = ent
            row += 1

        def salvar_novo():
            # Garante que está operando no arquivo correto da aba ativa
            if self.current_file:
                logica.set_ranking_file(self.current_file)
            logica.push_undo()
            registro = {col: entry.get() for col, entry in entries.items()}
            df = logica.carregar_dataframe()
            df = pd.concat([df, pd.DataFrame([registro])], ignore_index=True)
            logica.salvar_lista(df.to_dict(orient="records"))
            messagebox.showinfo("Sucesso", "Item adicionado! 🎉")
            janela.destroy()
            self._df_cache = None
            self._filtered_df = None
            self.listar_items()
            self.atualizar_status("➕ Item adicionado!", cor="#4caf50")

        ctk.CTkButton(
            container,
            text="➕ ADICIONAR",
            command=salvar_novo,
            height=40,
            corner_radius=12,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=row, column=0, pady=15)

        # Força atualização pra garantir renderização
        janela.update_idletasks()
        janela.update()

        janela.protocol("WM_DELETE_WINDOW", janela.destroy)

    # ── ESTATÍSTICAS ──────────────────────────────────────────────

    def mostrar_stats(self):
        """Abre janela com estatísticas detalhadas."""
        df = logica.carregar_dataframe()
        if df.empty:
            messagebox.showinfo("Estatísticas", "📭 Nenhum item cadastrado ainda.")
            return

        top = ctk.CTkToplevel(self.root)
        top.title("📈 Estatísticas Detalhadas")
        top.geometry("600x500")
        top.configure(fg_color="#101018")
        top.transient(self.root)

        texto = ctk.CTkTextbox(
            top, corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#14141f",
        )
        texto.pack(fill="both", expand=True, padx=10, pady=10)

        if self.is_anime_like:
            import sys, io
            old_stdout = sys.stdout
            sys.stdout = mystdout = io.StringIO()
            logica.mostrar_estatisticas()
            sys.stdout = old_stdout
            capturado = mystdout.getvalue()
            texto.insert("1.0", capturado or "📭 Nenhum item cadastrado ainda!\n")
        else:
            texto.insert("1.0", logica.estatisticas_genericas())

        texto.configure(state="disabled")
        top.lift()

    def mostrar_grafico_stats(self):
        df = logica.carregar_dataframe()
        if df.empty:
            messagebox.showinfo("Estatísticas", "📭 Nenhum item cadastrado ainda.")
            return

        coluna = self.group_field or self.group_var.get().strip()
        if not coluna or coluna not in df.columns:
            for nome in ("status", "categoria", "tag"):
                if nome in df.columns:
                    coluna = nome
                    break
            if not coluna:
                for col in df.columns:
                    if df[col].dtype == object:
                        coluna = col
                        break
        if not coluna or coluna not in df.columns:
            messagebox.showwarning(
                "Estatísticas",
                "Não foi possível determinar uma coluna categórica para o gráfico.",
            )
            return

        vc = df[coluna].astype(str).value_counts()
        if vc.empty:
            messagebox.showinfo("Estatísticas", f"Nenhum dado para coluna '{coluna}'.")
            return

        fig, ax = plt.subplots(figsize=(7, 4))
        vc.plot(kind="bar", ax=ax, color="#03a9f4")
        ax.set_title(f"Distribuição por '{coluna}'", fontsize=12)
        ax.set_ylabel("Contagem")
        ax.set_xlabel(coluna)
        ax.grid(axis="y", alpha=0.3)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
        fig.tight_layout()

        top = ctk.CTkToplevel(self.root)
        top.title(f"📊 Gráfico de '{coluna}'")
        top.geometry("700x500")
        top.configure(fg_color="#101018")
        top.lift()
        top.focus_force()
        top.attributes("-topmost", True)
        top.after(100, lambda: top.attributes("-topmost", False))

        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True, padx=10, pady=10)

        self.atualizar_status(f"📊 Gráfico exibido para '{coluna}'.", cor="#03a9f4")

    # ── SALVAR ────────────────────────────────────────────────────

    def salvar_items(self):
        """Salva os dados atuais no JSON."""
        df = logica.carregar_dataframe()
        if df.empty:
            self.atualizar_status("📭 Nada para salvar.", cor="#ffa726")
            return
        logica.salvar_lista(df.to_dict(orient="records"))
        self.atualizar_status("💾 Salvo com sucesso!", cor="#1567E2")
        self.listar_items()

    # ── EXPORTAR CSV ─────────────────────────────────────────────

    def exportar_csv(self):
        """Exporta os dados atuais para CSV."""
        from tkinter import filedialog

        df = logica.carregar_dataframe()
        if df.empty:
            self.atualizar_status("📭 Nada para exportar.", cor="#ffa726")
            return

        caminho = filedialog.asksaveasfilename(
            title="Exportar como CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            return

        if logica.exportar_csv(caminho):
            nome = caminho.split("/")[-1].split("\\")[-1]
            self.atualizar_status(f"📥 Exportado: {nome}", cor="#4caf50")
        else:
            self.atualizar_status("❌ Erro ao exportar CSV", cor="#ef5350")

    # ── UNDO / REDO ──────────────────────────────────────────────

    def desfazer(self):
        if logica.undo():
            self._df_cache = None
            self._filtered_df = None
            self.listar_items()
            self.atualizar_status("↩️ Desfeito", cor="#ffa726")
        else:
            self.atualizar_status("⚠️ Nada para desfazer", cor="#ffa726")

    def refazer(self):
        if logica.redo():
            self._df_cache = None
            self._filtered_df = None
            self.listar_items()
            self.atualizar_status("↪️ Refito", cor="#03a9f4")
        else:
            self.atualizar_status("⚠️ Nada para refazer", cor="#ffa726")

    # ── TAGS ─────────────────────────────────────────────────────

    def gerenciar_tags(self):
        """Abre janela para gerenciar tags do item selecionado."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Tags", "Selecione um item na lista primeiro.")
            return

        item_id = selection[0]
        idx = int(item_id)
        cols = self.tree["columns"]

        # get item data
        valores = {c: self.tree.set(item_id, c) for c in cols}

        if "tags" not in valores:
            valores["tags"] = ""

        # parse current tags
        tags_str = str(valores.get("tags", ""))
        tags_atuais = {t.strip() for t in tags_str.split(",") if t.strip()}

        janela = ctk.CTkToplevel(self.root)
        janela.title(f"🏷️ Tags: {valores.get('nome', valores.get(cols[0], ''))}")
        janela.geometry("400x350")
        janela.configure(fg_color="#14141f")
        janela.transient(self.root)
        janela.grab_set()

        ctk.CTkLabel(
            janela, text="Gerenciar Tags",
            font=("Arial", 16, "bold"), text_color="#03a9f4",
        ).pack(pady=(15, 10))

        frame_tags = ctk.CTkFrame(janela, fg_color="#1a1a2e")
        frame_tags.pack(fill="both", expand=True, padx=15, pady=5)

        # list existing tags as removable chips
        lbl_tags = ctk.CTkLabel(
            frame_tags, text="Tags atuais:",
            font=("Arial", 12), anchor="w",
        )
        lbl_tags.pack(fill="x", padx=10, pady=(10, 5))

        tags_frame = ctk.CTkFrame(frame_tags, fg_color="transparent")
        tags_frame.pack(fill="x", padx=10, pady=5)

        chips = []
        def recarregar_chips():
            for w in tags_frame.winfo_children():
                w.destroy()
            chips.clear()
            for tag in sorted(tags_atuais):
                chip_frame = ctk.CTkFrame(tags_frame, fg_color="#202840", corner_radius=6)
                chip_frame.pack(side="left", padx=3, pady=2)

                ctk.CTkLabel(chip_frame, text=f" {tag} ", font=("Arial", 11)).pack(side="left", padx=4)
                rm_btn = ctk.CTkButton(
                    chip_frame, text="✕", width=20, height=20,
                    fg_color="#ef5350", hover_color="#c62828",
                    font=("Arial", 10),
                    command=lambda t=tag: remover_tag(t),
                )
                rm_btn.pack(side="right", padx=(0, 2))
                chips.append((tag, chip_frame))

        def remover_tag(tag):
            tags_atuais.discard(tag)
            logica.push_undo()
            nova_str = ", ".join(sorted(tags_atuais))
            logica.atualizar_item(idx, "tags", nova_str) if "tags" in cols else None
            self._df_cache = None
            recarregar_chips()

        recarregar_chips()

        # add new tag
        add_frame = ctk.CTkFrame(janela, fg_color="transparent")
        add_frame.pack(fill="x", padx=15, pady=10)

        nova_tag_var = ctk.StringVar()
        nova_tag_entry = ctk.CTkEntry(
            add_frame, textvariable=nova_tag_var,
            placeholder_text="Nova tag...", width=200, height=30,
        )
        nova_tag_entry.pack(side="left", padx=(0, 5))

        def adicionar_tag():
            tag = nova_tag_var.get().strip().lower()
            if tag and tag not in tags_atuais:
                tags_atuais.add(tag)
                logica.push_undo()

                if "tags" not in cols:
                    if self.current_file:
                        logica.set_ranking_file(self.current_file)
                    df = logica.carregar_dataframe()
                    df["tags"] = ""
                    logica.salvar_lista(df.to_dict(orient="records"))

                nova_str = ", ".join(sorted(tags_atuais))
                logica.atualizar_item(idx, "tags", nova_str)
                self._df_cache = None
                nova_tag_var.set("")
                recarregar_chips()

        ctk.CTkButton(
            add_frame, text="+ Adicionar",
            command=adicionar_tag, width=100, height=30,
            fg_color="#03a9f4",
        ).pack(side="left")

        nova_tag_entry.bind("<Return>", lambda e: adicionar_tag())

        def fechar():
            self._df_cache = None
            self._filtered_df = None
            self.listar_items()
            janela.destroy()

        ctk.CTkButton(
            janela, text="Fechar", command=fechar,
            width=120, height=35, fg_color="#313150",
        ).pack(pady=10)

        janela.protocol("WM_DELETE_WINDOW", fechar)

    # ── EXCLUIR ───────────────────────────────────────────────────

    def excluir_items(self):
        janela = ctk.CTkToplevel(self.root)
        janela.title("❌ Excluir Item")
        janela.geometry("700x500")
        janela.configure(fg_color="#14141f")
        janela.transient(self.root)
        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="Selecione item para excluir:",
            font=("Arial", 14, "bold"),
            text_color="#ff6b6b",
            fg_color="#1a1a2e",
        ).pack(pady=10)

        lista_frame = ctk.CTkFrame(janela, fg_color="#1a1a2e")
        lista_frame.pack(pady=10, fill="both", expand=True)

        df = logica.carregar_dataframe()
        if df.empty:
            ctk.CTkLabel(
                janela,
                text="📭 Nenhum item para excluir.",
                font=("Arial", 12),
                text_color="#ffffff",
                fg_color="#1a1a2e",
            ).pack(pady=10)
            janela.protocol("WM_DELETE_WINDOW", janela.destroy)
            return

        colunas = list(df.columns)
        col_principal = colunas[0]
        for cand in colunas:
            if cand.lower() == "nome":
                col_principal = cand
                break
        else:
            for cand in colunas:
                if cand.lower() not in ("eps", "nota", "status"):
                    col_principal = cand
                    break

        listbox = tk.Listbox(
            lista_frame,
            bg="#0f0f23",
            fg="#ffffff",
            selectbackground="#ff4757",
            font=("Consolas", 11),
            activestyle="none",
        )
        scrollbar = tk.Scrollbar(lista_frame, orient="vertical", command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for i, (_, row) in enumerate(df.iterrows(), 1):
            valor = str(row.get(col_principal, ""))
            if len(valor) > 40:
                valor = valor[:37] + "..."
            listbox.insert("end", f"{i:2}. {valor}")

        def confirmar_exclusao():
            selecao = listbox.curselection()
            if not selecao:
                messagebox.showwarning("Atenção", "Selecione um item!")
                return
            idx = selecao[0]
            linha_idx = df.index[idx]
            valor = str(df.loc[linha_idx].get(col_principal, ""))
            if not valor:
                valor = f"linha {idx+1}"

            if messagebox.askyesno("Confirmar?", f"Excluir '{valor}'?"):
                if self.current_file:
                    logica.set_ranking_file(self.current_file)
                logica.push_undo()
                df_drop = df.drop(index=linha_idx)
                logica.salvar_lista(df_drop.to_dict(orient="records"))
                messagebox.showinfo("Sucesso", f"❌ '{valor}' excluído!")
                janela.destroy()
                self._df_cache = None
                self._filtered_df = None
                self.listar_items()
                self.atualizar_status(f"🗑️ Excluído: {valor}", cor="#f33a44")

        ctk.CTkButton(
            janela,
            text="🗑️ EXCLUIR SELECIONADO",
            command=confirmar_exclusao,
            fg_color="#ff4757",
            text_color="white",
            font=ctk.CTkFont(size=12),
        ).pack(pady=20)
        janela.protocol("WM_DELETE_WINDOW", janela.destroy)

    # ── DROPADO / PLANEJADO ──────────────────────────────────────

    def add_dropado(self):
        janela = ctk.CTkToplevel(self.root)
        janela.title("💔 Item Dropado")
        janela.geometry("450x350")
        janela.configure(fg_color="#14141f")
        janela.transient(self.root)
        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="💔 Marcar como dropado",
            font=("Arial", 16, "bold"),
            text_color="#ff6b6b",
            fg_color="#1a1a2e",
        ).pack(pady=20)

        ctk.CTkLabel(
            janela, text="Nome do item:", text_color="white", fg_color="#1a1a2e"
        ).pack(pady=(0, 5))
        nome_entry = ctk.CTkEntry(janela, font=("Arial", 12), width=350)
        nome_entry.pack(pady=5)
        nome_entry.focus()

        ctk.CTkLabel(
            janela, text="Nota (0-10):", text_color="white", fg_color="#1a1a2e"
        ).pack(pady=(10, 5))
        nota_entry = ctk.CTkEntry(janela, font=("Arial", 12), width=350)
        nota_entry.pack(pady=5)

        def salvar_dropado():
            try:
                nome = nome_entry.get().strip()
                if not nome:
                    messagebox.showerror("Erro", "Nome é obrigatório!")
                    return
                nota = float(nota_entry.get() or 0)
                logica.push_undo()
                logica.add_dropado_gui(nome, nota)
                messagebox.showinfo("Dropado", f"💔 '{nome}' marcado como dropado!\n")
                janela.destroy()
                self._df_cache = None
                self._filtered_df = None
                self.listar_items()
                self.atualizar_status(f"💔 Dropado: {nome}", cor="#f33a44")
            except ValueError:
                messagebox.showerror("Erro", "Nota deve ser um número")

        ctk.CTkButton(
            janela,
            text="💔 CONFIRMAR DROP",
            command=salvar_dropado,
            fg_color="#ff4757",
            text_color="white",
            font=("Arial", 12, "bold"),
        ).pack(pady=25)
        janela.protocol("WM_DELETE_WINDOW", janela.destroy)

    def add_planejado(self):
        janela = ctk.CTkToplevel(self.root)
        janela.title("⏳ Planejar Item")
        janela.geometry("450x350")
        janela.configure(fg_color="#14141f")
        janela.transient(self.root)
        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="⏳ Adicionar aos planejados",
            font=("Arial", 16, "bold"),
            text_color="#ffa726",
            fg_color="#1a1a2e",
        ).pack(pady=20)

        ctk.CTkLabel(
            janela, text="Nome do item:", text_color="white", fg_color="#1a1a2e"
        ).pack(pady=(0, 5))
        nome_entry = ctk.CTkEntry(janela, font=("Arial", 12), width=350)
        nome_entry.pack(pady=5)
        nome_entry.focus()

        ctk.CTkLabel(
            janela, text="Nota esperada (0-10):", text_color="white", fg_color="#1a1a2e"
        ).pack(pady=(10, 5))
        nota_entry = ctk.CTkEntry(janela, font=("Arial", 12), width=350)
        nota_entry.pack(pady=5)
        nota_entry.insert(0, "9.0")

        def salvar_planejado():
            try:
                nome = nome_entry.get().strip()
                if not nome:
                    messagebox.showerror("Erro", "Nome é obrigatório!")
                    return
                nota = float(nota_entry.get() or 9.0)
                logica.push_undo()
                logica.add_planejado_gui(nome, nota)
                messagebox.showinfo(
                    "Planejado", f"⏳ '{nome}' adicionado aos planejados!"
                )
                janela.destroy()
                self._df_cache = None
                self._filtered_df = None
                self.listar_items()
                self.atualizar_status(f"⏳ Planejado: {nome}", cor="#F7A53A")
            except ValueError:
                messagebox.showerror("Erro", "Nota deve ser um número!")

        ctk.CTkButton(
            janela,
            text="⏳ ADICIONAR AOS PLANEJADOS",
            command=salvar_planejado,
            fg_color="#ffa726",
            text_color="black",
            font=("Arial", 12, "bold"),
        ).pack(pady=25)
        janela.protocol("WM_DELETE_WINDOW", janela.destroy)

    # ── ANIMAÇÕES ─────────────────────────────────────────────────

    def animar_gifs_left(self, delay=400):
        if not self.left_gif_sets or not self.left_gif_label:
            return
        frames = self.left_gif_sets[self.left_gif_index]
        frame = frames[self.left_gif_frame_index]
        self.left_gif_label.configure(image=frame)
        self.left_gif_frame_index += 1
        if self.left_gif_frame_index >= len(frames):
            self.left_gif_frame_index = 0
            self.left_gif_index = (self.left_gif_index + 1) % len(self.left_gif_sets)
        self.root.after(delay, self.animar_gifs_left)

    def animar_botao_click(self, botao, comando):
        original = botao.cget("fg_color")
        click_color = "#007a99"

        def fazer():
            botao.configure(fg_color=click_color)
            self.root.after(
                120, lambda: (botao.configure(fg_color=original), comando())
            )

        fazer()

    def atualizar_status(self, msg, cor=None):
        self.status_var.set(msg)
        if cor:
            original = self.status_bar.cget("text_color")
            self.status_bar.configure(text_color=cor)
            self.root.after(400, lambda: self.status_bar.configure(text_color=original))
        self.root.update_idletasks()


if __name__ == "__main__":
    root = ctk.CTk()
    app = ItemTrackerGUI(root)

    def _on_close():
        app._theme_watcher.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()
