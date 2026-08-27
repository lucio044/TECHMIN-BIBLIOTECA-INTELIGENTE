/** Deteccion de idioma, para decidir si ofrecer el boton de traducir.
 *
 *  Un acento resuelve el caso; si no hay, gana quien puso mas palabras
 *  funcionales. Las mismas listas viven en backend/app/ml/traductor.py, que
 *  decide en que direccion traducir: si se tocan aca, se tocan alla.
 *
 *  Los \b son obligatorios. En el prototipo estuvieron rotos --eran
 *  caracteres de retroceso literales en lugar de escapes-- asi que ninguna
 *  de las dos expresiones matcheaba nada, `pareceIngles` devolvia siempre
 *  falso y el boton no llego a aparecer nunca. Sin los \b tampoco alcanza:
 *  matchean dentro de las palabras, y «autenticacion con tokens» daba
 *  ingles por el «to» de «tokens» y el «on» de «autenticacion». Sobre
 *  treinta consultas de prueba, 13 aciertos pasaron a 28. */

const ACENTOS = /[áéíóúñü¿¡]/i;

const FUNC_ES =
  /\b(de|la|el|los|las|un|una|que|con|para|por|del|al|se|su|es|son|como|cuando|donde|pero|mas|muy|todo|este|esta|hay|sobre|entre|desde|hasta|sin|cual|cuales|porque|si|no|lo|mi|tiene|puedo|hacer|mejor|nuestro)\b/gi;

const FUNC_EN =
  /\b(the|of|and|to|in|is|are|for|with|that|this|from|by|on|as|you|your|it|be|have|has|can|will|not|how|do|does|did|what|when|where|why|which|an|or|if|should|would|could|about|between|over|under|than|best|my)\b/gi;

const cuenta = (texto: string, re: RegExp) => (texto.match(re) ?? []).length;

/** Esta esto en ingles? Se pregunta sobre material del historico, que es
 *  ingles al 95,9 %: sin senales, lo probable es que lo sea. */
export function pareceIngles(texto: string): boolean {
  if (!texto) return false;
  if (ACENTOS.test(texto)) return false;
  return cuenta(texto, FUNC_EN) >= cuenta(texto, FUNC_ES);
}

/** Pregunto en ingles? Decide si se ofrece el boton, y ahi el empate va al
 *  otro lado: «testing automatizado» no tiene una sola palabra funcional, y
 *  ante la duda conviene un boton de mas antes que esconderselo a quien lo
 *  necesita. */
export function preguntoEnIngles(texto: string): boolean {
  if (!texto) return false;
  if (ACENTOS.test(texto)) return false;
  return cuenta(texto, FUNC_EN) > cuenta(texto, FUNC_ES);
}
