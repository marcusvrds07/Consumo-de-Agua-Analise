"""
Dashboard: Consumo de Água no Brasil (2015–2024)
Projeto G1 · Análise e Visualização de Dados com Python · Tema 7
Aluno: Marcus Vinicius Rodrigues da Silva
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Consumo de Água no Brasil", page_icon="💧", layout="wide")

PASTA = Path(__file__).parent
CAMINHO_CSV = PASTA / "dados" / "simulacao_consumo_agua_brasil.csv"
CAMINHO_GEOJSON = PASTA / "dados" / "brasil_estados.geojson"
CAMINHO_BANCO = PASTA / "database" / "consumo_agua.sqlite"

AZUL = "#1F6F8B"
AZUL_CLARO = "#8EC3D1"
AZUL_ESCURO = "#12394A"
OCRE = "#B7791F"
PALETA = ["#12394A", "#1F6F8B", "#4A9BB5", "#8EC3D1", "#5E8C6A"]
CORES_ALERTA = {"Baixo": "#8EC3D1", "Médio": "#4A9BB5", "Alto": "#D9A24A", "Crítico": "#B7791F"}

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
ORDEM_ALERTA = ["Baixo", "Médio", "Alto", "Crítico"]
ORDEM_REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
ESTACOES = {12: "Verão", 1: "Verão", 2: "Verão", 3: "Outono", 4: "Outono", 5: "Outono",
            6: "Inverno", 7: "Inverno", 8: "Inverno", 9: "Primavera", 10: "Primavera", 11: "Primavera"}
NOMES_UF = {
    "AM": "Amazonas", "PA": "Pará", "RO": "Rondônia", "TO": "Tocantins",
    "BA": "Bahia", "PE": "Pernambuco", "CE": "Ceará", "MA": "Maranhão", "PB": "Paraíba",
    "DF": "Distrito Federal", "GO": "Goiás", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "SP": "São Paulo", "RJ": "Rio de Janeiro", "MG": "Minas Gerais", "ES": "Espírito Santo",
    "PR": "Paraná", "SC": "Santa Catarina", "RS": "Rio Grande do Sul",
}
COLUNAS_OBRIGATORIAS = [
    "ano", "mes", "data", "regiao", "uf", "setor_consumo", "consumo_milhoes_litros",
    "desperdicio_percentual", "reservatorios_percentual", "chuva_mm", "temperatura_media",
    "populacao", "consumo_per_capita", "nivel_alerta",
]

sns.set_theme(style="whitegrid")


def br(valor, casas=2):
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def sinal(valor, casas=1):
    return f"{'+' if valor >= 0 else '−'}{br(abs(valor), casas)}"


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for coluna in ["regiao", "uf", "setor_consumo", "nivel_alerta"]:
        df[coluna] = df[coluna].astype(str).str.strip()
    df["uf"] = df["uf"].str.upper()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.drop_duplicates().dropna(subset=["data", "consumo_milhoes_litros"])
    df = df[df["consumo_milhoes_litros"] > 0]
    df = df[df["desperdicio_percentual"].between(0, 100) & df["reservatorios_percentual"].between(0, 100)]

    df["nivel_alerta"] = pd.Categorical(df["nivel_alerta"], categories=ORDEM_ALERTA, ordered=True)
    df["ano_mes"] = df["data"].dt.to_period("M").astype(str)
    df["estacao"] = df["mes"].map(ESTACOES)
    df["volume_perdido"] = df["consumo_milhoes_litros"] * df["desperdicio_percentual"] / 100
    df["consumo_aproveitado"] = df["consumo_milhoes_litros"] - df["volume_perdido"]
    df["estiagem"] = np.where(df["chuva_mm"] < df["chuva_mm"].quantile(0.25), "Estiagem", "Chuva normal")
    df["alerta_grave"] = df["nivel_alerta"].isin(["Alto", "Crítico"])
    df["estado"] = df["uf"].map(NOMES_UF).fillna(df["uf"])
    return df.reset_index(drop=True)

DDL = [
    """CREATE TABLE IF NOT EXISTS estados (
        uf VARCHAR(2) PRIMARY KEY,
        nome VARCHAR(40) NOT NULL,
        regiao VARCHAR(20) NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS medicoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data VARCHAR(10), ano INTEGER, mes INTEGER,
        uf VARCHAR(2) REFERENCES estados(uf),
        setor_consumo VARCHAR(20),
        consumo_milhoes_litros FLOAT, desperdicio_percentual FLOAT,
        reservatorios_percentual FLOAT, chuva_mm FLOAT, temperatura_media FLOAT,
        populacao INTEGER, consumo_per_capita FLOAT, nivel_alerta VARCHAR(10)
    )""",
]

CONSULTA_BASE = """
SELECT m.ano, m.mes, m.data, e.regiao, m.uf, m.setor_consumo, m.consumo_milhoes_litros,
       m.desperdicio_percentual, m.reservatorios_percentual, m.chuva_mm, m.temperatura_media,
       m.populacao, m.consumo_per_capita, m.nivel_alerta
FROM medicoes m
JOIN estados e ON e.uf = m.uf
"""


def obter_engine():
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)
    return create_engine(f"sqlite:///{CAMINHO_BANCO.as_posix()}")


def criar_banco_a_partir_do_csv(engine):
    bruto = pd.read_csv(CAMINHO_CSV)
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS medicoes"))
        conexao.execute(text("DROP TABLE IF EXISTS estados"))
        for comando in DDL:
            conexao.execute(text(comando))
        estados = bruto[["uf", "regiao"]].drop_duplicates().assign(nome=lambda d: d["uf"].map(NOMES_UF))
        estados[["uf", "nome", "regiao"]].to_sql("estados", conexao, if_exists="append", index=False)
        bruto[[c for c in COLUNAS_OBRIGATORIAS if c != "regiao"]].to_sql(
            "medicoes", conexao, if_exists="append", index=False
        )


@st.cache_data(show_spinner="Carregando dados do banco SQLite...")
def carregar_do_banco() -> pd.DataFrame:
    engine = obter_engine()
    try:
        with engine.connect() as conexao:
            total = conexao.execute(text("SELECT COUNT(*) FROM medicoes")).scalar()
        if not total:
            raise ValueError("banco vazio")
    except Exception:
        criar_banco_a_partir_do_csv(engine)
    return preparar(pd.read_sql(CONSULTA_BASE, engine))


@st.cache_data
def carregar_geojson():
    with open(CAMINHO_GEOJSON, encoding="utf-8") as arquivo:
        return json.load(arquivo)


@st.cache_data
def executar_sql(consulta: str) -> pd.DataFrame:
    return pd.read_sql(consulta, obter_engine())


def normalizar(serie):
    amplitude = serie.max() - serie.min()
    return (serie - serie.min()) / amplitude if amplitude else serie * 0

st.sidebar.title("💧 Consumo de Água")
st.sidebar.caption("Brasil, 2015 a 2024")

with st.sidebar.expander("Fonte dos dados"):
    arquivo_enviado = st.file_uploader(
        "Enviar outro CSV com a mesma estrutura",
        type="csv",
        help="Sem envio, o dashboard usa a base do projeto gravada no banco SQLite.",
    )

fonte = "Banco SQLite do projeto"
dados = carregar_do_banco()
if arquivo_enviado is not None:
    try:
        enviado = pd.read_csv(arquivo_enviado)
        faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in enviado.columns]
        if faltando:
            st.sidebar.error(f"O CSV enviado não tem as colunas: {', '.join(faltando)}. Usando a base do projeto.")
        else:
            dados = preparar(enviado)
            fonte = f"Arquivo enviado: {arquivo_enviado.name}"
    except Exception as erro:
        st.sidebar.error(f"Não foi possível ler o CSV enviado ({erro}). Usando a base do projeto.")

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------
st.sidebar.header("Filtros")
st.sidebar.caption("Campos vazios consideram todas as opções.")

ano_min, ano_max = int(dados["ano"].min()), int(dados["ano"].max())
if ano_min < ano_max:
    faixa_anos = st.sidebar.slider("Ano", ano_min, ano_max, (ano_min, ano_max))
else:
    faixa_anos = (ano_min, ano_max)
    st.sidebar.caption(f"Ano: {ano_min}")
meses_sel = st.sidebar.multiselect("Mês", options=list(range(1, 13)), format_func=lambda m: MESES[m - 1],
                                   placeholder="Todos os meses")
regioes_disp = [r for r in ORDEM_REGIOES if r in dados["regiao"].unique()]
regioes_sel = st.sidebar.multiselect("Região", regioes_disp, placeholder="Todas as regiões")
ufs_disp = sorted(dados.loc[dados["regiao"].isin(regioes_sel or regioes_disp), "uf"].unique())
ufs_sel = st.sidebar.multiselect("Estado", ufs_disp, format_func=lambda u: f"{u} - {NOMES_UF.get(u, u)}",
                                 placeholder="Todos os estados")
setores_sel = st.sidebar.multiselect("Setor de consumo", sorted(dados["setor_consumo"].unique()),
                                     placeholder="Todos os setores")
alertas_sel = st.sidebar.multiselect("Nível de alerta", ORDEM_ALERTA, placeholder="Todos os níveis")

filtro = dados["ano"].between(*faixa_anos)
if meses_sel:
    filtro &= dados["mes"].isin(meses_sel)
if regioes_sel:
    filtro &= dados["regiao"].isin(regioes_sel)
if ufs_sel:
    filtro &= dados["uf"].isin(ufs_sel)
if setores_sel:
    filtro &= dados["setor_consumo"].isin(setores_sel)
if alertas_sel:
    filtro &= dados["nivel_alerta"].isin(alertas_sel)
df = dados[filtro]

st.sidebar.divider()
st.sidebar.caption(f"Fonte: {fonte}")
st.sidebar.caption(f"{br(len(df), 0)} de {br(len(dados), 0)} medições no recorte")

st.title("Consumo de Água no Brasil (2015–2024)")
st.markdown(
    "**Aluno:** Marcus Vinicius Rodrigues da Silva  \n"
    "**Professor:** Alexandre Louzada  \n"
    "**Disciplina:** Linguagens de Programação"
)
st.divider()

st.markdown(
    "O crescimento populacional, as mudanças climáticas e o desperdício tornam o monitoramento da água "
    "cada vez mais importante. Este dashboard investiga **onde e em quais setores** a água é consumida, "
    "**se há sazonalidade ou crescimento**, **como chuva e estiagem se relacionam com o consumo** e "
    "**quanto se perde** em cada estado, para apoiar decisões de gestão hídrica."
)
with st.expander("Sobre a base e as perguntas do projeto"):
    st.markdown(
        """
Base simulada com medições mensais por estado e setor: consumo, desperdício, reservatórios, chuva,
temperatura, população, consumo per capita e nível de alerta.

**Perguntas orientadoras:** quais estados consomem mais; se existe sazonalidade; quais setores consomem mais;
quais regiões são mais vulneráveis à escassez; se há relação entre estiagem e consumo; se o consumo aumentou;
e quais estados desperdiçam mais.

**Atenção à comparação entre estados:** os estados têm quantidades diferentes de medições por mês
(o RJ tem 4 e oito estados têm 1). Por isso o dashboard mostra o consumo **total** e o consumo **médio por medição**.
"""
    )

if df.empty:
    st.warning("Nenhuma medição atende aos filtros selecionados. Amplie o período ou remova algum filtro.")
    st.stop()

consumo_uf = df.groupby("uf")["consumo_milhoes_litros"].agg(["sum", "mean"])
consumo_setor = df.groupby("setor_consumo")["consumo_milhoes_litros"].sum()
media_geral_desp = dados["desperdicio_percentual"].mean()
media_geral_res = dados["reservatorios_percentual"].mean()
media_geral_pc = dados["consumo_per_capita"].mean()

linha1 = st.columns(4)
linha1[0].metric("Consumo total de água", f"{br(df['consumo_milhoes_litros'].sum() / 1000)} bi L",
                 help="Soma do consumo no recorte, em bilhões de litros.")
linha1[1].metric("Estado com maior consumo", consumo_uf["sum"].idxmax(),
                 f"média por medição: {consumo_uf['mean'].idxmax()}", delta_color="off", delta_arrow="off",
                 help="Ranking pelo consumo total. O valor abaixo mostra o líder pelo consumo médio por medição.")
linha1[2].metric("Setor que mais consome", consumo_setor.idxmax(),
                 f"{br(consumo_setor.max() / consumo_setor.sum() * 100, 1)}% do total", delta_color="off",
                 delta_arrow="off")
linha1[3].metric("Consumo per capita médio", f"{br(df['consumo_per_capita'].mean(), 1)} L/dia",
                 f"{sinal(df['consumo_per_capita'].mean() - media_geral_pc)} vs. base completa", delta_color="off")

linha2 = st.columns(4)
linha2[0].metric("Média de desperdício", f"{br(df['desperdicio_percentual'].mean(), 1)}%",
                 f"{sinal(df['desperdicio_percentual'].mean() - media_geral_desp, 2)} p.p. vs. base completa",
                 delta_color="off")
linha2[1].metric("Nível médio dos reservatórios", f"{br(df['reservatorios_percentual'].mean(), 1)}%",
                 f"{sinal(df['reservatorios_percentual'].mean() - media_geral_res, 2)} p.p. vs. base completa",
                 delta_color="off")
linha2[2].metric("Volume perdido", f"{br(df['volume_perdido'].sum() / 1000)} bi L",
                 help="Consumo × desperdício percentual: água que não chegou ao uso.")
linha2[3].metric("Medições em alerta Alto ou Crítico", f"{br(df['alerta_grave'].mean() * 100, 1)}%")

st.divider()

abas = st.tabs(["Evolução e sazonalidade", "Estados e regiões", "Setores",
                "Chuva e reservatórios", "Desperdício", "Tabela dinâmica", "Consultas SQL"])

with abas[0]:
    serie = df.groupby("data")["consumo_milhoes_litros"].sum().sort_index().to_frame("consumo")
    serie["media_movel"] = serie["consumo"].rolling(12, min_periods=12).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=serie.index, y=serie["consumo"], name="Consumo mensal",
                             line=dict(color=AZUL_CLARO, width=1.5)))
    if serie["media_movel"].notna().any():
        fig.add_trace(go.Scatter(x=serie.index, y=serie["media_movel"], name="Média móvel de 12 meses",
                                 line=dict(color=AZUL_ESCURO, width=3)))
    fig.update_layout(title="Linha temporal: evolução mensal do consumo", yaxis_title="Milhões de litros",
                      legend=dict(orientation="h", y=-0.15), height=420, margin=dict(t=60, b=20))
    st.plotly_chart(fig, width="stretch")

    anual = df.groupby("ano")["consumo_milhoes_litros"].sum().to_frame("consumo")
    anual["variacao_%"] = anual["consumo"].pct_change() * 100

    col_a, col_b = st.columns([1, 1.3])
    with col_a:
        fig = px.bar(anual.reset_index(), x="ano", y="consumo", color_discrete_sequence=[AZUL],
                     hover_data={"variacao_%": ":.1f"},
                     labels={"ano": "Ano", "consumo": "Milhões de litros", "variacao_%": "Variação (%)"},
                     title="Consumo anual")
        fig.update_yaxes(range=[anual["consumo"].min() * 0.85, anual["consumo"].max() * 1.05])
        fig.update_layout(height=430, margin=dict(t=60, b=20))
        st.plotly_chart(fig, width="stretch")
    with col_b:
        matriz = df.pivot_table(index="ano", columns="mes", values="consumo_milhoes_litros", aggfunc="sum")
        matriz.columns = [MESES[m - 1] for m in matriz.columns]
        fig_h, ax = plt.subplots(figsize=(9, 5))
        sns.heatmap(matriz, cmap="Blues", annot=True, fmt=".0f", linewidths=0.5,
                    cbar_kws={"label": "Milhões de litros"}, annot_kws={"size": 7}, ax=ax)
        ax.set_title("Heatmap mensal (sazonalidade)", fontweight="bold")
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(axis="y", rotation=0)
        st.pyplot(fig_h)
        plt.close(fig_h)

    perfil = df.groupby("mes")["consumo_milhoes_litros"].mean()
    if len(anual) >= 2:
        variacao_total = (anual["consumo"].iloc[-1] / anual["consumo"].iloc[0] - 1) * 100
        texto_tendencia = (f"Entre {anual.index[0]} e {anual.index[-1]}, o consumo do recorte variou "
                           f"**{sinal(variacao_total)}%**.")
    else:
        texto_tendencia = "Selecione mais de um ano para avaliar a tendência."
    texto_sazonal = ""
    if len(perfil) >= 2:
        amplitude = (perfil.max() / perfil.min() - 1) * 100
        texto_sazonal = (f"No perfil médio, **{MESES[perfil.idxmax() - 1]}** é o mês de maior consumo e "
                         f"**{MESES[perfil.idxmin() - 1]}** o de menor, uma diferença de {br(amplitude, 1)}%.")
    st.info(
        f"**Interpretação.** {texto_tendencia} {texto_sazonal} Na base completa, a média móvel de 12 meses "
        "fica praticamente estável e o heatmap não repete o mesmo padrão a cada ano: **não há tendência de "
        "aumento nem sazonalidade forte** no consumo."
    )

with abas[1]:
    METRICAS_UF = ["Consumo total (milhões de L)", "Consumo médio por medição (milhões de L)",
                   "Desperdício médio (%)", "Reservatórios médio (%)", "Consumo per capita médio (L/dia)",
                   "Índice de vulnerabilidade (0–100)"]
    escolha = st.radio("Métrica para comparar os estados", METRICAS_UF, horizontal=True)

    por_uf = df.groupby(["uf", "estado", "regiao"]).agg(
        total=("consumo_milhoes_litros", "sum"),
        media=("consumo_milhoes_litros", "mean"),
        desperdicio=("desperdicio_percentual", "mean"),
        reservatorios=("reservatorios_percentual", "mean"),
        per_capita=("consumo_per_capita", "mean"),
        chuva=("chuva_mm", "mean"),
        alerta=("alerta_grave", "mean"),
        medicoes=("consumo_milhoes_litros", "size"),
    ).reset_index()
    por_uf["vulnerabilidade"] = (
        (1 - normalizar(por_uf["reservatorios"])) + (1 - normalizar(por_uf["chuva"]))
        + normalizar(por_uf["desperdicio"]) + normalizar(por_uf["alerta"])
    ) / 4 * 100
    por_uf.columns = ["uf", "estado", "regiao"] + METRICAS_UF[:5] + ["chuva", "alerta", "Medições", METRICAS_UF[5]]

    escala = "YlOrBr" if escolha in ("Desperdício médio (%)", "Índice de vulnerabilidade (0–100)") else "Blues"
    if escolha == "Reservatórios médio (%)":
        escala = "Blues"

    col_mapa, col_barras = st.columns([1.1, 1])
    with col_mapa:
        fig = px.choropleth_map(por_uf, geojson=carregar_geojson(), locations="uf", featureidkey="id",
                                color=escolha, hover_name="estado", color_continuous_scale=escala,
                                hover_data={"uf": False, "regiao": True, "Medições": True, escolha: ":.2f"},
                                map_style="white-bg", center={"lat": -14.5, "lon": -52}, zoom=2.9, opacity=0.9)
        fig.update_layout(title=f"Mapa interativo: {escolha}", height=520, margin=dict(t=50, l=0, r=0, b=0),
                          coloraxis_colorbar=dict(title=""))
        st.plotly_chart(fig, width="stretch")
    with col_barras:
        ordenado = por_uf.sort_values(escolha)
        fig = px.bar(ordenado, x=escolha, y="uf", color="regiao", orientation="h", hover_name="estado",
                     category_orders={"regiao": ORDEM_REGIOES}, color_discrete_sequence=PALETA,
                     labels={"uf": "", "regiao": "Região"}, title=f"Barras por estado: {escolha}")
        if escolha in METRICAS_UF[1:5]:
            fig.update_xaxes(range=[ordenado[escolha].min() * 0.9, ordenado[escolha].max() * 1.02])
        fig.update_layout(height=520, margin=dict(t=50, b=20),
                          yaxis=dict(categoryorder="array", categoryarray=ordenado["uf"].tolist()))
        st.plotly_chart(fig, width="stretch")

    por_regiao = df.groupby("regiao").agg(
        consumo_total=("consumo_milhoes_litros", "sum"),
        consumo_medio=("consumo_milhoes_litros", "mean"),
    ).reindex([r for r in ORDEM_REGIOES if r in df["regiao"].unique()]).reset_index()
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        fig = px.bar(por_regiao, x="regiao", y="consumo_total", color_discrete_sequence=[AZUL],
                     labels={"regiao": "", "consumo_total": "Milhões de litros"}, title="Consumo total por região")
        fig.update_layout(height=380, margin=dict(t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with col_r2:
        fig = px.bar(por_regiao, x="regiao", y="consumo_medio", color_discrete_sequence=[AZUL_CLARO],
                     text=por_regiao["consumo_medio"].map(br),
                     labels={"regiao": "", "consumo_medio": "Milhões de litros por medição"},
                     title="Consumo médio por medição, por região")
        fig.update_layout(height=380, margin=dict(t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    lider_total = por_uf.loc[por_uf[METRICAS_UF[0]].idxmax()]
    lider_media = por_uf.loc[por_uf[METRICAS_UF[1]].idxmax()]
    lider_vuln = por_uf.loc[por_uf[METRICAS_UF[5]].idxmax()]
    texto_vuln = (f" O estado mais vulnerável à escassez pelo índice (reservatórios, chuva, desperdício e alertas) "
                  f"é **{lider_vuln['estado']}**." if len(por_uf) > 1 else "")
    st.info(
        f"**Interpretação.** No recorte, **{lider_total['estado']}** lidera o consumo total "
        f"({br(lider_total[METRICAS_UF[0]], 0)} milhões de L em {lider_total['Medições']} medições), "
        f"mas **{lider_media['estado']}** tem o maior consumo por medição "
        f"({br(lider_media[METRICAS_UF[1]])} milhões de L). "
        "Os totais refletem principalmente a quantidade de medições de cada estado; na média, as diferenças são pequenas."
        + texto_vuln
    )

with abas[2]:
    por_setor = df.groupby("setor_consumo").agg(
        consumo_total=("consumo_milhoes_litros", "sum"),
        consumo_medio=("consumo_milhoes_litros", "mean"),
    ).sort_values("consumo_total", ascending=False).reset_index()
    por_setor["participacao"] = por_setor["consumo_total"] / por_setor["consumo_total"].sum() * 100

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        fig = px.bar(por_setor, x="setor_consumo", y="consumo_total", color="setor_consumo",
                     color_discrete_sequence=PALETA, text=por_setor["participacao"].map(lambda v: f"{br(v, 1)}%"),
                     labels={"setor_consumo": "", "consumo_total": "Milhões de litros"},
                     title="Barras por setor: consumo total")
        fig.update_layout(showlegend=False, height=420, margin=dict(t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with col_s2:
        fig = px.box(df, x="setor_consumo", y="consumo_milhoes_litros", color="setor_consumo",
                     category_orders={"setor_consumo": por_setor["setor_consumo"].tolist()},
                     color_discrete_sequence=PALETA,
                     labels={"setor_consumo": "", "consumo_milhoes_litros": "Milhões de litros"},
                     title="Distribuição do consumo por medição")
        fig.update_layout(showlegend=False, height=420, margin=dict(t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    setor_regiao = df.groupby(["regiao", "setor_consumo"])["consumo_milhoes_litros"].sum().reset_index()
    fig = px.bar(setor_regiao, x="regiao", y="consumo_milhoes_litros", color="setor_consumo",
                 category_orders={"regiao": ORDEM_REGIOES}, color_discrete_sequence=PALETA,
                 labels={"regiao": "", "consumo_milhoes_litros": "Milhões de litros", "setor_consumo": "Setor"},
                 title="Composição do consumo por setor em cada região")
    fig.update_layout(height=400, margin=dict(t=50, b=20))
    st.plotly_chart(fig, width="stretch")

    topo, fim = por_setor.iloc[0], por_setor.iloc[-1]
    st.info(
        f"**Interpretação.** **{topo['setor_consumo']}** é o setor que mais consome no recorte "
        f"({br(topo['participacao'], 1)}% do total) e **{fim['setor_consumo']}** o que menos consome "
        f"({br(fim['participacao'], 1)}%). As distribuições por medição são muito parecidas entre setores, "
        "então as diferenças de total vêm mais do número de medições do que de um uso mais intenso."
    )

with abas[3]:
    r_chuva = round(df["chuva_mm"].corr(df["consumo_milhoes_litros"]), 3) + 0.0 if len(df) > 2 else 0.0
    col_c1, col_c2 = st.columns([1.4, 1])
    with col_c1:
        amostra = df.sample(min(len(df), 2500), random_state=1)
        fig = px.scatter(amostra, x="chuva_mm", y="consumo_milhoes_litros", color="estiagem",
                         color_discrete_map={"Estiagem": OCRE, "Chuva normal": AZUL}, opacity=0.5,
                         hover_data=["uf", "setor_consumo", "ano_mes"],
                         labels={"chuva_mm": "Chuva no mês (mm)", "consumo_milhoes_litros": "Consumo (milhões de L)",
                                 "estiagem": ""},
                         title=f"Dispersão chuva × consumo (r de Pearson = {br(r_chuva, 3)})")
        if len(df) > 2:
            coef = np.polyfit(df["chuva_mm"], df["consumo_milhoes_litros"], 1)
            xs = np.linspace(df["chuva_mm"].min(), df["chuva_mm"].max(), 50)
            fig.add_trace(go.Scatter(x=xs, y=np.polyval(coef, xs), name="Tendência linear",
                                     line=dict(color=AZUL_ESCURO, width=3)))
        fig.update_layout(height=450, margin=dict(t=50, b=20), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
    with col_c2:
        variaveis = {"consumo_milhoes_litros": "Consumo", "desperdicio_percentual": "Desperdício",
                     "reservatorios_percentual": "Reservatórios", "chuva_mm": "Chuva",
                     "temperatura_media": "Temperatura", "consumo_per_capita": "Per capita"}
        corr = df[list(variaveis)].corr().rename(index=variaveis, columns=variaveis)
        fig_c, ax = plt.subplots(figsize=(5.5, 4.6))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="BrBG", center=0, vmin=-1, vmax=1,
                    mask=np.triu(np.ones_like(corr, dtype=bool), k=1), cbar=False, annot_kws={"size": 8}, ax=ax)
        ax.set_title("Correlação de Pearson", fontweight="bold")
        st.pyplot(fig_c)
        plt.close(fig_c)

    estiagem = df.groupby("estiagem").agg(
        medicoes=("consumo_milhoes_litros", "size"),
        consumo_medio=("consumo_milhoes_litros", "mean"),
        per_capita=("consumo_per_capita", "mean"),
        reservatorios=("reservatorios_percentual", "mean"),
    )
    estiagem.columns = ["Medições", "Consumo médio (mi L)", "Per capita médio (L/dia)", "Reservatórios médio (%)"]
    estiagem.index.name = ""
    st.markdown("**Meses de estiagem × meses de chuva normal** (estiagem = chuva abaixo do 1º quartil da base)")
    st.dataframe(estiagem.style.format(precision=2, thousands=".", decimal=","), width="stretch")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        res_ano = df.groupby("ano")["reservatorios_percentual"].mean().reset_index()
        fig = px.line(res_ano, x="ano", y="reservatorios_percentual", markers=True, color_discrete_sequence=[AZUL],
                      labels={"ano": "Ano", "reservatorios_percentual": "Reservatórios (%)"},
                      title="Nível médio dos reservatórios por ano")
        fig.add_hline(y=50, line_dash="dash", line_color=OCRE, annotation_text="50% da capacidade",
                      annotation_position="bottom right")
        fig.update_yaxes(range=[30, 70])
        fig.update_layout(height=380, margin=dict(t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with col_r2:
        fig = px.box(df, x="nivel_alerta", y="reservatorios_percentual", color="nivel_alerta",
                     category_orders={"nivel_alerta": ORDEM_ALERTA}, color_discrete_map=CORES_ALERTA,
                     labels={"nivel_alerta": "Nível de alerta", "reservatorios_percentual": "Reservatórios (%)"},
                     title="Reservatórios por nível de alerta")
        fig.update_layout(showlegend=False, height=380, margin=dict(t=50, b=20))
        st.plotly_chart(fig, width="stretch")

    pct_critico = (df["reservatorios_percentual"] <= 30).mean() * 100
    st.info(
        f"**Interpretação.** A correlação entre chuva e consumo é **r = {br(r_chuva, 3)}**, praticamente nula: "
        "o consumo nos meses de estiagem é quase igual ao dos meses com chuva normal. "
        f"No recorte, {br(pct_critico, 1)}% das medições têm reservatórios em 30% ou menos. "
        "Os reservatórios têm a mesma distribuição em todos os níveis de alerta, o que indica que o "
        "nível de alerta da base não acompanha a situação hídrica medida. Por ser uma base simulada, "
        "essas ausências de relação não devem ser generalizadas para a realidade."
    )

with abas[4]:
    desp_uf = df.groupby(["uf", "estado"]).agg(
        desperdicio=("desperdicio_percentual", "mean"), perdido=("volume_perdido", "sum")
    ).reset_index().sort_values("desperdicio")
    media_rec = df["desperdicio_percentual"].mean()

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        cores = [OCRE if v > media_rec else AZUL_CLARO for v in desp_uf["desperdicio"]]
        fig = go.Figure(go.Bar(x=desp_uf["desperdicio"], y=desp_uf["uf"], orientation="h", marker_color=cores,
                               hovertext=desp_uf["estado"], name="Desperdício"))
        fig.add_vline(x=media_rec, line_dash="dash", line_color=AZUL_ESCURO,
                      annotation_text=f"Média: {br(media_rec, 1)}%")
        fig.update_xaxes(range=[desp_uf["desperdicio"].min() * 0.9, desp_uf["desperdicio"].max() * 1.03],
                         title="Desperdício médio (%)")
        fig.update_layout(title="Desperdício médio por estado (acima da média em ocre)", height=540,
                          margin=dict(t=50, b=20))
        st.plotly_chart(fig, width="stretch")
    with col_d2:
        desp_ano = df.groupby("ano")["desperdicio_percentual"].mean().reset_index()
        fig = px.line(desp_ano, x="ano", y="desperdicio_percentual", markers=True, color_discrete_sequence=[OCRE],
                      labels={"ano": "Ano", "desperdicio_percentual": "Desperdício médio (%)"},
                      title="Evolução do desperdício médio")
        fig.update_layout(height=260, margin=dict(t=50, b=10))
        st.plotly_chart(fig, width="stretch")

        perdas = df.groupby("setor_consumo")[["consumo_aproveitado", "volume_perdido"]].sum().reset_index()
        perdas = perdas.melt(id_vars="setor_consumo", var_name="tipo", value_name="volume")
        perdas["tipo"] = perdas["tipo"].map({"consumo_aproveitado": "Aproveitado", "volume_perdido": "Perdido"})
        fig = px.bar(perdas, x="setor_consumo", y="volume", color="tipo",
                     color_discrete_map={"Aproveitado": AZUL, "Perdido": OCRE},
                     labels={"setor_consumo": "", "volume": "Milhões de litros", "tipo": ""},
                     title="Água aproveitada × perdida por setor")
        fig.update_layout(height=300, margin=dict(t=50, b=10), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")

    top3 = desp_uf.sort_values("desperdicio", ascending=False).head(3)
    um_pp = df["consumo_milhoes_litros"].sum() / 100
    st.info(
        "**Interpretação.** Os maiores índices de desperdício no recorte são de "
        + ", ".join(f"**{r.uf}** ({br(r.desperdicio, 1)}%)" for r in top3.itertuples())
        + f". O desperdício médio é de {br(media_rec, 1)}% e aparece em patamar parecido em todos os estados "
        "e setores, o que aponta para um problema estrutural de perdas. "
        f"Cada ponto percentual a menos de desperdício equivale a cerca de {br(um_pp, 0)} milhões de litros no recorte."
    )

with abas[5]:
    dimensoes = {"Ano": "ano", "Mês": "mes", "Estação": "estacao", "Região": "regiao", "Estado": "uf",
                 "Setor": "setor_consumo", "Nível de alerta": "nivel_alerta", "Estiagem": "estiagem"}
    valores = {"Consumo (milhões de L)": "consumo_milhoes_litros", "Volume perdido (milhões de L)": "volume_perdido",
               "Desperdício (%)": "desperdicio_percentual", "Reservatórios (%)": "reservatorios_percentual",
               "Chuva (mm)": "chuva_mm", "Temperatura (°C)": "temperatura_media",
               "Consumo per capita (L/dia)": "consumo_per_capita"}
    agregacoes = {"Soma": "sum", "Média": "mean", "Máximo": "max", "Mínimo": "min", "Contagem": "count"}

    c1, c2, c3, c4 = st.columns(4)
    linhas_sel = c1.selectbox("Linhas", list(dimensoes), index=4)
    opcoes_colunas = ["(nenhuma)"] + [d for d in dimensoes if d != linhas_sel]
    colunas_sel = c2.selectbox("Colunas", opcoes_colunas,
                               index=opcoes_colunas.index("Setor") if "Setor" in opcoes_colunas else 0)
    valor_sel = c3.selectbox("Valor", list(valores))
    agg_sel = c4.selectbox("Agregação", list(agregacoes), index=0)

    tabela = pd.pivot_table(
        df, index=dimensoes[linhas_sel],
        columns=None if colunas_sel == "(nenhuma)" else dimensoes[colunas_sel],
        values=valores[valor_sel], aggfunc=agregacoes[agg_sel], observed=True,
    )
    if isinstance(tabela, pd.Series):
        tabela = tabela.to_frame(valor_sel)
    if colunas_sel == "(nenhuma)":
        tabela.columns = [valor_sel]
    if dimensoes[linhas_sel] == "mes":
        tabela.index = [MESES[m - 1] for m in tabela.index]
    if colunas_sel != "(nenhuma)" and dimensoes[colunas_sel] == "mes":
        tabela.columns = [MESES[m - 1] for m in tabela.columns]
    tabela.index.name = linhas_sel
    tabela.columns = [str(c) for c in tabela.columns]

    st.dataframe(tabela.style.format(precision=2, thousands=".", decimal=",").background_gradient(cmap="Blues"),
                 width="stretch", height=min(36 * (len(tabela) + 1) + 4, 620))
    st.download_button("Baixar tabela em CSV", tabela.to_csv(sep=";", decimal=",").encode("utf-8-sig"),
                       file_name="tabela_dinamica_consumo_agua.csv", mime="text/csv")

    with st.expander("Ver as medições filtradas"):
        st.dataframe(df[COLUNAS_OBRIGATORIAS + ["volume_perdido", "estiagem"]], width="stretch", height=400)

with abas[6]:
    st.markdown(
        "Os dados ficam persistidos em **SQLite** (`database/consumo_agua.sqlite`) com modelo relacional: "
        "a tabela `estados` (UF, nome, região) se liga à tabela `medicoes` pela chave estrangeira `uf`. "
        "As consultas abaixo rodam com **SQLAlchemy** sobre a base completa do banco."
    )
    consultas = {
        "Consumo e desperdício por região (JOIN estados × medicoes)": """
SELECT e.regiao,
       ROUND(SUM(m.consumo_milhoes_litros), 2)   AS consumo_total,
       ROUND(AVG(m.consumo_milhoes_litros), 2)   AS consumo_medio,
       ROUND(AVG(m.desperdicio_percentual), 2)   AS desperdicio_medio,
       ROUND(AVG(m.reservatorios_percentual), 2) AS reservatorios_medio
FROM medicoes m
JOIN estados e ON e.uf = m.uf
GROUP BY e.regiao
ORDER BY consumo_total DESC""",
        "Estados com mais medições de reservatório crítico (até 30%)": """
SELECT e.nome AS estado,
       COUNT(*) AS medicoes_criticas,
       ROUND(AVG(m.reservatorios_percentual), 2) AS reservatorio_medio
FROM medicoes m
JOIN estados e ON e.uf = m.uf
WHERE m.reservatorios_percentual <= 30
GROUP BY e.nome
ORDER BY medicoes_criticas DESC""",
        "Volume perdido por ano": """
SELECT ano,
       ROUND(SUM(consumo_milhoes_litros * desperdicio_percentual / 100), 2) AS volume_perdido,
       ROUND(AVG(desperdicio_percentual), 2) AS desperdicio_medio
FROM medicoes
GROUP BY ano
ORDER BY ano""",
        "Setor que mais consome em cada região": """
WITH totais AS (
    SELECT e.regiao, m.setor_consumo, SUM(m.consumo_milhoes_litros) AS consumo
    FROM medicoes m JOIN estados e ON e.uf = m.uf
    GROUP BY e.regiao, m.setor_consumo
)
SELECT regiao, setor_consumo, ROUND(consumo, 2) AS consumo
FROM totais t
WHERE consumo = (SELECT MAX(consumo) FROM totais WHERE regiao = t.regiao)
ORDER BY consumo DESC""",
    }
    escolha_sql = st.selectbox("Consulta", list(consultas))
    st.code(consultas[escolha_sql].strip(), language="sql")
    st.dataframe(executar_sql(consultas[escolha_sql]), width="stretch")
st.divider()
st.header("Conclusão executiva")
st.markdown(
    f"""
- **Consumo estável e sem sazonalidade forte.** Entre 2015 e 2024 o consumo praticamente não mudou (+0,5%),
  e o padrão mensal varia de um ano para outro. Não há sinal de crescimento da demanda na base.
- **Volume total reflete cobertura, não intensidade.** RJ, SP e MG lideram o consumo total porque têm mais
  medições por mês. No consumo médio por medição, BA, MA e SC ficam à frente, com diferenças pequenas.
- **Setores equilibrados.** Agrícola e Residencial dividem a liderança, com cerca de 21% do consumo cada.
- **Chuva e estiagem não explicam o consumo.** As correlações entre as variáveis da base são praticamente nulas.
- **O desperdício é o problema central.** Cerca de 30% da água registrada se perde, em todos os estados e
  setores, com leve alta no período. CE, DF e AM têm os maiores índices.
- **Atenção hídrica.** Os reservatórios operam em média pouco acima de 50% da capacidade, e cerca de um quarto
  das medições está em 30% ou menos. CE, SP, PR, MS e PE lideram o índice de vulnerabilidade.

**Recomendação:** priorizar programas de redução de perdas, que têm o maior potencial de ganho, monitorar os
estados mais vulneráveis e revisar o critério de nível de alerta, que hoje não acompanha os reservatórios.

**No recorte atual:** {br(df['consumo_milhoes_litros'].sum(), 0)} milhões de litros consumidos,
{br(df['volume_perdido'].sum(), 0)} milhões de litros perdidos ({br(df['desperdicio_percentual'].mean(), 1)}%
de desperdício médio) e reservatórios em {br(df['reservatorios_percentual'].mean(), 1)}% da capacidade, em média.
"""
)
st.caption("Base simulada fornecida para fins educacionais: as conclusões descrevem os dados, não a realidade "
           "hídrica do Brasil. Projeto G1, Análise e Visualização de Dados com Python. "
           "Marcus Vinicius Rodrigues da Silva.")
