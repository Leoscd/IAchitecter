class AppError(Exception):
    """Base exception para la app."""


class ValidationError(AppError):
    """Input o output no cumple el schema."""


class TimeoutError(AppError):
    """Función superó el tiempo límite."""


class LogicError(AppError):
    """Error de lógica de negocio esperado."""


class SystemError(AppError):
    """Error inesperado del sistema."""


class DispatchError(AppError):
    """Tool call de MiniMax no está en whitelist o tiene params inválidos."""
