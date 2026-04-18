# Arquitectura del paquete

`password_generator/` contiene el código de aplicación.

## Módulos

- `ui.py`: interfaz Tkinter y eventos de usuario.
- `core.py`: motor de generación de combinaciones.
- `infra.py`: persistencia de configuración y carga de diccionarios.
- `security.py`: utilidades de entropía y políticas mínimas.
- `clipboard.py`: gestión de copiado y limpieza de portapapeles.
- `models.py`: contratos tipados y dataclasses.
- `defaults.py`: listas embebidas por defecto.
- `__main__.py`: entrada por `python -m password_generator`.

## Principios

- Separación clara entre UI, dominio e infraestructura.
- Tipado estático progresivo.
- Componentes reutilizables y testeables.
