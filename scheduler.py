"""Simulador do escalonamento MLFQ."""

from cpu import CPU
from gantt import formatar_gantt
from metrics import metricas_gerais
from process import Estado, Processo
from queue_manager import QueueManager


class Scheduler:
    QUANTA = {0: 2, 1: 4}  # quantum de cada fila: Fila 0 = 2 UTs, Fila 1 = 4 UTs

    def __init__(self, processos, entrada=None, mostrar=True, max_uts=10000):
        # ordenar por chegada (e pid no empate) so deixa o laco mais previsivel;
        # quem de fato decide a ordem de execucao sao as filas, nao esta lista
        self.processos = sorted(processos, key=lambda processo: (processo.chegada, processo.pid))
        self.filas = QueueManager()
        self.cpu = CPU(entrada)
        self.mostrar = mostrar
        self.tempo = 0            # relogio da simulacao, em UTs
        self.executando = None    # processo com a CPU nesta UT (ou None se ociosa)
        self.historico = []       # 1 registro por UT, usado no Gantt e no log
        self.eventos = []         # mensagens de SYSCALL (impressao/finalizado), impressas em bloco no final
        self.max_uts = max_uts    # trava de seguranca contra loop infinito no .asm

    def _admitir(self):
        # todo processo NOVO cuja chegada ja passou entra no fim da Fila 0
        for processo in self.processos:
            if processo.estado == Estado.NOVO and processo.chegada <= self.tempo:
                processo.estado = Estado.PRONTO
                self.filas.adicionar_fila0(processo)

    def _acordar(self):
        # quem completou as 3 UTs de I/O volta para o fim da Fila 0 (regra: retorno
        # de I/O sempre entra pela Fila 0); quem ainda nao completou so acumula
        # mais 1 UT de tempo bloqueado (usado depois nas metricas de espera)
        for processo in self.processos:
            if processo.estado == Estado.BLOQUEADO:
                if processo.bloqueado_ate <= self.tempo:
                    processo.estado = Estado.PRONTO
                    processo.bloqueado_ate = None
                    processo.quantum_usado = 0
                    self.filas.adicionar_fila0(processo)
                else:
                    processo.tempo_bloqueado += 1

    def _escolher(self):
        # Fila 0 tem prioridade absoluta: so olha a Fila 1 se a Fila 0 estiver vazia
        if self.filas.fila0:
            return self.filas.retirar_fila0()
        return self.filas.retirar_fila1()

    def _registrar(self, processo):
        # tira uma "foto" do sistema nesta UT: quem esta na CPU, o estado de todo
        # mundo e o conteudo das duas filas + lista de bloqueados. E o que aparece
        # no log "UT n: CPU=... | estados=... | F0=... | F1=... | bloqueados=..."
        item = {
            "tempo": self.tempo,
            "processo": processo.nome if processo else "IDLE",
            "estados": {p.nome: p.estado.value for p in self.processos},
            "fila0": [p.nome for p in self.filas.fila0],
            "fila1": self.filas.conteudo_fila1(),
            "bloqueados": [p.nome for p in self.processos if p.estado == Estado.BLOQUEADO],
        }
        self.historico.append(item)
        if self.mostrar:
            print(f"UT {self.tempo}: CPU={item['processo']} | estados={item['estados']} | "
                  f"F0={item['fila0']} | F1={item['fila1']} | bloqueados={item['bloqueados']}")

    def executar(self):
        # laco principal: 1 iteracao = 1 unidade de tempo (UT). Pseudo-codigo do ciclo:
        #   1. checa o limite de seguranca (max_uts)
        #   2. admite quem chegou e acorda quem terminou o I/O
        #   3. se quem esta rodando e da Fila 1 e a Fila 0 acabou de receber alguem -> preempcao
        #   4. se ninguem esta rodando, escolhe o proximo (Fila 0 tem prioridade sobre a Fila 1)
        #   5. manda a CPU executar 1 instrucao desse processo
        #   6. trata o resultado: bloqueou / finalizou / estourou quantum
        #   7. registra a foto desta UT e avanca o relogio
        while not all(processo.finalizado for processo in self.processos):
            if self.tempo >= self.max_uts:
                # trava contra .asm com loop infinito: forca o fim de tudo que sobrou
                pendentes = [processo for processo in self.processos if not processo.finalizado]
                for processo in pendentes:
                    processo.estado = Estado.FINALIZADO
                    processo.tempo_termino = self.tempo
                    processo.erro = f"limite de {self.max_uts} UTs atingido"
                    if self.mostrar:
                        print(f"[{processo.nome}] Finalizado por limite de execucao ({self.max_uts} UTs)")
                break
            self._admitir()
            self._acordar()
            # checagem defensiva: se quem estava executando deixou de estar EXECUTANDO
            # por algum outro motivo, libera a CPU antes de seguir
            if self.executando is not None and self.executando.estado != Estado.EXECUTANDO:
                self.executando = None

            # preempcao imediata: quem esta na CPU veio da Fila 1 e a Fila 0 tem gente
            # esperando -> tira da CPU e devolve para a FRENTE do seu grupo de prioridade
            if self.executando is not None and self.executando.fila == 1 and self.filas.fila0:
                self.executando.estado = Estado.PRONTO
                self.filas.adicionar_fila1(self.executando, frente=True)
                self.executando = None
            # se a CPU esta livre, escolhe o proximo processo pronto
            if self.executando is None:
                self.executando = self._escolher()
                if self.executando:
                    self.executando.estado = Estado.EXECUTANDO

            processo = self.executando
            if processo is None:
                # ninguem pronto: CPU fica ociosa por essa UT (aparece como IDLE no log)
                self._registrar(None)
                self.tempo += 1
                continue

            try:
                # executa exatamente 1 instrucao (= 1 UT) do processo escolhido
                resultado = self.cpu.executar_uma(processo, self.tempo)
            except RuntimeError as erro:
                # erro de execucao (ex: divisao por zero, variavel inexistente):
                # so este processo e finalizado, a simulacao dos demais continua normalmente
                processo.estado = Estado.FINALIZADO
                processo.tempo_termino = self.tempo + 1
                processo.erro = str(erro)
                self.executando = None
                if self.mostrar:
                    print(f"[{processo.nome}] Erro: {erro}")
                self._registrar(processo)
                self.tempo += 1
                continue
            processo.quantum_usado += 1

            if resultado.syscall == 1:
                self.eventos.append(f"[{processo.nome}] Impressao (SYSCALL 1): {resultado.valor}")
            elif resultado.syscall == 0:
                self.eventos.append(f"[{processo.nome}] Finalizado (SYSCALL 0)")
            if resultado.bloqueou or resultado.finalizou:
                # processo saiu da CPU por bloqueio de I/O ou por ter terminado
                self.executando = None
            elif processo.quantum_usado >= self.QUANTA[processo.fila]:
                # estourou o quantum da fila em que estava
                processo.estado = Estado.PRONTO
                if processo.fila == 0:
                    # Fila 0: quantum de 2 UTs esgotado -> rebaixado para a Fila 1
                    processo.quantum_usado = 0
                    self.filas.adicionar_fila1(processo)
                else:
                    # Fila 1: quantum de 4 UTs esgotado -> volta para o fim do
                    # seu proprio grupo de prioridade dentro da Fila 1
                    processo.quantum_usado = 0
                    self.filas.adicionar_fila1(processo)
                self.executando = None
            # se nao caiu em nenhum dos dois "if" acima, o processo continua
            # executando normalmente na proxima UT (ainda tem quantum sobrando)
            self._registrar(processo)
            self.tempo += 1
        if self.mostrar and self.eventos:
            # bloco separado do log de UTs, no formato pedido no enunciado
            print("\n=== EXECUTANDO SIMULAÇÃO ===")
            for evento in self.eventos:
                print(evento)
        return self.resultado()

    def resultado(self):
        # empacota tudo que o main.py precisa mostrar no final da simulacao
        return {
            "tempo_final": self.tempo,
            "gantt": formatar_gantt(self.historico),
            "historico": self.historico,
            "eventos": self.eventos,
            "metricas": metricas_gerais(self.processos),
        }