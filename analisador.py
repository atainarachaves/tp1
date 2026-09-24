"""Compatibilidade com a API original do trabalho."""

from assembler import Assembler, ErroDeMontagem, Instrucao


def analisar_programa(caminho):
    # mantem o nome de funcao usado na entrega original; por baixo dos panos
    # so chama o Assembler novo e devolve os dois pedacos separados (instrucoes, dados)
    programa = Assembler().assemble(caminho)
    return programa.instrucoes, programa.dados


__all__ = ["analisar_programa", "ErroDeMontagem", "Instrucao"]
