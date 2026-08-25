"""
Contrato de datos tipado para el resultado de la clasificación.

Usar un dataclass (en vez de pasar un dict suelto entre funciones) hace
que la forma del resultado sea explícita y verificable por el tipado
estático — un cambio accidental en el nombre de un campo se detecta
como error de tipos, no como un bug silencioso en producción.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ResultadoClasificacion:
    """Resultado de clasificar un contenido técnico.

    Attributes:
        categoria: Categoría predicha con mayor probabilidad.
        probabilidad: Probabilidad de la categoría predicha (0.0 a 1.0).
        informacion_adicional: Palabras clave extraídas del texto.
        categoria_alternativa: Segunda categoría candidata, presente solo
            cuando `probabilidad` está por debajo del umbral configurado
            (ver `config.UMBRAL_CATEGORIA_ALTERNATIVA`).
    """

    categoria: str
    probabilidad: float
    informacion_adicional: List[str] = field(default_factory=list)
    categoria_alternativa: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado al formato JSON acordado con el equipo
        ("formato del reto": categoria + probabilidad + informacion_adicional).
        `categoria_alternativa` solo se incluye cuando aplica, para no
        alterar el contrato base en el caso común.

        Returns:
            Diccionario serializable con `json.dumps`.
        """
        resultado: Dict[str, Any] = {
            "categoria": self.categoria,
            "probabilidad": self.probabilidad,
            "informacion_adicional": self.informacion_adicional,
        }
        if self.categoria_alternativa is not None:
            resultado["categoria_alternativa"] = self.categoria_alternativa
        return resultado
