import json
import random

import pandas as pd

from database.connection import agora_str, get_connection
from repositories.oficina_repo import (
    atualizar_passagem_campos,
    carregar_tabela,
    inserir_passagem,
    salvar_tabela_df,
)

STATUS_PASSAGEM_ENCERRADA = {
    "Entregue / Retirado",
    "Orçamento Recusado",
}


def obter_passagem_ativa_maquina(id_maquina: str) -> dict | None:
    """Retorna a primeira passagem ainda em aberto para a máquina, ou None."""
    df_pass = carregar_tabela("passagens_oficina")
    if df_pass.empty:
        return None

    col_id = "ID_Maquina" if "ID_Maquina" in df_pass.columns else "ID"
    if col_id not in df_pass.columns:
        return None

    ativas = df_pass[
        (df_pass[col_id].astype(str) == str(id_maquina).strip())
        & (~df_pass["Status"].isin(STATUS_PASSAGEM_ENCERRADA))
    ]
    if ativas.empty:
        return None

    return ativas.iloc[0].to_dict()


def cadastrar_cliente(nome: str, telefone_validado: str, logar_acao_fn) -> str:
    """Cadastra novo cliente com próximo ID sequencial CLI-XXX."""
    df_cli = carregar_tabela("clientes")
    novo_id_cli = f"CLI-{len(df_cli) + 1:03d}"
    novo_c = pd.DataFrame([
        {
            "ID_Cliente": novo_id_cli,
            "Nome": nome.strip(),
            "Telefone": telefone_validado,
        }
    ])
    salvar_tabela_df(
        pd.concat([df_cli, novo_c], ignore_index=True), "clientes"
    )
    logar_acao_fn(
        "CADASTRO_CLIENTE",
        f"Cliente '{nome.strip()}' ({novo_id_cli}, tel {telefone_validado}) cadastrado.",
    )
    return novo_id_cli


def cadastrar_maquina_fluxo(
    id_cliente: str,
    cliente_nome: str,
    telefone: str,
    modelo: str,
    codigo_manual: str,
    obs_cadastro: str,
    fotos_json: str,
    abrir_passagem_agora: bool,
    logar_acao_fn,
) -> tuple[bool, str, int | None]:
    """Cadastra máquina e opcionalmente já abre a primeira passagem.

    Retorna (sucesso, mensagem_ou_codigo, id_passagem_ou_none).
    """
    codigo_num = (
        codigo_manual.strip()
        if codigo_manual and codigo_manual.strip()
        else f"{random.randint(1000, 9999)}"
    )
    df_maq = carregar_tabela("maquinas")
    if "Fotos_Cadastro" not in df_maq.columns:
        df_maq["Fotos_Cadastro"] = "[]"

    if not df_maq.empty and codigo_num in df_maq["ID"].astype(str).values:
        return False, f"Já existe uma máquina cadastrada com o código {codigo_num}!", None

    if abrir_passagem_agora:
        passagem_aberta = obter_passagem_ativa_maquina(str(codigo_num))
        if passagem_aberta is not None:
            id_aberta = passagem_aberta.get("ID_Passagem", "?")
            st_aberta = passagem_aberta.get("Status", "Em andamento")
            return (
                False,
                f"A máquina {codigo_num} já possui a passagem #{id_aberta} aberta ({st_aberta}). Encerre antes de abrir outra.",
                None,
            )

    data_hora_atual = agora_str()
    nova_maq = {
        "ID": str(codigo_num),
        "QR_Code": f"QR-EQP-{codigo_num}",
        "ID_Cliente": id_cliente,
        "Cliente_Nome": cliente_nome,
        "Telefone": telefone,
        "Modelo": modelo.strip(),
        "Data_Hora_Cadastro": data_hora_atual,
        "Obs_Cadastro": obs_cadastro or "",
        "Fotos_Cadastro": fotos_json or "[]",
    }
    salvar_tabela_df(
        pd.concat([df_maq, pd.DataFrame([nova_maq])], ignore_index=True),
        "maquinas",
    )

    if abrir_passagem_agora:
        id_pass = inserir_passagem(str(codigo_num), data_entrada=data_hora_atual)
        logar_acao_fn(
            "ENTRADA_MAQUINA_PASSAGEM",
            f"Máquina ID {codigo_num} ({modelo.strip()}) cadastrada para '{cliente_nome}' com passagem #{id_pass}.",
        )
        return True, str(codigo_num), id_pass

    logar_acao_fn(
        "CADASTRO_MAQUINA_SEM_PASSAGEM",
        f"Máquina ID {codigo_num} ({modelo.strip()}) cadastrada para '{cliente_nome}' sem passagem aberta.",
    )
    return True, str(codigo_num), None


def abrir_nova_passagem_com_fotos(
    id_maquina: str,
    fotos_json: str,
    logar_acao_fn,
) -> tuple[bool, str, int | None]:
    """Abre nova passagem apenas se não houver passagem em aberto para a máquina.

    Retorna (sucesso, mensagem_ou_hora, id_passagem_ou_none).
    """
    passagem_aberta = obter_passagem_ativa_maquina(str(id_maquina))
    if passagem_aberta is not None:
        id_aberta = passagem_aberta.get("ID_Passagem", "?")
        st_aberta = passagem_aberta.get("Status", "Em andamento")
        return (
            False,
            f"A máquina {id_maquina} já possui a passagem #{id_aberta} em aberto ({st_aberta}).",
            None,
        )

    hora_entrada = agora_str()
    id_pass = inserir_passagem(str(id_maquina), data_entrada=hora_entrada)
    if fotos_json and fotos_json != "[]":
        atualizar_passagem_campos(id_pass, {"Fotos_Laudo": fotos_json})
    logar_acao_fn(
        "NOVA_PASSAGEM",
        f"Nova passagem #{id_pass} aberta para máquina ID {id_maquina} em {hora_entrada}.",
    )
    return True, hora_entrada, id_pass


def redefinir_laudo_passagem(
    id_passagem: int,
    id_maquina: str,
    logar_acao_fn,
) -> None:
    atualizar_passagem_campos(
        id_passagem,
        {
            "Descricao_Laudo": "Pendente",
            "Anomalias": "Nenhuma",
            "Pecas_Solicitadas": json.dumps([]),
            "Mecanico_Laudo": "Pendente",
            "Data_Hora_Laudo": "Pendente",
            "Fotos_Laudo": "[]",
            "Status": "Aguardando Avaliação Técnica",
        },
    )
    logar_acao_fn(
        "REDEFINIR_LAUDO",
        f"Laudo da passagem #{id_passagem} (Máquina ID {id_maquina}) redefinido.",
    )


def salvar_laudo_passagem(
    id_passagem: int,
    id_maquina: str,
    descricao_laudo: str,
    anomalias: str,
    pecas_solicitadas: list[dict],
    estoque_atual_map: dict[str, int],
    mecanico_nome: str,
    fotos_json: str,
    logar_acao_fn,
) -> tuple[str, bool]:
    falta_pecas = any(
        int(item.get("qtd", 0))
        > int(estoque_atual_map.get(item.get("peca", ""), 0))
        for item in pecas_solicitadas
    )
    hora_laudo = agora_str()
    novo_status = (
        "Aguardando Precificação (Falta Peças no Estoque)"
        if falta_pecas
        else "Aguardando Precificação (Secretaria)"
    )
    atualizar_passagem_campos(
        id_passagem,
        {
            "Descricao_Laudo": descricao_laudo.strip(),
            "Anomalias": (
                anomalias.strip() if anomalias and anomalias.strip() else "Nenhuma"
            ),
            "Pecas_Solicitadas": json.dumps(pecas_solicitadas),
            "Mecanico_Laudo": mecanico_nome,
            "Data_Hora_Laudo": hora_laudo,
            "Fotos_Laudo": fotos_json or "[]",
            "Status": novo_status,
        },
    )
    logar_acao_fn(
        "ENVIO_LAUDO_FALTA_PECAS" if falta_pecas else "ENVIO_LAUDO",
        f"Laudo enviado na passagem #{id_passagem} (Máquina ID {id_maquina}) em {hora_laudo}.",
    )
    return novo_status, falta_pecas


def iniciar_servico_passagem(
    id_passagem: int,
    id_maquina: str,
    mecanico_nome: str,
    logar_acao_fn,
) -> str:
    hora_inicio = agora_str()
    atualizar_passagem_campos(
        id_passagem,
        {
            "Status": "Em Manutenção (Na Bancada)",
            "Mecanico_Execucao": mecanico_nome,
            "Data_Hora_Inicio_Servico": hora_inicio,
        },
    )
    logar_acao_fn(
        "INICIO_SERVICO",
        f"Manutenção iniciada na passagem #{id_passagem} (Máquina ID {id_maquina}) em {hora_inicio}.",
    )
    return hora_inicio


def concluir_servico_passagem(
    id_passagem: int,
    id_maquina: str,
    logar_acao_fn,
) -> str:
    hora_conclusao = agora_str()
    atualizar_passagem_campos(
        id_passagem,
        {
            "Status": "Serviço Concluído (Aguardando Notificação ao Cliente)",
            "Data_Hora_Conclusao_Servico": hora_conclusao,
        },
    )
    logar_acao_fn(
        "CONCLUSAO_SERVICO",
        f"Serviço concluído na passagem #{id_passagem} (Máquina ID {id_maquina}) em {hora_conclusao}.",
    )
    return hora_conclusao


def calcular_custo_pecas_json(pecas_json: str | None) -> float:
    """Soma o custo total das peças serializadas no laudo."""
    if not pecas_json:
        return 0.0
    try:
        pecas = json.loads(pecas_json)
        if not isinstance(pecas, list):
            return 0.0
        return float(
            sum(
                float(item.get("qtd", 0)) * float(item.get("preco_unit", 0.0))
                for item in pecas
            )
        )
    except Exception:
        return 0.0


def precificar_passagem(
    id_passagem: int,
    id_maquina: str,
    valor_total: float,
    logar_acao_fn,
) -> None:
    atualizar_passagem_campos(
        id_passagem,
        {
            "Valor_Orcamento": float(valor_total),
            "Status": "Aguardando Envio ao Cliente",
        },
    )
    logar_acao_fn(
        "PRECIFICACAO_ORCAMENTO",
        f"Passagem #{id_passagem} (Máquina ID {id_maquina}) precificada em R$ {float(valor_total):.2f}.",
    )


def enviar_orcamento_ao_cliente(
    id_passagem: int,
    id_maquina: str,
    cliente_nome: str,
    logar_acao_fn,
) -> str:
    hora_envio = agora_str()
    atualizar_passagem_campos(
        id_passagem,
        {
            "Data_Hora_Envio_Orcamento": hora_envio,
            "Status": "Standby (Aguardando Resposta do Cliente)",
        },
    )
    logar_acao_fn(
        "ENVIO_ORCAMENTO_CLIENTE",
        f"Orçamento #{id_passagem} (Máq. {id_maquina}) enviado a '{cliente_nome}' em {hora_envio}.",
    )
    return hora_envio


def processar_resposta_cliente(
    id_passagem: int,
    id_maquina: str,
    cliente_nome: str,
    aprovado: bool,
    pecas_json: str,
    logar_acao_fn,
) -> str:
    hora_resp = agora_str()
    if not aprovado:
        atualizar_passagem_campos(
            id_passagem,
            {
                "Data_Hora_Resposta_Cliente": hora_resp,
                "Status": "Orçamento Recusado",
            },
        )
        logar_acao_fn(
            "CLIENTE_REPROVOU",
            f"Cliente '{cliente_nome}' reprovou passagem #{id_passagem} (Máq. {id_maquina}) em {hora_resp}.",
        )
        return "Orçamento Recusado"

    try:
        pecas_req = json.loads(pecas_json) if pecas_json else []
    except Exception:
        pecas_req = []

    conn = get_connection()
    cursor = conn.cursor()
    falta_estoque = False
    try:
        for item in pecas_req:
            nome_peca = item.get("peca", "")
            qtd_pedida = int(item.get("qtd", 0))
            cursor.execute(
                "SELECT Quantidade FROM estoque WHERE Nome = ?", (nome_peca,)
            )
            row = cursor.fetchone()
            qtd_atual = int(row["Quantidade"]) if row else 0
            if qtd_pedida > qtd_atual:
                falta_estoque = True
            else:
                cursor.execute(
                    "UPDATE estoque SET Quantidade = Quantidade - ? WHERE Nome = ?",
                    (qtd_pedida, nome_peca),
                )

        novo_status = (
            "Aguardando Peças"
            if falta_estoque
            else "Cliente Aprovou (Pronto para Iniciar)"
        )
        cursor.execute(
            """
            UPDATE passagens_oficina
            SET Data_Hora_Resposta_Cliente = ?, Status = ?
            WHERE ID_Passagem = ?
            """,
            (hora_resp, novo_status, int(id_passagem)),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    logar_acao_fn(
        "CLIENTE_APROVOU_FALTA_PECAS" if falta_estoque else "CLIENTE_APROVOU",
        f"Cliente '{cliente_nome}' aprovou passagem #{id_passagem} (Máq. {id_maquina}) em {hora_resp} ({novo_status}).",
    )
    return novo_status


def notificar_conclusao_cliente(
    id_passagem: int,
    id_maquina: str,
    cliente_nome: str,
    logar_acao_fn,
) -> str:
    hora_notif = agora_str()
    atualizar_passagem_campos(
        id_passagem,
        {
            "Data_Hora_Notificacao_Conclusao": hora_notif,
            "Status": "Serviço Concluído (Aguardando Retirada)",
        },
    )
    logar_acao_fn(
        "NOTIFICACAO_CONCLUSAO_CLIENTE",
        f"Cliente '{cliente_nome}' notificado da conclusão da passagem #{id_passagem} (Máq. {id_maquina}) em {hora_notif}.",
    )
    return hora_notif


def confirmar_saida_maquina(
    id_passagem: int,
    id_maquina: str,
    logar_acao_fn,
) -> str:
    hora_saida = agora_str()
    atualizar_passagem_campos(
        id_passagem,
        {
            "Status": "Entregue / Retirado",
            "Data_Hora_Saida": hora_saida,
        },
    )
    logar_acao_fn(
        "SAIDA_MAQUINA",
        f"Saída da passagem #{id_passagem} (Máq. {id_maquina}) confirmada em {hora_saida}.",
    )
    return hora_saida


def repor_estoque_peca(nome_peca: str, qtd_adicionar: int, logar_acao_fn) -> None:
    """Adiciona unidades de uma peça no estoque e registra no log."""
    df_est = carregar_tabela("estoque")
    idx_p = df_est[df_est["Nome"] == nome_peca].index[0]
    df_est.loc[idx_p, "Quantidade"] = int(df_est.loc[idx_p, "Quantidade"]) + int(
        qtd_adicionar
    )
    salvar_tabela_df(df_est, "estoque")
    logar_acao_fn(
        "REPOSICAO_ESTOQUE",
        f"Adicionadas {int(qtd_adicionar)} unidade(s) de '{nome_peca}'.",
    )