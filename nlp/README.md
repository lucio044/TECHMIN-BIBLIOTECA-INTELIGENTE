# techmind-nlp

El procesamiento de texto de TechMind, como paquete instalable.

```bash
pip install -e ./nlp
```

**La API lo importa.** `backend/app/services/clasificador.py` saca de acá el
extractor de términos. Antes tenía su propia copia del mismo archivo: daban
resultados idénticos, pero eso sólo quería decir que todavía no habían
divergido — el primer arreglo en uno habría dejado al otro atrás sin que
nada avisara. Ahora hay una sola implementación y una prueba que falla si
reaparece la copia.

**Lo demás no lo usa la API.** `classifier`, `model_repository` e
`inference` son un diseño alternativo del mismo flujo, más elaborado —con
protocolos, inyección de dependencias y excepciones propias— que quedó del
reparto de trabajo por áreas. Se conserva porque sus pruebas cubren los
algoritmos, pero la API resuelve eso con sus propios módulos en
`backend/app/`. Conviene saberlo antes de tocar acá esperando cambiar el
comportamiento de la API.

| Módulo | Lo usa la API |
|---|---|
| `keywords` | **sí** |
| `cleaning`, `tokenization` | no |
| `classifier`, `model_repository`, `inference`, `schemas` | no |

```bash
cd nlp && pytest        # 72 pruebas
```

---

