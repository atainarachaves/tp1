"""CPU que executa exatamente uma instrucao por chamada."""

from dataclasses import dataclass

from process import Estado, Processo


@dataclass
class ResultadoExecucao:
    # "recibo" que a CPU devolve ao Scheduler depois de rodar 1 instrucao;
    # o Scheduler decide o resto (fila, print, quantum) com base nesses campos
    bloqueou: bool = False      # True se o processo entrou em I/O (SYSCALL 1 ou 2)
    finalizou: bool = False     # True se o processo acabou (fim do codigo ou SYSCALL 0)
    syscall: int | None = None  # qual syscall rodou (0, 1 ou 2); None se nao foi syscall
    valor: int | None = None    # valor impresso/lido, usado so para exibir no log


class CPU:
    def __init__(self, entrada=None):
        # "entrada" e a funcao que sabe pedir um numero ao usuario (SYSCALL 2);
        # se nada for passado, usa uma funcao burra que sempre devolve 0
        # (util nos testes automatizados, onde nao ha teclado de verdade)
        self.entrada = entrada or (lambda processo: 0)

    @staticmethod
    def _valor(processo, operando):
        # resolve o operando de uma instrucao aritmetica/LOAD:
        # comeca com "#" -> valor constante (modo imediato), ex: "#5" vira 5
        if operando.startswith("#"):
            return int(operando[1:])
        # senao, e o nome de uma variavel na area de dados (modo direto)
        operando = operando.lower()
        if operando not in processo.memoria:
            raise RuntimeError(f"PID {processo.pid}: dado inexistente '{operando}'")
        return processo.memoria[operando]

    def executar_uma(self, processo, tempo):
        # se o pc ja passou do fim do programa, o processo acabou sem precisar de SYSCALL 0
        if processo.pc >= len(processo.instrucoes):
            processo.estado = Estado.FINALIZADO
            processo.tempo_termino = tempo
            return ResultadoExecucao(finalizou=True)

        # pega a instrucao atual e ja avanca o pc (se for um desvio tomado, o pc
        # e sobrescrito de novo logo abaixo); cada chamada deste metodo == 1 UT
        instrucao = processo.instrucoes[processo.pc]
        processo.pc += 1
        processo.cpu_consumida += 1
        mnemonico, operando = instrucao.mnemonico, instrucao.operando

        # pseudo-codigo do bloco abaixo:
        #   instrucao aritmetica/memoria -> mexe no acc ou na memoria do processo
        #   instrucao de desvio         -> so troca o pc quando a condicao bate
        #   SYSCALL                     -> finaliza (0) ou bloqueia por I/O (1 ou 2)
        if mnemonico == "LOAD":
            processo.acc = self._valor(processo, operando)
        elif mnemonico == "STORE":
            processo.memoria[operando.lower()] = processo.acc
        elif mnemonico == "ADD":
            processo.acc += self._valor(processo, operando)
        elif mnemonico == "SUB":
            processo.acc -= self._valor(processo, operando)
        elif mnemonico == "MULT":
            processo.acc *= self._valor(processo, operando)
        elif mnemonico == "DIV":
            divisor = self._valor(processo, operando)
            if divisor == 0:
                raise RuntimeError(f"PID {processo.pid}: divisao por zero")
            processo.acc //= divisor
        elif mnemonico == "BRANY":
            # desvio incondicional: sempre pula para o indice ja resolvido pelo Assembler
            processo.pc = instrucao.indice_alvo
        elif mnemonico == "BRPOS" and processo.acc > 0:
            processo.pc = instrucao.indice_alvo
        elif mnemonico == "BRZERO" and processo.acc == 0:
            processo.pc = instrucao.indice_alvo
        elif mnemonico == "BRNEG" and processo.acc < 0:
            processo.pc = instrucao.indice_alvo
        elif mnemonico == "SYSCALL":
            codigo = int(operando)
            if codigo == 0:
                # HALT: o processo termina, mas so "libera" a CPU na UT seguinte (tempo + 1),
                # porque a UT atual ja foi gasta executando esta propria instrucao
                processo.estado = Estado.FINALIZADO
                processo.tempo_termino = tempo + 1
                return ResultadoExecucao(finalizou=True, syscall=codigo, valor=processo.acc)
            if codigo == 1:
                # imprime na tela: so guarda o valor do acc, quem imprime de fato e o Scheduler
                processo.saidas.append(processo.acc)
            elif codigo == 2:
                # le do teclado: chama a funcao de entrada e guarda o valor lido no acc
                processo.acc = int(self.entrada(processo))
                processo.entradas.append(processo.acc)
            # tanto SYSCALL 1 quanto 2 bloqueiam o processo por 3 UTs fixas:
            # tempo+4 porque esta UT (tempo) ja foi consumida executando a syscall,
            # entao ele fica bloqueado em tempo+1, tempo+2 e tempo+3, acordando em tempo+4
            processo.estado = Estado.BLOQUEADO
            processo.bloqueado_ate = tempo + 4
            return ResultadoExecucao(bloqueou=True, syscall=codigo, valor=processo.acc)
        # chegou aqui: instrucao aritmetica normal, ou desvio cuja condicao nao foi atendida
        return ResultadoExecucao()