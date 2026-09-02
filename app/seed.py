"""Seed data para desarrollo. Ejecutar: python -m app.seed"""
from app.database import SessionLocal, engine, Base
from app.models.cliente import Cliente, Contacto
from app.models.proveedor import Proveedor
from app.models.producto import Producto

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Clientes de ejemplo
if not db.query(Cliente).first():
    cli1 = Cliente(razon_social="SpA Viñedos del Sur", rut="76.123.456-7", direccion="Av. Providencia 1234, Santiago", giro="Comercio al por mayor de vinos")
    cli2 = Cliente(razon_social="Constructora Los Andes Ltda", rut="89.234.567-0", direccion="San Bernardo 567, Santiago", giro="Construcción")
    cli3 = Cliente(razon_social="TechHub SpA", rut="78.345.678-1", direccion="Av. Apoquindo 3000, Las Condes", giro="Tecnología")
    db.add_all([cli1, cli2, cli3])
    db.flush()

    db.add_all([
        Contacto(cliente_id=cli1.id, nombre="María Paz Soto", cargo="Gerente Compra", email="mpoto@vinos.cl", telefono="+56912345678", es_principal=True),
        Contacto(cliente_id=cli1.id, nombre="Andrés Reyes", cargo="Jefe Logística", email="areyes@vinos.cl", telefono="+56987654321", es_principal=False),
        Contacto(cliente_id=cli2.id, nombre="Roberto Fuentes", cargo="Director de Operaciones", email="rfuentes@losandes.cl", telefono="+56911223344", es_principal=True),
        Contacto(cliente_id=cli3.id, nombre="Camila Vega", cargo="Head of Ops", email="cvega@techhub.cl", telefono="+56955667788", es_principal=True),
    ])

# Proveedores de ejemplo
if not db.query(Proveedor).first():
    db.add_all([
        Proveedor(razon_social="Guangzhou Textile Co.", tax_id="CN-91440100MA5D", pais_origen="China", etiquetas_productos=["Poleras", "Polos", "Gorros"]),
        Proveedor(razon_social="Alpaca Wear SAC", tax_id="PE-20512345678", pais_origen="Perú", etiquetas_productos=["Poleras Algodón", "Bordado"]),
        Proveedor(razon_social="PrintMaster Brasil", tax_id="BR-12.345.678/0001-90", pais_origen="Brasil", etiquetas_productos=["Sublimación", "DTF", "Full Print"]),
    ])

# Productos de ejemplo
if not db.query(Producto).first():
    db.add_all([
        Producto(nombre="Polera Básica Algodón", descripcion="Polera unicolor 100% algodón, tallas S-XXL", unidad="Unidad"),
        Producto(nombre="Polera Dri-Fit", descripcion="Polera deportiva material sintético, tallas S-XXL", unidad="Unidad"),
        Producto(nombre="Gorro Beanie", descripcion="Gorro tejido con etiqueta bordada", unidad="Unidad"),
        Producto(nombre="Polo Clásico", descripcion="Polo 2 botones, cuello rib, tallas S-XXL", unidad="Unidad"),
        Producto(nombre="Chaqueta Softshell", descripcion="Chaqueta impermeable con cierre, bordable", unidad="Unidad"),
        Producto(nombre="Tote Bag Algodón", descripcion="Bolsa tote 10oz, asas reforzadas", unidad="Unidad"),
        Producto(nombre="Gorra Structured", descripcion="Gorra structured 6 paneles, cierre adjustable", unidad="Unidad"),
        Producto(nombre="Bufanda Rústica", descripcion="Bufanda tejida con etiqueta personalizada", unidad="Unidad"),
    ])

db.commit()
db.close()
print("Seed data insertado correctamente")
