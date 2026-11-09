import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Afazeres Domésticos e Cuidados", 
    layout="wide", 
    page_icon='https://i.scdn.co/image/ab67616d0000b27332fdd9cfd9c3b89028ff58e6'
)

@st.cache_data
def carregar_dados(caminho_arquivo):
    xls = pd.ExcelFile(caminho_arquivo, engine="calamine")
    abas_anos = [sheet for sheet in xls.sheet_names if "(CV)" not in sheet]
    dados_totais = []

    for ano in abas_anos:
        df_raw = pd.read_excel(xls, sheet_name=ano, header=None, engine="calamine")
        
        try:
            start_idx = df_raw[df_raw[0] == "Brasil"].index[0]
            end_idx = df_raw[df_raw[0].astype(str).str.startswith("Fonte", na=False)].index[0]
        except IndexError:
            continue 

        df_dados = df_raw.iloc[start_idx:end_idx].copy()
        
        colunas = {
            0: "Localidade", 
            1: "Total_Geral", 2: "Homem_Geral", 3: "Mulher_Geral",
            4: "Total_14 a 29", 5: "Homem_14 a 29", 6: "Mulher_14 a 29",
            7: "Total_30 a 49", 8: "Homem_30 a 49", 9: "Mulher_30 a 49",
            10: "Total_50 a 59", 11: "Homem_50 a 59", 12: "Mulher_50 a 59",
            13: "Total_60 ou mais", 14: "Homem_60 ou mais", 15: "Mulher_60 ou mais"
        }
        
        df_dados = df_dados[list(colunas.keys())].rename(columns=colunas)
        df_dados["Ano"] = str(ano)
        
        df_melt = df_dados.melt(id_vars=["Localidade", "Ano"], var_name="Variavel", value_name="Horas")
        df_melt["Sexo"] = df_melt["Variavel"].apply(lambda x: x.split("_")[0])
        df_melt["Faixa Etária"] = df_melt["Variavel"].apply(lambda x: x.split("_")[1].replace("Geral", "Todas as idades"))
        df_melt["Horas"] = pd.to_numeric(df_melt["Horas"], errors="coerce")
        
        dados_totais.append(df_melt)

    df_completo = pd.concat(dados_totais, ignore_index=True)
    df_completo = df_completo.dropna(subset=["Localidade", "Horas"])
    df_completo["Localidade"] = df_completo["Localidade"].astype(str).str.strip()
    
    return df_completo[df_completo["Localidade"] != ""]

caminho_arquivo = "Tabela 1.1.2.xls"

try:
    df = carregar_dados(caminho_arquivo)

    st.sidebar.header("🔍 Filtros de Análise")

    anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
    ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", anos_disponiveis)

    faixas_disponiveis = df["Faixa Etária"].unique().tolist()
    faixas_disponiveis = ["Todas as idades"] + [f for f in faixas_disponiveis if f != "Todas as idades"]
    faixa_selecionada = st.sidebar.selectbox("Faixa Etária:", faixas_disponiveis)

    estados_foco = ["Bahia", "Pernambuco", "Amazonas", "Ceará"]
    localidades_disponiveis = df["Localidade"].unique().tolist()
    padroes = ["Brasil"] + [e for e in estados_foco if e in localidades_disponiveis]

    localidades_selecionadas = st.sidebar.multiselect(
        "Selecione Estados/Regiões:",
        options=localidades_disponiveis,
        default=padroes
    )

    st.title("📊Horas Dedicadas a Cuidados e Afazeres Domésticos")
    st.markdown("""
    Análise das horas semanais dedicadas a cuidados de pessoas e/ou afazeres domésticos.
    
    """)
    
   
    st.markdown("---")

    df_filtrado = df[
        (df["Ano"] == ano_selecionado) & 
        (df["Localidade"].isin(localidades_selecionadas)) &
        (df["Faixa Etária"] == faixa_selecionada)
    ]

    if not df_filtrado.empty:
        st.subheader(f" Indicadores-Chave ({ano_selecionado})")
        
        df_pivot = df_filtrado.pivot_table(index="Localidade", columns="Sexo", values="Horas", aggfunc="mean").reset_index()
        
        if "Mulher" in df_pivot.columns and "Homem" in df_pivot.columns:
            df_pivot["Discrepância"] = df_pivot["Mulher"] - df_pivot["Homem"]
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Média Mulheres (h/sem)", f"{df_pivot['Mulher'].mean():.1f}h")
            col2.metric("Média Homens (h/sem)", f"{df_pivot['Homem'].mean():.1f}h")
            col3.metric("Sobrecarga Feminina", f"+{df_pivot['Discrepância'].mean():.1f}h")
            col4.metric("Cenário Analisado", f"{len(df_pivot)} Localidades")
            
            st.markdown("---")

            st.subheader("Comparativo de Horas Semanais")
            
            col_esq, col_dir = st.columns(2)

            with col_esq:
                fig_bar = px.bar(
                    df_pivot,
                    x="Localidade",
                    y=["Homem", "Mulher"],
                    barmode="group",
                    title=f"Horas por Gênero - {ano_selecionado} ({faixa_selecionada})",
                    labels={"value": "Horas Semanais", "variable": "Gênero", "Localidade": ""},
                    color_discrete_sequence=["#1f77b4", "#e377c2"]
                )
                fig_bar.update_layout(legend_title_text='Gênero')
                fig_bar.update_traces(
                    hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:.1f} h/sem<extra></extra>"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_dir:
                df_pivot_sorted = df_pivot.sort_values(by="Discrepância", ascending=True)
                fig_gap = px.bar(
                    df_pivot_sorted,
                    x="Discrepância",
                    y="Localidade",
                    orientation="h",
                    title="Discrepância de Horas (Mulheres - Homens)",
                    labels={"Discrepância": "Horas a mais para Mulheres", "Localidade": ""},
                    color="Discrepância",
                    color_continuous_scale="Reds"
                )
                fig_gap.update_layout(coloraxis_showscale=False)
                fig_gap.update_traces(
                    hovertemplate="<b>%{y}</b><br>Horas a mais: %{x:.1f} h/sem<extra></extra>"
                )
                st.plotly_chart(fig_gap, use_container_width=True)

            st.markdown("---")
            st.subheader("📈 Evolução Histórica")
            
            df_evolucao = df[
                (df["Localidade"].isin(localidades_selecionadas)) & 
                (df["Faixa Etária"] == faixa_selecionada)
            ]
            
            fig_line = px.line(
                df_evolucao,
                x="Ano",
                y="Horas",
                color="Localidade",
                line_dash="Sexo",
                markers=True,
                title=f"Evolução das Horas por Gênero ({faixa_selecionada})",
                labels={"Horas": "Horas/Semana", "Ano": "Ano", "Sexo": "Gênero"}
            )
            fig_line.update_traces(
                hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:.1f} h/sem<extra></extra>"
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
            with st.expander("📋 Ver Tabela de Dados Detalhada"):
                st.dataframe(df_filtrado[["Localidade", "Sexo", "Horas"]].reset_index(drop=True), use_container_width=True)

    else:
        st.warning("Nenhuma localidade selecionada ou dados não encontrados nos filtros da barra lateral.")

except Exception as e:
    st.error(f"Erro ao carregar o arquivo: {e}")
    st.info("Certifique-se de que o arquivo 'Tabela 1.1.2.xls' está no mesmo diretório do script.")