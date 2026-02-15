# PeakVault

⚠️ **DUAL LICENSE**  
🎁 **Grátis (MIT)**: Uso pessoal, estudo, hobby  
💰 **Paga (R$10/mês)**: Empresas, revenda, produção  
📧 [y2kgif@gmail.com](mailto:y2kgif@gmail.com)

Sistema para análise de arquivos JSON.

![Tela inicial](https://raw.githubusercontent.com/ismaeldouglasdev/PeakVault/refs/heads/main/images/Screenshot%202026-02-14%20214557.png)

PeakVault é um projeto pessoal desenvolvido em Python para gerenciamento genérico de listas JSON planas. Ele oferece uma interface gráfica moderna e intuitiva, ideal para organizar coleções como animes, filmes ou séries com suporte a CRUD completo e visualizações de dados.

## Tecnologias Utilizadas
- **Python**: Linguagem principal.
- **CustomTkinter**: GUI em tons de azul escuro e design moderno.
- **Pandas**: Análise e processamento de dados em listas JSON.
- **Matplotlib**: Geração de gráficos baseados em agrupamentos.

## Funcionalidades Principais
- **CRUD Completo**: Adicionar itens (adaptando-se às keys do JSON carregado), editar dados manualmente, excluir por nome ou primeira coluna de texto (string), e salvar a lista.
- **Carregamento Genérico**: Abre qualquer lista JSON plana; campos de adição se ajustam automaticamente ao número de keys (ex.: nome, nota, status; ou mais keys se existirem em outras listas).
  
  ![JSON Carregado](https://raw.githubusercontent.com/ismaeldouglasdev/PeakVault/380f477067d856c7aba776ec55479df80bce5631/images/Screenshot%202026-02-14%20214613.png)
  
- **Agrupamento Dinâmico**: Agrupa dados por qualquer key disponível (ex.: por nome, nota ou status), adaptando-se às keys do JSON.

  ![JSON Agrupado](https://raw.githubusercontent.com/ismaeldouglasdev/PeakVault/380f477067d856c7aba776ec55479df80bce5631/images/Screenshot%202026-02-14%20214627.png)

- **Visualização de Gráficos**: Gera gráficos Matplotlib baseados no agrupamento selecionado (sempre agrupe primeiro, depois visualize).

![Gráficos](https://raw.githubusercontent.com/ismaeldouglasdev/PeakVault/refs/heads/main/images/Screenshot%202026-02-14%20220021.png)

- **Pesquisa**: Barra no topo esquerdo para buscar itens na lista carregada.

![Pesquisa](https://raw.githubusercontent.com/ismaeldouglasdev/PeakVault/refs/heads/main/images/Screenshot%202026-02-14%20220127.png)

- **Status e Erros**: Barra inferior mostra última ação realizada, com tratamento de erros em todas as funções.

![Status](https://raw.githubusercontent.com/ismaeldouglasdev/PeakVault/refs/heads/main/images/Screenshot%202026-02-14%20220207.png)

- **Geral**: Funciona para qualquer lista JSON plana, com interface intuitiva e feedback visual.

## Como Usar
1. Execute o script principal via CMD (ex.: `python interface.py`).
2. Na interface: carregue uma lista JSON via botão "Carregar lista".
3. Use botões à esquerda para CRUD, agrupar ou visualizar.
4. A interface adapta campos automaticamente às keys do arquivo.

## Instalação
```bash
pip install customtkinter pandas matplotlib
```
Clone o repositório e rode o script principal. Compatível com Windows 10 e 11.

## Limitações e Futuro
- Projetado para uso próprio, focado em listas planas (sem objetos aninhados).
- Expansível para mais formatos de dados ou temas.

Criado por @ismaeldouglasdev, como ferramenta de produtividade pessoal para listas, tracking de animes, e métricas em jogos. Contribuições via issues!
