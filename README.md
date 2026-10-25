# Misión Eco-Reto 🌿

Aplicación web educativa para registrar y consultar acciones ecológicas. Está hecha con Python, Flask, Jinja2, HTML, CSS y JavaScript, y puede utilizar PostgreSQL en Neon para el despliegue en Render.

## Funciones incluidas

- Crear cuenta e iniciar/cerrar sesión.
- Contraseñas guardadas mediante hash, no en texto plano.
- Registrar acciones ecológicas.
- Consultar y buscar las acciones propias.
- Ver el detalle de una acción.
- Editar y eliminar registros con confirmación.
- Estadísticas básicas por categoría.
- Diseño adaptable a computadora y celular.
- PostgreSQL/Neon cuando existe `DATABASE_URL`.
- SQLite local automáticamente cuando no existe `DATABASE_URL`.

## Estructura

```text
EcoReto/
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── app/
│   ├── __init__.py
│   ├── db.py
│   └── routes.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── registro.html
│   ├── index.html
│   ├── formulario.html
│   ├── detalle.html
│   └── error.html
└── static/
    ├── css/estilos.css
    └── js/validacion.js
```

## Ejecutar en VS Code (modo local)

1. Instala Python 3.11 o posterior.
2. Abre esta carpeta en VS Code.
3. Crea y activa un entorno virtual:

   **Windows**
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   **macOS/Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
5. (Recomendado) define una clave secreta para la sesión. En PowerShell:
   ```powershell
   $env:SECRET_KEY="pon-aqui-una-clave-larga-y-aleatoria"
   ```
6. Inicia la aplicación:
   ```bash
   python run.py
   ```
7. Abre `http://127.0.0.1:5000` y crea una cuenta. En modo local, la base se crea en `instance/eco_reto.db`.

## Usar Neon PostgreSQL

1. Crea un proyecto en [Neon](https://neon.tech/).
2. Copia la cadena de conexión PostgreSQL desde el panel **Connect**.
3. Define la variable de entorno `DATABASE_URL` con esa cadena. No la escribas en el código ni la subas a GitHub.
4. Reinicia la aplicación. Al iniciar, crea las tablas `usuarios` y `acciones` si todavía no existen.

En PowerShell, para una sesión local:

```powershell
$env:DATABASE_URL="postgresql://USUARIO:CONTRASENA@HOST/BASE?sslmode=require"
$env:SECRET_KEY="una-clave-larga-y-aleatoria"
python run.py
```

Sustituye el ejemplo por la URL real de tu base; no compartas esa URL ni la incluyas en capturas.

### Tabla `acciones`

El proyecto conserva los campos principales indicados en la guía (`titulo`, `categoria`, `descripcion`, `propuesto_por`) y agrega `fecha`, `impacto` y `usuario_id` para las pantallas de referencia y para separar las acciones de cada cuenta.

Si prefieres crear las tablas manualmente en el SQL Editor de Neon, puedes ejecutar:

```sql
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS acciones (
    id BIGSERIAL PRIMARY KEY,
    titulo VARCHAR(80) NOT NULL,
    categoria VARCHAR(40) NOT NULL,
    descripcion TEXT NOT NULL,
    propuesto_por VARCHAR(100) NOT NULL,
    fecha DATE,
    impacto VARCHAR(100) DEFAULT '',
    usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Publicar con GitHub y Render

1. Sube a GitHub los archivos del proyecto. `.gitignore` excluye `.env`, bases locales y archivos temporales.
2. En Render, crea un **Web Service** conectado al repositorio.
3. Configura:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn run:app`
4. En **Environment**, agrega:
   - `DATABASE_URL` = cadena de conexión de Neon.
   - `SECRET_KEY` = una clave secreta larga y aleatoria.
5. Guarda y espera a que Render termine el despliegue.
6. Abre la URL pública y prueba registro, inicio de sesión y todas las operaciones CRUD.
7. En Neon SQL Editor, ejecuta `SELECT * FROM acciones ORDER BY id DESC;` para comprobar los registros.

No subas credenciales, tokens ni la cadena de conexión a GitHub.

## Pruebas recomendadas

- [ ] Crear una cuenta.
- [ ] Iniciar sesión y cerrar sesión.
- [ ] Crear una acción.
- [ ] Consultar el listado y buscar una acción.
- [ ] Abrir los detalles.
- [ ] Editar la acción.
- [ ] Eliminar una acción de prueba.
- [ ] Confirmar que los registros creados desde Render aparecen en Neon.
- [ ] Volver a abrir la URL y verificar la persistencia.

## Notas

- Este proyecto es una base funcional para que puedas estudiar y mejorar el diseño y las funciones poco a poco.
- El formulario de registro no tiene verificación por correo ni recuperación de contraseña.
- La estadística muestra cantidades por categoría; no calcula equivalencias reales de CO₂ o litros ahorrados.
- Para producción real conviene agregar protección CSRF, límites de intentos de inicio de sesión, pruebas automatizadas y una política de privacidad.
