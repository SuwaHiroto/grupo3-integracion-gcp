import datetime
import os
import uuid
from dotenv import load_dotenv
from google.cloud import firestore, storage

# 1. Cargar variables de entorno desde el archivo .env local
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "(default)")
COLLECTION_NAME = os.getenv("FIRESTORE_COLLECTION", "productos")
CREDS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not PROJECT_ID or not BUCKET_NAME:
    raise ValueError("Faltan variables en .env (GCP_PROJECT_ID o GCS_BUCKET_NAME).")
if not CREDS_PATH or not os.path.exists(CREDS_PATH):
    raise FileNotFoundError(
        f"No se encontró el archivo de credenciales JSON en: {CREDS_PATH}"
    )

# 2. Inicializar clientes oficiales de Google Cloud (Cloud Storage + Firestore)
storage_client = storage.Client(project=PROJECT_ID)
firestore_client = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DATABASE)
bucket = storage_client.bucket(BUCKET_NAME)


def registrar_producto_con_imagen(
    nombre: str, precio: float, categoria: str, ruta_local: str
) -> dict:
    """
    Flujo de integración (persistencia políglota + patrón de referencia):
    1) Sube la imagen al bucket privado de Cloud Storage.
    2) Obtiene la clave única del objeto.
    3) Registra metadatos y clave en Cloud Firestore (con rollback ante fallos).
    4) Genera URL directa (denegada) y URL firmada V4 (temporal 15 min).
    """
    if not os.path.exists(ruta_local):
        raise FileNotFoundError(f"No se encontró la imagen local: {ruta_local}")

    producto_id = str(uuid.uuid4())
    extension = os.path.splitext(ruta_local)[1].lower()
    anio_actual = datetime.datetime.now(datetime.timezone.utc).year
    clave_objeto = f"productos/{anio_actual}/{producto_id}{extension}"

    # Paso 1: Subir el archivo binario al bucket privado (Componente A)
    blob = bucket.blob(clave_objeto)
    content_type = "image/png" if extension == ".png" else "image/jpeg"
    blob.upload_from_filename(ruta_local, content_type=content_type)
    print(f"[OK - Storage]   Archivo subido con clave: {clave_objeto}")

    # Paso 2: Preparar documento con la clave del objeto (NO la URL firmada)
    registro = {
        "producto_id": producto_id,
        "nombre": nombre,
        "precio": float(precio),
        "categoria": categoria,
        "clave_archivo": clave_objeto,
        "tipo_archivo": content_type,
        "fecha_registro": datetime.datetime.now(datetime.timezone.utc),
    }

    # Paso 3: Guardar en Firestore (Componente B) con prevención de huérfanos
    try:
        doc_ref = firestore_client.collection(COLLECTION_NAME).document(producto_id)
        doc_ref.set(registro)
        print(
            f"[OK - Firestore] Registro guardado en '{FIRESTORE_DATABASE}/{COLLECTION_NAME}' | ID: {producto_id}"
        )
    except Exception as error_bd:
        print(f"[ERROR - Firestore] Falló la escritura en la base de datos: {error_bd}")
        print("[ROLLBACK] Eliminando archivo huérfano del bucket...")
        blob.delete()
        raise

    # Paso 4: URL directa (para prueba denegada) y URL firmada V4 (válida 15 min)
    url_directa = f"https://storage.googleapis.com/{BUCKET_NAME}/{clave_objeto}"
    url_firmada = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=15),
        method="GET",
    )

    return {
        "producto_id": producto_id,
        "clave_archivo": clave_objeto,
        "url_directa": url_directa,
        "url_firmada": url_firmada,
    }


if __name__ == "__main__":
    productos_prueba = [
        {
            "nombre": "Poncho Tejido de Alpaca",
            "precio": 185.50,
            "categoria": "Textilería",
            "ruta_local": "imagenes/poncho_alpaca.jpg",
        },
        {
            "nombre": "Torito de Pucará Decorativo",
            "precio": 65.00,
            "categoria": "Cerámica",
            "ruta_local": "imagenes/torito_pucara.jpg",
        },
        {
            "nombre": "Retablo Andino Artesanal",
            "precio": 140.00,
            "categoria": "Tallado y Escultura",
            "ruta_local": "imagenes/retablo_andino.jpg",
        },
    ]

    print("=== Iniciando flujo integrado Cloud Storage + Firestore ===\n")
    for item in productos_prueba:
        resultado = registrar_producto_con_imagen(**item)
        print(f"Producto: {item['nombre']}")
        print(f"  -> Clave en Storage / Firestore : {resultado['clave_archivo']}")
        print(f"  -> URL directa (prueba denegada): {resultado['url_directa']}")
        print(f"  -> URL firmada (válida 15 min)  : {resultado['url_firmada']}\n")
    print("=== Flujo completado exitosamente ===")