# Consumo de Água no Brasil (2015–2024)

Projeto de análise e visualização de dados sobre padrões de consumo de água no Brasil, desenvolvido para a avaliação G1 da disciplina **Linguagem de Programação: Análise e Visualização de Dados com Python** (Tema 7).

**Aluno:** Marcus Vinicius Rodrigues da Silva
**Professor**: Alexandre Louzada
**Disciplina**: Linguagens de Programação

| Entrega | Link |
|---|---|
| Página do projeto (GitHub Pages) | https://marcusvrds07.github.io/Consumo-de-Agua-Analise/ |
| Dashboard (Streamlit Cloud) | https://consumoagua.streamlit.app |
| Repositório | https://github.com/marcusvrds07/Consumo-de-Agua-Analise/ |

## Problema

Crescimento populacional, mudanças climáticas e desperdício tornam o monitoramento da água cada vez mais importante. O projeto investiga quais estados e setores consomem mais, se há sazonalidade ou crescimento do consumo, se a estiagem afeta a demanda, quais regiões são mais vulneráveis à escassez e quais estados desperdiçam mais.

## Base de dados

`dados/simulacao_consumo_agua_brasil.csv`: base **simulada**, fornecida pelo professor, com 4.440 medições mensais (jan/2015 a dez/2024) de 20 estados, 5 regiões e 5 setores de consumo. As colunas incluem consumo, desperdício, reservatórios, chuva, temperatura, população, consumo per capita e nível de alerta.

Os estados têm quantidades diferentes de medições por mês: o RJ tem 4 e oito estados têm 1. Por isso, as comparações entre estados mostram o consumo total e o consumo médio por medição.

## Principais resultados

| Pergunta | Resposta |
|---|---|
| Quais estados consomem mais? | RJ, SP e MG no total. Na média por medição, BA, MA e SC. |
| Existe sazonalidade? | Não de forma relevante. A diferença entre o maior e o menor mês médio é de cerca de 9%. |
| Quais setores consomem mais? | Agrícola e Residencial, com cerca de 20,8% do total cada. |
| Há regiões mais vulneráveis? | Nordeste e Sudeste, puxados por CE e SP, pelo índice de vulnerabilidade. |
| Estiagem afeta o consumo? | Não. A correlação entre chuva e consumo é praticamente zero. |
| O consumo aumentou? | Não. Houve variação de +0,5% entre 2015 e 2024. |
| Quem desperdiça mais? | CE (32,3%), DF (31,8%) e AM (31,3%). A média nacional é de 30,2%. |

**Conclusão:** o consumo é estável e homogêneo. O problema central é o desperdício: cerca de 27,9 bilhões de litros perdidos, quase um terço de toda a água registrada. Como a base é simulada, as conclusões descrevem os dados fornecidos e não a realidade do país.

## KPIs

Consumo total de água, estado com maior consumo, setor que mais consome, consumo per capita médio, média de desperdício, nível médio dos reservatórios, volume perdido e percentual de medições em alerta Alto ou Crítico.

## Funcionalidades

**Dashboard:** filtros por ano, mês, região, estado, setor e nível de alerta; KPIs dinâmicos; linha temporal com média móvel; heatmap mensal; barras por estado e por setor; dispersão chuva × consumo; mapa interativo; tabela dinâmica com download; consultas SQL; upload de CSV; interpretações que se ajustam ao recorte; conclusão executiva.

**Funcionalidades intermediárias:** filtros múltiplos, KPIs dinâmicos, gráficos interativos, análise temporal, tratamento avançado de dados, integração entre tabelas, upload de arquivos, dashboard em seções, visualizações comparativas e análise geográfica.

**Funcionalidades avançadas:** persistência em banco (SQLAlchemy + SQLite), modelagem relacional (`estados` → `medicoes`), mapa interativo (Plotly), correlação estatística (Pandas/NumPy) e séries temporais com média móvel de 12 meses.

## Tecnologias

Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, SQLAlchemy, SQLite, Streamlit, GitHub e GitHub Pages.

## Estrutura

```
projeto-consumo-agua/
├── app.py                         dashboard Streamlit
├── requirements.txt
├── README.md
├── index.html                     página do projeto (GitHub Pages)
├── .streamlit/config.toml         tema visual do dashboard
├── dados/
│   ├── simulacao_consumo_agua_brasil.csv
│   └── brasil_estados.geojson     contornos dos estados para o mapa
├── notebooks/
│   └── analise_consumo_agua.ipynb
├── database/
│   └── consumo_agua.sqlite        tabelas estados e medicoes
└── imagens/                       gráficos gerados pelo notebook
```

## Como executar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

O dashboard lê os dados do banco `database/consumo_agua.sqlite`. Se o arquivo não existir, o banco é recriado automaticamente a partir do CSV.

Para refazer a análise, abra `notebooks/analise_consumo_agua.ipynb` no Jupyter ou no Google Colab. No Colab, envie o CSV para a sessão antes de executar. O notebook regenera os gráficos em `imagens/` e o banco em `database/`.
