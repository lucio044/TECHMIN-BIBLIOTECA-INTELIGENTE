biblioteca_en_memoria: dict[str, list[dict]] = {}


def guardar_en_biblioteca(usuario_id: str, entrada: dict) -> None:
    if usuario_id not in biblioteca_en_memoria:
        biblioteca_en_memoria[usuario_id] = []
    biblioteca_en_memoria[usuario_id].append(entrada)


def obtener_biblioteca(usuario_id: str) -> list[dict]:
    return biblioteca_en_memoria.get(usuario_id, [])