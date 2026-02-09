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

# ------------------ PATH ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAP_IMAGE = os.path.join(BASE_DIR, "mapa_venezuela.png")

if sys.platform == "win32":
    APP_DATA = os.path.join(os.getenv('LOCALAPPDATA'), 'VenezuelaRoutes')
else:
    APP_DATA = os.path.join(os.path.expanduser('~'), '.venezuela_routes')

os.makedirs(APP_DATA, exist_ok=True)
NODES_FILE = os.path.join(APP_DATA, "node_positions.json")
ROADS_FILE = os.path.join(APP_DATA, "roads_config.json")

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
COLOR_PATH = "#3498db"      # CAMBIADO: De amarillo (#FFD369) a azul (#3498db) para mejor visibilidad
COLOR_WAYPOINT = "#2ecc71"  # Cambiado a verde para diferenciar mejor
COLOR_CITY = "#E21717"
COLOR_SELECTED = "#f39c12"
COLOR_DRAWING = "#e74c3c"   # Color para dibujo en tiempo real
COLOR_AUTO_ROAD = "#27ae60" # Color para rutas automáticas

# ------------------ GRAFO ------------------
G = nx.Graph()

# ------------------ HISTORIAL DE ACCIONES ------------------
class ActionHistory:
    def __init__(self, max_history=50):
        self.history = []  # Lista de acciones para deshacer
        self.redo_stack = []  # Lista de acciones para rehacer
        self.max_history = max_history
    
    def add_action(self, action_type, data):
        """Agrega una acción al historial"""
        action = {
            'type': action_type,
            'data': data,
            'timestamp': datetime.datetime.now()
        }
        self.history.append(action)
        self.redo_stack.clear()  # Limpiar pila de rehacer cuando hay nueva acción
        
        # Limitar tamaño del historial
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def undo(self):
        """Deshace la última acción"""
        if not self.history:
            return None
        
        action = self.history.pop()
        self.redo_stack.append(action)
        return action
    
    def redo(self):
        """Rehace la última acción deshecha"""
        if not self.redo_stack:
            return None
        
        action = self.redo_stack.pop()
        self.history.append(action)
        return action
    
    def clear(self):
        """Limpia el historial"""
        self.history.clear()
        self.redo_stack.clear()
    
    def can_undo(self):
        return len(self.history) > 0
    
    def can_redo(self):
        return len(self.redo_stack) > 0

# Crear instancia del historial
history = ActionHistory(max_history=100)

# ------------------ FUNCIONES AUXILIARES ------------------
def distance(a, b): 
    return math.hypot(a[0] - b[0], a[1] - b[1])

def distance_between_nodes(node1, node2):
    """Calcula la distancia entre dos nodos usando sus coordenadas"""
    if node1 in all_nodes and node2 in all_nodes:
        x1, y1 = all_nodes[node1]
        x2, y2 = all_nodes[node2]
        return distance((x1, y1), (x2, y2))
    return float('inf')

# CIUDADES con las coordenadas que me diste
original_cities = {
    "Caracas": [1127.0, 286.0],
    "Puerto Ayacucho": [1050.0, 980.0],
    "Barcelona": [1452.0, 333.0],
    "San Fernando de Apure": [1043.0, 661.0],
    "Maracay": [1120.0, 493.0],
    "Barinas": [610.0, 550.0],
    "Ciudad Bolívar": [1645.0, 627.0],
    "Valencia": [895.0, 493.0],
    "San Carlos": [905.0, 405.0],
    "Tucupita": [1870.0, 480.0],
    "Coro": [700.0, 165.0],
    "San Juan de los Morros": [1092.0, 376.0],
    "Barquisimeto": [765.0, 340.70649848716266],
    "Mérida": [490.0, 567.0],
    "Los Teques": [1133.0, 314.0],
    "Maturín": [1693.0, 366.0],
    "La Asunción": [1581.0, 196.0],
    "Guanare": [691.0, 501.0],
    "Cumaná": [1541.0, 286.0],
    "San Cristóbal": [314.0596505135865, 712.2386020543461],
    "Trujillo": [560.0, 455.0],
    "La Guaira": [1165.0, 271.0],
    "San Felipe": [855.0, 299.0],
    "Maracaibo": [394, 271]  # ¡CORREGIDO! Coordenadas actualizadas
}

# WAYPOINTS que me enviaste (usando todos los que proporcionaste)
waypoints = {
    "wp_001": [349.9777101325837, 727.5426490237116],
    "wp_002": [400.4923519647134, 733.759835710743],
    "wp_003": [457.2241804838744, 753.188544107716],
    "wp_004": [521.7274923618247, 778.0572908558414],
    "wp_005": [582.3450625603804, 769.5086591611733],
    "wp_006": [646.8483744383306, 760.9600274665052],
    "wp_007": [682.5971978887608, 771.0629558329312],
    "wp_008": [726.8946530338592, 748.5256540924426],
    "wp_009": [756.426289797258, 735.3141323825009],
    "wp_010": [769.6378115071997, 713.5539789778911],
    "wp_011": [757.9805864690159, 671.5879688404295],
    "wp_012": [753.3176964537424, 639.724887069394],
    "wp_013": [724.5632080262224, 612.5246953136318],
    "wp_014": [686.4829395681554, 601.6446186113269],
    "wp_015": [667.0542311711824, 585.3245035578697],
    "wp_016": [630.5282593848733, 574.4444268555648],
    "wp_017": [614.9852926672949, 556.5700151303496],
    "wp_018": [561.3620574916495, 528.5926750387085],
    "wp_019": [561.3620574916495, 528.5926750387085],
    "wp_020": [528.721827384735, 534.032713389861],
    "wp_021": [505.4073773083674, 552.6842734509551],
    "wp_022": [482.09292723199985, 575.9987235273226],
    "wp_023": [451.784142132722, 596.2045802601745],
    "wp_024": [416.8124670181707, 601.6446186113269],
    "wp_025": [397.3837586211977, 614.8561403212685],
    "wp_026": [370.9607152013145, 621.0733270082999],
    "wp_027": [353.0863034760994, 628.0676620312101],
    "wp_028": [381.84079190361933, 654.4907054510934],
    "wp_029": [399.7152036288345, 677.8051555274609],
    "wp_030": [396.6066102853188, 713.5539789778911],
    "wp_031": [453.33843880447984, 705.005347283223],
    "wp_032": [498.41304228545715, 659.1535954663668],
    "wp_033": [531.8304207282506, 610.9703986418739],
    "wp_034": [590.8936942550484, 568.2272401685334],
    "wp_035": [566.024947506923, 581.438761878475],
    "wp_036": [523.6112912953294, 520.0649679024161],
    "wp_037": [545.448517262175, 496.3009278796723],
    "wp_038": [551.8712307818354, 468.04098839316623],
    "wp_039": [538.3835323905485, 509.1463549189933],
    "wp_040": [549.3021453739713, 518.7804251984841],
    "wp_041": [566.0012005250885, 500.7968273434347],
    "wp_042": [593.6188686596286, 489.2359430080458],
    "wp_043": [607.7488384028816, 472.53688785692856],
    "wp_044": [607.1065670509156, 472.53688785692856],
    "wp_045": [629.5860643697272, 459.6914608176076],
    "wp_046": [653.992375744437, 451.341933242049],
    "wp_047": [659.1305465601655, 475.10597326479274],
    "wp_048": [672.6182449514524, 489.87821436001184],
    "wp_049": [692.5286568623999, 500.7968273434347],
    "wp_050": [671.3337022475204, 518.138153846518],
    "wp_051": [643.7160341129803, 532.268123589771],
    "wp_052": [623.1633508500668, 543.1867365731938],
    "wp_053": [663.6264460239278, 556.0321636125149],
    "wp_054": [687.3904860466715, 576.5848468754283],
    "wp_055": [709.8699833654832, 598.422072842274],
    "wp_056": [741.9835509637857, 595.8529874344098],
    "wp_057": [759.3248774668689, 571.4466760596999],
    "wp_058": [771.5280331542239, 549.6094500928543],
    "wp_059": [751.6176212432764, 527.1299527740426],
    "wp_060": [727.2113098685666, 518.138153846518],
    "wp_061": [706.658626605653, 504.65045545523094],
    "wp_062": [710.5122547174493, 486.66685760018163],
    "wp_063": [723.3576817567703, 470.6100738010304],
    "wp_064": [739.4144655559214, 464.82963163333596],
    "wp_065": [768.3166763943937, 422.4397224035768],
    "wp_066": [750.9753498913103, 444.9192197223885],
    "wp_067": [774.097118562088, 401.24476778869723],
    "wp_068": [673.2605163034185, 422.4397224035768],
    "wp_069": [689.9595714545358, 391.6106975092065],
    "wp_070": [716.9349682371097, 376.19618506202136],
    "wp_071": [611.6024665146779, 452.6264759459811],
    "wp_072": [592.3343259556965, 439.7810489066601],
    "wp_073": [577.5620848604774, 434.0006067389657],
    "wp_074": [570.4970999888508, 446.84603377828665],
    "wp_075": [551.8712307818354, 431.4315213311015],
    "wp_076": [536.4567183346503, 427.5778932193052],
    "wp_077": [522.3267485913972, 450.05739053811686],
    "wp_078": [501.7740653284837, 472.53688785692856],
    "wp_079": [482.50592476950226, 493.0895711198421],
    "wp_080": [464.5223269144529, 509.78862627095936],
    "wp_081": [445.8964577074375, 524.5608673661784],
    "wp_082": [423.4169603886258, 537.4062944054995],
    "wp_083": [408.00244794144066, 558.601249020379],
    "wp_084": [400.93746306981416, 580.4384749872246],
    "wp_085": [399.010649013916, 593.9261733785116],
    "wp_086": [425.98604579649003, 590.7148166186814],
    "wp_087": [450.3923571711998, 583.6498317470549],
    "wp_088": [548.9230833732089, 414.724705486784],
    "wp_089": [565.1725485779499, 398.475240282043],
    "wp_090": [588.4869986543174, 387.17126448744057],
    "wp_091": [618.1599351151489, 387.17126448744057],
    "wp_092": [604.7364638590584, 408.36621910232014],
    "wp_093": [594.1389865516187, 422.49618884557316],
    "wp_094": [628.7574124225887, 367.38930684688626],
    "wp_095": [637.9418927557032, 349.0203461806573],
    "wp_096": [651.3653640117935, 338.4228688732175],
    "wp_097": [669.0278261908599, 334.1838779502416],
    "wp_098": [692.3422762672274, 334.89037643740426],
    "wp_099": [705.0592490361552, 348.31384769349467],
    "wp_100": [715.656726343595, 359.6178234880971],
    "wp_101": [727.6672006253599, 353.96583559079585],
    "wp_102": [744.6231643172637, 349.0203461806573],
    "wp_103": [759.4596325476793, 342.6618597961934],
    "wp_104": [759.4596325476793, 342.6618597961934],
    "wp_105": [770.7636083422817, 361.7373189495851],
    "wp_106": [777.8285932139083, 384.3452705387899],
    "wp_107": [780.6545871625589, 341.2488628218681],
    "wp_108": [798.3170493416252, 337.71637038605485],
    "wp_109": [827.9899858024567, 334.1838779502416],
    "wp_110": [850.5979373916615, 327.8253915657777],
    "wp_111": [879.5643753653303, 330.65138551442834],
    "wp_112": [906.4113178775111, 335.5968749245669],
    "wp_113": [932.5517619025293, 339.83586584754283],
    "wp_114": [957.2792089532221, 339.1293673603802],
    "wp_115": [741.0906718814504, 331.357884001591],
    "wp_116": [714.9502278564323, 327.8253915657777],
    "wp_117": [695.168270215878, 324.29289912996444],
    "wp_118": [676.799309549649, 318.64091123266326],
    "wp_119": [618.8664336023115, 352.5528386164706],
    "wp_120": [596.2584820131066, 349.0203461806573],
    "wp_121": [582.1285122698536, 347.607349206332],
    "wp_122": [558.814062193486, 345.487853744844],
    "wp_123": [541.1516000144197, 341.95536130903076],
    "wp_124": [534.7931136299559, 353.25933710363324],
    "wp_125": [518.5436484252148, 350.4333431549826],
    "wp_126": [496.6421953231726, 349.72684466781993],
    "wp_127": [488.16421347722076, 338.42286887321757],
    "wp_128": [471.2082497853171, 332.77088097591627],
    "wp_129": [450.0132951704375, 315.10841879684995],
    "wp_130": [445.7743042474616, 298.1524551049463],
    "wp_131": [440.12231635016036, 284.7289838488559],
    "wp_132": [421.0468571967687, 276.9575004900667],
    "wp_133": [440.828814837323, 265.6535246954643],
    "wp_134": [467.67575734950384, 262.8275307468137],
    "wp_135": [487.4577149900581, 249.40405949072326],
    "wp_136": [502.2941832204738, 238.80658218328347],
    "wp_137": [515.7176544765642, 230.32860033733164],
    "wp_138": [797.7099174780744, 711.7118052853536],
    "wp_139": [797.7099174780744, 711.7118052853536],
    "wp_140": [805.417173701667, 689.874579318508],
    "wp_141": [841.3843694117656, 680.2405090390173],
    "wp_142": [867.7174948423736, 666.1105392957643],
    "wp_143": [913.318760831963, 666.1105392957643],
    "wp_144": [961.4891122294166, 668.0373533516624],
    "wp_145": [935.7982581507747, 664.8259965918321],
    "wp_146": [980.1149814364319, 673.8177955193569],
    "wp_147": [996.1717652355832, 673.8177955193569],
    "wp_148": [1032.7812322976479, 662.256911183968],
    "wp_149": [1014.7976344425985, 668.0373533516624],
    "wp_150": [1037.9194031133761, 646.2001273848168],
    "wp_151": [1018.6512625543947, 598.0297759873632],
    "wp_152": [1024.4317047220893, 617.2979165463446],
    "wp_153": [1022.504890666191, 573.6234646126534],
    "wp_154": [1025.7162474260213, 547.2903391820455],
    "wp_155": [1028.9276041858516, 521.5994851034036],
    "wp_156": [1048.195744744833, 513.892228879811],
    "wp_157": [1047.5534733928669, 492.6972742649314],
    "wp_158": [890.1969921611853, 663.5414538879],
    "wp_159": [888.9124494572532, 646.2001273848168],
    "wp_160": [891.4815348651174, 623.078358714039],
    "wp_161": [895.3351629769137, 599.9565900432614],
    "wp_162": [903.0424192005063, 572.9811932606874],
    "wp_163": [901.1156051446081, 551.1439672938418],
    "wp_164": [902.4001478485402, 529.3067413269962],
    "wp_165": [906.2537759603365, 513.2499575278449],
    "wp_166": [938.3673435586388, 484.3477466893728],
    "wp_167": [924.2373738153858, 502.9736158963882],
    "wp_168": [934.5137154468425, 457.37234990679883],
    "wp_169": [932.5869013909444, 432.32376718012296],
    "wp_170": [932.5869013909444, 421.40515419670015],
    "wp_171": [903.0424192005063, 496.5509023767277],
    "wp_172": [889.5547208092192, 486.27456074527095],
    # Añado waypoint específico para Maracaibo
    "wp_maracaibo_city": [394.0, 271.0]  # Waypoint en la ubicación exacta de Maracaibo
}

# Combinar todos los nodos
all_nodes = {**original_cities, **waypoints}

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

# Variables para el modo dibujo
drawing_points = []  # Puntos temporales mientras dibujas
drawing_line_id = None  # ID de la línea temporal en el canvas
draw_start_node = None  # Nodo inicial de la carretera
drawing_road = []  # Almacena los waypoints creados durante el dibujo
last_draw_point = None  # Último punto dibujado (para controlar densidad)
is_drawing = False  # BANDERA CRÍTICA: Controla si estamos en medio de un dibujo

# ------------------ LÓGICA ------------------
def update_weights():
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

def save_configuration():
    """Guarda la configuración actual"""
    try:
        nodes_data = {}
        for node, pos in all_nodes.items():
            nodes_data[node] = {
                "x": float(pos[0]), 
                "y": float(pos[1]), 
                "type": "city" if node in original_cities else "waypoint"
            }
        
        with open(NODES_FILE, 'w') as f: 
            json.dump(nodes_data, f, indent=4)
        
        roads_data = {"roads": roads}
        with open(ROADS_FILE, 'w') as f: 
            json.dump(roads_data, f, indent=4)
        
        # Crear archivo TXT para que yo lo vea
        txt_file = os.path.join(APP_DATA, "mi_configuracion.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("=== MI CONFIGURACIÓN DE RUTAS ===\n\n")
            f.write(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total waypoints: {len(waypoints)}\n")
            f.write(f"Total rutas creadas: {len(roads)}\n\n")
            
            f.write("=== RUTAS CREADAS ===\n")
            if roads:
                for i, (a, b) in enumerate(roads, 1):
                    f.write(f"{i:3d}. {a:20} -> {b}\n")
            else:
                f.write("(No hay rutas aún)\n")
            
            f.write("\n=== INSTRUCCIONES PARA EL DESARROLLADOR ===\n")
            f.write("1. Estas son las rutas que he creado manualmente\n")
            f.write("2. Por favor, optimiza las conexiones para que sea más eficiente\n")
            f.write("3. Mantén los waypoints donde están (están sobre las carreteras)\n")
            f.write("4. Asegúrate de que todas las ciudades estén conectadas\n")
            f.write("5. Maracaibo está en [394.0, 271.0]\n")
        
        messagebox.showinfo("Guardado", 
                          f"Configuración guardada exitosamente en:\n{APP_DATA}\n\n"
                          f"Envíame el archivo 'mi_configuracion.txt' para que yo lo optimice.")
        
        # Actualizar estadísticas
        road_count.set(f"Rutas: {len(roads)}")
        
        # Guardar estado actual en historial
        save_snapshot("save_configuration")
        
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo guardar: {e}")

def load_configuration():
    """Carga la configuración guardada"""
    global waypoints, roads, all_nodes
    
    try:
        # Guardar copia para poder deshacer
        old_waypoints = waypoints.copy()
        old_roads = roads.copy()
        old_all_nodes = all_nodes.copy()
        
        # Limpiar datos actuales
        waypoints.clear()
        roads.clear()
        
        if os.path.exists(NODES_FILE):
            with open(NODES_FILE, 'r') as f:
                nodes_data = json.load(f)
            
            # Restaurar ciudades originales primero
            for city in original_cities:
                if city in nodes_data:
                    original_cities[city] = [nodes_data[city]["x"], nodes_data[city]["y"]]
            
            # Cargar waypoints
            for node, data in nodes_data.items():
                pos = [data["x"], data["y"]]
                if data.get("type") == "waypoint":
                    waypoints[node] = pos
        
        if os.path.exists(ROADS_FILE):
            with open(ROADS_FILE, 'r') as f:
                roads_data = json.load(f)
            roads = roads_data.get("roads", [])
        
        # Reconstruir all_nodes
        all_nodes = {**original_cities, **waypoints}
        
        update_weights()
        print(f"Configuración cargada: {len(waypoints)} waypoints, {len(roads)} rutas")
        print(f"Maracaibo ubicado en: {original_cities['Maracaibo']}")
        
        # Guardar acción en historial
        history.add_action("load_config", {
            "old_waypoints": old_waypoints,
            "old_roads": old_roads,
            "old_all_nodes": old_all_nodes,
            "new_waypoints": waypoints.copy(),
            "new_roads": roads.copy(),
            "new_all_nodes": all_nodes.copy()
        })
        
    except Exception as e:
        print(f"Error cargando: {e}")

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

def toggle_edit_mode():
    global edit_mode, selected_node, draw_mode, is_drawing
    edit_mode = not edit_mode
    if edit_mode:
        edit_btn.config(text="SALIR DEL MODO EDICIÓN")
        path_info.set("MODO EDICIÓN: Selecciona nodos para crear rutas")
        # Limpiar cualquier dibujo pendiente
        if is_drawing:
            cleanup_drawing()
            is_drawing = False
        messagebox.showinfo("Modo Edición", 
                          "MODO EDICIÓN ACTIVADO\n\n"
                          "INSTRUCCIONES:\n"
                          "1. Click en un nodo (ciudad o waypoint) para seleccionarlo\n"
                          "2. Click en otro nodo para crear una ruta entre ellos\n"
                          "3. Click derecho en una ruta para eliminarla\n"
                          "4. Arrastra nodos para moverlos\n"
                          "5. Click en DIBUJAR CARRETERA para trazar libremente\n"
                          "6. Ctrl+Z para deshacer, Ctrl+Y para rehacer\n"
                          "7. Usa 'CONEXIÓN AUTOMÁTICA' para crear rutas inteligentes\n"
                          "8. Guarda cuando termines")
    else:
        edit_btn.config(text="MODO EDICIÓN")
        selected_node = None
        draw_mode = False
        is_drawing = False
        draw_btn.config(text="DIBUJAR CARRETERA")
        cleanup_drawing()
        path_info.set("Selecciona origen y destino para calcular ruta")
    
    redraw()

def toggle_draw_mode():
    """Activa/desactiva el modo de dibujo de carreteras"""
    global draw_mode, selected_node, drawing_points, draw_start_node, is_drawing
    
    if not edit_mode:
        messagebox.showwarning("Modo Dibujo", "Primero activa el MODO EDICIÓN")
        return
    
    if draw_mode:
        # Si ya está en modo dibujo, cancelarlo
        draw_mode = False
        is_drawing = False
        draw_btn.config(text="DIBUJAR CARRETERA")
        cleanup_drawing()
        path_info.set("Modo dibujo cancelado")
    else:
        draw_mode = True
        is_drawing = False  # No empezamos a dibujar hasta que hagamos click en un nodo
        draw_btn.config(text="CANCELAR DIBUJO")
        selected_node = None
        drawing_points = []
        draw_start_node = None
        path_info.set("MODO DIBUJO: Haz click en un nodo para empezar a dibujar")
        messagebox.showinfo("Modo Dibujo", 
                          "MODO DIBUJO ACTIVADO\n\n"
                          "INSTRUCCIONES:\n"
                          "1. Click en un nodo existente (ciudad o waypoint) para empezar\n"
                          "2. Mantén click y arrastra para dibujar la carretera\n"
                          "3. Suelta el click para terminar\n"
                          "4. Se crearán waypoints automáticamente SOLO en la línea que dibujaste\n"
                          "5. Click en otro nodo para conectar el final\n"
                          "6. Ctrl+Z para deshacer si te equivocas\n\n"
                          "IMPORTANTE: Las nuevas carreteras NO se conectarán automáticamente a otras existentes.\n"
                          "Puedes dibujar múltiples carreteras sin salir del modo.")
    
    redraw()

def cleanup_drawing():
    """Limpia el dibujo temporal"""
    global drawing_points, drawing_line_id, draw_start_node, last_draw_point, is_drawing
    if drawing_line_id:
        canvas.delete(drawing_line_id)
    drawing_points = []
    drawing_line_id = None
    draw_start_node = None
    last_draw_point = None
    is_drawing = False

def start_drawing_from_node(node_name, x, y):
    """Comienza a dibujar desde un nodo existente"""
    global draw_start_node, drawing_points, last_draw_point, is_drawing
    
    if node_name:
        draw_start_node = node_name
        drawing_points = [(x, y)]
        last_draw_point = (x, y)
        is_drawing = True
        path_info.set(f"Dibujando desde {node_name}... arrastra para continuar")
        return True
    return False

def add_drawing_point(x, y):
    """Agrega un punto al dibujo en curso"""
    global drawing_points, last_draw_point, drawing_line_id
    
    if not is_drawing:
        return False
    
    # Verificar distancia mínima para evitar puntos muy cercanos
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

def finish_drawing(end_node=None):
    """Termina el dibujo y crea los waypoints y rutas - MODIFICADO para evitar conexiones automáticas"""
    global drawing_points, draw_start_node, roads, waypoints, all_nodes, is_drawing
    
    if len(drawing_points) < 2:
        cleanup_drawing()
        return
    
    # Guardar estado antes de crear la carretera
    old_waypoints = waypoints.copy()
    old_roads = roads.copy()
    old_all_nodes = all_nodes.copy()
    
    # Crear waypoints a lo largo del trazo
    created_waypoints = []
    previous_node = draw_start_node
    
    # Contador para waypoints creados
    wp_counter = len(waypoints) + 1
    
    # Crear waypoints cada cierta distancia (más espaciados para evitar muchos waypoints)
    step_distance = 30  # Distancia mínima entre waypoints (en píxeles de pantalla)
    
    for i in range(len(drawing_points)):
        # Solo crear waypoint cada cierta distancia
        if i % 2 == 0 or i == len(drawing_points) - 1:
            x, y = drawing_points[i]
            
            # Convertir coordenadas de pantalla a mapa
            map_x, map_y = inverse_transform_coords(x, y)
            
            # Crear nombre único para el waypoint
            wp_name = f"drawn_wp_{wp_counter}"
            wp_counter += 1
            
            # Agregar waypoint
            waypoints[wp_name] = [map_x, map_y]
            all_nodes[wp_name] = [map_x, map_y]
            created_waypoints.append(wp_name)
            
            # Crear ruta SOLO entre waypoints consecutivos de ESTE dibujo
            if previous_node:
                roads.append((previous_node, wp_name))
                previous_node = wp_name
    
    # Conectar el último waypoint al nodo final si existe
    if end_node and previous_node:
        roads.append((previous_node, end_node))
        path_info.set(f"Carretera creada: {draw_start_node} → ... → {end_node} ({len(created_waypoints)} waypoints)")
    elif previous_node:
        # Si no hay nodo final, solo mostrar que se creó la carretera
        path_info.set(f"Carretera creada desde {draw_start_node} ({len(created_waypoints)} waypoints)")
    
    # IMPORTANTE: NO ejecutar funciones de conexión automática aquí
    # Solo actualizar el grafo con las nuevas conexiones
    update_weights()
    
    # Actualizar estadísticas
    waypoint_count.set(f"📍 Waypoints: {len(waypoints)}")
    road_count.set(f"🛣️  Rutas: {len(roads)}")
    
    # Guardar acción en historial
    history.add_action("draw_road", {
        "old_waypoints": old_waypoints,
        "old_roads": old_roads,
        "old_all_nodes": old_all_nodes,
        "start_node": draw_start_node,
        "end_node": end_node,
        "created_waypoints": created_waypoints.copy(),
        "drawing_points": drawing_points.copy()
    })
    
    # Limpiar dibujo temporal PERO mantener el modo dibujo activo
    cleanup_drawing()
    is_drawing = False
    draw_start_node = None
    drawing_points = []
    
    # NO salir del modo dibujo - permitir dibujar otra carretera
    # Solo mostrar mensaje informativo
    path_info.set("Carretera creada. Puedes dibujar otra o salir del modo dibujo.")
    
    redraw()
    
    # Mensaje informativo (más breve)
    messagebox.showinfo("Carretera Creada", 
                       f"✅ Carretera creada exitosamente\n\n"
                       f"Waypoints creados: {len(created_waypoints)}\n"
                       f"Rutas agregadas: {len(created_waypoints) + (1 if end_node else 0)}\n\n"
                       f"Puedes seguir dibujando más carreteras.\n"
                       f"Presiona CANCELAR DIBUJO cuando termines.")
    
    return created_waypoints

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

# ------------------ NUEVAS FUNCIONES PARA ELIMINAR CONEXIONES ------------------
def delete_all_city_connections():
    """Elimina todas las conexiones de una ciudad seleccionada"""
    global roads, selected_node
    
    if not edit_mode:
        messagebox.showwarning("Eliminar Conexiones", "Primero activa el MODO EDICIÓN")
        return
    
    if not selected_node:
        messagebox.showwarning("Eliminar Conexiones", "Primero selecciona una ciudad haciendo click en ella")
        return
    
    if selected_node not in original_cities:
        messagebox.showwarning("Eliminar Conexiones", "Por favor selecciona una ciudad (punto rojo), no un waypoint")
        return
    
    # Contar conexiones actuales
    connections_to_delete = []
    for road in roads:
        if selected_node in road:
            connections_to_delete.append(road)
    
    if not connections_to_delete:
        messagebox.showinfo("Eliminar Conexiones", f"La ciudad '{selected_node}' no tiene conexiones para eliminar")
        return
    
    # Confirmar eliminación
    response = messagebox.askyesno(
        "Eliminar Conexiones", 
        f"¿Estás seguro de eliminar TODAS las conexiones de '{selected_node}'?\n\n"
        f"Se eliminarán {len(connections_to_delete)} conexiones:\n" +
        "\n".join([f"  • {a} ↔ {b}" for a, b in connections_to_delete[:5]]) +
        (f"\n  ... y {len(connections_to_delete)-5} más" if len(connections_to_delete) > 5 else "")
    )
    
    if not response:
        return
    
    # Guardar estado antes de eliminar
    old_roads = roads.copy()
    
    # Eliminar todas las conexiones que involucren a la ciudad seleccionada
    roads = [road for road in roads if selected_node not in road]
    
    # Actualizar grafo y estadísticas
    update_weights()
    road_count.set(f"🛣️  Rutas: {len(roads)}")
    
    # Guardar en historial
    history.add_action("delete_city_connections", {
        "old_roads": old_roads,
        "new_roads": roads.copy(),
        "city": selected_node,
        "deleted_connections": connections_to_delete
    })
    
    # Actualizar interfaz
    update_history_display()
    path_info.set(f"Eliminadas {len(connections_to_delete)} conexiones de '{selected_node}'")
    redraw()
    
    messagebox.showinfo(
        "Conexiones Eliminadas", 
        f"Se eliminaron {len(connections_to_delete)} conexiones de '{selected_node}'"
    )

def delete_waypoint():
    """Elimina un waypoint seleccionado y todas sus conexiones"""
    global waypoints, roads, all_nodes, selected_node
    
    if not edit_mode:
        messagebox.showwarning("Eliminar Waypoint", "Primero activa el MODO EDICIÓN")
        return
    
    if not selected_node:
        messagebox.showwarning("Eliminar Waypoint", "Primero selecciona un waypoint haciendo click en él")
        return
    
    if selected_node not in waypoints:
        messagebox.showwarning("Eliminar Waypoint", "Por favor selecciona un waypoint (punto verde), no una ciudad")
        return
    
    # Contar conexiones y confirmar
    connections_to_delete = []
    for road in roads:
        if selected_node in road:
            connections_to_delete.append(road)
    
    # Obtener posición para el mensaje
    wp_pos = waypoints[selected_node]
    
    response = messagebox.askyesno(
        "Eliminar Waypoint", 
        f"¿Estás seguro de eliminar el waypoint '{selected_node}'?\n\n"
        f"Posición: [{wp_pos[0]:.1f}, {wp_pos[1]:.1f}]\n"
        f"Conexiones que serán eliminadas: {len(connections_to_delete)}\n\n"
        f"Esta acción no se puede deshacer fácilmente."
    )
    
    if not response:
        return
    
    # Guardar estado antes de eliminar
    old_waypoints = waypoints.copy()
    old_roads = roads.copy()
    old_all_nodes = all_nodes.copy()
    
    # Eliminar el waypoint
    del waypoints[selected_node]
    
    # Eliminar todas las rutas que involucren este waypoint
    roads = [road for road in roads if selected_node not in road]
    
    # Actualizar all_nodes
    all_nodes = {**original_cities, **waypoints}
    
    # Deseleccionar el nodo eliminado
    selected_node = None
    
    # Actualizar grafo y estadísticas
    update_weights()
    waypoint_count.set(f"📍 Waypoints: {len(waypoints)}")
    road_count.set(f"🛣️  Rutas: {len(roads)}")
    
    # Guardar en historial
    history.add_action("delete_waypoint", {
        "old_waypoints": old_waypoints,
        "old_roads": old_roads,
        "old_all_nodes": old_all_nodes,
        "waypoint_name": selected_node,
        "waypoint_position": wp_pos,
        "deleted_connections": connections_to_delete
    })
    
    # Actualizar interfaz
    update_history_display()
    path_info.set(f"Waypoint '{selected_node}' eliminado con {len(connections_to_delete)} conexiones")
    redraw()
    
    messagebox.showinfo(
        "Waypoint Eliminado", 
        f"Waypoint '{selected_node}' eliminado exitosamente.\n"
        f"Se eliminaron {len(connections_to_delete)} conexiones."
    )

def delete_waypoint_connections():
    """Elimina todas las conexiones de un waypoint seleccionado (pero mantiene el waypoint)"""
    global roads, selected_node
    
    if not edit_mode:
        messagebox.showwarning("Eliminar Conexiones", "Primero activa el MODO EDICIÓN")
        return
    
    if not selected_node:
        messagebox.showwarning("Eliminar Conexiones", "Primero selecciona un waypoint haciendo click en él")
        return
    
    if selected_node not in waypoints:
        messagebox.showwarning("Eliminar Conexiones", "Por favor selecciona un waypoint (punto verde), no una ciudad")
        return
    
    # Contar conexiones actuales
    connections_to_delete = []
    for road in roads:
        if selected_node in road:
            connections_to_delete.append(road)
    
    if not connections_to_delete:
        messagebox.showinfo("Eliminar Conexiones", f"El waypoint '{selected_node}' no tiene conexiones para eliminar")
        return
    
    # Confirmar eliminación
    response = messagebox.askyesno(
        "Eliminar Conexiones de Waypoint", 
        f"¿Estás seguro de eliminar TODAS las conexiones de '{selected_node}'?\n\n"
        f"Se eliminarán {len(connections_to_delete)} conexiones:\n" +
        "\n".join([f"  • {a} ↔ {b}" for a, b in connections_to_delete[:5]]) +
        (f"\n  ... y {len(connections_to_delete)-5} más" if len(connections_to_delete) > 5 else "") +
        f"\n\nEl waypoint se mantendrá en su posición actual."
    )
    
    if not response:
        return
    
    # Guardar estado antes de eliminar
    old_roads = roads.copy()
    
    # Eliminar todas las conexiones que involucren al waypoint seleccionado
    roads = [road for road in roads if selected_node not in road]
    
    # Actualizar grafo y estadísticas
    update_weights()
    road_count.set(f"🛣️  Rutas: {len(roads)}")
    
    # Guardar en historial
    history.add_action("delete_waypoint_connections", {
        "old_roads": old_roads,
        "new_roads": roads.copy(),
        "waypoint": selected_node,
        "deleted_connections": connections_to_delete
    })
    
    # Actualizar interfaz
    update_history_display()
    path_info.set(f"Eliminadas {len(connections_to_delete)} conexiones de '{selected_node}'")
    redraw()
    
    messagebox.showinfo(
        "Conexiones Eliminadas", 
        f"Se eliminaron {len(connections_to_delete)} conexiones de '{selected_node}'\n\n"
        f"El waypoint se mantiene en su posición para que puedas reconectarlo manualmente."
    )

# ------------------ ALGORITMOS DE CONEXIÓN AUTOMÁTICA (MODIFICADOS) ------------------
def find_nearest_waypoint(city_name, max_distance=100):
    """Encuentra el waypoint más cercano a una ciudad"""
    if city_name not in original_cities:
        return None
    
    city_pos = original_cities[city_name]
    nearest = None
    min_dist = float('inf')
    
    for wp_name, wp_pos in waypoints.items():
        # Evitar waypoints dibujados manualmente
        if wp_name.startswith("drawn_wp_"):
            continue
            
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
        
        # Evitar waypoints dibujados manualmente
        if other_node.startswith("drawn_wp_"):
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
    """Conecta cada waypoint a sus k vecinos más cercanos - MODIFICADO para evitar conectar waypoints dibujados recientemente"""
    global roads
    
    # Guardar estado antes de la acción
    old_roads = roads.copy()
    
    connections_made = 0
    for wp in waypoints.keys():
        # Evitar conectar waypoints dibujados recientemente (empiezan con "drawn_wp_")
        if wp.startswith("drawn_wp_"):
            continue
            
        neighbors = find_k_nearest_neighbors(wp, k, "waypoint", max_distance)
        for dist, neighbor in neighbors:
            # Evitar conectar waypoints dibujados recientemente
            if neighbor.startswith("drawn_wp_"):
                continue
                
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
    """Construye un árbol de expansión mínimo para conectar todos los waypoints - MODIFICADO para excluir waypoints dibujados"""
    global roads
    
    if len(waypoints) < 2:
        return 0
    
    # Guardar estado antes de la acción
    old_roads = roads.copy()
    
    # Crear un grafo temporal solo con waypoints (excluyendo los dibujados recientemente)
    temp_graph = nx.Graph()
    
    # Agregar nodos (excluyendo waypoints dibujados)
    waypoints_to_connect = [wp for wp in waypoints.keys() if not wp.startswith("drawn_wp_")]
    
    if len(waypoints_to_connect) < 2:
        return 0
        
    for wp in waypoints_to_connect:
        temp_graph.add_node(wp)
    
    # Agregar aristas con peso de distancia
    for i in range(len(waypoints_to_connect)):
        for j in range(i + 1, len(waypoints_to_connect)):
            wp1 = waypoints_to_connect[i]
            wp2 = waypoints_to_connect[j]
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
    """Generación inteligente de rutas siguiendo la lógica de carreteras - MODIFICADO para no tocar waypoints dibujados"""
    global roads
    
    # Guardar estado antes de la acción
    old_roads = roads.copy()
    
    connections_made = 0
    
    # Paso 1: Conectar ciudades a waypoints cercanos (excluyendo dibujados recientemente)
    connections_made += connect_cities_to_nearest_waypoints(max_distance=100)
    
    # Paso 2: Conectar waypoints entre sí (vecinos cercanos, excluyendo dibujados)
    connections_made += connect_waypoints_to_neighbors(k=3, max_distance=150)
    
    # Paso 3: Construir árbol de expansión mínimo (excluyendo dibujados)
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

def auto_connect_all():
    """Función principal para conectar automáticamente todo"""
    if not edit_mode:
        messagebox.showwarning("Conexión Automática", "Primero activa el MODO EDICIÓN")
        return
    
    response = messagebox.askyesno("Conexión Automática", 
                                   "¿Deseas generar rutas automáticamente?\n\n"
                                   "Esto creará conexiones inteligentes entre:\n"
                                   "1. Ciudades y waypoints cercanos\n"
                                   "2. Waypoints entre sí (excluyendo los dibujados manualmente)\n"
                                   "3. Ciudades principales cercanas\n\n"
                                   "IMPORTANTE: Las carreteras dibujadas manualmente\n"
                                   "NO se conectarán automáticamente para evitar cruces.")
    
    if response:
        # Mostrar progreso
        path_info.set("Generando rutas automáticas...")
        root.update()
        
        total_connections = smart_road_generation()
        
        # Actualizar estadísticas
        waypoint_count.set(f"📍 Waypoints: {len(waypoints)}")
        road_count.set(f"🛣️  Rutas: {len(roads)}")
        update_history_display()
        
        # Mostrar resultados
        path_info.set(f"¡Listo! Se crearon {total_connections} conexiones automáticas")
        messagebox.showinfo("Conexión Completada", 
                          f"✅ Conexiones automáticas creadas: {total_connections}\n\n"
                          f"🏙️  Ciudades conectadas: {len(original_cities)}\n"
                          f"📍 Waypoints conectados: {len(waypoints)}\n"
                          f"🛣️  Total de rutas: {len(roads)}\n\n"
                          f"Nota: Waypoints dibujados manualmente (drawn_wp_*) \n"
                          f"NO fueron conectados automáticamente para evitar cruces.")
        
        redraw()

# ------------------ FUNCIONES DE EDICIÓN ------------------
def select_node_at(x, y):
    """Selecciona un nodo en las coordenadas de pantalla (x, y)"""
    global selected_node
    
    for node_name, pos in all_nodes.items():
        sx, sy = transform_coords(*pos)
        if math.hypot(x - sx, y - sy) < 15:
            return node_name
    return None

def create_road_between(node1, node2):
    """Crea una ruta entre dos nodos"""
    if node1 == node2:
        return False
    
    # Verificar si la ruta ya existe
    if (node1, node2) in roads or (node2, node1) in roads:
        return False
    
    # Guardar estado antes de la acción
    old_roads = roads.copy()
    
    # Agregar ruta
    roads.append((node1, node2))
    update_weights()
    
    # Guardar en historial
    history.add_action("create_road", {
        "old_roads": old_roads,
        "new_roads": roads.copy(),
        "node1": node1,
        "node2": node2
    })
    
    return True

def delete_road_at(x, y):
    """Elimina una ruta cerca de las coordenadas (x, y)"""
    global roads
    
    for i, (a, b) in enumerate(roads):
        if a in all_nodes and b in all_nodes:
            x1, y1 = transform_coords(*all_nodes[a])
            x2, y2 = transform_coords(*all_nodes[b])
            
            # Calcular distancia del punto a la línea
            dx, dy = x2 - x1, y2 - y1
            if dx == 0 and dy == 0:
                continue
                
            t = ((x - x1) * dx + (y - y1) * dy) / (dx*dx + dy*dy)
            t = max(0, min(1, t))
            
            closest_x = x1 + t * dx
            closest_y = y1 + t * dy
            
            if math.hypot(x - closest_x, y - closest_y) < 10:
                # Guardar estado antes de eliminar
                old_roads = roads.copy()
                
                # Eliminar la ruta
                del roads[i]
                update_weights()
                
                # Guardar en historial
                history.add_action("delete_road", {
                    "old_roads": old_roads,
                    "new_roads": roads.copy(),
                    "deleted_road": (a, b)
                })
                
                return True
    
    return False

def move_node_to(node_name, x, y):
    """Mueve un nodo a nuevas coordenadas (coordenadas de mapa)"""
    global all_nodes, waypoints, original_cities
    
    if node_name in all_nodes:
        # Guardar estado antes de mover
        old_pos = all_nodes[node_name].copy()
        
        # Mover el nodo
        all_nodes[node_name] = [x, y]
        if node_name in waypoints:
            waypoints[node_name] = [x, y]
        elif node_name in original_cities:
            original_cities[node_name] = [x, y]
        
        update_weights()
        
        # Guardar en historial (solo una vez por movimiento, no por cada evento de arrastre)
        if not hasattr(move_node_to, 'last_move'):
            move_node_to.last_move = None
        
        current_move = (node_name, x, y)
        if move_node_to.last_move != current_move:
            history.add_action("move_node", {
                "node_name": node_name,
                "old_pos": old_pos,
                "new_pos": [x, y]
            })
            move_node_to.last_move = current_move
        
        return True
    return False

# Inicializar atributo estático
move_node_to.last_move = None

# ------------------ ALGORITMO DE RUTA (DIJKSTRA) ------------------
def find_path():
    global current_path, current_start, current_end
    
    s, e = start_var.get(), end_var.get()
    if s and e and s != e:
        try:
            update_weights()
            
            # 🚨 ALGORITMO USADO: Dijkstra
            # Usamos NetworkX que implementa el algoritmo de Dijkstra
            # para encontrar el camino más corto entre dos nodos
            
            # Información sobre el algoritmo
            algorithm_info = """
            🧠 ALGORITMO USADO: Dijkstra
            
            Características:
            • Encuentra el camino más cortos entre dos nodos
            • Considera pesos (distancias) en las aristas
            • Garantiza el camino óptimo para pesos no negativos
            • Complejidad: O((V+E) log V) usando cola de prioridad
            
            Variables:
            • V = número de vértices (nodos) = {v}
            • E = número de aristas (rutas) = {e}
            • Peso = distancia euclidiana entre nodos
            
            Implementación: NetworkX.dijkstra_path()
            """.format(v=len(G.nodes()), e=len(G.edges()))
            
            print("="*60)
            print("CALCULANDO RUTA CON ALGORITMO DE DIJKSTRA")
            print("="*60)
            print(algorithm_info)
            
            # Verificar si los nodos están en el grafo
            if s not in G.nodes():
                print(f"ERROR: Ciudad de origen '{s}' no está en el grafo")
                messagebox.showerror("Error", f"La ciudad '{s}' no está conectada a la red.")
                return
                
            if e not in G.nodes():
                print(f"ERROR: Ciudad de destino '{e}' no está en el grafo")
                messagebox.showerror("Error", f"La ciudad '{e}' no está conectada a la red.")
                return
            
            # Calcular ruta usando Dijkstra
            print(f"\nCalculando ruta: {s} → {e}")
            print(f"Nodos en el grafo: {len(G.nodes())}")
            print(f"Aristas en el grafo: {len(G.edges())}")
            
            path = nx.dijkstra_path(G, s, e, weight="weight")
            
            current_path, current_start, current_end = path, s, e
            
            # Calcular distancia total
            total_dist = 0
            dist_details = []
            for i in range(len(path)-1):
                if path[i] in all_nodes and path[i+1] in all_nodes:
                    x1, y1 = all_nodes[path[i]]
                    x2, y2 = all_nodes[path[i+1]]
                    segment_dist = distance((x1, y1), (x2, y2))
                    total_dist += segment_dist
                    dist_details.append(f"  {path[i]} → {path[i+1]}: {segment_dist/40:.1f} km")
            
            # Información detallada de la ruta
            print(f"\nRUTA ENCONTRADA ({len(path)} segmentos):")
            print("-" * 40)
            for i, node in enumerate(path):
                node_type = "CIUDAD" if node in original_cities else "waypoint"
                print(f"{i+1:2d}. {node:25} [{node_type}]")
            
            print(f"\nDISTANCIA TOTAL: {total_dist/40:.1f} km")
            print("Detalle por segmentos:")
            for detail in dist_details:
                print(detail)
            
            print(f"\nNodos intermedios (waypoints): {len([n for n in path if n in waypoints])}")
            print(f"Ciudades en la ruta: {len([n for n in path if n in original_cities])}")
            
            # Simplificar ruta mostrada (solo ciudades)
            display_path = []
            for node in path:
                if node in original_cities:
                    display_path.append(node)
            
            if len(display_path) < 2:
                display_path = [s, "...", e]
            
            # Actualizar información en la interfaz
            path_info.set(f"Ruta (Dijkstra): {' → '.join(display_path)} | Distancia: ~{total_dist/40:.0f} km | Segmentos: {len(path)-1}")
            
            # Mostrar información del algoritmo
            algorithm_label.config(
                text=f"🧠 Algoritmo: Dijkstra | Nodos: {len(G.nodes())} | Rutas: {len(G.edges())}",
                fg="#2ecc71",  # Verde para destacar
                font=("Segoe UI", 9, "bold")
            )
            
            redraw()
            
        except nx.NetworkXNoPath:
            print(f"\nERROR: No existe ruta entre {s} y {e}")
            messagebox.showerror("Error", f"No hay ruta disponible entre '{s}' y '{e}'.\n\n"
                                      "Usa CONEXIÓN AUTOMÁTICA o crea rutas manualmente en modo edición.")
            path_info.set(f"No hay ruta entre {s} y {e}")
            
        except Exception as e:
            print(f"\nERROR: {e}")
            messagebox.showerror("Error", f"Error al calcular la ruta: {e}")
            path_info.set("Error al calcular ruta")
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

def redo_action(event=None):
    """Rehace la última acción deshecha"""
    if not history.can_redo():
        messagebox.showinfo("Rehacer", "No hay acciones para rehacer")
        return
    
    action = history.redo()
    if action:
        apply_redo_action(action)
        update_history_display()

def apply_undo_action(action):
    """Aplica la acción de deshacer"""
    global waypoints, roads, all_nodes
    
    action_type = action['type']
    data = action['data']
    
    if action_type == "create_road":
        # Deshacer creación de ruta
        roads.clear()
        roads.extend(data['old_roads'])
        path_info.set(f"Deshecho: Ruta {data['node1']} → {data['node2']}")
        
    elif action_type == "delete_road":
        # Deshacer eliminación de ruta
        roads.clear()
        roads.extend(data['old_roads'])
        path_info.set(f"Deshecho: Eliminación de ruta {data['deleted_road'][0]} → {data['deleted_road'][1]}")
        
    elif action_type == "draw_road":
        # Deshacer dibujo de carretera
        waypoints = data['old_waypoints'].copy()
        roads = data['old_roads'].copy()
        all_nodes = data['old_all_nodes'].copy()
        path_info.set(f"Deshecho: Carretera con {len(data['created_waypoints'])} waypoints")
        
    elif action_type == "move_node":
        # Deshacer movimiento de nodo
        node_name = data['node_name']
        all_nodes[node_name] = data['old_pos'].copy()
        if node_name in waypoints:
            waypoints[node_name] = data['old_pos'].copy()
        elif node_name in original_cities:
            original_cities[node_name] = data['old_pos'].copy()
        path_info.set(f"Deshecho: Movimiento de {node_name}")
        
    elif action_type == "load_config":
        # Deshacer carga de configuración
        waypoints = data['old_waypoints'].copy()
        roads = data['old_roads'].copy()
        all_nodes = data['old_all_nodes'].copy()
        path_info.set(f"Deshecho: Carga de configuración")
    
    elif action_type in ["auto_connect_cities", "auto_connect_waypoints", "build_mst", "smart_generation"]:
        # Deshacer conexiones automáticas
        roads.clear()
        roads.extend(data['old_roads'])
        path_info.set(f"Deshecho: Conexiones automáticas ({data.get('connections_made', 0)} rutas)")
        
    elif action_type == "delete_city_connections":
        # Deshacer eliminación de conexiones de ciudad
        roads.clear()
        roads.extend(data['old_roads'])
        path_info.set(f"Deshecho: Eliminación de conexiones de {data['city']}")
        
    elif action_type == "delete_waypoint":
        # Deshacer eliminación de waypoint
        waypoints = data['old_waypoints'].copy()
        roads = data['old_roads'].copy()
        all_nodes = data['old_all_nodes'].copy()
        path_info.set(f"Deshecho: Eliminación de waypoint {data['waypoint_name']}")
        
    elif action_type == "delete_waypoint_connections":
        # Deshacer eliminación de conexiones de waypoint
        roads.clear()
        roads.extend(data['old_roads'])
        path_info.set(f"Deshecho: Eliminación de conexiones de {data['waypoint']}")
    
    update_weights()
    waypoint_count.set(f"📍 Waypoints: {len(waypoints)}")
    road_count.set(f"🛣️  Rutas: {len(roads)}")
    redraw()

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
        # Rehacer dibujo de carretera
        # Primero restaurar el estado anterior
        waypoints = data['old_waypoints'].copy()
        roads = data['old_roads'].copy()
        all_nodes = data['old_all_nodes'].copy()
        
        # Luego recrear los waypoints y rutas
        previous_node = data['start_node']
        created_waypoints = []
        
        for i, wp_name in enumerate(data['created_waypoints']):
            # Recuperar posición del waypoint (aproximada)
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
        
        # Reconectar el nodo final si existe
        if data['end_node'] and previous_node:
            roads.append((previous_node, data['end_node']))
        
        path_info.set(f"Rehecho: Carretera con {len(created_waypoints)} waypoints")
        
    elif action_type == "move_node":
        # Rehacer movimiento de nodo
        node_name = data['node_name']
        all_nodes[node_name] = data['new_pos'].copy()
        if node_name in waypoints:
            waypoints[node_name] = data['new_pos'].copy()
        elif node_name in original_cities:
            original_cities[node_name] = data['new_pos'].copy()
        path_info.set(f"Rehecho: Movimiento de {node_name}")
        
    elif action_type == "load_config":
        # Rehacer carga de configuración
        waypoints = data['new_waypoints'].copy()
        roads = data['new_roads'].copy()
        all_nodes = data['new_all_nodes'].copy()
        path_info.set(f"Rehecho: Carga de configuración")
    
    elif action_type in ["auto_connect_cities", "auto_connect_waypoints", "build_mst", "smart_generation"]:
        # Rehacer conexiones automáticas
        roads.clear()
        roads.extend(data['new_roads'])
        path_info.set(f"Rehecho: Conexiones automáticas ({data.get('connections_made', 0)} rutas)")
        
    elif action_type == "delete_city_connections":
        # Rehacer eliminación de conexiones de ciudad
        roads.clear()
        roads.extend(data['new_roads'])
        path_info.set(f"Rehecho: Eliminación de conexiones de {data['city']}")
        
    elif action_type == "delete_waypoint":
        # Rehacer eliminación de waypoint
        waypoints = data['new_waypoints'].copy()
        roads = data['new_roads'].copy()
        all_nodes = data['new_all_nodes'].copy()
        path_info.set(f"Rehecho: Eliminación de waypoint {data['waypoint_name']}")
        
    elif action_type == "delete_waypoint_connections":
        # Rehacer eliminación de conexiones de waypoint
        roads.clear()
        roads.extend(data['new_roads'])
        path_info.set(f"Rehecho: Eliminación de conexiones de {data['waypoint']}")
    
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

# ------------------ DIBUJO MEJORADO ------------------
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
    
    # Dibujar ciudades (incluyendo Maracaibo)
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
            # Texto con sombra (para Maracaibo, ajustar posición si es necesario)
            offset_y = y-r-10
            # Ajustar posición del texto para Maracaibo si está muy cerca del borde
            if city == "Maracaibo" and y < 50:
                offset_y = y + r + 15
            
            canvas.create_text(x+1, offset_y+1, text=city, 
                             fill="white", font=("Segoe UI", f_size, "bold"))
            canvas.create_text(x, offset_y, text=city, 
                             fill="black", font=("Segoe UI", f_size, "bold"))
    
    # Dibujar ruta calculada (EN AZUL)
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
        # Primero dibujar una línea más gruesa de fondo (opcional, para mejor visibilidad)
        for i in range(len(path_points) - 1):
            x1, y1 = path_points[i]
            x2, y2 = path_points[i + 1]
            # Línea de fondo blanca (para contraste)
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

# ------------------ MANEJADORES DE EVENTOS MEJORADOS ------------------
def on_canvas_click(event):
    global selected_node, dragging, draw_mode, is_drawing
    
    if draw_mode and not is_drawing:
        # En modo dibujo: empezar desde un nodo existente
        node = select_node_at(event.x, event.y)
        if node:
            # Empezar a dibujar desde este nodo
            if start_drawing_from_node(node, event.x, event.y):
                selected_node = node
                redraw()
        else:
            # Click en espacio vacío: cancelar dibujo solo si es click derecho
            if event.num == 3:  # Click derecho
                messagebox.showwarning("Modo Dibujo", "Debes hacer click en un nodo existente (ciudad o waypoint) para empezar a dibujar.")
                toggle_draw_mode()  # Cancelar modo dibujo
    
    elif draw_mode and is_drawing:
        # Ya estamos dibujando, click para terminar en un nodo (opcional)
        if event.num == 1 and len(drawing_points) > 1:  # Click izquierdo para terminar
            end_node = select_node_at(event.x, event.y)
            finish_drawing(end_node)
            # NO salir del modo dibujo - permite dibujar otra carretera
    
    elif edit_mode:
        # En modo edición normal
        node = select_node_at(event.x, event.y)
        
        if event.num == 1:  # Click izquierdo
            if node:
                if selected_node and selected_node != node:
                    # Crear ruta entre nodos seleccionados
                    if create_road_between(selected_node, node):
                        path_info.set(f"Ruta creada: {selected_node} -> {node}")
                        road_count.set(f"🛣️  Rutas: {len(roads)}")
                        update_history_display()
                    selected_node = node
                else:
                    # Seleccionar nodo
                    selected_node = node
                    path_info.set(f"Nodo seleccionado: {node}")
            else:
                # Click en espacio vacío: deseleccionar
                selected_node = None
                path_info.set("Click en un nodo para seleccionarlo")
            
            redraw()
            
        elif event.num == 3:  # Click derecho
            # Intentar eliminar una ruta
            if delete_road_at(event.x, event.y):
                path_info.set("Ruta eliminada")
                road_count.set(f"🛣️  Rutas: {len(roads)}")
                update_history_display()
                redraw()
    else:
        # Fuera del modo edición: inicio de arrastre para pan
        dragging = True
        drag_start = (event.x, event.y)

def on_canvas_drag(event):
    global pan_x, pan_y, dragging, draw_mode, is_drawing
    
    if draw_mode and is_drawing:
        # En modo dibujo: agregar puntos al trazo
        add_drawing_point(event.x, event.y)
    elif edit_mode and selected_node and not draw_mode:
        # En modo edición: mover nodo seleccionado
        map_x, map_y = inverse_transform_coords(event.x, event.y)
        if move_node_to(selected_node, map_x, map_y):
            redraw()
    elif dragging and not edit_mode:
        # Fuera del modo edición: pan
        dx = event.x - drag_start[0]
        dy = event.y - drag_start[1]
        pan_x += dx
        pan_y += dy
        drag_start = (event.x, event.y)
        constrain_pan()
        redraw()

def on_canvas_release(event):
    global dragging, draw_mode, is_drawing
    
    if draw_mode and is_drawing and len(drawing_points) > 1:
        # Terminar el dibujo al soltar el click (pero solo si hay suficientes puntos)
        end_node = select_node_at(event.x, event.y)
        finish_drawing(end_node)
        # IMPORTANTE: NO salir del modo dibujo aquí
        # Solo limpiar el estado de dibujo actual
        path_info.set("Carretera creada. Puedes dibujar otra o salir del modo dibujo.")
        update_history_display()
    
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

# Configurar atajos de teclado
root.bind('<Control-z>', undo_action)
root.bind('<Control-Z>', undo_action)
root.bind('<Control-y>', redo_action)
root.bind('<Control-Y>', redo_action)

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

edit_btn = ttk.Button(sidebar, text="MODO EDICIÓN", command=toggle_edit_mode)
edit_btn.pack(fill="x", ipady=8, pady=(0, 5))

# Botón de dibujo de carreteras
draw_btn = ttk.Button(sidebar, text="DIBUJAR CARRETERA", command=toggle_draw_mode)
draw_btn.pack(fill="x", ipady=8, pady=(0, 5))

# NUEVO: Botón de conexión automática
auto_connect_btn = ttk.Button(sidebar, text="🤖 CONEXIÓN AUTOMÁTICA", 
                              command=auto_connect_all)
auto_connect_btn.pack(fill="x", ipady=8, pady=(0, 5))

# NUEVO: Botón para eliminar conexiones de ciudad
delete_city_btn = ttk.Button(sidebar, text="🗑️ ELIMINAR CONEXIONES CIUDAD", 
                             command=delete_all_city_connections)
delete_city_btn.pack(fill="x", ipady=8, pady=(0, 5))

# NUEVO: Botón para eliminar waypoint
delete_waypoint_btn = ttk.Button(sidebar, text="❌ ELIMINAR WAYPOINT", 
                                 command=delete_waypoint)
delete_waypoint_btn.pack(fill="x", ipady=8, pady=(0, 5))

# NUEVO: Botón para eliminar conexiones de waypoint
delete_wp_connections_btn = ttk.Button(sidebar, text="🔗 ELIMINAR CONEXIONES WAYPOINT", 
                                       command=delete_waypoint_connections)
delete_wp_connections_btn.pack(fill="x", ipady=8, pady=(0, 5))

# Botones de deshacer/rehacer
undo_frame = ttk.Frame(sidebar)
undo_frame.pack(fill="x", pady=(0, 5))

undo_btn = ttk.Button(undo_frame, text="↶ DESHACER (Ctrl+Z)", command=undo_action, state="disabled")
undo_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

redo_btn = ttk.Button(undo_frame, text="↷ REHACER (Ctrl+Y)", command=redo_action, state="disabled")
redo_btn.pack(side="right", fill="x", expand=True, padx=(2, 0))

ttk.Button(sidebar, text="💾 GUARDAR MI TRABAJO", command=save_configuration).pack(fill="x", ipady=8, pady=(0, 10))

# Estadísticas
stats_frame = ttk.Frame(sidebar)
stats_frame.pack(fill="x", pady=(10, 0))

ttk.Label(stats_frame, text="📊 ESTADÍSTICAS:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
ttk.Label(stats_frame, text=f"🏙️  Ciudades: {len(original_cities)}").pack(anchor="w")
waypoint_count = tk.StringVar(value=f"📍 Waypoints: {len(waypoints)}")
ttk.Label(stats_frame, textvariable=waypoint_count).pack(anchor="w")
road_count = tk.StringVar(value=f"🛣️  Rutas: {len(roads)}")
ttk.Label(stats_frame, textvariable=road_count).pack(anchor="w")

# Información del algoritmo
algorithm_label = tk.Label(stats_frame, text="🧠 Algoritmo: Dijkstra (No calculado)", 
                          bg=COLOR_SIDEBAR, fg="#888", font=("Segoe UI", 9))
algorithm_label.pack(anchor="w", pady=(5, 0))

# Información del historial
history_info = tk.StringVar(value="Historial: 0 acciones | Deshacer: ✗ | Rehacer: ✗")
ttk.Label(stats_frame, textvariable=history_info, font=("Segoe UI", 9), foreground="#888").pack(anchor="w", pady=(5, 0))

# Instrucciones actualizadas
instructions = """
🚨 INFORMACIÓN IMPORTANTE:

🧠 ALGORITMO USADO: Dijkstra
• Calcula el camino más corto
• Ruta se muestra en COLOR AZUL
• Considera distancias reales
• Implementado con NetworkX

🎨 COLORES ACTUALIZADOS:
• RUTA CALCULADA: Azul (#3498db)
• WAYPOINTS: Verde (#2ecc71)
• CIUDADES: Rojo (#E21717)
• CARRETERAS: Gris oscuro (#393E46)

🛣️ MODO DIBUJO MEJORADO:

• Ahora puedes dibujar MÚLTIPLES
  carreteras sin salir del modo

• Después de terminar una carretera,
  puedes empezar otra inmediatamente

• Waypoints dibujados tienen nombres
  especiales (drawn_wp_*)

• Waypoints dibujados NO se conectan
  automáticamente a nada

🗑️ FUNCIONES DE ELIMINACIÓN:

• ELIMINAR CONEXIONES CIUDAD:
  - Selecciona una ciudad (rojo)
  - Elimina TODAS sus conexiones

• ELIMINAR WAYPOINT:
  - Selecciona waypoint (verde)
  - Elimina waypoint + conexiones

• ELIMINAR CONEXIONES WAYPOINT:
  - Selecciona waypoint (verde)
  - Elimina solo sus conexiones
  - Mantiene el waypoint en su lugar

📍 MARACAIBO CORREGIDO:
• Ubicación: [394.0, 271.0]
• Ahora aparece como punto rojo

INSTRUCCIONES DIBUJO:

1. Activa MODO EDICIÓN
2. Click en DIBUJAR CARRETERA
3. Click en un nodo para empezar
4. ARRASTRA para dibujar
5. SUELTA para terminar
6. ¡Puedes dibujar otra inmediatamente!
7. Presiona CANCELAR DIBUJO cuando termines

INSTRUCCIONES NORMALES:
• Click en nodos para seleccionar
• Click en otro nodo para conectar
• Click derecho en rutas para eliminar
• Arrastra nodos para mover
• Ctrl+Z para DESHACER
• Ctrl+Y para REHACER
• Guarda cuando termines

Envía el archivo TXT generado
para que optimice el código.
"""

ttk.Label(sidebar, text=instructions, 
          font=("Segoe UI", 9), foreground="#888", justify="left").pack(anchor="w", pady=(10, 0))

# Panel inferior
info_frame = tk.Frame(root, bg=COLOR_BG, height=40)
info_frame.pack(side="bottom", fill="x", padx=10, pady=5)
path_info = tk.StringVar(value="¡Ruta en AZUL! Usa Dijkstra para calcular camino más corto")
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

# Actualizar estadísticas
road_count.set(f"Rutas: {len(roads)}")
update_history_display()

# Eventos del mouse
canvas.bind("<MouseWheel>", do_zoom)
canvas.bind("<Button-1>", on_canvas_click)
canvas.bind("<B1-Motion>", on_canvas_drag)
canvas.bind("<ButtonRelease-1>", on_canvas_release)
canvas.bind("<Button-3>", on_canvas_click)  # Click derecho

redraw()
root.mainloop()