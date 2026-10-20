"""Avaliação cronológica e exportação do modelo demonstrativo da Semana 9."""
from __future__ import annotations
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

COLUNAS=['categoria','media_gastos_anteriores','qtd_gastos_anteriores','tem_historico']


def preparar_features(dados: pd.DataFrame) -> pd.DataFrame:
    df=dados.sort_values(['data','id']).reset_index(drop=True).copy()
    if len(df)<5 or df['valor'].isna().any() or df['data'].isna().any():
        raise ValueError('É necessário ter pelo menos 5 despesas válidas.')
    grupo=df.groupby('estudante_id',sort=False)
    df['qtd_gastos_anteriores']=grupo.cumcount()
    df['media_gastos_anteriores']=grupo['valor'].transform(lambda x:x.shift(1).expanding(min_periods=1).mean()).fillna(0.)
    df['tem_historico']=df['qtd_gastos_anteriores'].gt(0).astype(int)
    df['categoria']=df['categoria'].fillna('nao_informado').astype(str).str.strip().str.lower()
    return df


def construir_pipeline() -> Pipeline:
    pre=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore'),['categoria']),
                           ('num','passthrough',COLUNAS[1:])])
    return Pipeline([('preprocessamento',pre),('regressao',LinearRegression())])


def avaliar(dados: pd.DataFrame):
    df=preparar_features(dados)
    limite=int(.8*len(df))
    treino,teste=df.iloc[:limite],df.iloc[limite:]
    estimador=construir_pipeline().fit(treino[COLUNAS],treino['valor'])
    previsto=estimador.predict(teste[COLUNAS])
    baseln=float(treino['valor'].mean())
    erro_modelo=float(mean_absolute_error(teste['valor'],previsto))
    erro_baseline=float(mean_absolute_error(teste['valor'],np.full(len(teste),baseln)))
    final=clone(estimador).fit(df[COLUNAS],df['valor'])
    resumo={
        'dados':'fintech_integrada.db fornecido; tabela despesas_clean',
        'n_registros':len(df),'n_treino':len(treino),'n_teste':len(teste),
        'corte':'cronológico 80/20; sem embaralhamento',
        'features':COLUNAS,'alvo':'valor',
        'mae_modelo':erro_modelo,'mae_baseline':erro_baseline,
        'baseline_media_treino':baseln,
        'outliers_no_teste':int(teste['is_outlier'].sum()),
        'versao_sklearn':sklearn.__version__,
        'treino_final_em_todos_os_registros':True,
        'aviso':'Modelo ilustrativo. Somente 7 registros e 2 observações de teste.',
        'teste':[{
            'id':int(row['id']),'data':str(pd.Timestamp(row['data']).date()),
            'valor_real':float(row['valor']),'previsao':float(pred),
            'categoria':str(row['categoria']),'outlier':bool(row['is_outlier'])}
                for (_,row),pred in zip(teste.iterrows(),previsto)],
    }
    return final,resumo


def exportar(dados: pd.DataFrame, caminho_modelo: Path, caminho_metadata: Path):
    modelo,meta=avaliar(dados)
    caminho_modelo=Path(caminho_modelo);caminho_metadata=Path(caminho_metadata)
    caminho_modelo.parent.mkdir(parents=True,exist_ok=True)
    caminho_metadata.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(modelo,caminho_modelo,compress=3)
    caminho_metadata.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    return meta
