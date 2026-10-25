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
- Retos ecológicos continuos, sin metas que bloqueen nuevas recompensas.
- Cada acción nueva otorga puntos y experiencia; el mismo envío no se acredita dos veces.
- Niveles y progreso consultables desde el tablero.
- Jardín virtual que evoluciona con las acciones y admite artículos colocados.
- Logros y distintivos persistentes que se desbloquean al alcanzar hitos.
- Tienda virtual con compras seguras con puntos e inventario por cuenta.
- Jardín y tienda en páginas independientes: `/jardin` y `/tienda`.
- Avisos animados al recibir recompensas y subir de nivel, respetando movimiento reducido.
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
│   ├── progression.py
│   └── routes.py
├── database/
│   └── neon_schema.sql
├── tests/
│   └── test_gamification.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── registro.html
│   ├── index.html
│   ├── jardin.html
│   ├── tienda.html
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
4. Reinicia la aplicación. Al iniciar, crea de forma segura las tablas que falten para usuarios, acciones, misiones y progreso. La actualización no borra usuarios ni acciones existentes.

En PowerShell, para una sesión local:

```powershell
$env:DATABASE_URL="postgresql://USUARIO:CONTRASENA@HOST/BASE?sslmode=require"
$env:SECRET_KEY="una-clave-larga-y-aleatoria"
python run.py
```

Sustituye el ejemplo por la URL real de tu base; no compartas esa URL ni la incluyas en capturas.

### Tabla `acciones`

El proyecto conserva los campos principales indicados en la guía (`titulo`, `categoria`, `descripcion`, `propuesto_por`) y agrega `fecha`, `impacto` y `usuario_id` para las pantallas de referencia y para separar las acciones de cada cuenta.

Los retos ecológicos son continuos: cada acción nueva otorga puntos y experiencia (10 puntos y 15 XP por defecto), sin detener futuras recompensas. Puedes ajustar esos valores con las variables opcionales `ECO_ACTION_POINTS` y `ECO_ACTION_EXPERIENCE` en el entorno local o Render. Cada acreditación se vincula al ID único de la acción y se guarda en el historial del servidor; repetir el mismo envío no duplica el registro ni su premio. Los saldos y niveles se calculan en el servidor. El esquema repetible para Neon está en [`database/neon_schema.sql`](database/neon_schema.sql).

El jardín tiene cinco niveles de crecimiento: Semilla (0 acciones), Brote (3), Jardín en crecimiento (7), Jardín floreciente (12) y Jardín ecológico (20). Los umbrales y la cantidad de plantas de cada nivel se pueden ajustar en `GARDEN_LEVELS`, en `app/progression.py`. El progreso se deriva de acciones registradas y de su historial de recompensas idempotente, por usuario; las acciones repetidas no cuentan de nuevo y borrar una acción de la lista no hace retroceder el jardín. Al llegar al nivel máximo, el usuario sigue acumulando acciones y recompensas. No requiere tablas ni migraciones adicionales; las decoraciones guardadas no se modifican por el crecimiento automático. Los artículos de la tienda se compran con puntos, se conservan en el inventario y se pueden colocar en el jardín; una compra repetida con el mismo token no vuelve a descontar puntos. Los logros se guardan por usuario y se sincronizan también para cuentas con acciones previas. La inicialización local no elimina datos. La actualización de `database/neon_schema.sql` es solo un archivo de esquema para uso manual: no se ejecutó ni se conectó a Neon.

Las pruebas de gamificación se ejecutan con `python -m unittest discover -s tests -v`.
Al iniciar sesión, el tablero ofrece botones para abrir `/jardin` y `/tienda`; ambas páginas comparten las mismas funciones de inventario, artículos, puntos y compras.

Si prefieres crear las tablas manualmente, revisa y ejecuta el contenido completo de [`database/neon_schema.sql`](database/neon_schema.sql) en el SQL Editor de Neon. No ejecutes el esquema contra una base de producción sin respaldo y autorización.

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
