import flet as ft
from pymongo import MongoClient

# Conectar a MongoDB
client = MongoClient("mongodb://localhost:27017/")
bd = client["dbtest"]
usuarios_col = bd["usuarios"]
juegos_col = bd["juegos"]
compras_col = bd["compras"]
carrito_col = bd["carrito"]

usuario_id = None  # Se actualizará tras iniciar sesión

def main(page: ft.Page):
    page.title = "Esencia Games"
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = True
    page.window.width = 800
    page.window.height = 600
    page.window.center()

    # --- Función para verificar credenciales ---
    def iniciar_sesion(e):
        global usuario_id
        usuario = usuarios_col.find_one({"email": email_input.value, "password": password_input.value})
        if usuario:
            usuario_id = usuario["_id"]
            cargar_launcher()
        else:
            page.open(ft.SnackBar(ft.Text(f"Credenciales Incorrectas",color="red"))) # PopUp abajo
            page.update()

    # --- Función para registrar usuario ---
    def registrar_usuario(e):
        global usuario_id
        if not email_input.value or not password_input.value:
            page.open(ft.SnackBar(ft.Text(f"Debe Llenar todos los campos",color="red")))
            page.update()
            return
        
        if usuarios_col.find_one({"email": email_input.value}):
            page.open(ft.SnackBar(ft.Text(f"Usuario ya existente",color="red")))
            page.update()
            return
        
        nuevo_usuario = {"email": email_input.value, "password": password_input.value, "saldo": 100}  # Saldo inicial opcional
        usuario_id = usuarios_col.insert_one(nuevo_usuario).inserted_id
        cargar_launcher()

    # --- Función para comprar un juego ---
    def comprar_juego(juego_id):
        if compras_col.find_one({"id_usuario": usuario_id, "id_juego": juego_id}):
            page.open(ft.SnackBar(ft.Text(f"Ya tienes este juego",color="red")))
            page.update()
            return

        # Opcional: Validar saldo
        usuario = usuarios_col.find_one({"_id": usuario_id})
        juego = juegos_col.find_one({"id_juego": juego_id})

        if usuario["saldo"] < juego["precio"]:
            page.open(ft.SnackBar(ft.Text(f"Saldo Insuficiente",color="red")))
            page.update()
            return

        # Registrar compra
        compras_col.insert_one({"id_usuario": usuario_id, "id_juego": juego_id})

        # Descontar saldo
        usuarios_col.update_one({"_id": usuario_id}, {"$inc": {"saldo": -juego["precio"]}})

        # Eliminar del carrito
        carrito_col.delete_one({"id_usuario": usuario_id, "id_juego": juego_id})

        page.open(ft.SnackBar(ft.Text(f"Compra realizada con exito",color="green")))
        page.update()

    # --- Función para cargar la Store ---

    def cargar_store():
        juegos = juegos_col.find()

        return ft.ListView(  # Se usa ListView para scroll
            expand=True,  # Ocupa todo el espacio disponible
            controls=[
                ft.Row([
                    ft.Image(
                        src=j["imagen"],  
                        width=150,
                        height=150,
                        fit=ft.ImageFit.CONTAIN
                    ),
                    ft.Text(f"{j['titulo']} - ${j['precio']}"),
                    ft.IconButton(
                        ft.Icons.SHOPPING_CART,
                        on_click=lambda e, id=j['id_juego']: agregar_al_carrito(id)
                    )
                ])
                for j in juegos
            ]
        )


    # --- Función para cargar el carrito  ---
    def cargar_carrito():

        carrito = carrito_col.find({"id_usuario": usuario_id})

        juegos_carrito = []
        for juegos in carrito:
            juego = juegos_col.find_one({"id_juego": juegos["id_juego"]})
            if juego:
                juegos_carrito.append(
                    ft.Row([
                        ft.Text(juego["titulo"], size=16, weight=ft.FontWeight.BOLD),
                        ft.ElevatedButton("Comprar", on_click=lambda e, j=juego["id_juego"]: comprar_juego(j))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )

        return ft.Column(controls=juegos_carrito if juegos_carrito else [ft.Text("No tienes juegos agregados al carrito todavía")])


    # --- Función para cargar la Biblioteca ---
    def cargar_biblioteca():
        compras = compras_col.find({"id_usuario": usuario_id})
        juegos_biblioteca = []

        for compra in compras:
            juego = juegos_col.find_one({"id_juego": compra["id_juego"]})
            if juego:
                juegos_biblioteca.append(ft.Text(juego["titulo"], size=16, weight=ft.FontWeight.BOLD))

        return ft.Column(controls=juegos_biblioteca if juegos_biblioteca else [ft.Text("No tienes juegos comprados aún.")])

    # --- Función para agregar juegos al carrito ---
    def agregar_al_carrito(juego_id):
        if carrito_col.find_one({"id_usuario": usuario_id, "id_juego": juego_id}):
            page.open(ft.SnackBar(ft.Text(f"El juego ya esta en el carrito",color="orange")))
            page.update()
            return
        
        carrito_col.insert_one({"id_usuario": usuario_id, "id_juego": juego_id, "cantidad": 1})
        page.open(ft.SnackBar(ft.Text(f"Juego Agregado al carrito",color="green")))
        page.update()

    # --- Función para cargar el Launcher ---
    def cargar_launcher():
        page.clean()

        # --- Saldo del usuario ---
        usuario = usuarios_col.find_one({"_id": usuario_id})
        saldo_text = ft.Text(f"Saldo: ${usuario['saldo']}", size=16, weight=ft.FontWeight.BOLD)

        def cambiar_seccion(e):
            if e.control.text == "Store":
                content.controls[1] = cargar_store()
            elif e.control.text == "Biblioteca":
                content.controls[1] = cargar_biblioteca()
            elif e.control.text == "Carrito":
                content.controls[1] = cargar_carrito()
            page.update()

        barra_superior = ft.Row([
            ft.WindowDragArea(
                ft.Container(
                    ft.Text("Esencia Gamesss", size=14),
                    bgcolor=ft.Colors.TRANSPARENT,
                    padding=10,
                    expand=True
                ),
                expand=True
            ),
            saldo_text,
            ft.IconButton(ft.Icons.CLOSE, on_click=lambda _: page.window.close(), icon_color="red")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        sidebar = ft.Column([
            ft.Text("Menú", size=18, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("Store", on_click=cambiar_seccion),
            ft.ElevatedButton("Biblioteca", on_click=cambiar_seccion),
            ft.ElevatedButton("Carrito", on_click=cambiar_seccion)
        ], spacing=10)

        content = ft.Column([
            ft.Text("Store", size=20, weight=ft.FontWeight.BOLD),
            cargar_store()
        ], expand=True)
        
        page.add(
            ft.Column([
                barra_superior,
                ft.Row([
                    sidebar,
                    ft.VerticalDivider(), # Separacion entre el menu y el contenido
                    content
                ], expand=True)
            ])
        )

        page.update()

    # --- UI de Login ---
    email_input = ft.TextField(label="Email", width=300)
    password_input = ft.TextField(label="Contraseña", password=True, width=300)
    login_button = ft.ElevatedButton("Iniciar Sesión", on_click=iniciar_sesion)
    register_button = ft.TextButton("¿No tienes cuenta? Regístrate", on_click=registrar_usuario)
    drag_area = ft.Row([
        ft.WindowDragArea(
            ft.Container(
                    #ft.Text("Esencia Gamesss", size=14),
                    bgcolor=ft.Colors.TRANSPARENT,
                    padding=20,
                    expand=True
                ),
                expand=True
                
        ),
        ft.IconButton(ft.Icons.CLOSE, on_click=lambda _: page.window.close(), icon_color="red")
        ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    login_view = ft.Column([
        ft.Text("Bienvenido a Esencia Games", size=20, weight=ft.FontWeight.BOLD),
        email_input,
        password_input,
        login_button,
        register_button,
        

    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
    page.add(ft.Container(drag_area, alignment=ft.alignment.top_right))
    page.add(ft.Container(login_view, alignment=ft.alignment.center))
    



ft.app(target=main)
