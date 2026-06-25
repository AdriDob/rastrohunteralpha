def endpoint_analysis_prompt(path: str, method: str, params: dict) -> str:
    return (
        f"Actúa como un analista senior de seguridad API."
        f"\nEndpoint: {method} {path}"
        f"\nParámetros: {params}"
        f"\nDescribe señales de riesgo de autorización, IDOR, multi-tenant o exportación. "
        f"Mantén el estilo conciso, profesional y basado en evidencia. "
        f"No inventes exploits ni payloads."
    )
