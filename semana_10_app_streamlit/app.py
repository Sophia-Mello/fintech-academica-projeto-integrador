"""Fintech Acadêmica — aplicação final do projeto integrador.

Executar a partir da raiz do repositório:
    streamlit run semana_10_app_streamlit/app.py
"""
from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from fintech_core.analise import indicadores, evolucao, por_categoria, moeda
from fintech_core.dados import (
    BASE_ORIGINAL, preparar_operacional, conectar, despesas_completas,
    cadastro, staging, registrar_despesa, hash_original,
)
from fintech_core.ibge import atualizar_municipios
from fintech_core.modelo import prever, carregar_modelo
from fintech_core.qualidade import auditar
from fintech_core.validacao import CATEGORIAS

st.set_page_config(page_title='Fintech Acadêmica', page_icon='💠', layout='wide')
COR_AZUL='#223B60'; COR_VERDE='#079F95'; COR_PESSEGO='#EC856C'
PALETA=[COR_VERDE, '#7097CB', '#9188BA', COR_PESSEGO, '#D0A34A']
st.markdown('''<style>
    .stApp { background-color: #F7F9FC; }
    [data-testid="stSidebar"] { background-color: #EAF0F7; }
    [data-testid="stMetric"] { background:white; border:1px solid #DEE6F0;
       padding:14px; border-radius:13px; }
    h1,h2,h3 { color: #223B60; }
</style>''', unsafe_allow_html=True)


def cabecalho(titulo, texto):
    st.title(titulo)
    st.caption(texto)


try:
    preparar_operacional()
    base=despesas_completas()
    alunos=cadastro('estudantes')
    cidades=cadastro('municipios')
except Exception as erro:
    st.error('Não consegui abrir o banco. Verifique se fintech_integrada.db está junto de app.py.')
    st.exception(erro)
    st.stop()

with st.sidebar:
    st.markdown('## 💠 Fintech Acadêmica')
    st.caption('Projeto Integrador — Semanas 1 a 10')
    st.divider()
    pagina=st.radio('Páginas',[
        'Visão geral','Registrar despesa','Previsão experimental',
        'Qualidade dos dados','Municípios e IBGE',
    ])
    st.divider()
    st.caption('Dados de setembro/2026; demonstração acadêmica.')
    st.caption('Sem receitas, login ou armazenamento remoto.')

if pagina=='Visão geral':
    cabecalho('Painel financeiro','Gastos estudantis a partir do SQLite fornecido na Semana 5.')
    with st.expander('Filtrar dados'):
        c1,c2,c3=st.columns(3)
        ufs=c1.multiselect('UF',sorted(base.uf.dropna().unique()),default=sorted(base.uf.dropna().unique()))
        categorias=c2.multiselect('Categoria',sorted(base.categoria.dropna().unique()),default=sorted(base.categoria.dropna().unique()))
        estudantes=c3.multiselect('Estudante',sorted(base.estudante.dropna().unique()),default=sorted(base.estudante.dropna().unique()))
    df=base[base.uf.isin(ufs)&base.categoria.isin(categorias)&base.estudante.isin(estudantes)].copy()
    if df.empty:
        st.warning('Nenhuma despesa corresponde aos filtros.')
        st.stop()
    k=indicadores(df)
    a,b,c,d=st.columns(4)
    a.metric('Despesas',moeda(k['total']))
    b.metric('Ticket médio',moeda(k['ticket']))
    c.metric('Registros',str(k['quantidade']))
    d.metric('Estudantes',str(k['estudantes']))
    st.markdown('### Evolução dos lançamentos')
    serie,freq=evolucao(df)
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=serie.data,y=serie.gastos,name='Total observado',mode='lines+markers',line_color='#7097CB'))
    fig.add_trace(go.Scatter(x=serie.data,y=serie.media_movel,name='Média móvel (3 períodos)',line_color=COR_VERDE))
    fig.update_layout(height=330,xaxis_title='Dia' if freq=='diaria' else 'Mês',yaxis_title='R$',legend_orientation='h',
                      paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig,use_container_width=True)
    if freq=='diaria':
        st.caption('Há dados de apenas um mês. A média móvel foi calculada sobre 3 dias, não 3 meses.')
    st.markdown('### Gastos por categoria')
    bar=por_categoria(df)
    a,b=st.columns([1.25,1])
    with a:
        f=px.bar(bar.sort_values('valor'),x='valor',y='categoria',orientation='h',text='valor',
                 color='categoria',color_discrete_sequence=PALETA)
        f.update_traces(texttemplate='R$ %{x:,.2f}',textposition='outside')
        f.update_layout(height=350,showlegend=False,xaxis_title='R$',yaxis_title='',margin=dict(r=120),
                        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(f,use_container_width=True)
    with b:
        top3=bar.head(3)
        f=px.pie(top3,values='valor',names='categoria',hole=.62,color_discrete_sequence=PALETA)
        f.update_layout(height=350,legend_orientation='h',paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(f,use_container_width=True)
        st.caption('A rosca considera apenas as três maiores categorias.')
    st.markdown('### Distribuição por estudante')
    retirar=st.checkbox('Excluir outliers apenas do boxplot',value=False)
    box=df.loc[~df.is_outlier] if retirar else df
    if not box.empty:
        f=px.box(box,x='estudante',y='valor',color='estudante',points='all',
                 hover_data=['categoria','uf','data'],color_discrete_sequence=PALETA)
        f.update_layout(height=350,showlegend=False,xaxis_title='',yaxis_title='R$',
                        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(f,use_container_width=True)
    if k['outliers']:
        st.warning(f"{k['outliers']} lançamento(s) fora do padrão IQR: {k['participacao_outlier']:.1f}% do valor filtrado.")
    st.dataframe(df[['data','estudante','categoria','municipio','uf','valor','is_outlier','origem_registro']],
                 hide_index=True,use_container_width=True)
    st.download_button('Baixar CSV filtrado',data=df.to_csv(index=False,sep=';').encode('utf-8-sig'),
                       file_name='despesas_filtradas.csv',mime='text/csv')

elif pagina=='Registrar despesa':
    cabecalho('Registrar despesa','Novos lançamentos ficam na cópia operacional. O SQLite recebido permanece preservado.')
    mapa_alunos={int(r.id):f'{r.nome} — {r.matricula}' for r in alunos.itertuples(index=False)}
    mapa_cidades={int(r.id):f'{r.nome}/{r.uf_sigla}' for r in cidades.itertuples(index=False)}
    if not mapa_alunos or not mapa_cidades:
        st.error('Sem estudantes ou municípios cadastrados.')
        st.stop()
    with st.form('form_nova_despesa'):
        a,b=st.columns(2)
        e=a.selectbox('Estudante',list(mapa_alunos),format_func=mapa_alunos.get)
        cat=a.selectbox('Categoria',list(CATEGORIAS))
        valor=a.number_input('Valor (R$)',min_value=.01,value=35.90,step=1.,format='%.2f')
        m=b.selectbox('Município',list(mapa_cidades),format_func=mapa_cidades.get)
        dia=b.date_input('Data',value=date.today(),max_value=date.today())
        enviou=st.form_submit_button('Salvar despesa',type='primary')
    if enviou:
        try:
            identificador=registrar_despesa(e,m,float(valor),dia,cat)
            st.success(f'Despesa #{identificador} registrada na cópia operacional.')
        except Exception as exc:
            st.error(f'Falha ao registrar: {exc}')
    st.info('No Streamlit Community Cloud, novos registros podem se perder após reinicialização do aplicativo.')

elif pagina=='Previsão experimental':
    cabecalho('Previsão da próxima despesa','Regressão linear com categoria e histórico anterior do estudante.')
    try:
        _,meta=carregar_modelo()
    except Exception as exc:
        st.error(f'Não foi possível carregar o modelo: {exc}')
        st.stop()
    a,b,c=st.columns(3)
    a.metric('MAE da regressão',moeda(meta['mae_modelo']))
    b.metric('MAE da média (baseline)',moeda(meta['mae_baseline']))
    c.metric('Treino / teste',f"{meta['n_treino']} / {meta['n_teste']}")
    st.warning('O modelo teve erro maior que o baseline e não serve para tomar decisões financeiras.')
    mapa={int(r.id):f'{r.nome} — {r.matricula}' for r in alunos.itertuples(index=False)}
    with st.form('previsao'):
        e=st.selectbox('Estudante',list(mapa),format_func=mapa.get)
        cat=st.selectbox('Categoria da próxima despesa',list(CATEGORIAS))
        enviar=st.form_submit_button('Simular',type='primary')
    if enviar:
        try:
            previsto,_=prever(base,e,CATEGORIAS[cat])
        except Exception as exc:
            st.error(f'Não foi possível prever: {exc}')
        else:
            if previsto<0:
                st.error(f'Previsão negativa ({moeda(previsto)}), sem interpretação como despesa válida.')
            else:
                st.metric('Estimativa ilustrativa',moeda(previsto))
            st.caption(f"O estudante possui {int(base.estudante_id.eq(e).sum())} despesas registradas. O modelo não se atualiza automaticamente.")
    st.markdown('**Variáveis:** categoria (One-Hot Encoding), média de gastos anteriores, número de gastos anteriores e indicador de histórico.')

elif pagina=='Qualidade dos dados':
    cabecalho('Qualidade da base','Inspeção do estado atual da tabela despesas_clean.')
    rel=auditar(base)
    a,b,c,d=st.columns(4)
    a.metric('Despesas tratadas',rel['registros'])
    b.metric('Células nulas',rel['nulos'])
    c.metric('IDs repetidos',rel['duplicados_id'])
    d.metric('Outliers',rel['outliers'])
    st.write(f"Faixa IQR calculada: {moeda(rel['limite_inferior'])} a {moeda(rel['limite_superior'])}.")
    st.write(f"Categorias não informadas: {rel['categoria_nao_informada']}. Divergências entre a flag e o IQR atual: {rel['divergencias']}.")
    st.warning('O banco recebido contém 3 despesas na tabela de origem e 7 tratadas. Não foi enviado o staging bruto; não é possível inferir quantos erros ou duplicatas foram corrigidos historicamente.')
    st.dataframe(base[['id','data','estudante','categoria','valor','is_outlier','origem_registro']],hide_index=True,use_container_width=True)
    eventos=staging()
    st.subheader('Lançamentos incluídos depois pelo aplicativo')
    if eventos.empty:
        st.info('Ainda não há lançamentos novos na cópia operacional.')
    else:
        st.dataframe(eventos,hide_index=True,use_container_width=True)
    with st.expander('Arquivo original e integridade'):
        st.text(f'Banco original: {BASE_ORIGINAL.name}')
        st.code(f'SHA-256: {hash_original()}')
        st.caption('O app usa uma cópia separada para gravar; o hash acima se refere ao arquivo recebido.')

elif pagina=='Municípios e IBGE':
    cabecalho('Municípios e IBGE','Consulta de localidades e gastos por UF.')
    a,b,c=st.columns(3)
    a.metric('Municípios',len(cidades))
    b.metric('Estados',cidades.uf_sigla.nunique())
    c.metric('Estudantes',len(alunos))
    por_uf=base.groupby('uf',as_index=False)['valor'].sum()
    f=px.bar(por_uf,x='uf',y='valor',color='uf',text='valor',color_discrete_sequence=PALETA)
    f.update_layout(height=330,showlegend=False,xaxis_title='UF',yaxis_title='Total de despesas (R$)')
    st.plotly_chart(f,use_container_width=True)
    st.dataframe(cidades,hide_index=True,use_container_width=True)
    st.info('A importação depende da API do IBGE e altera somente a cópia operacional.')
    if st.button('Atualizar municípios de MG, RJ e SP'):
        try:
            with conectar() as c:
                n=atualizar_municipios(c,('MG','RJ','SP'))
            st.success(f'{n} municípios recebidos/atualizados. Recarregue a página para ver a lista.')
        except Exception as erro:
            st.error(f'Erro na consulta do IBGE: {erro}')

st.divider()
st.caption('Fintech Acadêmica — projeto integrador de caráter acadêmico. Dados de setembro/2026; modelo exploratório.')
