"""Auditoria da base tratada. Não reconstrói dados brutos ausentes."""
import pandas as pd


def auditar(df: pd.DataFrame) -> dict:
    campos=['id','valor','data','estudante_id','municipio_id','categoria','is_outlier']
    base=df[campos].copy()
    if base.empty:
        return {'registros':0,'nulos':0,'duplicados_id':0,'categoria_nao_informada':0,'outliers':0,'divergencias':0,
                'limite_inferior':None,'limite_superior':None}
    q1,q3=base['valor'].quantile([0.25,0.75])
    li,ls=q1-1.5*(q3-q1),q3+1.5*(q3-q1)
    flags=(base['valor']<li)|(base['valor']>ls)
    return {'registros':len(base),'nulos':int(base.isna().sum().sum()),
            'duplicados_id':int(base['id'].duplicated().sum()),
            'categoria_nao_informada':int(base['categoria'].isin(['nao_informado','']).sum()),
            'outliers':int(base['is_outlier'].sum()),'divergencias':int((flags!=base['is_outlier']).sum()),
            'limite_inferior':float(li),'limite_superior':float(ls)}


def sanear_copia(df: pd.DataFrame) -> tuple[pd.DataFrame,dict]:
    """Saneia a própria tabela tratada e relata SOMENTE o observado nessa entrada."""
    if df.empty: raise ValueError('DataFrame vazio.')
    c=df.copy()
    n_dupl=int(c.duplicated(subset=['id']).sum())
    n_nulos=int(c.isna().sum().sum())
    c=c.drop_duplicates(subset=['id'],keep='first').copy()
    c['data']=pd.to_datetime(c['data'],errors='coerce')
    c['valor']=pd.to_numeric(c['valor'],errors='coerce')
    mediana=c['valor'].median()
    n_imputados=int(c['valor'].isna().sum())
    if n_imputados and pd.isna(mediana):
        raise ValueError('Mediana indisponível para imputação.')
    c['valor']=c['valor'].fillna(mediana)
    c['categoria']=c['categoria'].astype('string').str.strip().str.lower().replace('',pd.NA).fillna('nao_informado')
    c=c.dropna(subset=['data','estudante_id','municipio_id'])
    q1,q3=c['valor'].quantile([.25,.75]); li,ls=q1-1.5*(q3-q1),q3+1.5*(q3-q1)
    c['is_outlier']=(c['valor'].lt(li)|c['valor'].gt(ls)).astype(int)
    return c,{'duplicados_na_entrada':n_dupl,'nulos_na_entrada':n_nulos,
              'valores_imputados_nesta_execucao':n_imputados,
              'linhas_resultantes':len(c),'outliers':int(c['is_outlier'].sum())}
