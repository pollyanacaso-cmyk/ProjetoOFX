import os
from io import BytesIO
from decimal import Decimal, InvalidOperation
from datetime import datetime
from flask import Flask, render_template, request
from ofxparse import OfxParser
import psycopg2

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

CLASSIFICACOES = [
    "Folha de pagamento",
    "Aluguel",
    "Recebimento de cliente",
    "Energia elétrica",
    "Material",
    "Outros",
]


def conectar():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "A variável DATABASE_URL não está configurada. "
            "Configure a URL de conexão do Neon no terminal."
        )
    return psycopg2.connect(url, sslmode="require")


def dinheiro(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_resumo(movimentacoes):
    entradas = sum((m["valor"] for m in movimentacoes if m["valor"] > 0), Decimal("0"))
    saidas = sum((m["valor"] for m in movimentacoes if m["valor"] < 0), Decimal("0"))
    return {
        "quantidade": len(movimentacoes),
        "entradas": dinheiro(entradas),
        "saidas": dinheiro(abs(saidas)),
        "saldo": dinheiro(entradas + saidas),
    }


def exibir_movimentacao(data, valor, descricao, classificacao=""):
    return {
        "data": data.strftime("%d/%m/%Y"),
        "data_banco": data,
        "valor": valor,
        "valor_formatado": dinheiro(valor),
        "descricao": descricao,
        "classificacao": classificacao,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    erro = None
    resultado = None
    sucesso = None

    if request.method == "POST":
        acao = request.form.get("acao", "importar")

        if acao == "salvar":
            conexao = None
            try:
                quantidade = int(request.form.get("quantidade", "0"))
                if quantidade < 1 or quantidade > 5000:
                    raise ValueError("Quantidade de movimentações inválida.")

                movimentacoes = []
                for i in range(quantidade):
                    data = datetime.strptime(request.form.get(f"data_{i}", ""), "%Y-%m-%d").date()
                    valor = Decimal(request.form.get(f"valor_{i}", ""))
                    descricao = request.form.get(f"descricao_{i}", "")[:255]
                    classificacao = request.form.get(f"classificacao_{i}", "")
                    if classificacao not in CLASSIFICACOES:
                        raise ValueError(f"Escolha uma classificação válida para a movimentação {i + 1}.")
                    movimentacoes.append({
                        "data_banco": data,
                        "valor": valor,
                        "descricao": descricao,
                        "classificacao": classificacao,
                    })

                conexao = conectar()
                with conexao.cursor() as cursor:
                    inseridas = 0
                    atualizadas = 0
                    for mov in movimentacoes:
                        cursor.execute("""
                            INSERT INTO movimentacoes
                                (data_movimentacao, valor, descricao, classificacao)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (data_movimentacao, valor, descricao)
                            DO UPDATE SET classificacao = EXCLUDED.classificacao
                            RETURNING (xmax = 0) AS foi_inserida
                        """, (
                            mov["data_banco"], mov["valor"],
                            mov["descricao"], mov["classificacao"]
                        ))
                        if cursor.fetchone()[0]:
                            inseridas += 1
                        else:
                            atualizadas += 1
                conexao.commit()
                sucesso = f"Classificações salvas! {inseridas} novas movimentações inseridas e {atualizadas} registros existentes atualizados."
            except (ValueError, InvalidOperation) as exc:
                if conexao:
                    conexao.rollback()
                erro = str(exc)
            except Exception as exc:
                if conexao:
                    conexao.rollback()
                erro = f"Não foi possível salvar as classificações. Detalhe: {exc}"
            finally:
                if conexao:
                    conexao.close()

        else:
            arquivo = request.files.get("arquivo")
            if not arquivo or not arquivo.filename:
                erro = "Selecione um arquivo OFX antes de enviar."
            elif not arquivo.filename.lower().endswith(".ofx"):
                erro = "O arquivo selecionado precisa ter a extensão .ofx."
            else:
                try:
                    ofx = OfxParser.parse(BytesIO(arquivo.read()))
                    transacoes = ofx.account.statement.transactions
                    if not transacoes:
                        raise ValueError("O arquivo OFX não contém movimentações.")

                    movimentacoes = []
                    for t in transacoes:
                        valor = Decimal(str(t.amount))
                        descricao = (t.memo or "Sem descrição")[:255]
                        movimentacoes.append(exibir_movimentacao(
                            t.date.date(), valor, descricao
                        ))

                    resultado = montar_resumo(movimentacoes)
                    resultado["movimentacoes"] = movimentacoes
                    resultado["nome_arquivo"] = arquivo.filename
                except Exception as exc:
                    erro = f"Não foi possível analisar o arquivo OFX. Detalhe: {exc}"

    return render_template(
        "index.html", erro=erro, resultado=resultado,
        sucesso=sucesso, classificacoes=CLASSIFICACOES
    )


@app.errorhandler(413)
def arquivo_grande(_erro):
    return render_template(
        "index.html", erro="O arquivo excede o limite de 10 MB.",
        resultado=None, sucesso=None, classificacoes=CLASSIFICACOES
    ), 413


if __name__ == "__main__":
    app.run(debug=True)
