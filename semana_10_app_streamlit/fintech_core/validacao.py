"""Validação financeira e classes do projeto (Semanas 2 e 3)."""
from dataclasses import dataclass, field
from datetime import date, datetime
from math import isfinite

CATEGORIAS = {
    'Alimentação': 'alimentação',
    'Transporte': 'transporte',
    'Material Didático': 'material didático',
    'Moradia': 'moradia',
    'Lazer': 'lazer',
    'Outros': 'outros',
}


def validar_despesa(valor: float, data: datetime | date, categoria: str) -> None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not isfinite(valor) or valor <= 0:
        raise ValueError('Informe um valor numérico, finito e maior que zero.')
    if not isinstance(data, (date, datetime)):
        raise ValueError('A data deve ser um objeto date ou datetime.')
    if categoria not in CATEGORIAS:
        raise ValueError('Selecione uma categoria válida.')


@dataclass(frozen=True)
class Estudante:
    nome: str
    matricula: str

    def __post_init__(self):
        if not isinstance(self.nome, str) or not self.nome.strip():
            raise ValueError('Nome obrigatório.')
        if not isinstance(self.matricula, str) or not self.matricula.strip():
            raise ValueError('Matrícula obrigatória.')


@dataclass(frozen=True)
class Despesa:
    valor: float
    data: datetime | date
    categoria: str

    def __post_init__(self):
        validar_despesa(self.valor, self.data, self.categoria)


@dataclass
class GestorFinanceiro:
    estudante: Estudante
    _despesas: list[Despesa] = field(default_factory=list, repr=False)

    def adicionar(self, despesa: Despesa):
        if not isinstance(despesa, Despesa):
            raise TypeError('Esperado objeto Despesa.')
        self._despesas.append(despesa)

    @property
    def total(self):
        return sum(d.valor for d in self._despesas)

    @property
    def quantidade(self):
        return len(self._despesas)
