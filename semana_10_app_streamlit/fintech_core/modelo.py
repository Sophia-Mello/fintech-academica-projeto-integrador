"""Inferência a partir de um artefato .joblib local gerado pelo projeto."""
from pathlib import Path
import json
import joblib
import pandas as pd
from .treinamento import COLUNAS

PASTA = Path(__file__).resolve().parents[1]


def carregar_modelo():
    meta=json.loads((PASTA/'metadata_modelo.json').read_text(encoding='utf-8'))
    if meta.get('features')!=COLUNAS:
        raise ValueError('As variáveis do modelo não correspondem aos metadados.')
    return joblib.load(PASTA/'modelo_despesas.joblib'),meta


def entrada_previsao(historico:pd.DataFrame,estudante_id:int,categoria:str):
    anterior=historico.loc[historico['estudante_id'].eq(estudante_id),'valor'].dropna()
    return pd.DataFrame([{'categoria':categoria,'media_gastos_anteriores':float(anterior.mean()) if len(anterior) else 0.,
                          'qtd_gastos_anteriores':len(anterior),'tem_historico':int(len(anterior)>0)}],columns=COLUNAS)


def prever(historico:pd.DataFrame,estudante_id:int,categoria:str):
    mod,meta=carregar_modelo()
    return float(mod.predict(entrada_previsao(historico,estudante_id,categoria))[0]),meta
