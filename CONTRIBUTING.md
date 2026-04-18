# Contribuir a Password Generator

Gracias por tu interés en contribuir.

Este documento define un flujo simple para mantener calidad, coherencia y
facilidad de mantenimiento.

## Requisitos

- Python 3.13+
- Entorno virtual activo
- Dependencias de desarrollo instaladas:

```powershell
pip install -e ".[dev]"
```

## Flujo recomendado

1. Sincroniza `main`.
2. Crea una rama con nombre claro:
   - `feat/<descripcion-corta>`
   - `fix/<descripcion-corta>`
   - `docs/<descripcion-corta>`
3. Realiza cambios pequeños y enfocados.
4. Añade o actualiza pruebas cuando aplique.
5. Ejecuta validaciones locales antes del commit.

## Validaciones obligatorias

```powershell
python -m mypy password_generator
python -m pytest
```

## Estilo de commits

Recomendaciones:

- Usa mensajes en imperativo.
- Explica el **por qué** en el cuerpo si el cambio no es trivial.
- Evita mezclar refactor + feature + docs en el mismo commit.

Ejemplos:

- `Añade soporte de icono en assets.`
- `Corrige resolución de rutas en build spec.`
- `Documenta estructura y flujo de contribución.`

## Pull Requests

Incluye en la PR:

- Resumen corto de cambios.
- Alcance (qué toca y qué no toca).
- Resultado de pruebas (`mypy`, `pytest`).
- Capturas si hay cambios de UI.

Checklist sugerido:

- [ ] El código compila/ejecuta sin errores.
- [ ] Pruebas pasando.
- [ ] No se incluyen secretos ni archivos locales.
- [ ] Documentación actualizada si aplica.

## Qué se considera una buena contribución

- Corrección de bugs con prueba de regresión.
- Mejoras de DX (build, tests, tooling).
- Mejoras de UI/UX coherentes con el estilo actual.
- Documentación precisa y accionable.

## Reporte de bugs

Al abrir un issue, incluye:

- Sistema operativo y versión de Python.
- Pasos para reproducir.
- Resultado esperado vs actual.
- Traceback/log si existe.

## Seguridad

No publiques credenciales ni datos sensibles.

Para reportes de seguridad, evita detalles explotables en público hasta
que exista mitigación.
