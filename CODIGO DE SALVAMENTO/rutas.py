import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import networkx as nx
import math
import os
import json
from PIL import Image, ImageTk

# ------------------ PATH ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAP_IMAGE = os.path.join(BASE_DIR, "mapa_venezuela.png")
SETTINGS_FILE = os.path.join(BASE_DIR, "map_settings.json")
NODES_FILE = os.path.join(BASE_DIR, "node_positions.json")

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
COLOR_PATH = "#FFD369"      

# ------------------ GRAFO ------------------
G = nx.Graph()

original_cities = {
    "Caracas": [420, 260], "Puerto Ayacucho": [500, 450], "Barcelona": [520, 300],
    "San Fernando de Apure": [380, 380], "Maracay": [380, 290], "Barinas": [320, 380],
    "Ciudad Bolívar": [580, 380], "Valencia": [360, 300], "San Carlos": [350, 320],
    "Tucupita": [650, 350], "Coro": [240, 200], "San Juan de los Morros": [400, 320],
    "Barquisimeto": [300, 340], "Mérida": [240, 400], "Los Teques": [410, 270],
    "Maturín": [580, 320], "La Asunción": [490, 180], "Guanare": [320, 320],
    "Cumaná": [550, 250], "San Cristóbal": [280, 450], "Trujillo": [270, 350],
    "La Guaira": [430, 250], "San Felipe": [340, 310], "Maracaibo": [180, 140],
}

roads = [
    ("Caracas", "La Guaira"), ("Caracas", "Los Teques"), ("Caracas", "Valencia"),
    ("Caracas", "Maracay"), ("Caracas", "San Juan de los Morros"), ("Caracas", "Barcelona"),
    ("Valencia", "Maracay"), ("Valencia", "San Carlos"), ("Valencia", "San Felipe"),
    ("Valencia", "Barquisimeto"), ("Valencia", "San Juan de los Morros"), ("Maracay", "San Carlos"),
    ("Maracay", "San Felipe"), ("Maracay", "Los Teques"), ("Maracaibo", "Coro"),
    ("Maracaibo", "Barquisimeto"), ("Coro", "Barquisimeto"), ("Barquisimeto", "Mérida"),
    ("Barquisimeto", "Guanare"), ("Barquisimeto", "Trujillo"), ("Mérida", "San Cristóbal"),
    ("Mérida", "Trujillo"), ("Mérida", "Barinas"), ("San Cristóbal", "Barinas"),
    ("Trujillo", "Guanare"), ("San Fernando de Apure", "Barinas"), ("San Fernando de Apure", "San Juan de los Morros"),
    ("San Fernando de Apure", "Guanare"), ("San Fernando de Apure", "Puerto Ayacucho"),
    ("Barcelona", "Maturín"), ("Barcelona", "Ciudad Bolívar"), ("Barcelona", "Cumaná"),
    ("Maturín", "Ciudad Bolívar"), ("Maturín", "Cumaná"), ("Ciudad Bolívar", "Tucupita"),
    ("Cumaná", "La Asunción"), ("Puerto Ayacucho", "Ciudad Bolívar"), ("Puerto Ayacucho", "San Fernando de Apure"),
]

# ------------------ ESTADO ------------------
zoom = 0.41
pan_x, pan_y = 50, 20
ZOOM_MIN, ZOOM_MAX = 0.4, 2.5
original_image = None
map_img = None
map_width = map_height = 0
current_path = current_start = current_end = None

# ------------------ LÓGICA ------------------
def distance(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])

def update_weights():
    for a, b in roads:
        x1, y1 = transform_coords(*original_cities[a])
        x2, y2 = transform_coords(*original_cities[b])
        G[a][b]["weight"] = distance((x1, y1), (x2, y2))

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

def save_node_positions():
    try:
        data = {c: {"x": float(p[0]), "y": float(p[1])} for c, p in original_cities.items()}
        with open(NODES_FILE, 'w') as f: json.dump(data, f, indent=4)
    except: pass

def load_node_positions():
    if os.path.exists(NODES_FILE):
        try:
            with open(NODES_FILE, 'r') as f:
                data = json.load(f)
                for c, p in data.items():
                    if c in original_cities: original_cities[c] = [p["x"], p["y"]]
        except: pass

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

# ------------------ DIBUJO ------------------
def redraw():
    canvas.delete("all")
    if map_img:
        ix, iy = pan_x + (CANVAS_WIDTH - map_img.width()) // 2, pan_y + (CANVAS_HEIGHT - map_img.height()) // 2
        canvas.create_image(ix, iy, image=map_img, anchor="nw")
    
    for a, b in roads:
        x1, y1 = transform_coords(*original_cities[a])
        x2, y2 = transform_coords(*original_cities[b])
        canvas.create_line(x1, y1, x2, y2, fill=COLOR_ROAD, width=2)
    
    for city, (ox, oy) in original_cities.items():
        x, y = transform_coords(ox, oy)
        r = max(4, min(NODE_RADIUS * zoom, 10))
        canvas.create_oval(x-r, y-r, x+r, y+r, fill="#E21717", outline="white", width=1)
        
        if zoom > 0.35:
            f_size = int(9*zoom+5)
            # Dibujar sombra/contorno blanco para que el negro resalte
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                canvas.create_text(x+dx, y-r-10+dy, text=city, fill="white", font=("Segoe UI", f_size, "bold"))
            # Texto principal en NEGRO
            canvas.create_text(x, y-r-10, text=city, fill="black", font=("Segoe UI", f_size, "bold"))

    if current_path: draw_path()

def draw_path():
    for i in range(len(current_path) - 1):
        x1, y1 = transform_coords(*original_cities[current_path[i]])
        x2, y2 = transform_coords(*original_cities[current_path[i+1]])
        canvas.create_line(x1, y1, x2, y2, fill=COLOR_PATH, width=5, capstyle="round")
    
    for c, col in [(current_start, "#2ecc71"), (current_end, "#e74c3c")]:
        x, y = transform_coords(*original_cities[c])
        canvas.create_oval(x-10, y-10, x+10, y+10, outline=col, width=3)

# ------------------ ACCIONES ------------------
def find_path():
    global current_path, current_start, current_end
    s, e = start_var.get(), end_var.get()
    if s and e and s != e:
        try:
            update_weights()
            path = nx.dijkstra_path(G, s, e, weight="weight")
            current_path, current_start, current_end = path, s, e
            path_info.set(f"Ruta: {' → '.join(path)}")
            redraw()
        except: messagebox.showerror("Error", "Ruta no encontrada")
    else: messagebox.showwarning("Aviso", "Seleccione ciudades distintas")

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

# ------------------ INTERFAZ ------------------
root = tk.Tk()
root.title("Sistema de Rutas Venezuela")
root.geometry("1150x700")
root.configure(bg=COLOR_BG)

style = ttk.Style()
style.theme_use('clam')
style.configure("TFrame", background=COLOR_SIDEBAR)
style.configure("TLabel", background=COLOR_SIDEBAR, foreground=COLOR_TEXT, font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 10, "bold"))

sidebar = ttk.Frame(root, width=280, padding=20)
sidebar.pack(side="left", fill="y")

ttk.Label(sidebar, text="NAVEGACIÓN", font=("Segoe UI", 14, "bold"), foreground=COLOR_ACCENT).pack(pady=(0,25))

ttk.Label(sidebar, text="Origen:").pack(anchor="w")
start_var = tk.StringVar()
cb_start = ttk.Combobox(sidebar, textvariable=start_var, values=sorted(list(original_cities.keys())), state="readonly")
cb_start.pack(fill="x", pady=(5, 15))
cb_start.set("Caracas")

ttk.Label(sidebar, text="Destino:").pack(anchor="w")
end_var = tk.StringVar()
cb_end = ttk.Combobox(sidebar, textvariable=end_var, values=sorted(list(original_cities.keys())), state="readonly")
cb_end.pack(fill="x", pady=(5, 25))
cb_end.set("Maracaibo")

ttk.Button(sidebar, text="CALCULAR RUTA", command=find_path).pack(fill="x", ipady=10)

# Panel de información inferior
info_frame = tk.Frame(root, bg=COLOR_BG, height=40)
info_frame.pack(side="bottom", fill="x", padx=10, pady=5)
path_info = tk.StringVar(value="Usa el botón derecho para mover el mapa y la rueda para el zoom")
tk.Label(info_frame, textvariable=path_info, bg=COLOR_BG, fg=COLOR_ACCENT, font=("Segoe UI", 10, "italic")).pack(side="left")

canvas = tk.Canvas(root, bg="#F0F0F0", highlightthickness=0)
canvas.pack(side="right", fill="both", expand=True)

# --- INICIO ---
try:
    original_image = Image.open(MAP_IMAGE)
    map_width, map_height = original_image.width, original_image.height
    map_img = resize_map_image()
except: pass

load_node_positions()
for c in original_cities: G.add_node(c)
for a, b in roads: G.add_edge(a, b)

# Eventos
canvas.bind("<MouseWheel>", do_zoom)
canvas.bind("<Button-3>", lambda e: globals().update(pan_start=(e.x, e.y)))
canvas.bind("<B3-Motion>", lambda e: [globals().update(pan_x=pan_x+(e.x-pan_start[0]), pan_y=pan_y+(e.y-pan_start[1]), pan_start=(e.x,e.y)), constrain_pan(), redraw()])

drag_city = None
def press_node(e):
    global drag_city, drag_off
    for c, p in original_cities.items():
        sx, sy = transform_coords(*p)
        if math.hypot(e.x-sx, e.y-sy) < 15:
            drag_city = c
            drag_off = (e.x-sx, e.y-sy)
            return

canvas.bind("<Button-1>", press_node)
canvas.bind("<B1-Motion>", lambda e: [original_cities.update({drag_city: list(inverse_transform_coords(e.x-drag_off[0], e.y-drag_off[1]))}) if drag_city else None, redraw()])
canvas.bind("<ButtonRelease-1>", lambda e: [save_node_positions(), update_weights(), redraw(), globals().update(drag_city=None)])

redraw()
root.mainloop()