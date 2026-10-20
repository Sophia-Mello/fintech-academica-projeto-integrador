"""Teste da inicialização Streamlit, executado quando a dependência está disponível."""
from pathlib import Path
import pytest

st=pytest.importorskip('streamlit')
from streamlit.testing.v1 import AppTest


def test_app_inicializa_sem_excecoes():
    raiz=Path(__file__).resolve().parents[1]
    teste=AppTest.from_file(str(raiz/'app.py'),default_timeout=45).run()
    assert not teste.exception,[e.message for e in teste.exception]
