from required_classes import Ambiente, Colonia, Tipo_Bacteria
import matplotlib.pyplot as plt #grilla y grafico 
import numpy as np
from matplotlib.patches import Patch #grilla
import gi 
import sys 
import cairo #genera una imagen en cada paso (para que pueda graficar se pasa a imagen el grafico)
import io #<--#hace un buffer                (asi se ve la expansion de las bacterias)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gio, Adw, Gdk, GLib

provider = Gtk.CssProvider()
provider.load_from_path("style.css")

def contador_de_resistencia(datos, total_pasos):
  arr = [0 for i in range(total_pasos)]
  for clave, valor in datos.items():
    for bacteria in valor:
      if bacteria[3] == True:
        arr[clave-1] += 1
  return arr

class Simulador(Gtk.ApplicationWindow):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    
    # Configuración de la ventana principal
    self.set_title("Simulador de bacterias")
    self.set_default_size(1000, 1000)

    # Crea la colonia 
    self.colonia = Colonia()

    self.curr_grilla = np.zeros((20, 20), dtype=int)

    # state system
    self.pasos_totales = 0
    self.paso_actual = 0
    self.activas = 0
    self.muertas = 0
    self.resistentes = 0
    self.biofilm = 0
    self.ini_energia = 0
    self.div_energia = 0

    # Crear el layout principal
    self.setup_ui()
    self.setup_css()
    self.setup_modal()
  
    # Pasos es el número de iteraciones que se ejecutarán en la simulación
  def run(self, pasos=0):
    
    if pasos <= 0:
      print("Número de pasos debe ser mayor que 0.")
      return
      # Graficar los resultados del paso actual
      # self.graficar_crecimiento()
      # self.graficar_resistencia()
    GLib.timeout_add(2000, self.update_screen)

  def graficar_crecimiento(self): 
    # TODO: Poner gráfico de doble barra muertas y activas
    crecimiento = [len(self.colonia.datos[i+1]) for i in range(self.pasos_totales)]
    pasos = [i+1 for i in range(self.pasos_totales)]
    plt.plot(pasos, crecimiento, marker='o', linestyle='-', color='blue')
    plt.xlabel('Pasos')
    plt.ylabel('Número de Bacterias')
    plt.title('Gráfico de Crecimiento de Bacterias')
    
  def graficar_resistencia(self):
    # Vertical Bar Plot
    resistencia = contador_de_resistencia(self.colonia.datos, self.pasos_totales)
    pasos = [i+1 for i in range(self.pasos_totales)]
    plt.bar(pasos, resistencia, color='skyblue')
    plt.xlabel('Pasos')
    plt.ylabel('Resistencia')
    plt.title('Gráfico de Resistencia de Bacterias')
    plt.show()

  def random_values(self):
    
    # Definimos posiciones de bacterias activas (1), muertas (2), resistentes (3), biofilm (4)   
    ambiente = Ambiente()

    # Difusión de elementos en la grilla 
    ambiente.difundir_nutrientes()
    ambiente.difundir_factor_ambiental()
    bacterias = ambiente.difundir_bacterias(
      total_activas=self.activas,
      total_muertas=self.muertas,
      total_biofilm=self.biofilm,
      ini_energia=self.ini_energia
    )

    self.colonia.set_bacterias(bacterias)
    self.colonia.set_ambiente(ambiente)
    self.colonia.set_div_energia(self.div_energia)
    self.colonia.set_pasos_totales(self.pasos_totales)

    self.curr_grilla = self.colonia.ambiente.aplicar_ambiente()
    
    GLib.timeout_add(2000, self.forzar_grafico)

  def setup_css(self):
    # css
    provider = Gtk.CssProvider()
    provider.load_from_path("style.css")  
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

  def screen(self):
    # Drawing Area
    screen_frame = Gtk.Frame()
    self.drawing_area = Gtk.DrawingArea()
    self.drawing_area.set_content_width(400)
    self.drawing_area.set_content_height(400)
    self.drawing_area.set_draw_func(self.on_draw)
    screen_frame.set_child(self.drawing_area)

    # Frame dentro de un contenedor (por si quieres agregar más cosas después)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.append(screen_frame)
    
    self.main_box.append(box)

    # Crear primer grafico 
    self.create_plot()
  
  def update_screen(self):
      
    self.curr_grilla, paso_actual = self.colonia.paso()

    if paso_actual > self.pasos_totales:
      return False

    datos = {
      "paso_actual": paso_actual,
      "activas": 0,
      "muertas": 0,
      "resistentes": 0,
      "biofilm": 0,
      "ini_energia": self.ini_energia,
      "div_energia": self.div_energia
    }

    for fila in self.curr_grilla:
      for valor in fila:  
        if valor == Tipo_Bacteria.ACTIVA.value: 
          datos["activas"] += 1
        elif valor == Tipo_Bacteria.MUERTA.value:
          datos["muertas"] += 1
        elif valor == Tipo_Bacteria.RESISTENTE.value:
          datos["resistentes"] += 1
        elif valor == Tipo_Bacteria.BIOFILM.value:
          datos["biofilm"] += 1

    self.update_state_ui(**datos)  

    self.forzar_grafico()

    if paso_actual <= self.pasos_totales:
      return True
  
  def forzar_grafico(self):
    # Volver a crear el gráfico
    self.create_plot()
    # Forzar redibujado 
    self.drawing_area.queue_draw()

  def create_plot(self):

    cmap = plt.cm.get_cmap('Set1', 5)
    fig , ax = plt.subplots(figsize=(8, 4))
    cax = ax.matshow(self.curr_grilla, cmap=cmap)
    ax.set_title("Grilla")

    legend_elements = [
      Patch(facecolor=cmap(1/5) , label='Bacteria activa'),
      Patch(facecolor=cmap(2/5) , label='Bacteria muerta'),
      Patch(facecolor=cmap(3/5) , label='Bacteria resistente'),
      Patch(facecolor=cmap(4/5) , label='Biofilm'),
    ]

    ax.legend(handles=legend_elements , loc='upper right', bbox_to_anchor=(1.7 , 1))
    ax.set_xticks(np.arange (0, 20, 1))
    ax.set_yticks(np.arange (0, 20, 1))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.grid(color='gray', linestyle='-', linewidth=0.5)

    # mostrar valores en cada celda
    for i in range(20):
      for j in range(20):
        val = self.curr_grilla[i,j]
        if val > 0:
          ax.text(j, i, int(val), va='center', ha='center', color='white')

    # Guardar en buffer PNG
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    self.image_surface = cairo.ImageSurface.create_from_png(buf)
    plt.close(fig)  # Evitar acumular figuras

  def on_draw(self, area, cr, width, height):
    cr.set_source_surface(self.image_surface, 0, 0)
    cr.paint()

  def setup_modal(self):
  
    # Set Dialog
    self.dialog = Adw.Dialog.new()
    self.dialog.set_content_width(500)
    self.dialog.set_content_height(500)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    # Simulamos un HeaderBar dentro del diálogo
    header = Adw.HeaderBar()
    header.set_title_widget(Gtk.Label(label="Configuración"))
    box.append(header)

    page = Adw.PreferencesPage()
    group = Adw.PreferencesGroup(title="Parámetros iniciales")
  
    # Pasos Input
    # Gtk.Adjustment.new(
    #   value_inicial = 0,
    #   min = 0,
    #   max = 100,
    #   step_increment = 1,    # <--- solo permite incrementar/decrementar en 1
    #   page_increment = 10,
    #   page_size = 0
    # )

    # Input pasos totales
    adjustment = Gtk.Adjustment.new(0, 0, 100, 1, 10, 0)
    self.pasos_input = Adw.SpinRow.new(
                                        adjustment=adjustment,
                                        climb_rate=1,
                                        digits=0
                                       )
    self.pasos_input.set_title("<b>⏱️ Pasos totales</b>")
    

    # Input bacterias activas
    adjustment2 = Gtk.Adjustment.new(0, 0, 100, 1, 10, 0)
    self.bac_activas_input = Adw.SpinRow.new(
                                        adjustment=adjustment2,
                                        climb_rate=1,
                                        digits=0
                                       )    
    self.bac_activas_input.set_title("<b>🟥 Bacterias activas</b>")

    # Input biofilm
    adjustment3 = Gtk.Adjustment.new(0, 0, 100, 1, 10, 0)
    self.biofilm_input = Adw.SpinRow.new(
                                        adjustment=adjustment3,
                                        climb_rate=1,
                                        digits=0
                                      )
    self.biofilm_input.set_title("<b>🟪 Biofilm</b>")
    
    # Input energía inicial
    adjustment4 = Gtk.Adjustment.new(0, 0, 100, 1, 10, 0)
    self.init_energia_input = Adw.SpinRow.new(
                                        adjustment=adjustment4,
                                        climb_rate=1,
                                        digits=0
                                      )
    self.init_energia_input.set_title("<b>⚡Energia inicial</b>")

    # Input Energía de división
    adjustment5 = Gtk.Adjustment.new(0, 0, 100, 1, 10, 0)
    self.div_energia_input = Adw.SpinRow.new(
                                        adjustment=adjustment5,
                                        climb_rate=1,
                                        digits=0
                                      )
    self.div_energia_input.set_title("<b>🧫Energia división</b>")

    group.add(self.pasos_input)
    group.add(self.bac_activas_input)
    group.add(self.biofilm_input)
    group.add(self.init_energia_input)
    group.add(self.div_energia_input)
  
    page.add(group)
    
    # Botones de acción
    button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    button_box.set_halign(Gtk.Align.CENTER)
    
    accept_btn = Gtk.Button(label="Aceptar")
    accept_btn.connect("clicked", self.set_state)
    button_box.append(accept_btn)
    
    clear_btn = Gtk.Button(label="Limpiar Todo")
    clear_btn.connect("clicked", self.on_clear_system)
    button_box.append(clear_btn)
    
    box.append(page)
    box.append(button_box)
  
    self.dialog.set_child(box)

  def state_ui(self):
    # Sección de estado del sistema
    state_frame = Gtk.Frame(label="Estado del sistema")
    state_box = Adw.WrapBox(orientation=Gtk.Orientation.HORIZONTAL)
    state_box.set_margin_top(10)
    state_box.set_margin_bottom(10)
    state_box.set_margin_start(10)
    state_box.set_margin_end(10)
    state_box.set_child_spacing(10)
    state_box.set_line_spacing(10)

    bin = Adw.Bin()
    self.scale_label = Gtk.Label(label=f"⏱️ Paso actual: {round(self.paso_actual)}")
    bin.set_child(self.scale_label)
    bin.set_css_classes(["bin-container"])
    state_box.append(bin)

    bin2 = Adw.Bin()
    self.scale_label2 = Gtk.Label(label=f"🟥 Bacterias activas: {round(self.activas)}")
    bin2.set_child(self.scale_label2)
    bin2.set_css_classes(["bin-container"])
    state_box.append(bin2)

    bin3 = Adw.Bin()
    self.scale_label3 = Gtk.Label(label=f"⬛ Bacterias muertas: {round(self.muertas)}")
    bin3.set_child(self.scale_label3)
    bin3.set_css_classes(["bin-container"])
    state_box.append(bin3)  

    bin4 = Adw.Bin()
    self.scale_label4 = Gtk.Label(label=f"🟧​ Bacterias resistentes: {round(self.resistentes)}")
    bin4.set_child(self.scale_label4)
    bin4.set_css_classes(["bin-container"])
    state_box.append(bin4)  

    bin5 = Adw.Bin()
    self.scale_label5 = Gtk.Label(label=f"🟪 Biofilm: {round(self.biofilm)}")
    bin5.set_child(self.scale_label5)
    bin5.set_css_classes(["bin-container"])
    state_box.append(bin5)

    bin6 = Adw.Bin()
    self.scale_label6 = Gtk.Label(label=f"⚡Energia inicial: {round(self.ini_energia)}")
    bin6.set_child(self.scale_label6)
    bin6.set_css_classes(["bin-container"])
    state_box.append(bin6)

    bin7 = Adw.Bin()
    self.scale_label7 = Gtk.Label(label=f"🧫Energia división: {round(self.div_energia)}")
    bin7.set_child(self.scale_label7)
    bin7.set_css_classes(["bin-container"])
    state_box.append(bin7)

    state_frame.set_child(state_box)
    self.main_box.append(state_frame)

  def update_state_ui(self, paso_actual, activas, muertas, resistentes, biofilm, ini_energia, div_energia):
    self.scale_label.set_label(f"⏱️ Paso actual: {round(paso_actual)}")
    self.scale_label2.set_label(f"🟥 Bacterias activas: {round(activas)}")
    self.scale_label3.set_label(f"⬛ Bacterias muertas: {round(muertas)}")
    self.scale_label4.set_label(f"🟧​ Bacterias resistentes: {round(resistentes)}")
    self.scale_label5.set_label(f"🟪 Biofilm: {round(biofilm)}")
    self.scale_label6.set_label(f"⚡Energia inicial: {round(ini_energia)}")
    self.scale_label7.set_label(f"🧫Energia división: {round(div_energia)}")

  def setup_ui(self):

    # HeaderBar 
    header = Adw.HeaderBar()
    self.set_titlebar(header)

    # (opcional) otro botón
    button2 = Gtk.Button()
    button2.connect("clicked", self.on_open_modal)
    icon2 = Gtk.Image.new_from_icon_name("applications-system")
    button2.set_child(icon2)
    header.pack_start(button2)

    # Crear un botón con icono
    content = Adw.ButtonContent()
    content.set_icon_name("x-office-document-template")
    content.set_label("Descargar csv")
    content.add_css_class("mi-boton-content")

    button = Gtk.Button()
    button.connect("clicked", self.colonia.exportar_csv)
    
    button.set_child(content)
    # Agregar el botón al lado izquierdo (start)
    header.pack_start(button)

    # Crear un botón con icono
    content2 = Adw.ButtonContent()
    content2.set_icon_name("x-office-spreadsheet")
    content2.set_label("Gráficos")
    # content2.add_css_class("mi-boton-content")
    button2 = Gtk.Button()
    button2.set_child(content2)
    # Agregar el botón al lado izquierdo (start)
    header.pack_start(button2)

    # Box principal vertical
    self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    self.main_box.set_margin_top(10)
    self.main_box.set_margin_bottom(10)
    self.main_box.set_margin_start(10)
    self.main_box.set_margin_end(10)
  
    self.box1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    self.box1.set_margin_top(10)
    self.box1.set_margin_bottom(10)
    self.box1.set_margin_start(10)
    self.box1.set_margin_end(10)

    self.screen()

    self.main_box.append(self.box1)

    # Separador
    self.separator = Gtk.Separator()
    self.main_box.append(self.separator)

    # Crea la barra de estado del sistema
    self.state_ui()

     # Crear un botón con icono
    content3= Adw.ButtonContent()
    content3.set_icon_name("media-playback-start")
    content3.set_label("Start")
    button3 = Gtk.Button()
    button3.connect("clicked", lambda btn: self.run(self.pasos_totales))
    button3.set_child(content3)
    # Agregar el botón al lado izquierdo (start)
    self.main_box.append(button3)

    # Establecer el contenido de la ventana
    self.set_child(self.main_box)

  def on_open_modal(self, button):
    self.dialog.present(parent=self)

  def on_clear_system(self, button):
    self.pasos_input.set_value(0)
    self.bac_activas_input.set_value(0)
    self.biofilm_input.set_value(0)
    self.init_energia_input.set_value(0)
    self.div_energia_input.set_value(0)

  def set_state(self, button):
    self.pasos_totales = round(self.pasos_input.get_value())
    self.paso_actual = 0
    self.activas = round(self.bac_activas_input.get_value())
    self.resistentes = 0
    self.muertas = 0
    self.biofilm = round(self.biofilm_input.get_value())
    self.ini_energia = round(self.init_energia_input.get_value())
    self.div_energia = round(self.div_energia_input.get_value())
    datos = {
      "paso_actual": self.paso_actual,
      "activas": self.activas,
      "muertas": self.muertas,
      "resistentes": self.resistentes,
      "biofilm": self.biofilm,
      "ini_energia": self.ini_energia,
      "div_energia": self.div_energia
    }
    self.update_state_ui(**datos)  
    self.random_values()
    self.on_close_modal()

  def on_close_modal(self):
    if self.dialog.get_can_close():
      self.dialog.close()

  def on_clear_clicked(self, button):
    # Lógica para limpiar la simulación
    pass
    
  def show_about(self, button):
    pass

class Main(Adw.Application):
  def __init__(self, **kwargs):
      super().__init__()
      self.connect("activate", self.on_activate)

  def on_activate(self, app):
      
      self.win = Simulador(application=app)
      self.win.present()

def main():
    app = Main(application_id="com.simulador.bacterias")
    return app.run(sys.argv)

if __name__ == "__main__":
    main() 

   
