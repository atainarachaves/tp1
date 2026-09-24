"""Interpretador/assembler da linguagem Assembly hipotetica."""

from dataclasses import dataclass


class ErroDeMontagem(Exception):
    """Erro de sintaxe ou semantica no programa Assembly."""


# todos os mnemonicos aceitos pela linguagem (Tabela 1 do enunciado)
MNEMONICOS_VALIDOS = {
    "LOAD", "STORE", "ADD", "SUB", "MULT", "DIV",
    "BRANY", "BRPOS", "BRZERO", "BRNEG", "SYSCALL",
}
DESVIOS = {"BRANY", "BRPOS", "BRZERO", "BRNEG"}          # usam rotulo como operando
OPERACOES_COM_DADO = {"LOAD", "STORE", "ADD", "SUB", "MULT", "DIV"}  # aceitam modo direto/imediato


@dataclass(frozen=True)
class Instrucao:
    mnemonico: str
    operando: str | None = None      # texto original: "#5", "variavel" ou nome de rotulo
    indice_alvo: int | None = None   # so para desvios: posicao ja resolvida para onde o pc deve ir

    def eh_imediato(self):
        # operando comecando com "#" = valor constante (ex: ADD #5)
        return isinstance(self.operando, str) and self.operando.startswith("#")


@dataclass(frozen=True)
class Programa:
    # produto final do Assembler, pronto para o cpu.py executar
    instrucoes: list   # lista de Instrucao, na ordem em que aparecem no .code
    dados: dict        # nome da variavel -> valor inicial (area .data)


def _imediato_valido(token):
    # um imediato valido e "#" seguido de digitos, podendo ter "-" na frente (#5, #-3)
    return token.startswith("#") and token[1:].lstrip("-").isdigit()


def _tokens_sem_comentario(linha):
    # separa a linha em palavras e para de ler assim que aparecer um "#" que
    # NAO seja um imediato valido (ou seja, um comentario "# texto qualquer")
    tokens = []
    for token in linha.split():
        if token.startswith("#") and not _imediato_valido(token):
            break
        tokens.append(token)
    return tokens


def _normalizar_nome(nome):
    # rotulos e nomes de variaveis nao diferenciam maiusculas de minusculas
    return nome.lower()


class Assembler:
    def assemble(self, caminho):
        # --- 1a passada: le o arquivo linha a linha e separa em .code / .data ---
        instrucoes, rotulos, dados = [], {}, {}
        secao = None  # None | "code" | "data": em qual secao a leitura esta agora
        with open(caminho, "r", encoding="utf-8") as arquivo:
            linhas = arquivo.readlines()
        for lineno, linha in enumerate(linhas, 1):
            tokens = _tokens_sem_comentario(linha)
            if not tokens:
                continue  # linha em branco ou so comentario
            diretiva = tokens[0].lower()
            if diretiva in (".code", ".data"):
                if secao is not None:
                    raise ErroDeMontagem(f"linha {lineno}: secao anterior nao encerrada")
                secao = diretiva[1:]  # ".code" -> "code", ".data" -> "data"
                continue
            if diretiva in (".endcode", ".enddata"):
                # ".endcode" so pode fechar quem abriu ".code" (mesma logica para .data)
                if secao != diretiva[4:]:
                    raise ErroDeMontagem(f"linha {lineno}: encerramento de secao invalido")
                secao = None
                continue
            if secao == "code":
                self._codigo(tokens, lineno, instrucoes, rotulos)
            elif secao == "data":
                self._dado(tokens, lineno, dados)
            else:
                raise ErroDeMontagem(f"linha {lineno}: comando fora de uma secao")
        if secao is not None:
            raise ErroDeMontagem("fim de arquivo dentro de uma secao")

        # --- 2a passada: resolve rotulos e valida os operandos de cada instrucao ---
        # pseudo-codigo:
        #   para cada instrucao bruta:
        #     se for desvio -> troca o nome do rotulo pelo indice real na lista de instrucoes
        #     se usa dado em modo direto -> confere se a variavel existe em .data
        #     se for SYSCALL -> confere se o indice e 0, 1 ou 2
        resolvidas = []
        for indice, instrucao in enumerate(instrucoes):
            if instrucao.mnemonico in DESVIOS:
                rotulo = _normalizar_nome(instrucao.operando)
                if rotulo not in rotulos:
                    raise ErroDeMontagem(f"instrucao {indice}: rotulo nao definido")
                # troca o operando textual pelo indice_alvo, que e o que o cpu.py usa de fato
                resolvidas.append(Instrucao(instrucao.mnemonico, rotulo, rotulos[rotulo]))
            elif instrucao.mnemonico in OPERACOES_COM_DADO and not instrucao.eh_imediato():
                nome = _normalizar_nome(instrucao.operando)
                if instrucao.mnemonico == "STORE" and instrucao.eh_imediato():
                    raise ErroDeMontagem(f"instrucao {indice}: STORE exige nome de dado")
                if nome not in dados:
                    raise ErroDeMontagem(f"instrucao {indice}: dado nao declarado '{instrucao.operando}'")
                resolvidas.append(Instrucao(instrucao.mnemonico, nome))
            elif instrucao.mnemonico == "SYSCALL" and instrucao.operando not in ("0", "1", "2"):
                raise ErroDeMontagem(f"instrucao {indice}: SYSCALL invalido")
            else:
                # instrucao aritmetica em modo imediato: nao precisa resolver nada
                resolvidas.append(instrucao)
        return Programa(resolvidas, dados)

    def _codigo(self, tokens, lineno, instrucoes, rotulos):
        # se a linha comeca com "rotulo:", registra a posicao atual (tamanho da lista
        # de instrucoes ate agora) como o indice desse rotulo, e segue lendo o resto da linha
        if tokens[0].endswith(":"):
            rotulo = tokens.pop(0)[:-1]
            rotulo = _normalizar_nome(rotulo)
            if not rotulo or rotulo in rotulos:
                raise ErroDeMontagem(f"linha {lineno}: rotulo invalido ou duplicado")
            rotulos[rotulo] = len(instrucoes)
            if not tokens:
                return  # linha so tinha o rotulo, sem instrucao junto

        mnemonico = tokens[0].upper()
        if mnemonico not in MNEMONICOS_VALIDOS:
            raise ErroDeMontagem(f"linha {lineno}: mnemonico desconhecido '{mnemonico}'")
        if len(tokens) > 2:
            raise ErroDeMontagem(f"linha {lineno}: operandos extras")
        operando = tokens[1] if len(tokens) == 2 else None
        if operando is None:
            raise ErroDeMontagem(f"linha {lineno}: operando ausente")
        if mnemonico == "STORE" and operando.startswith("#"):
            # STORE so aceita endereco direto (regra do enunciado)
            raise ErroDeMontagem(f"linha {lineno}: STORE exige nome de dado")
        instrucoes.append(Instrucao(mnemonico, operando))

    def _dado(self, tokens, lineno, dados):
        # cada linha da secao .data e "nome valor", ex: "valor 10"
        if len(tokens) != 2:
            raise ErroDeMontagem(f"linha {lineno}: declaracao de dado invalida")
        nome, valor = tokens
        nome = _normalizar_nome(nome)
        if nome in dados:
            raise ErroDeMontagem(f"linha {lineno}: dado duplicado '{nome}'")
        try:
            dados[nome] = int(valor)
        except ValueError as exc:
            raise ErroDeMontagem(f"linha {lineno}: valor de dado invalido") from exc