import base64
import io
import json
import cv2
import numpy as np
import qrcode


def serializar_imagens(arquivos) -> str:
    """Converte uma lista de arquivos enviados em JSON com base64."""
    if not arquivos:
        return "[]"

    itens = []
    for arq in arquivos:
        try:
            raw = arq.getvalue()
            mime = getattr(arq, "type", None) or "image/jpeg"
            b64 = base64.b64encode(raw).decode("utf-8")
            itens.append({
                "nome": getattr(arq, "name", "imagem"),
                "mime": mime,
                "b64": b64,
            })
        except Exception:
            continue

    return json.dumps(itens)


def decodificar_imagens(json_str: str) -> list[dict]:
    """Converte o JSON salvo no banco em uma lista de dicionários com bytes prontos."""
    if not json_str or str(json_str).strip() in ("", "[]", "None", "nan"):
        return []

    try:
        dados = json.loads(json_str)
    except Exception:
        return []

    if not isinstance(dados, list):
        return []

    imagens = []
    for indice, item in enumerate(dados, start=1):
        if not isinstance(item, dict) or "b64" not in item:
            continue
        try:
            imagens.append({
                "nome": item.get("nome") or f"Imagem {indice}",
                "mime": item.get("mime") or "image/jpeg",
                "bytes": base64.b64decode(item["b64"]),
            })
        except Exception:
            continue

    return imagens


def gerar_bytes_qrcode(texto_dado: str, box_size: int = 10, border: int = 2) -> bytes:
    """Gera uma imagem PNG de QR Code em bytes."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(str(texto_dado))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def gerar_qrcode_base64(texto_dado: str, box_size: int = 10, border: int = 2) -> str:
    """Retorna o QR Code PNG codificado em base64 para uso em HTML/etiquetas."""
    png_bytes = gerar_bytes_qrcode(texto_dado, box_size=box_size, border=border)
    return base64.b64encode(png_bytes).decode("utf-8")


def ler_qrcode_de_bytes(bytes_img: bytes) -> str | None:
    """Decodifica o conteúdo de um QR Code a partir de bytes de imagem."""
    if not bytes_img:
        return None

    np_arr = np.frombuffer(bytes_img, np.uint8)
    img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_cv is None:
        return None

    detector = cv2.QRCodeDetector()
    codigo_lido, _, _ = detector.detectAndDecode(img_cv)
    if codigo_lido and str(codigo_lido).strip():
        return str(codigo_lido).strip()
    return None