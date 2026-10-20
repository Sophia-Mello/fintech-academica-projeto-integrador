# Semana 10 — Aplicação Streamlit

Nesta pasta estão os arquivos usados na aplicação final da Fintech Acadêmica:

- `app.py`: painel, filtros, cadastro, previsão, auditoria e municípios;
- `fintech_integrada.db`: SQLite da atividade, preservado;
- `modelo_despesas.joblib` e `metadata_modelo.json`: pipeline treinado e informações da avaliação;
- `requirements.txt`: dependências;
- `fintech_core/`: código de validação, leitura, análise, tratamento e treinamento;
- `tests/`: testes do backend e inicialização opcional do Streamlit.

A partir da raiz do repositório:

```bash
python -m pip install -r semana_10_app_streamlit/requirements.txt
streamlit run semana_10_app_streamlit/app.py
```

Para os testes:

```bash
python -m pytest -q semana_10_app_streamlit/tests
```

**Link indicado para o aplicativo:** https://fintech-academica-projeto-integrador.streamlit.app/

**Observação:** a gravação de novas despesas acontece em `fintech_operacional.db`, criado localmente a partir do banco original. Essa cópia pode ser perdida em reinicializações do Streamlit Cloud. A previsão é ilustrativa porque o conjunto de treinamento é muito pequeno.
