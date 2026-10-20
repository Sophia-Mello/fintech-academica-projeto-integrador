"""Testes sobre o SQLite entregue e uma cópia isolada para operações de escrita."""
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd
import pytest
from fintech_core.dados import (
    BASE_ORIGINAL, preparar_operacional, despesas_completas, cadastro,
    staging, registrar_despesa, hash_original,
)
from fintech_core.analise import indicadores, evolucao, por_categoria
from fintech_core.qualidade import auditar, sanear_copia
from fintech_core.modelo import carregar_modelo, entrada_previsao, prever
from fintech_core.treinamento import preparar_features, avaliar, exportar
from fintech_core.validacao import validar_despesa, Estudante, Despesa, GestorFinanceiro

@pytest.fixture
def db_teste(tmp_path):
    return preparar_operacional(tmp_path/'operacional_teste.db')


def test_banco_integridade():
    assert BASE_ORIGINAL.is_file()
    with sqlite3.connect(f'file:{BASE_ORIGINAL}?mode=ro', uri=True) as conn:
        assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_dados_originais():
    with sqlite3.connect(BASE_ORIGINAL) as c:
        assert c.execute('SELECT COUNT(*) FROM estudantes').fetchone()[0]==3
        assert c.execute('SELECT COUNT(*) FROM municipios').fetchone()[0]==1590
        assert c.execute('SELECT COUNT(*) FROM despesas').fetchone()[0]==3
        assert c.execute('SELECT COUNT(*) FROM despesas_clean').fetchone()[0]==7


def test_hash_dados_recebidos():
    assert hash_original()=='cc21e3e842b6371f7a98f92c8bafbcd44682ce4b27dc67197ff5da4e29da132a'


def test_copia_sem_modificar_banco(db_teste):
    antes=hash_original()
    registrar_despesa(1,3500105,50.0,datetime(2026,9,11),'Lazer',db_teste)
    assert hash_original()==antes
    assert len(despesas_completas(BASE_ORIGINAL))==7


def test_total_e_outlier():
    d=despesas_completas(BASE_ORIGINAL)
    assert len(d)==7
    assert d['valor'].sum()==5673
    assert d.loc[d.id==6,'valor'].iloc[0]==5000
    assert d['is_outlier'].sum()==1


def test_outlier_e_resumo():
    k=indicadores(despesas_completas(BASE_ORIGINAL))
    assert k['mediana']==107.7
    assert k['total']==5673
    assert abs(k['participacao_outlier']-5000/5673*100)<1e-6


def test_evolucao_temporaria():
    s,f=evolucao(despesas_completas(BASE_ORIGINAL))
    assert f=='diaria'
    assert len(s)==10
    assert s.loc[s.data.eq('2026-09-09'),'gastos'].iloc[0]==5000


def test_categorias_conferem():
    d=por_categoria(despesas_completas(BASE_ORIGINAL))
    assert len(d)==4
    assert d.loc[d.categoria=='transporte','valor'].iloc[0]==5089.5


def test_qualidade():
    d=despesas_completas(BASE_ORIGINAL)
    q=auditar(d)
    assert q['registros']==7
    assert q['categoria_nao_informada']==1
    assert q['duplicados_id']==0
    assert q['divergencias']==0


def test_limpeza_sem_fabricacao():
    d=despesas_completas(BASE_ORIGINAL)
    limp,r=sanear_copia(d)
    assert len(limp)==7
    assert r['valores_imputados_nesta_execucao']==0
    assert r['duplicados_na_entrada']==0
    assert r['outliers']==1


@pytest.mark.parametrize('valor',[0,-1,float('nan'),float('inf'),True,'10'])
def test_validacao_rejeita_valores(valor):
    with pytest.raises(ValueError):
        validar_despesa(valor,datetime(2026,9,3),'Lazer')


def test_poo():
    aluno=Estudante('Teste','2026001')
    gestor=GestorFinanceiro(aluno)
    gestor.adicionar(Despesa(10,datetime(2026,9,3),'Lazer'))
    assert gestor.quantidade==1
    assert gestor.total==10


def test_rollback_integridade(db_teste):
    with pytest.raises(sqlite3.IntegrityError):
        registrar_despesa(1,999999999,35.0,datetime(2026,9,11),'Lazer',db_teste)
    assert len(despesas_completas(db_teste))==7
    assert len(staging(db_teste))==0


def test_nova_despesa_auditoria(db_teste):
    new=registrar_despesa(1,3500105,39.5,datetime(2026,9,11),'Lazer',db_teste)
    assert new==8
    df=despesas_completas(db_teste)
    assert len(df)==8
    assert df.loc[df.id==8,'origem_registro'].iloc[0]=='aplicativo'
    assert len(staging(db_teste))==1


def test_features_nao_usam_valor_alvo():
    df=preparar_features(despesas_completas(BASE_ORIGINAL))
    assert (df.loc[df.qtd_gastos_anteriores.eq(0),'media_gastos_anteriores']==0).all()
    assert abs(df.loc[df.id.eq(6),'media_gastos_anteriores'].iloc[0]-(125.9+107.7+75)/3)<1e-8


def test_metricas_de_machine_learning():
    _,meta=avaliar(despesas_completas(BASE_ORIGINAL))
    assert meta['n_treino']==5 and meta['n_teste']==2
    assert round(meta['mae_modelo'],2)==2540.18
    assert round(meta['mae_baseline'],2)==2467.55
    assert meta['mae_modelo']>meta['mae_baseline']


def test_artifact_reproduz_modelo():
    modelo,meta=carregar_modelo()
    assert meta['n_registros']==7
    entrada=entrada_previsao(despesas_completas(BASE_ORIGINAL),1,'transporte')
    assert list(entrada.columns)==meta['features']
    valor,_=prever(despesas_completas(BASE_ORIGINAL),1,'transporte')
    assert isinstance(valor,float)


def test_exportacao_independente(tmp_path):
    nome=tmp_path/'teste.joblib'
    meta=exportar(despesas_completas(BASE_ORIGINAL),nome,tmp_path/'teste.json')
    assert nome.is_file()
    assert meta['n_registros']==7


def test_municipios_cadastrados():
    tabela=cadastro('municipios',BASE_ORIGINAL)
    assert len(tabela)==1590
    assert set(tabela.uf_sigla)=={'SP','RJ','MG'}
