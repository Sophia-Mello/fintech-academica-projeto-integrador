"""Métricas dos gastos e séries temporais (com distinção de média diária/mensal)."""
from __future__ import annotations
import pandas as pd


def moeda(valor: float) -> str:
    return 'R$ ' + f'{float(valor):,.2f}'.replace(',','_').replace('.',',').replace('_','.')


def indicadores(df: pd.DataFrame) -> dict:
    if df.empty:
        return {'total':0.,'ticket':0.,'mediana':0.,'quantidade':0,'estudantes':0,'outliers':0,'participacao_outlier':0.}
    total=float(df['valor'].sum())
    atipicos=float(df.loc[df['is_outlier'],'valor'].sum())
    return {'total':total, 'ticket':float(df['valor'].mean()), 'mediana':float(df['valor'].median()),
            'quantidade':len(df),'estudantes':df['estudante_id'].nunique(),
            'outliers':int(df['is_outlier'].sum()),'participacao_outlier':100*atipicos/total if total else 0.}


def evolucao(df: pd.DataFrame):
    if df.empty:
        return pd.DataFrame(columns=['data','gastos','media_movel']), 'sem_dados'
    if df['data'].dt.to_period('M').nunique() >= 2:
        s = df.groupby(df['data'].dt.to_period('M'))['valor'].sum().sort_index()
        s.index=s.index.to_timestamp()
        granularidade='mensal'
    else:
        s = df.groupby(df['data'].dt.floor('D'))['valor'].sum().sort_index()
        s=s.asfreq('D',fill_value=0)
        granularidade='diaria'
    return pd.DataFrame({'data':s.index,'gastos':s.values,'media_movel':s.rolling(3,min_periods=1).mean().values}),granularidade


def por_categoria(df: pd.DataFrame):
    return df.groupby('categoria',as_index=False)['valor'].agg('sum').sort_values('valor',ascending=False) if not df.empty else pd.DataFrame(columns=['categoria','valor'])
