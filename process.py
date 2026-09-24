"""PCB e estados de um processo da simulacao."""

from dataclasses import dataclass, field
from enum import Enum


class Estado(str, Enum):
    # os 4 estados do enunciado + um estado inicial (NOVO) antes da admissao na Fila 0
    NOVO = "Novo"              # cadastrado, mas a chegada (arrivalTime) ainda nao ocorreu
    PRONTO = "Pronto"          # esta em uma das filas, esperando a CPU
    EXECUTANDO = "Executando"  # e o processo que a CPU esta rodando nesta UT
    BLOQUEADO = "Bloqueado"    # esperando o fim do I/O (SYSCALL 1 ou 2), 3 UTs fixas
    FINALIZADO = "Finalizado"  # ja rodou SYSCALL 0 ou chegou ao fim do codigo


@dataclass
class Processo:
    """PCB (Process Control Block): guarda tudo que o processo precisa para
    ser interrompido e depois retomado exatamente do ponto onde parou."""

    # --- parametros de carga, nao mudam durante a simulacao ---
    pid: int            # identificador numerico, so para log/debug
    nome: str           # nome exibido nos prints (ex: "P1")
    chegada: int        # instante (arrivalTime) em que o processo pode ser admitido
    prioridade: int     # prioridade estatica (1 a 5), usada so no ordenamento da Fila 1
    instrucoes: list    # instrucoes ja montadas pelo Assembler (list[Instrucao])
    memoria: dict       # area de dados (.data): nome da variavel -> valor inteiro

    # --- registradores da CPU hipotetica, "presos" ao processo entre uma execucao e outra ---
    estado: Estado = Estado.NOVO
    pc: int = 0         # ponteiro para a proxima instrucao a executar
    acc: int = 0        # acumulador, onde ADD/SUB/MULT/DIV realmente acontecem

    # --- controle de escalonamento ---
    fila: int = 0                       # em qual fila (0 ou 1) o processo esta agora
    quantum_usado: int = 0              # UTs ja consumidas desde que entrou na fila atual
    tempo_termino: int | None = None    # UT em que terminou, usado no calculo do turnaround
    cpu_consumida: int = 0              # total de UTs em que este processo ocupou a CPU
    tempo_bloqueado: int = 0            # total de UTs passadas no estado Bloqueado
    bloqueado_ate: int | None = None    # UT em que deve acordar (definida pela CPU ao bloquear)

    # --- historico de I/O, usado para gerar o log "Impressao (SYSCALL 1)" e nos testes ---
    saidas: list = field(default_factory=list)     # valores impressos via SYSCALL 1
    entradas: list = field(default_factory=list)   # valores lidos via SYSCALL 2
    erro: str | None = None    # mensagem de erro de execucao (ex: divisao por zero)

    @property
    def finalizado(self):
        # atalho usado pelo Scheduler na condicao de parada do laco principal
        return self.estado == Estado.FINALIZADO