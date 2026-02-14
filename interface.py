import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import logica
import importlib
import pandas as pd

importlib.reload(logica)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ItemTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🗂️ PeakVault")
        self.root.geometry("900x700")
        self.root.configure(fg_color="#1a1a2e")

        # arquivo JSON atual (padrão: lista de items)
        self.current_file = "ranking_animes.json"
        logica.set_ranking_file(self.current_file)

        self.items = logica.carregar_items()

        self.columns = list(logica.carregar_dataframe().columns)
        # flag: arquivo atual é "tipo anime" (tem nome/nota/status)?
        self.is_anime_like = {"nome", "nota", "status"}.issubset(set(self.columns))
        self.group_field = None

        self.criar_interface()

    def criar_interface(self):

        # Frame principal
        main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=10, pady=20)

        # Botões (Esquerda (30%))
        left_frame = ctk.CTkFrame(main_frame, width=240, corner_radius=15)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False)  # fixa largura 250px

        # Título
        titulo = ctk.CTkLabel(
            left_frame,
            text="PeakVault",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        titulo.pack(pady=(20, 8))

        # barra de pesquisa

        ctk.CTkLabel(
            left_frame,
            text="🔍 Buscar item:",
            font=ctk.CTkFont(size=11),
        ).pack(pady=(5, 0))
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(
            left_frame,
            textvariable=self.search_var,
            width=200,
            corner_radius=8,
        )
        search_entry.pack(pady=(0, 4), padx=(16))

        ctk.CTkButton(
            left_frame,
            text="🔍 Pesquisar",
            command=self.pesquisar_item,
            height=28,
            width=120,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(pady=(0, 12), padx=16)

        # criamos os botões individualmente para poder esconder/mostrar alguns
        self.botao_defs = []

        def add_botao(texto, comando, attr_name=None):
            btn = ctk.CTkButton(
                left_frame,
                text=texto,
                command=lambda c=comando, b=None: None,  # placeholder
                height=34,
                width=200,
                corner_radius=10,
                font=ctk.CTkFont(size=12, weight="bold"),
                hover_color="#00abce",
            )
            btn.configure(
                command=lambda c=comando, b=btn: self.animar_botao_click(b, c)
            )
            btn.pack(pady=5, padx=16)
            if attr_name:
                setattr(self, attr_name, btn)
            self.botao_defs.append(btn)

        add_botao("📊 Listar Items", self.listar_items)
        add_botao("➕ Novo Item", self.adicionar_item)
        add_botao("❌ Excluir Item", self.excluir_items)
        add_botao("💔 Dropado", self.add_dropado, attr_name="btn_dropado")
        add_botao("⏳ Planejar", self.add_planejado, attr_name="btn_planejado")
        add_botao("📈 Estatísticas", self.mostrar_stats)
        add_botao("💾 Salvar", self.salvar_items)
        add_botao("📂 Carregar lista", self.carregar_lista)

        # se o arquivo atual não for "anime-like", escondemos botões específicos de status
        if not self.is_anime_like:
            self.btn_dropado.pack_forget()
            self.btn_planejado.pack_forget()

        # Área de texto (lista + stats)
        # === direita: output (70%)

        right_frame = ctk.CTkFrame(main_frame, corner_radius=15)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 10))

        # Título output

        ctk.CTkLabel(
            right_frame, text="📋 OUTPUT", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(18, 6))

        # painel de agrupamento
        group_frame = ctk.CTkFrame(right_frame, fg_color="#333333")
        group_frame.pack(fill="x", pady=5, padx=(5, 10))
        
        ctk.CTkLabel(
            group_frame,
            text="Agrupar por:",
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(4, 4))
        
        self.group_var = ctk.StringVar(value="")
        self.group_combo = ctk.CTkComboBox(
            group_frame,
            variable=self.group_var,
            width=140,
            height=26,
            corner_radius=8,
            state="readonly",
            values=self.columns if self.columns else [],
        )
        self.group_combo.pack(side="left", padx=(0, 8))
        
        ctk.CTkButton(
            group_frame,
            text="Aplicar",
            width=70,
            height=26,
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            command=self.aplicar_agrupamento,
        ).pack(side="left")
        
        self.text_area = ctk.CTkTextbox(
            right_frame,
            height=460,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=13),
        )
        self.text_area.pack(fill="both", expand=True, padx=8, pady=(0, 16))

        # Status bar

        self.status_var = ctk.StringVar()
        self.status_var.set("🔥 Pronto! Clique em Listar Items")
        self.status_bar = ctk.CTkLabel(
            right_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self.status_bar.pack(fill="x", side="bottom", padx=10, pady=(0, 10))

    def animar_botao_click(self, botao, comando):
        # pequena animação visual ao clicar no botão

        # cor original
        original = botao.cget("fg_color")
        # cor mais escura para o "clique"
        click_color = "#007a99"

        def fazer():
            botao.configure(fg_color=click_color)
            # volta à cor original e chama o comando depois de 120ms
            self.root.after(
                120, lambda: (botao.configure(fg_color=original), comando())
            )

        fazer()

    def atualizar_status(self, msg, cor=None):
        # atualize a barra de status, opcionalmente com destaque temporário.
        self.status_var.set(msg)
        if cor:
            # salva cor original
            original = self.status_bar.cget("text_color")
            self.status_bar.configure(text_color=cor)
            # volta à cor original depois de 400ms
            self.root.after(400, lambda: self.status_bar.configure(text_color=original))
        self.root.update_idletasks()

    def aplicar_agrupamento(self):
        # atualiza a coluna usada para agrupar no modo genérico
        valor = self.group_var.get().strip()
        if valor:
            self.group_field = valor
            self.atualizar_status(f"📊 Agrupando por: {valor}", cor="#03a9f4")
        else:
            self.group_field = None
            self.atualizar_status("📊 Agrupamento removido.", cor="#03a9f4")
        # re-renderiza a listagem
        self.listar_items()
    
    def carregar_lista(self):
        # Abre um JSON e passa a usá-lo como base de dados.
        from tkinter import filedialog

        caminho = filedialog.askopenfilename(
            title="Escolha o arquivo de lista (JSON)",
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")],
        )
        if not caminho:
            self.atualizar_status("📂 Carregamento cancelado.")
            return

        # atualiza o arquivo atual na lógica e na GUI.
        self.current_file = caminho
        logica.set_ranking_file(caminho)

        # recarrega dados e output
        try:
            self.items = logica.carregar_items()
            # guarda as colunas atuais para gerar formulários dinâmicos
            df = logica.carregar_dataframe()
            self.columns = list(df.columns)
            self.is_anime_like = {"nome", "nota", "status"}.issubset(set(self.columns))

            # atualiza opções do combobox de agrupamento
            if hasattr(self, "group_combo"):
                self.group_combo.configure(values=self.columns)
                # se coluna anterior ainda existir, mantém seleção
                if self.group_field in self.columns:
                    self.group_var.set(self.group_field)
                else:
                    self.group_var.set("")
                    self.group_field = None

            # atualiza visibilidade dos botões especiais
            if hasattr(self, "btn_dropado") and hasattr(self, "btn_planejado"):
                if self.is_anime_like:
                    # garante que estão visíveis
                    self.btn_dropado.pack(pady=5, padx=16)
                    self.btn_planejado.pack(pady=5, padx=16)
                else:
                    self.btn_dropado.pack_forget()
                    self.btn_planejado.pack_forget()

            self.listar_items()
            nome_curto = caminho.split("/")[-1].split("\\")[-1]
            self.atualizar_status(f"📂 Lista Carregada: {nome_curto}", cor="#03a9f4")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar lista:\n{e}")
            self.atualizar_status("❌ Erro ao carregar lista.", cor="#ff5252")

    def pesquisar_item(self):
        consulta = self.search_var.get()
        self.limpar_area()

        if not consulta.strip():
            self.text_area.insert("end", "Digite um nome para pesquisar.\n")
            self.atualizar_status("ℹ️ Informe um termo de busca.")
            return

        resultados = logica.buscar_items(consulta)

        # pega info genérica de tabela
        tabela_info = logica.obter_tabela_generica()

        if not tabela_info:
            self.text_area.insert(
                "end",
                "📭 Nenhum item válido encontrado no arquivo.\n",
            )
            self.atualizar_status("📭 Nenhum item válido.", cor="#ffa726")
            return

        colunas = tabela_info["colunas"]
        registros = tabela_info["registros"]
        larguras = tabela_info["larguras"]

        # filtra registros cuja string da consulta aparece em qualquer campo
        consulta_lower = consulta.lower()
        resultados = []
        for r in registros:
            if any(consulta_lower in str(v).lower() for v in r.values()):
                resultados.append(r)
        self.text_area.insert(
            "end", f"🔍 Resultado da busca por: '{consulta}'\n\n", ("header",)
        )

        if not resultados:
            self.text_area.insert(
                "end",
                "📭 Nenhum item encontrado.\n",
            )
            self.atualizar_status("📭 Nenhum item encontrado.", cor="#ffa726")
            return

        # cabeçalho
        partes_header = []
        for chave in colunas:
            partes_header.append(f"{chave.upper():<{larguras[chave]}}")
        header = " | ".join(partes_header)
        self.text_area.insert("end", header + "\n")
        self.text_area.insert("end", "-" * len(header) + "\n")

        # linhas
        for r in resultados:
            partes = []
            for chave in colunas:
                valor = str(r.get(chave, ""))
                partes.append(f"{valor:<{larguras[chave]}}")
            linha = " | ".join(partes)
            self.text_area.insert("end", linha + "\n")

        self.text_area.see("end")
        self.atualizar_status(
            f"🔍 {len(resultados)} item(s) encontrado(s).", cor="#03a9f4"
        )

    def limpar_area(self):
        self.text_area.delete("1.0", "end")

    def _inserir_linhas_animado(self, linhas_com_tags, delay=10):
        # insere uma lista de (texto, tags) linha alinha com pequeno delay.
        def passo(i):
            if i >= len(linhas_com_tags):
                return
            texto, tags = linhas_com_tags[i]
            if tags:
                self.text_area.insert("end", texto, tags)
            else:
                self.text_area.insert("end", texto)
            self.text_area.see("end")
            self.root.after(delay, lambda: passo(i + 1))

        passo(0)

    def listar_items(self):
        self.limpar_area()

        # carrega dados crus do JSON
        dados = logica.carregar_dataframe()

        if dados.empty:
            self.text_area.insert(
                "end",
                "📭 Nenhum item cadastrado ainda!\nAdicione items com ➕ Novo Item.",
            )
            self.atualizar_status("📭 Nenhum Item cadastrado.")
            return

        # checa se é compatível com o modelo antigo de items
        colunas_df = set(dados.columns)
        eh_item_like = {"nome", "nota", "status"}.issubset(colunas_df)

        # estilos / cores

        self.text_area.tag_config(
            "header",
            justify="center",
        )
        self.text_area.tag_config(
            "titulo_bloco",
            foreground="#ffffff",
        )

        self.text_area.tag_config("completo", foreground="#4caf50")
        self.text_area.tag_config("assistindo", foreground="#03a9f4")
        self.text_area.tag_config("planejado", foreground="#ffa726")
        self.text_area.tag_config("dropado", foreground="#ef5350")

        # se for "anime_like" e o usuario não escolheu 
        # agrupamento customizado, usa o modo especial por 
        # status; senão, cai no modo genérico
        if eh_item_like and not self.group_field:
            # visão agrupada por status
            grupos = logica.obter_grupos_items()
            linhas = []
            # cabeçalho geral
            linhas.append(("📋 SEUS ITEMS:\n\n", ("header",)))

            for grupo in grupos:
                status = grupo["status"]
                titulo = grupo["titulo"]

                # título do bloco
                linhas.append((titulo + "\n", ("titulo_bloco", status)))

                # separador proporcional ao título
                largura = max(len(titulo), 20)
                linhas.append(("-" * largura + "\n", (status,)))

                # linhas do bloco
                for linha in grupo["linhas"]:
                    linhas.append((linha + "\n", (status,)))
                linhas.append(("\n", None))

            # insere com animação leve (10 ms entre linhas)
            self._inserir_linhas_animado(linhas, delay=10)  # Auto-scroll
            self.atualizar_status("✅ Items listados!", cor="#4caf50")
        else:
            # tabela genérica para qualquer JSON, com agrupamento e cor por tipo
            tabela_info = logica.obter_tabela_generica()
            if not tabela_info:
                self.text_area.insert(
                    "end",
                    "📭 Nenhum item válido encontrado no arquivo.\n",
                )
                self.atualizar_status("📭 Nenhum Item válido.", cor="#ffa726")
                return

            colunas = tabela_info["colunas"]
            registros = tabela_info["registros"]
            larguras = tabela_info["larguras"]

            # escolhe coluna por agrupamento:
            # 1) se o usuário escolheu uma coluna válida no combobox, usa ela
            # 2) senão, heurística: status -> categoria -> primeira coluna
            if self.group_field in colunas:
                col_grupo = self.group_field
            elif "status" in colunas:
                col_grupo = "status"
            elif "categoria" in colunas:
                col_grupo = "categoria"
            else:
                col_grupo = colunas[0]

            # conta ocorrências por grupo
            from collections import Counter

            contagens = Counter(str(r.get(col_grupo, "")) for r in registros)
            # ordena grupos por contagens desc (mais frequentes primeiro)
            grupos_ord = sorted(contagens.items(), key=lambda x: (-x[1], x[0].lower()))

            # define cores para até alguns grupos diferentes

            paleta = [
                "#4caf50",  # verde
                "#03a9f4",  # azul
                "#ffa726",  # laranja
                "#ef5350",  # vermelho
                "#ab47bc",  # roxo
                "#26a69a",  # teal
            ]

            cor_por_grupo = {}
            for idx, (valor, _) in enumerate(grupos_ord):
                cor_por_grupo[valor] = paleta[idx % len(paleta)]

            # criar tags de cor dinamicamente
            for valor, cor in cor_por_grupo.items():
                tag_name = f"grupo_{valor}"
                self.text_area.tag_config(tag_name, foreground=cor)

            # cabeçalho geral
            self.text_area.insert("end", "📋 SEUS ITEMS :\n\n", ("header",))

            # monta linha de cabeçalho com alinhamento
            # monta cabeçalho
            partes_header = []
            for chave in colunas:
                partes_header.append(f"{chave.upper():<{larguras[chave]}}")
            header_line = " | ".join(partes_header)
            self.text_area.insert("end", header_line + "\n")

            # para cada grupo: bloco com título + linhas daquele tipo
            for valor_grupo, _ in grupos_ord:
                titulo_bloco = f"{col_grupo.upper()}: {valor_grupo or '(vazio)'} ({contagens[valor_grupo]})"
                tag_grupo = f"grupo_{valor_grupo}"

                # titulo do bloco
                self.text_area.insert(
                    "end", "\n" + titulo_bloco + "\n", ("titulo_bloco", tag_grupo)
                )
                self.text_area.insert(
                    "end", "-" * max(len(titulo_bloco), 20) + "\n", (tag_grupo,)
                )

                # linhas do grupo
                for r in registros:
                    if str(r.get(col_grupo, "")) != valor_grupo:
                        continue
                    partes = []
                    for chave in colunas:
                        valor = str(r.get(chave, ""))
                        partes.append(f"{valor:<{larguras[chave]}}")
                    linha = " | ".join(partes)
                    self.text_area.insert("end", linha + "\n", (tag_grupo,))

            self.text_area.see("end")
            self.atualizar_status("✅ Items listados!", cor="#4caf50")

    def adicionar_item(self):
        janela = ctk.CTkToplevel(self.root)
        janela.title("➕ Novo Item")
        janela.geometry("450x500")
        janela.configure(fg_color="#1a1a2e")
        janela.transient(self.root)
        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="Novo Item",
            font=("Arial", 18, "bold"),
            text_color="#00d4ff",
            fg_color="#1a1a2e",
        ).pack(pady=(15, 10))

        # se não houver colunas definidas, assume 'nome' como única
        if not getattr(self, "columns", None):
            self.columns = ["nome"]

        entries = {}

        for col in self.columns:
            ctk.CTkLabel(janela, text=f"{col}:").pack(pady=(5, 0))
            ent = ctk.CTkEntry(janela, width=350, height=30, corner_radius=8)
            ent.pack(pady=(0, 5))
            entries[col] = ent

        def salvar_novo():
            # monta novo registro como dict baseado no que o usuário digitou
            registro = {col: entry.get() for col, entry in entries.items()}

            # carrega DataFrame atual, adiciona linha e salva
            df = logica.carregar_dataframe()
            df = pd.concat([df, pd.DataFrame([registro])], ignore_index=True)
            logica.salvar_lista(df.to_dict(orient="records"))

            messagebox.showinfo("Sucesso", "Item adicionado! 🎉")
            janela.destroy()
            # atualiza output automaticamente
            self.listar_items()
            self.atualizar_status("➕ Item adicionado!", cor="#4caf50")

        btn = ctk.CTkButton(
            janela,
            text="➕ ADICIONAR",
            command=salvar_novo,
            width=200,
            height=40,
            corner_radius=12,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        btn.pack(pady=25)
        janela.protocol("WM_DELETE_WINDOW", janela.destroy)

    def mostrar_stats(self):
        self.limpar_area()
        self.text_area.insert("end", "📈 Estatísticas:\n")

        if self.is_anime_like:
            # modo legado: estatísticas por status da lógica antiga
            import sys
            import io

            old_stdout = sys.stdout
            sys.stdout = mystdout = io.StringIO()

            logica.mostrar_estatisticas()

            sys.stdout = old_stdout

            texto_capturado = mystdout.getvalue()

            if texto_capturado.strip():
                self.text_area.insert("end", texto_capturado)
            else:
                self.text_area.insert(
                    "end",
                    "📈 ESTATÍSTICAS:\n\n 📭 Nenhum item cadastrado ainda!\n\nAdicione items com ➕",
                )
        else:
            # modo genérico: usa pandas para estatísticas em qualquer JSON plano
            texto = logica.estatisticas_genericas()
            self.text_area.insert("end", texto)

        self.text_area.see("end")
        self.atualizar_status("📈 Estátísticas atualizadas!", cor="#ffff00")

    def salvar_items(self):
        logica.salvar_lista(logica.carregar_items())
        # Atualiza output automaticamente
        self.listar_items()
        self.atualizar_status("💾 Salvo com sucesso!", cor="#1567E2")

    def excluir_items(self):
        janela = ctk.CTkToplevel(self.root)
        janela.title("❌ Excluir Item")
        janela.geometry("700x500")
        janela.configure(fg_color="#1a1a2e")
        janela.transient(self.root)
        janela.grab_set()

        # lista atual
        ctk.CTkLabel(
            janela,
            text="Selecione item para excluir:",
            font=("Arial", 14, "bold"),
            text_color="#ff6b6b",
            fg_color="#1a1a2e",
        ).pack(pady=10)

        lista_frame = ctk.CTkFrame(janela, fg_color="#1a1a2e")
        lista_frame.pack(pady=10, fill="both", expand=True)

        # carrega dados como DataFrame
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

        # escolhe coluna principal para exibir (nome, se existir; senão a primeira)
        colunas = list(df.columns)
        if "nome" in colunas:
            col_principal = "nome"
        else:
            col_principal = colunas[0]

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

        # Preenche lista com índice + valor da coluna principal
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

            # texto para confirmação
            valor = str(df.loc[linha_idx].get(col_principal, ""))
            if not valor:
                valor = f"linha {idx+1}"

            if messagebox.askyesno(
                "Confirmar?",
                f"Excluir '{valor}'?",
            ):
                # remove do DataFrame e salva
                df_drop = df.drop(index=linha_idx)
                logica.salvar_lista(df_drop.to_dict(orient="records"))

                messagebox.showinfo("Sucesso", f"❌ '{valor}' excluído!")
                janela.destroy()
                # atualiza output automaticamente
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

    def add_dropado(self):
        # interface para marcar como dropado.
        janela = ctk.CTkToplevel(self.root)
        janela.title("💔 Item Dropado")
        janela.geometry("450x350")
        janela.configure(fg_color="#1a1a2e")
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
        nome_entry.focus()  # cursor já no campo

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

                logica.add_dropado_gui(nome, nota)
                messagebox.showinfo("Dropado", f"💔 '{nome}' marcado como dropado!\n")
                janela.destroy()
                # Atualiza output automaticamente
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
        # interface para planejar item
        janela = ctk.CTkToplevel(self.root)
        janela.title("⏳ Planejar Item")
        janela.geometry("450x350")
        janela.configure(fg_color="#1a1a2e")
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
        nome_entry.focus()  # cursor já no campo

        ctk.CTkLabel(
            janela, text="Nota esperada (0-10):", text_color="white", fg_color="#1a1a2e"
        ).pack(pady=(10, 5))
        nota_entry = ctk.CTkEntry(janela, font=("Arial", 12), width=350)
        nota_entry.pack(pady=5)
        nota_entry.insert(0, "9.0")  # nota padrão pra planejados

        def salvar_planejado():
            try:
                nome = nome_entry.get().strip()
                if not nome:
                    messagebox.showerror("Erro", "Nome é obrigatório!")
                    return
                nota = float(nota_entry.get() or 9.0)

                # Chama logica com status fixo "planejado"
                logica.add_planejado_gui(nome, nota)
                messagebox.showinfo(
                    "Planejado", f"⏳ '{nome}' adicionado aos planejados!"
                )
                janela.destroy()
                # Atualiza output automaticamente
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


if __name__ == "__main__":
    root = ctk.CTk()
    app = ItemTrackerGUI(root)
    root.mainloop()
