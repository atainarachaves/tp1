"""Calculo das metricas da simulacao."""


def metricas_processo(processo):
    # turnaround = tempo total desde a chegada ate o fim (formula do enunciado)
    termino = processo.tempo_termino
    turnaround = None if termino is None else termino - processo.chegada
    # espera na fila de prontos = turnaround menos o que ele realmente ocupou a CPU
    # e menos o tempo que ficou bloqueado esperando I/O (tambem formula do enunciado)
    espera = None if turnaround is None else turnaround - processo.cpu_consumida - processo.tempo_bloqueado
    return {
        "pid": processo.pid,
        "nome": processo.nome,
        "chegada": processo.chegada,
        "termino": termino,
        "turnaround": turnaround,
        "cpu": processo.cpu_consumida,
        "bloqueio": processo.tempo_bloqueado,
        "espera": espera,
    }


def metricas_gerais(processos):
    dados = [metricas_processo(processo) for processo in processos]
    # so entram na media os processos que de fato terminaram (termino != None);
    # um processo cortado pelo limite de UTs nao deveria distorcer a media
    concluidos = [item for item in dados if item["termino"] is not None]
    quantidade = len(concluidos)
    return {
        "processos": dados,
        "media_espera": sum(item["espera"] for item in concluidos) / quantidade if quantidade else 0,
        "media_turnaround": sum(item["turnaround"] for item in concluidos) / quantidade if quantidade else 0,
    }