import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import networkx as nx
import math
import os
import json
from PIL import Image, ImageTk
import sys
import datetime
import heapq
import time
from data.ciudades import original_cities, waypoints, all_nodes, distance, distance_between_nodes

# ------------------ PATH ------------------

# 1. Carpeta principal donde está main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Carpeta de utilidades
UTILS_DIR = os.path.join(BASE_DIR, "utils")

# 3. Definimos las rutas apuntando ADENTRO de utils
MAP_IMAGE = os.path.join(UTILS_DIR, "mapa_venezuela.png")
NODES_FILE = os.path.join(UTILS_DIR, "node_positions.json")
ROADS_FILE = os.path.join(UTILS_DIR, "roads_config.json")

# ------------------ CONFIG ------------------
NODE_RADIUS = 7
ZOOM_STEP = 1.1
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 650
COLOR_BG = "#121212"        
COLOR_SIDEBAR = "#1e1e1e"   
COLOR_ACCENT = "#00ADB5"    
COLOR_TEXT = "#EEEEEE"      
COLOR_ROAD = "#393E46"      
COLOR_PATH = "#3498db"      
COLOR_WAYPOINT = "#2ecc71"
COLOR_CITY = "#E21717"
COLOR_SELECTED = "#f39c12"
COLOR_DRAWING = "#e74c3c"  
COLOR_AUTO_ROAD = "#27ae60"

# ------------------ GRAFO ------------------
G = nx.Graph()

# ------------------ RUTAS INICIALES (VACÍAS) ------------------
roads = []

# ------------------ ESTADO ------------------
zoom = 0.41
pan_x, pan_y = 50, 20
ZOOM_MIN, ZOOM_MAX = 0.4, 2.5
original_image = None
map_img = None
map_width = map_height = 0
current_path = current_start = current_end = None
show_waypoints = True
show_roads = True
edit_mode = False
draw_mode = False
selected_node = None
dragging = False
drag_start = (0, 0)

# ------------------ LÓGICA ------------------
def update_weights():
    G.clear()
    for node in all_nodes.keys():
        G.add_node(node)
    
    ESCALA_KM = 7.0  
    
    for a, b in roads:
        if a in all_nodes and b in all_nodes:
            x1, y1 = all_nodes[a]
            x2, y2 = all_nodes[b]
            
            # Calculamos la distancia en píxeles
            dist_pixeles = math.hypot(x2 - x1, y2 - y1)
            
            # LA MAGIA: Convertimos píxeles a kilómetros reales
            dist_km = dist_pixeles * ESCALA_KM
            
            G.add_edge(a, b, weight=dist_km)
    G.clear()
    for node in all_nodes.keys():
        G.add_node(node)
    
    for a, b in roads:
        if a in all_nodes and b in all_nodes:
            x1, y1 = transform_coords(*all_nodes[a])
            x2, y2 = transform_coords(*all_nodes[b])
            dist = distance((x1, y1), (x2, y2))
            G.add_edge(a, b, weight=dist)

def transform_coords(x, y):
    x_z, y_z = x * zoom, y * zoom
    iw, ih = map_width * zoom, map_height * zoom
    return pan_x + (CANVAS_WIDTH - iw) // 2 + x_z, pan_y + (CANVAS_HEIGHT - ih) // 2 + y_z

def inverse_transform_coords(sx, sy):
    iw, ih = map_width * zoom, map_height * zoom
    mx, my = pan_x + (CANVAS_WIDTH - iw) // 2, pan_y + (CANVAS_HEIGHT - ih) // 2
    return (sx - mx) / zoom if zoom > 0 else 0, (sy - my) / zoom if zoom > 0 else 0

def resize_map_image():
    if original_image:
        nw, nh = int(original_image.width * zoom), int(original_image.height * zoom)
        return ImageTk.PhotoImage(original_image.resize((nw, nh), Image.Resampling.LANCZOS))
    return None

def load_configuration():
    """Carga la configuración guardada desde la carpeta utils"""
    global waypoints, roads, all_nodes
    
    try:
        # 1. Limpiar datos actuales para cargar lo nuevo
        waypoints.clear()
        roads.clear()
        
        # 2. Cargar Posiciones de Nodos (Ciudades y Waypoints)
        if os.path.exists(NODES_FILE):
            with open(NODES_FILE, 'r') as f:
                nodes_data = json.load(f)
        
            for city in original_cities:
                if city in nodes_data:
                    original_cities[city] = [nodes_data[city]["x"], nodes_data[city]["y"]]
            
            for node, data in nodes_data.items():
                pos = [data["x"], data["y"]]
                if data.get("type") == "waypoint":
                    waypoints[node] = pos
        
        # 3. Cargar Carreteras (Conexiones)
        if os.path.exists(ROADS_FILE):
            with open(ROADS_FILE, 'r') as f:
                roads_data = json.load(f)
            roads = roads_data.get("roads", [])
        
        # 4. Reconstruir el diccionario total de nodos
        all_nodes = {**original_cities, **waypoints}
        
        # 5. IMPORTANTE: Actualizar el grafo G y pesos
        update_weights()
        
        print(f"Configuración cargada: {len(waypoints)} waypoints, {len(roads)} rutas")
        if 'Maracaibo' in original_cities:
            print(f"Maracaibo ubicado en: {original_cities['Maracaibo']}")
        
    except Exception as e:
        print(f"Error cargando los archivos: {e}")

def constrain_pan():
    global pan_x, pan_y
    if not original_image: return
    iw, ih = map_width * zoom, map_height * zoom
    if iw >= CANVAS_WIDTH:
        lim = (iw - CANVAS_WIDTH) // 2
        pan_x = max(-lim, min(lim, pan_x))
    else: pan_x = (CANVAS_WIDTH - iw) // 2
    if ih >= CANVAS_HEIGHT:
        lim = (ih - CANVAS_HEIGHT) // 2
        pan_y = max(-lim, min(lim, pan_y))
    else: pan_y = (CANVAS_HEIGHT - ih) // 2

def toggle_waypoints():
    global show_waypoints
    show_waypoints = not show_waypoints
    waypoint_btn.config(text="OCULTAR WAYPOINTS" if show_waypoints else "MOSTRAR WAYPOINTS")
    redraw()

def toggle_roads():
    global show_roads
    show_roads = not show_roads
    road_btn.config(text="OCULTAR CARRETERAS" if show_roads else "MOSTRAR CARRETERAS")
    redraw()


def start_drawing_from_node(node_name, x, y):
    """Comienza a dibujar desde un nodo existente"""
    global draw_start_node, drawing_points, last_draw_point
    
    if node_name:
        draw_start_node = node_name
        drawing_points = [(x, y)]
        last_draw_point = (x, y)
        path_info.set(f"Dibujando desde {node_name}... arrastra para continuar")
        return True
    return False

def add_drawing_point(x, y):
    """Agrega un punto al dibujo en curso"""
    global drawing_points, last_draw_point, drawing_line_id
    
    if last_draw_point and distance(last_draw_point, (x, y)) < 15:
        return False
    
    drawing_points.append((x, y))
    last_draw_point = (x, y)
    
    # Dibujar línea temporal
    if len(drawing_points) >= 2:
        if drawing_line_id:
            canvas.delete(drawing_line_id)
        drawing_line_id = canvas.create_line(
            drawing_points, fill=COLOR_DRAWING, width=4, 
            dash=(10, 5), capstyle="round", smooth=True
        )
    return True

def save_snapshot(action_name):
    """Guarda un snapshot del estado actual"""
    snapshot = {
        "waypoints": waypoints.copy(),
        "roads": roads.copy(),
        "all_nodes": all_nodes.copy(),
        "action": action_name,
        "timestamp": datetime.datetime.now()
    }
    return snapshot

def restore_snapshot(snapshot):
    """Restaura un snapshot del estado"""
    global waypoints, roads, all_nodes
    
    waypoints = snapshot["waypoints"].copy()
    roads = snapshot["roads"].copy()
    all_nodes = snapshot["all_nodes"].copy()
    
    # Actualizar datos
    update_weights()
    waypoint_count.set(f"📍 Waypoints: {len(waypoints)}")
    road_count.set(f"🛣️  Rutas: {len(roads)}")
    redraw()

# ------------------ ALGORITMOS DE CONEXIÓN AUTOMÁTICA ------------------
def find_nearest_waypoint(city_name, max_distance=100):
    """Encuentra el waypoint más cercano a una ciudad"""
    if city_name not in original_cities:
        return None
    
    city_pos = original_cities[city_name]
    nearest = None
    min_dist = float('inf')
    
    for wp_name, wp_pos in waypoints.items():
        dist = distance(city_pos, wp_pos)
        if dist < min_dist and dist < max_distance:
            min_dist = dist
            nearest = wp_name
    
    return nearest, min_dist if nearest else None

def connect_cities_to_nearest_waypoints(max_distance=80):
    """Conecta cada ciudad a su waypoint más cercano"""
    global roads
    
    # Guardar estado antes de la acción
    old_roads = roads.copy()
    
    connections_made = 0
    for city in original_cities.keys():
        nearest_wp, dist = find_nearest_waypoint(city, max_distance)
        if nearest_wp and dist is not None:
            # Verificar si la conexión ya existe
            if (city, nearest_wp) not in roads and (nearest_wp, city) not in roads:
                roads.append((city, nearest_wp))
                connections_made += 1
                print(f"Conectado: {city} -> {nearest_wp} (distancia: {dist:.1f})")
    
    update_weights()
    
    if connections_made > 0:
        # Guardar en historial
        history.add_action("auto_connect_cities", {
            "old_roads": old_roads,
            "new_roads": roads.copy(),
            "connections_made": connections_made
        })
    
    return connections_made

def find_k_nearest_neighbors(node, k=3, node_type="all", max_distance=150):
    """Encuentra los k vecinos más cercanos a un nodo"""
    if node not in all_nodes:
        return []
    
    node_pos = all_nodes[node]
    neighbors = []
    
    for other_node, other_pos in all_nodes.items():
        if other_node == node:
            continue
        
        # Filtrar por tipo si es necesario
        if node_type == "city" and other_node not in original_cities:
            continue
        elif node_type == "waypoint" and other_node not in waypoints:
            continue
        
        dist = distance(node_pos, other_pos)
        if dist < max_distance:
            neighbors.append((dist, other_node))
    
    # Ordenar por distancia y tomar los k más cercanos
    neighbors.sort(key=lambda x: x[0])
    return neighbors[:k]

def connect_waypoints_to_neighbors(k=3, max_distance=120):
    """Conecta cada waypoint a sus k vecinos más cercanos"""
    global roads
    
    # Guardar estado antes de la acción
    old_roads = roads.copy()
    
    connections_made = 0
    for wp in waypoints.keys():
        neighbors = find_k_nearest_neighbors(wp, k, "waypoint", max_distance)
        for dist, neighbor in neighbors:
            # Verificar si la conexión ya existe
            if (wp, neighbor) not in roads and (neighbor, wp) not in roads:
                roads.append((wp, neighbor))
                connections_made += 1
    
    update_weights()
    
    if connections_made > 0:
        # Guardar en historial
        history.add_action("auto_connect_waypoints", {
            "old_roads": old_roads,
            "new_roads": roads.copy(),
            "connections_made": connections_made
        })
    
    return connections_made

def build_minimum_spanning_tree():
    """Construye un árbol de expansión mínimo para conectar todos los waypoints"""
    global roads
    
    if len(waypoints) < 2:
        return 0
    
    # Guardar estado antes de la acción
    old_roads = roads.copy()
    
    # Crear un grafo temporal solo con waypoints
    temp_graph = nx.Graph()
    
    # Agregar nodos
    for wp in waypoints.keys():
        temp_graph.add_node(wp)
    
    # Agregar aristas con peso de distancia
    waypoint_list = list(waypoints.keys())
    for i in range(len(waypoint_list)):
        for j in range(i + 1, len(waypoint_list)):
            wp1 = waypoint_list[i]
            wp2 = waypoint_list[j]
            dist = distance_between_nodes(wp1, wp2)
            if dist < 200:  # Solo conectar si están relativamente cerca
                temp_graph.add_edge(wp1, wp2, weight=dist)
    
    # Construir árbol de expansión mínimo
    try:
        mst = nx.minimum_spanning_tree(temp_graph)
        
        # Agregar las conexiones del MST a las rutas
        connections_made = 0
        for wp1, wp2 in mst.edges():
            if (wp1, wp2) not in roads and (wp2, wp1) not in roads:
                roads.append((wp1, wp2))
                connections_made += 1
        
        update_weights()
        
        if connections_made > 0:
            # Guardar en historial
            history.add_action("build_mst", {
                "old_roads": old_roads,
                "new_roads": roads.copy(),
                "connections_made": connections_made
            })
        
        return connections_made
    except:
        return 0

def smart_road_generation():
    """Generación inteligente de rutas siguiendo la lógica de carreteras"""
    global roads
    
    # Guardar estado antes de la acción
    old_roads = roads.copy()
    
    connections_made = 0
    
    # Paso 1: Conectar ciudades a waypoints cercanos
    connections_made += connect_cities_to_nearest_waypoints(max_distance=100)
    
    # Paso 2: Conectar waypoints entre sí (vecinos cercanos)
    connections_made += connect_waypoints_to_neighbors(k=3, max_distance=150)
    
    # Paso 3: Construir árbol de expansión mínimo para garantizar conectividad
    connections_made += build_minimum_spanning_tree()
    
    # Paso 4: Conectar ciudades principales entre sí si están relativamente cerca
    city_connections = 0
    city_list = list(original_cities.keys())
    for i in range(len(city_list)):
        for j in range(i + 1, len(city_list)):
            city1 = city_list[i]
            city2 = city_list[j]
            dist = distance_between_nodes(city1, city2)
            
            # Conectar ciudades si están relativamente cerca (ej: Caracas-La Guaira)
            if dist < 80:
                if (city1, city2) not in roads and (city2, city1) not in roads:
                    roads.append((city1, city2))
                    city_connections += 1
                    print(f"Conectadas ciudades cercanas: {city1} -> {city2}")
    
    connections_made += city_connections
    
    update_weights()
    
    if connections_made > 0:
        # Guardar en historial
        history.add_action("smart_generation", {
            "old_roads": old_roads,
            "new_roads": roads.copy(),
            "connections_made": connections_made,
            "city_connections": city_connections
        })
    
    return connections_made

def select_node_at(x, y):
    """Selecciona un nodo en las coordenadas de pantalla (x, y)"""
    global selected_node
    
    for node_name, pos in all_nodes.items():
        sx, sy = transform_coords(*pos)
        if math.hypot(x - sx, y - sy) < 15:
            return node_name
    return None

# ------------------ ALGORITMO DE RUTA (DIJKSTRA) ------------------
def find_path():
    global current_path, current_start, current_end
    
    s, e = start_var.get(), end_var.get()
    if s and e and s != e:
        try:
            # --- 1. LIMPIEZA TOTAL (Visual y de Memoria) ---
            current_path = None  # <--- ESTO ES LO MÁS IMPORTANTE
            canvas.delete("path_layer") # Borra la línea azul
            
            # Si tu función redraw() usa current_path, al ser None ya no dibujará nada
            redraw() 
            
            path_info.set("Iniciando nueva búsqueda...")
            root.update() 
            
            update_weights()
            
            if s not in G.nodes() or e not in G.nodes():
                messagebox.showerror("Error", "Ciudad no conectada.")
                return

            # --- 2. ANIMACIÓN DE EXPLORACIÓN ---
            nodes_to_animate = list(G.nodes())[:30] 
            for node in nodes_to_animate:
                if node in all_nodes:
                    x, y = transform_coords(*all_nodes[node])
                    flash = canvas.create_oval(x-6, y-6, x+6, y+6, fill="#FF9800", outline="white", width=2)
                    root.update_idletasks()
                    canvas.after(100, lambda f=flash: canvas.delete(f))
                    time.sleep(0.01)

            # --- 3. CÁLCULO Y DIBUJO ---
            path = nx.dijkstra_path(G, s, e, weight="weight")
            
            # NO asignamos a current_path todavía para que redraw() no la pinte antes de tiempo
            temp_dist = 0
            for i in range(len(path)-1):
                n1, n2 = path[i], path[i+1]
                x1, y1 = transform_coords(*all_nodes[n1])
                x2, y2 = transform_coords(*all_nodes[n2])
                
                # Dibujamos el tramo actual
                canvas.create_line(x1, y1, x2, y2, fill="#2196F3", width=5, tags="path_layer")
                
                temp_dist += distance(all_nodes[n1], all_nodes[n2])
                path_info.set(f"Trazando: {temp_dist:.0f} km")
                root.update()
                time.sleep(0.04)

            # --- 4. GUARDAR Y FINALIZAR ---
            # Ahora sí guardamos la ruta oficial
            current_path, current_start, current_end = path, s, e
            
            display_path = [n for n in path if n in original_cities]
            path_info.set(f"Ruta: {' → '.join(display_path)} | {temp_dist:.0f} km")
            
            # El redraw final pone los nombres de las ciudades por encima
            redraw() 

        except nx.NetworkXNoPath:
            messagebox.showerror("Error", "No hay conexión.")
        except Exception as ex:
            print(f"Error: {ex}")
    else:
        messagebox.showwarning("Aviso", "Seleccione ciudades distintas")
        
# ------------------ FUNCIONES DE DESHACER/REHACER ------------------
def undo_action(event=None):
    """Deshace la última acción"""
    if not history.can_undo():
        messagebox.showinfo("Deshacer", "No hay acciones para deshacer")
        return
    
    action = history.undo()
    if action:
        apply_undo_action(action)
        update_history_display()

def apply_redo_action(action):
    """Aplica la acción de rehacer"""
    global waypoints, roads, all_nodes
    
    action_type = action['type']
    data = action['data']
    
    if action_type == "create_road":
        # Rehacer creación de ruta
        roads.clear()
        roads.extend(data['new_roads'])
        path_info.set(f"Rehecho: Ruta {data['node1']} → {data['node2']}")
        
    elif action_type == "delete_road":
        # Rehacer eliminación de ruta
        roads.clear()
        roads.extend(data['new_roads'])
        path_info.set(f"Rehecho: Eliminación de ruta {data['deleted_road'][0]} → {data['deleted_road'][1]}")
        
    elif action_type == "draw_road":
 
        waypoints = data['old_waypoints'].copy()
        roads = data['old_roads'].copy()
        all_nodes = data['old_all_nodes'].copy()
        
        # Luego recrear los waypoints y rutas
        previous_node = data['start_node']
        created_waypoints = []
        
        for i, wp_name in enumerate(data['created_waypoints']):
            
            if i < len(data['drawing_points']):
                x, y = data['drawing_points'][i]
                map_x, map_y = inverse_transform_coords(x, y)
                waypoints[wp_name] = [map_x, map_y]
                all_nodes[wp_name] = [map_x, map_y]
                created_waypoints.append(wp_name)
            
            # Recrear rutas
            if previous_node:
                roads.append((previous_node, wp_name))
                previous_node = wp_name
        
        if data['end_node'] and previous_node:
            roads.append((previous_node, data['end_node']))
        
        path_info.set(f"Rehecho: Carretera con {len(created_waypoints)} waypoints")
        
    elif action_type == "move_node":
        #movimiento de nodo
        node_name = data['node_name']
        all_nodes[node_name] = data['new_pos'].copy()
        if node_name in waypoints:
            waypoints[node_name] = data['new_pos'].copy()
        elif node_name in original_cities:
            original_cities[node_name] = data['new_pos'].copy()
        path_info.set(f"Rehecho: Movimiento de {node_name}")
        
    elif action_type == "load_config":
        #carga de configuración
        waypoints = data['new_waypoints'].copy()
        roads = data['new_roads'].copy()
        all_nodes = data['new_all_nodes'].copy()
        path_info.set(f"Rehecho: Carga de configuración")
    
    elif action_type in ["auto_connect_cities", "auto_connect_waypoints", "build_mst", "smart_generation"]:
        #conexiones automáticas
        roads.clear()
        roads.extend(data['new_roads'])
        path_info.set(f"Rehecho: Conexiones automáticas ({data.get('connections_made', 0)} rutas)")
        
    elif action_type == "delete_city_connections":
        #eliminación de conexiones de ciudad
        roads.clear()
        roads.extend(data['new_roads'])
        path_info.set(f"Rehecho: Eliminación de conexiones de {data['city']}")
        
    elif action_type == "delete_waypoint":
        #eliminación de waypoint
        waypoints = data['new_waypoints'].copy()
        roads = data['new_roads'].copy()
        all_nodes = data['new_all_nodes'].copy()
        path_info.set(f"Rehecho: Eliminación de waypoint {data['waypoint_name']}")
    
    update_weights()
    waypoint_count.set(f"📍 Waypoints: {len(waypoints)}")
    road_count.set(f"🛣️  Rutas: {len(roads)}")
    redraw()

def update_history_display():
    """Actualiza la información del historial en la interfaz"""
    undo_btn.config(state="normal" if history.can_undo() else "disabled")
    redo_btn.config(state="normal" if history.can_redo() else "disabled")
    
    # Actualizar información en la barra de estado
    history_info.set(f"Historial: {len(history.history)} acciones | Deshacer: {'✓' if history.can_undo() else '✗'} | Rehacer: {'✓' if history.can_redo() else '✗'}")

def clear_history():
    """Limpia el historial"""
    history.clear()
    update_history_display()
    path_info.set("Historial limpiado")

def redraw():
    canvas.delete("all")
    if map_img:
        ix, iy = pan_x + (CANVAS_WIDTH - map_img.width()) // 2, pan_y + (CANVAS_HEIGHT - map_img.height()) // 2
        canvas.create_image(ix, iy, image=map_img, anchor="nw")
    
    # Dibujar carreteras existentes
    if show_roads:
        for a, b in roads:
            if a in all_nodes and b in all_nodes:
                x1, y1 = transform_coords(*all_nodes[a])
                x2, y2 = transform_coords(*all_nodes[b])
                
                # Determinar color de la carretera
                road_color = COLOR_ROAD
                
                # Dibujar carretera
                canvas.create_line(x1, y1, x2, y2, 
                                 fill=road_color, width=4, capstyle="round")
    
    # Dibujar waypoints
    if show_waypoints:
        for wp_name, (ox, oy) in waypoints.items():
            x, y = transform_coords(ox, oy)
            r = max(3, min(NODE_RADIUS * zoom * 0.7, 8))
            
            # Waypoint seleccionado
            if selected_node == wp_name:
                canvas.create_oval(x-r-2, y-r-2, x+r+2, y+r+2, 
                                 fill=COLOR_SELECTED, outline="white", width=2)
            
            # Waypoint normal
            canvas.create_oval(x-r, y-r, x+r, y+r, 
                             fill=COLOR_WAYPOINT, outline="white", width=1)
    
    # Dibujar ciudades
    for city, (ox, oy) in original_cities.items():
        x, y = transform_coords(ox, oy)
        r = max(5, min(NODE_RADIUS * zoom, 12))
        
        # Ciudad seleccionada
        if selected_node == city:
            canvas.create_oval(x-r-3, y-r-3, x+r+3, y+r+3, 
                             fill=COLOR_SELECTED, outline="white", width=3)
        
        # Ciudad normal
        canvas.create_oval(x-r, y-r, x+r, y+r, 
                         fill=COLOR_CITY, outline="white", width=2)
        
        if zoom > 0.35:
            f_size = int(9*zoom+5)
           
            offset_y = y-r-10
           
            if city == "Maracaibo" and y < 50:
                offset_y = y + r + 15
            
            canvas.create_text(x+1, offset_y+1, text=city, 
                             fill="white", font=("Segoe UI", f_size, "bold"))
            canvas.create_text(x, offset_y, text=city, 
                             fill="black", font=("Segoe UI", f_size, "bold"))
    
    # Dibujar ruta calculada
    if current_path: 
        draw_path()

def draw_path():
    """Dibuja la ruta calculada EN COLOR AZUL para mejor visibilidad"""
    path_points = []
    
    # Recolectar puntos de la ruta
    for node in current_path:
        if node in all_nodes:
            x, y = transform_coords(*all_nodes[node])
            path_points.append((x, y))
    
    # Dibujar línea de ruta EN AZUL
    if len(path_points) >= 2:
        #dibujar una línea
        for i in range(len(path_points) - 1):
            x1, y1 = path_points[i]
            x2, y2 = path_points[i + 1]
            # Línea de fondo blanca
            canvas.create_line(x1, y1, x2, y2, 
                             fill="white", width=10, capstyle="round")
            # Línea principal AZUL
            canvas.create_line(x1, y1, x2, y2, 
                             fill=COLOR_PATH, width=8, capstyle="round")
    
    # Resaltar origen y destino
    for c, col in [(current_start, "#2ecc71"), (current_end, "#e74c3c")]:
        if c in all_nodes:
            x, y = transform_coords(*all_nodes[c])
            canvas.create_oval(x-15, y-15, x+15, y+15, 
                             fill=col, outline="white", width=4)
            # Texto para origen/destino
            label = "" if c == current_start else ""
            canvas.create_text(x, y-25, text=label, 
                             fill="white", font=("Segoe UI", 10, "bold"),
                             anchor="center")

# ------------------ MANEJADORES DE EVENTOS LIMPIOS ------------------

def on_canvas_click(event):
    global selected_node, dragging, drag_start
    
    # Intentar seleccionar una ciudad o waypoint para la ruta
    node = select_node_at(event.x, event.y)
    
    if node:
        selected_node = node
        path_info.set(f"Seleccionado: {node}")
        redraw()
    else:
        #permite arrastrar el mapa
        dragging = True
        drag_start = (event.x, event.y)
        selected_node = None
        redraw()

def on_canvas_drag(event):
    global pan_x, pan_y, dragging, drag_start
    
    # Permite mover el mapa de Venezuela
    if dragging:
        dx = event.x - drag_start[0]
        dy = event.y - drag_start[1]
        pan_x += dx
        pan_y += dy
        drag_start = (event.x, event.y)
        constrain_pan()
        redraw()

def on_canvas_release(event):
    global dragging
    dragging = False

def do_zoom(event):
    global zoom, pan_x, pan_y, map_img
    factor = ZOOM_STEP if event.delta > 0 else 1 / ZOOM_STEP
    ox, oy = inverse_transform_coords(event.x, event.y)
    new_z = max(ZOOM_MIN, min(ZOOM_MAX, zoom * factor))
    if new_z != zoom:
        zoom = new_z
        nx_s, ny_s = transform_coords(ox, oy)
        pan_x -= (nx_s - event.x)
        pan_y -= (ny_s - event.y)
        constrain_pan()
        map_img = resize_map_image()
        redraw()

# ------------------ INTERFAZ MEJORADA ------------------
root = tk.Tk()
root.title("Editor de Rutas Venezuela - Dijkstra Algorithm (Ruta en AZUL)")
root.geometry("1150x700")
root.configure(bg=COLOR_BG)

style = ttk.Style()
style.theme_use('clam')
style.configure("TFrame", background=COLOR_SIDEBAR)
style.configure("TLabel", background=COLOR_SIDEBAR, foreground=COLOR_TEXT, font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 10, "bold"))

sidebar = ttk.Frame(root, width=280, padding=20)
sidebar.pack(side="left", fill="y")

ttk.Label(sidebar, text="EDITOR DE RUTAS", 
          font=("Segoe UI", 14, "bold"), foreground=COLOR_ACCENT).pack(pady=(0,20))

ttk.Label(sidebar, text="Origen:").pack(anchor="w")
start_var = tk.StringVar()
cb_start = ttk.Combobox(sidebar, textvariable=start_var, 
                       values=sorted(list(original_cities.keys())), 
                       state="readonly", height=15)
cb_start.pack(fill="x", pady=(5, 15))
cb_start.set("Caracas")

ttk.Label(sidebar, text="Destino:").pack(anchor="w")
end_var = tk.StringVar()
cb_end = ttk.Combobox(sidebar, textvariable=end_var, 
                     values=sorted(list(original_cities.keys())), 
                     state="readonly", height=15)
cb_end.pack(fill="x", pady=(5, 20))
cb_end.set("Maracaibo")

# Botón para calcular ruta con información del algoritmo
ttk.Button(sidebar, text="🚗 CALCULAR RUTA (DIJKSTRA)", command=find_path).pack(fill="x", ipady=10, pady=(0, 10))

# Botones de control
waypoint_btn = ttk.Button(sidebar, text="OCULTAR WAYPOINTS", command=toggle_waypoints)
waypoint_btn.pack(fill="x", ipady=8, pady=(0, 5))

road_btn = ttk.Button(sidebar, text="OCULTAR CARRETERAS", command=toggle_roads)
road_btn.pack(fill="x", ipady=8, pady=(0, 5))

# Estadísticas
stats_frame = ttk.Frame(sidebar)
stats_frame.pack(fill="x", pady=(10, 0))

# Información del algoritmo
algorithm_label = tk.Label(stats_frame, text="", 
                          bg=COLOR_SIDEBAR, fg="#888", font=("Segoe UI", 9))
algorithm_label.pack(anchor="w", pady=(5, 0))

# Panel inferior
info_frame = tk.Frame(root, bg=COLOR_BG, height=40)
info_frame.pack(side="bottom", fill="x", padx=10, pady=5)
path_info = tk.StringVar(value="")
tk.Label(info_frame, textvariable=path_info, bg=COLOR_BG, fg=COLOR_PATH,  # Ahora usa COLOR_PATH (azul)
        font=("Segoe UI", 10, "bold")).pack(side="left")

# Canvas
canvas = tk.Canvas(root, bg="#F0F0F0", highlightthickness=0)
canvas.pack(side="right", fill="both", expand=True)

# --- INICIALIZACIÓN ---
try:
    original_image = Image.open(MAP_IMAGE)
    map_width, map_height = original_image.width, original_image.height
    map_img = resize_map_image()
    print(f"Mapa cargado: {map_width}x{map_height}")
    print(f"Waypoints cargados: {len(waypoints)}")
    print(f"Maracaibo ubicado en: {original_cities['Maracaibo']}")
except Exception as e:
    print(f"Error: {e}")
    messagebox.showerror("Error", f"No se pudo cargar el mapa: {e}")

# Cargar configuración si existe
load_configuration()
update_weights()


# Eventos del mouse
canvas.bind("<MouseWheel>", do_zoom)
canvas.bind("<Button-1>", on_canvas_click)
canvas.bind("<B1-Motion>", on_canvas_drag)
canvas.bind("<ButtonRelease-1>", on_canvas_release)
canvas.bind("<Button-3>", on_canvas_click)  # Click derecho

redraw()
root.mainloop()