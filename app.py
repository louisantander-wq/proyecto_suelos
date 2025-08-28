import os
from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, Column, Integer, String, Float, exc
from sqlalchemy.orm import sessionmaker, declarative_base
from geoalchemy2 import Geography

# --- 1. Configuración Inicial ---
app = Flask(__name__)
# Se necesita una 'secret_key' para mostrar mensajes flash (notificaciones)
app.secret_key = os.environ.get('SECRET_KEY', 'una-llave-secreta-por-defecto')

# --- 2. Conexión a la Base de Datos de Render ---
# Render proporciona la URL de conexión a través de una variable de entorno para mayor seguridad.
db_uri = os.environ.get('DATABASE_URL')

# Pequeña modificación para asegurar la compatibilidad con SQLAlchemy v2
if db_uri and db_uri.startswith("postgres://"):
    db_uri = db_uri.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_uri)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 3. Definición del Modelo de Datos (la tabla en la base de datos) ---
class MuestraSuelo(Base):
    __tablename__ = "muestras" # Nombre de la tabla
    
    id = Column(Integer, primary_key=True, index=True)
    ubicacion_nombre = Column(String(200), nullable=False)
    # Usamos el tipo Geography de PostGIS para almacenar coordenadas de forma nativa.
    # SRID 4326 es el estándar para coordenadas geográficas (latitud/longitud).
    coordenadas = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    ph = Column(Float)
    plomo_ppm = Column(Float)
    arsenico_ppm = Column(Float)

# --- 4. Creación de la Tabla en la Base de Datos ---
# Esta línea intenta crear la tabla si no existe al iniciar la aplicación.
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Error al crear la tabla: {e}")

# --- 5. Rutas de la Aplicación Web (las URLs) ---

@app.route('/')
def index():
    """Esta función se ejecuta cuando alguien visita la página principal.
    Simplemente muestra el archivo index.html."""
    return render_template('index.html')

@app.route('/registrar', methods=['POST'])
def registrar_muestra():
    """Esta función se ejecuta cuando el usuario envía el formulario.
    Recibe los datos y los guarda en la base de datos."""
    db = SessionLocal()
    try:
        # Crea el formato de punto geográfico que PostGIS entiende: 'POINT(longitud latitud)'
        lat = request.form['latitud']
        lon = request.form['longitud']
        punto_wkt = f'POINT({lon} {lat})'

        # Crea un nuevo objeto 'MuestraSuelo' con los datos del formulario
        nueva_muestra = MuestraSuelo(
            ubicacion_nombre=request.form['ubicacion_nombre'],
            coordenadas=punto_wkt,
            ph=float(request.form['ph']),
            plomo_ppm=float(request.form['plomo_ppm']),
            arsenico_ppm=float(request.form['arsenico_ppm'])
        )
        
        # Agrega la nueva muestra a la sesión y la guarda en la base de datos
        db.add(nueva_muestra)
        db.commit()
        print("Muestra guardada exitosamente!")

    except exc.SQLAlchemyError as e:
        # Si ocurre un error con la base de datos, lo deshace y lo imprime
        db.rollback()
        print(f"Error al guardar en la base de datos: {e}")
    except ValueError:
        # Si los números no son válidos (ej. texto en vez de número)
        print("Error: Datos numéricos inválidos.")
    finally:
        # Cierra la conexión a la base de datos para liberar recursos
        db.close()
    
    # Redirige al usuario de vuelta a la página principal
    return redirect(url_for('index'))

# --- 6. Punto de Entrada para Ejecutar la Aplicación ---
# Render usará un servidor de producción como Gunicorn, pero esto es útil para pruebas locales.
if __name__ == '__main__':
    # El puerto se obtiene de una variable de entorno, estándar en plataformas cloud.
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)