# Executar todos os testes
pytest

# Executar testes específicos
pytest tests/test_client.py -v
pytest tests/test_auth.py::TestOAuth2TokenManager -v

# Executar testes com cobertura
pytest --cov=opensky --cov-report=term-missing

# Executar testes de integração (requer credenciais reais)
pytest tests/test_integration.py -m integration

# Executar testes sem marcação slow
pytest -m "not slow"

# Executar testes e gerar relatório HTML
pytest --cov=opensky --cov-report=html

# Executar testes com paralelismo
pytest -n auto