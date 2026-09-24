"""Formatacao do historico temporal da CPU."""


def formatar_gantt(historico):
    # historico e a lista de "fotos" (uma por UT) montada pelo Scheduler em _registrar.
    # Aqui so pegamos tempo + nome do processo de cada UT e juntamos numa string
    # "0:P1 1:P1 2:P2 ...": e o diagrama de Gantt textual pedido no enunciado.
    if not historico:
        return "(sem execucao)"
    return " ".join(f"{item['tempo']}:{item['processo']}" for item in historico)


def tabela_gantt(historico):
    # mesma informacao do formatar_gantt, mas como lista de tuplas (tempo, processo),
    # caso seja mais facil de manipular numa tabela em vez de uma unica linha de texto
    return [(item["tempo"], item["processo"]) for item in historico]