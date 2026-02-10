# 📍 GPS Venezuela - Buscador de Rutas (Algoritmo de Dijkstra)

Este es un proyecto universitario desarrollado para la **Universidad de Oriente (UDO)**. La aplicación es un sistema de información geográfica (SIG) simplificado que permite calcular la ruta más corta entre diferentes ciudades y puntos de control (waypoints) de Venezuela.

## 🎓 Información del Proyecto
* **Institución:** Universidad de Oriente (UDO)
* **Asignatura:** Estructura de Datos
* **Objetivo:** Implementación del Algoritmo de Dijkstra para la optimización de rutas en un grafo ponderado.

---

## 🚀 Características
* **Cálculo de Ruta Óptima:** Encuentra el camino más corto basado en la distancia real (kilómetros).
* **Visualización Dinámica:** Mapa interactivo de Venezuela donde se trazan las rutas en tiempo real.
* **Base de Datos Portable:** Almacenamiento de nodos y conexiones en archivos JSON dentro de la carpeta `utils/`.
* **Escalabilidad:** Soporte para más de 1900 waypoints y conexiones viales.

---

## 🛠️ Tecnologías Utilizadas
* **Python 3.14+**
* **NetworkX:** Para la gestión de grafos y ejecución del algoritmo de Dijkstra.
* **Pillow (PIL):** Para el procesamiento y renderizado del mapa de fondo.
* **Tkinter:** Para la interfaz gráfica de usuario (GUI).

---

## 📁 Estructura del Proyecto
```text
venezuela_routes/
├── main.py              # Archivo principal de la aplicación
├── utils/               # Recursos del sistema
│   ├── mapa_venezuela.png
│   ├── node_positions.json
│   └── roads_config.json
└── .gitignore           # Archivos omitidos en Git
