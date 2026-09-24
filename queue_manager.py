"""Estruturas das filas 0 e 1 do MLFQ."""

from collections import deque


class QueueManager:
    def __init__(self):
        self.fila0 = deque()        # Fila 0: FIFO simples (Round Robin puro, quantum 2)
        self.grupos_fila1 = {}      # Fila 1: {prioridade: deque([...])}, uma fila por prioridade

    def adicionar_fila0(self, processo):
        # toda entrada na Fila 0 vai para o fim (regra: admissao/retorno de I/O sempre em FIFO)
        processo.fila = 0
        self.fila0.append(processo)

    def adicionar_fila1(self, processo, frente=False):
        # frente=True e usado so na preempcao por interrupcao: o processo tirado da CPU
        # volta para a FRENTE do seu grupo de prioridade (mantem o "lugar na fila");
        # frente=False (padrao) e o caso normal de estouro de quantum: vai para o fim do grupo
        processo.fila = 1
        grupo = self.grupos_fila1.setdefault(processo.prioridade, deque())
        if frente:
            grupo.appendleft(processo)
        else:
            grupo.append(processo)

    def retirar_fila0(self):
        # pseudo: se tem alguem, tira o primeiro da fila (FIFO); senao devolve None
        return self.fila0.popleft() if self.fila0 else None

    def retirar_fila1(self):
        # percorre as prioridades da maior para a menor (reverse=True) e retorna o
        # primeiro processo do primeiro grupo nao vazio -> prioridade alta primeiro,
        # FIFO como desempate dentro da mesma prioridade
        for prioridade in sorted(self.grupos_fila1, reverse=True):
            if self.grupos_fila1[prioridade]:
                processo = self.grupos_fila1[prioridade].popleft()
                return processo
        return None

    def fila1_vazia(self):
        # True quando nenhum grupo de prioridade tem processo
        return not any(self.grupos_fila1.values())

    def conteudo_fila1(self):
        # so para exibir no log: nomes na ordem em que seriam atendidos
        # (prioridade alta -> baixa, e dentro da mesma prioridade, ordem de chegada)
        return [processo.nome for prioridade in sorted(self.grupos_fila1, reverse=True)
                for processo in self.grupos_fila1[prioridade]]

    def remover(self, processo):
        # tenta tirar o processo de onde ele estiver, sem gerar erro se ele nao
        # estiver em nenhuma das duas filas (usado so em casos excepcionais)
        try:
            self.fila0.remove(processo)
        except ValueError:
            for grupo in self.grupos_fila1.values():
                try:
                    grupo.remove(processo)
                    return
                except ValueError:
                    continue

    def vazia(self):
        # True quando as duas filas estao completamente vazias
        return not self.fila0 and self.fila1_vazia()