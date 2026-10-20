"""Consultas opcionais a municípios do IBGE, sem alterar a base original."""
import requests

ENDPOINT = 'https://servicodados.ibge.gov.br/api/v1/localidades'


def obter_municipios(ufs=('MG','RJ','SP'), timeout=12):
    r=requests.get(f'{ENDPOINT}/estados',timeout=timeout)
    r.raise_for_status()
    estados={p['sigla']:p['id'] for p in r.json()}
    resultado=[]
    for uf in ufs:
        sigla=uf.upper().strip()
        if sigla not in estados:
            raise ValueError(f'UF inválida: {uf}')
        resposta=requests.get(f'{ENDPOINT}/estados/{estados[sigla]}/municipios',timeout=timeout)
        resposta.raise_for_status()
        resultado.extend((int(m['id']),str(m['nome']),sigla) for m in resposta.json())
    return resultado


def atualizar_municipios(conn, ufs=('MG','RJ','SP')):
    lista=obter_municipios(ufs)
    conn.executemany('''INSERT INTO municipios(id,nome,uf_sigla) VALUES(?,?,?)
                        ON CONFLICT(id) DO UPDATE SET nome=excluded.nome,uf_sigla=excluded.uf_sigla''',lista)
    conn.commit()
    return len(lista)
