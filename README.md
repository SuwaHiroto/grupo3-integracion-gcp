# Grupo 3 — Integración de Componentes de Almacenamiento en GCP

Módulo práctico en Python que aplica **persistencia políglota** y el **patrón de referencia de archivos** para el registro de productos de una tienda de artesanías, integrando **Google Cloud Storage** (bucket privado) y **Cloud Firestore** (base de datos NoSQL documental).

## Arquitectura del flujo
1. Sube la fotografía del producto artesanal al bucket privado de Cloud Storage.
2. Obtiene la clave única del objeto (`productos/2026/<uuid>.jpg`) y genera una URL firmada temporal V4 (15 minutos).
3. Registra los metadatos y la `clave_archivo` en Cloud Firestore, aplicando eliminación compensatoria (`blob.delete()`) ante fallos para evitar archivos huérfanos.

El archivo fuente editable del diagrama de arquitectura se encuentra en `diagrama/arquitectura_grupo3.drawio`.

## Requisitos previos
- Python 3.10 o superior.
- Proyecto en Google Cloud Platform con **Cloud Storage** (bucket privado) y **Cloud Firestore** (Modo Nativo) habilitados.
- Cuenta de servicio IAM con permisos mínimos:
  - `roles/storage.objectUser` asignado exclusivamente sobre el bucket.
  - `roles/datastore.user` para operar sobre Firestore.

## Instalación y ejecución
1. Clonar el repositorio:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd grupo3-integracion-gcp