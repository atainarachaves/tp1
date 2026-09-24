"""Executa os casos de demonstracao do trabalho."""

import argparse
import json
import os

from assembler import Assembler
from process import Processo
from scheduler import Scheduler

def carregar_processos(configuracoes):
    processos = []
    for pid, configuracao in enumerate(configuracoes, 1):
        programa = Assembler().assemble(configuracao["arquivo"])
        processos.append(Processo(pid, configuracao["nome"], configuracao["arrivalTime"],
                                  configuracao["prioridade"], programa.instrucoes, dict(programa.dados)))
    return processos


def imprimir_resultado(resultado):
    print("\nDiagrama de Gantt:")
    print(resultado["gantt"])
    print("\nMetricas individuais:")
    for item in resultado["metricas"]["processos"]:
        print(item)
    print(f"\nMedia de espera: {resultado['metricas']['media_espera']:.2f}")
    print(f"Media de turnaround: {resultado['metricas']['media_turnaround']:.2f}")


def main():
    parser = argparse.ArgumentParser(description="Simulador MLFQ")
    parser.add_argument("--config", help="JSON com a lista de processos")
    parser.add_argument("--programa", help="Executa um unico arquivo Assembly")
    parser.add_argument("--silencioso", action="store_true")
    parser.add_argument("--max-uts", type=int, default=10000)
    
    args = parser.parse_args()
    base = os.path.dirname(__file__)

    if args.config:
        with open(args.config, "r", encoding="utf-8") as arquivo:
            configuracoes = json.load(arquivo)
    elif args.programa:
        configuracoes = [{"nome": "P1", "arrivalTime": 0, "prioridade": 3,
                          "arquivo": os.path.abspath(args.programa)}]
    else:
        configuracoes = [
            {"nome": "P1", "arrivalTime": 0, "prioridade": 3,
             "arquivo": os.path.join(base, "programs", "teste1.asm")},
            {"nome": "P2", "arrivalTime": 1, "prioridade": 5,
             "arquivo": os.path.join(base, "programs", "teste2.asm")},
        ]
    def entrada_teclado(processo):
        # usada pela CPU quando o programa executa SYSCALL 2 (leitura via teclado)
        while True:
            try:
                return int(input(f"[{processo.nome}] Digite um valor inteiro (SYSCALL 2): "))
            except ValueError:
                print("Entrada invalida: informe um numero inteiro.")

    resultado = Scheduler(carregar_processos(configuracoes), entrada=entrada_teclado,
                          mostrar=not args.silencioso, max_uts=args.max_uts).executar()
    imprimir_resultado(resultado)


if __name__ == "__main__":
    main()