import json
import pandas as pd

ranking = "ranking_animes.json"


def set_ranking_file(path: str):
    # Define o arquivo JSON atual a ser usado como base de dados.
    global ranking
    ranking = path


def carregar_items():
    # Carrega lista do JSON como lista de dicts (compatibilidade antiga).
    df = carregar_dataframe()

    # garante que 'eps' (ou 'EPS') seja texto ao entregar para a lógica.
    for col in ("eps", "EPS"):
        if col in df.columns:
            df[col] = df[col].astype(str)

    return df.to_dict(orient="records")


def carregar_dataframe():
    # carrega o JSON atual como DataFrame genérico.
    if not ranking:
        return pd.DataFrame()
    try:
        with open(ranking, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    if isinstance(data, list):
        return pd.DataFrame(data)

    elif isinstance(data, dict):
        # para dict simples de chave->valor, cada par vira linha
        return pd.DataFrame([{"chave": k, "valor": v} for k, v in data.items()])
    else:
        return pd.DataFrame()


def salvar_lista(items):
    # Salva lista no JSON (a partir de lista de dicts).
    df = pd.DataFrame(items)

    # garante que 'eps' (se existir) seja tratada como texto, não float.
    for col in ("eps", "EPS"):
        if col in df.columns:
            df[col] = df[col].astype(str)

    with open(ranking, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, indent=2, ensure_ascii=False)


def listar_items():
    # Lista todos os items (opção 1).
    tabela = obter_tabela_generica()

    if tabela.strip():
        print(tabela)
    else:
        print("📭 Nenhum item cadastrado ainda!")


def obter_grupos_items():
    # Gera uma string formatada com a lista de items, por status.
    items = carregar_items()

    if not items:
        return []

    items = ordenar_items(items)

    status_titulos = {
        "planejado": "⏳ PLANEJADOS",
        "assistindo": "📺 ASSISTINDO",
        "completo": "✅ COMPLETOS",
        "dropado": "💔 DROPADOS",
    }

    grupos = []
    status_atual = None
    grupo_atual = None

    # verifica se algum item tem status
    tem_status = any("status" in a for a in items)

    for i, item in enumerate(items, 1):
        nome = item.get("nome", "(sem nome)")
        nota = item.get("nota", "")
        eps = item.get("eps", "")
        status = item.get("status", "") if tem_status else ""

        # decide agrupamento: por status se existir, senão grupo único "ITENS"

        if tem_status:
            chave_status = status
            titulo_grupo = status_titulos.get(status, status.upper() or "ITENS")
        else:
            chave_status = "itens"
            titulo_grupo = "📋 ITENS"

        if chave_status != status_atual:
            # começa novo grupo
            status_atual = chave_status  # linha em branco
            grupo_atual = {
                "status": status_atual,
                "titulo": titulo_grupo,
                "linhas": [],
            }
            grupos.append(grupo_atual)

        # corta nome para 40 caracteres com "..." se for maior
        if len(nome) > 40:
            nome_cortado = nome[:37] + "..."
        else:
            nome_cortado = nome

        # formata linha base: índice + nome
        linha = f"{i:>3}. {nome_cortado:<40}"
        # adiciona nota se existir
        if nota != "":
            linha += f" | {str(nota):>4}"
        # adiciona quantidade de eps se existir
        if eps != "":
            linha += f" | {eps}"
        # adiciona status se estivermos usando status
        if tem_status and status:
            linha += f" | {status}"

        grupo_atual["linhas"].append(linha)

    return grupos


def obter_tabela_generica():
    # Retorna estrutura de tabela genérica: colunas, registros e larguras.
    df = carregar_dataframe()
    if df.empty:
        return None

    # garante que tudo é dict
    registros = df.to_dict(orient="records")

    # descobre todas as chaves existentes
    todas_chaves = set()
    for r in registros:
        todas_chaves.update(r.keys())

    # ordenar chaves deixando 'nome' primeiro, 'nota' e 'status' em seguida se existirem
    colunas = []
    for preferida in ("nome", "NOME", "nota", "status", "eps", "EPS"):
        if preferida in todas_chaves:
            colunas.append(preferida)
            todas_chaves.remove(preferida)
    colunas.extend(sorted(todas_chaves))

    # calcula largura de cada coluna
    larguras = {}
    for chave in colunas:
        max_val = len(chave)
        for r in registros:
            s = str(r.get(chave, ""))
            if len(s) > max_val:
                max_val = len(s)
        larguras[chave] = max_val

    return {
        "colunas": colunas,
        "registros": registros,
        "larguras": larguras,
    }


def buscar_items(consulta):
    # busca items pelo nome (parcial, case-sensitive) e retorna lista já ordenada.
    consulta = consulta.strip().lower()
    if not consulta:
        return []

    items = ordenar_items(carregar_items())
    encontrados = []
    for item in items:
        if any(consulta in str(v).lower() for v in item.values()):
            encontrados.append(item)
    return encontrados


def adicionar_item():
    # adiciona novo item via input() interativo.
    print("=" * 100)
    nome = input("Nome do item: ")
    nota = float(input("Nota: "))
    status = input("Status (assistindo/completo/planejado): ")

    items = carregar_items()
    items.append({"nome": nome, "nota": nota, "status": status})
    items = ordenar_items(items)
    salvar_lista(items)
    print(f"{nome} adicionado!")
    print("=" * 100)


def excluir_item():
    # exclui item por indice (opção 3).
    items = carregar_items()
    listar_items(items)
    idx = int(input("indice para excluir: ")) - 1
    if 0 <= idx < len(items):
        removido = items.pop(idx)
        items = ordenar_items(items)
        salvar_lista(items)
        print(f'{removido["nome"]} excluído!')

    else:
        print("Índice invalido.")
    print("=" * 100)


def add_dropado():
    # adiciona com status 'dropado' (opção 4, extensão).
    print("=" * 100)
    nome = input("Nome do item dropado: ")
    items = carregar_items()
    items.append({"nome": nome, "nota": "--", "status": "dropado"})
    items = ordenar_items(items)
    salvar_lista(items)
    print(f"{nome} marcado como dropado.")
    print("=" * 100)


def add_assistir_dps():
    # adiciona como 'planejado' (opção 5).
    print("=" * 100)
    nome = input("Nome do item para assistir depois: ")
    items = carregar_items()
    items.append({"nome": nome, "nota": "--", "status": "planejado"})
    salvar_lista(items)
    print(f"{nome} adicionado aos planejados!")
    print("=" * 100)


def mostrar_estatisticas():
    # total por status (opção 6) - modo legado
    items = carregar_items()
    stats = {"assistindo": 0, "completo": 0, "planejado": 0, "dropado": 0}
    for item in items:
        stats[item.get("status", "")] = stats.get(item.get("status", ""), 0) + 1
    print("=" * 80)
    for status, count in stats.items():
        print(f"- {status}: {count}")
    print("=" * 80)


def estatisticas_genericas(coluna=None):
    # Estatísticas genéricas para qualquer DataFrame.
    df = carregar_dataframe()
    if df.empty:
        return "📭 Nenhum item cadastrado ainda.\n"

    linhas = []

    # tenta usar uma coluna categórica para contagem
    # prioridade: status, categoria, tag, qualquer coluna 'object'
    cand = None
    for nome in ("status", "categoria", "tag"):
        if nome in df.columns:
            cand = nome
            break
    if cand is None:
        # primeira coluna do tipo object (texto)
        for col in df.columns:
            if df[col].dtype == object:
                cand = col
                break

    if cand:
        vc = df[cand].astype(str).value_counts()
        linhas.append(f"Contagem por '{cand}':")
        for valor, cnt in vc.items():
            linhas.append(f"    - {valor}: {cnt}")
        linhas.append("")

    # estatísticas numéricas básicas (se houver colunas numéricas)
    df_num = df.select_dtypes(include=["number"])
    if not df_num.empty and len(df_num.columns) > 0:
        desc = df_num.describe()
        if not desc.empty:
            linhas.append("Estatísticas numéricas:")
            linhas.append(str(desc))

    if not linhas:
        return "📭 Nenhuma estatística disponível para este conjunto.\n"

    return "\n".join(linhas) + "\n"


def ordenar_items(items):
    # Ordena: 1° por status (planejado->assistindo->completo->dropado), 2° por nota DESC.

    # Ordem prioritária dos status (0=maior prioridade)
    ordem_status = {"planejado": 1, "assistindo": 3, "completo": 0, "dropado": 2}

    def chave_ordenacao(item):
        status = item.get("status", "")
        # nota pode não existir ou ser não numérica; usamos 0 como fallback
        nota_val = item.get("nota", 0)
        try:
            nota_float = float(nota_val)
        except (TypeError, ValueError):
            nota_float = 0.0
        return (ordem_status.get(status, 99), -nota_float)

    return sorted(items, key=chave_ordenacao)


# GUI functions


def adicionar_gui(nome, nota, status):
    # versão GUI do add_item()
    items = carregar_items()
    items.append({"nome": nome, "nota": nota, "status": status})
    items = ordenar_items(items)
    salvar_lista(items)


def excluir_gui(idx):
    # exclui items por índice da GUI
    items = carregar_items()
    if 0 <= idx < len(items):
        removido = items.pop(idx)
        items = ordenar_items(items)
        salvar_lista(items)
        return removido["nome"]  # retorna nome pra mostrar
    return None


def add_dropado_gui(nome, nota):
    items = carregar_items()
    items.append({"nome": nome, "nota": nota, "status": "dropado"})
    items = ordenar_items(items)
    salvar_lista(items)


def add_planejado_gui(nome, nota):
    items = carregar_items()
    items.append({"nome": nome, "nota": nota, "status": "planejado"})
    salvar_lista(items)


def salvar_tabela_generica(texto_tabela: str):
    """Recebe texto de uma tabela genérica (como exibida na GUI) e salva no JSON.

    A primeira linha deve conter os nomes das colunas separados por " | ".
    As linhas seguintes devem conter valores nas mesmas posições."""
    linhas = [l for l in texto_tabela.splitlines() if l.strip()]
    if len(linhas) < 2:
        return  # nada para salvar

    # primeira linha: cabeçalho
    header = linhas[0]
    colunas = [h.strip() for h in header.split("|")]

    novos_registros = []
    for linha in linhas[1:]:
        partes = [p for p in linha.split("|")]
        # ignora linhas que não têm a mesma quantidade de colunas
        if len(partes) != len(colunas):
            continue
        registro = {}
        for chave, valor in zip(colunas, partes):
            registro[chave.strip()] = valor.strip()
        novos_registros.append(registro)

    if novos_registros:
        salvar_lista(novos_registros)
