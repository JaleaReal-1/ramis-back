from app.schemas.user_schema import UserCreate, UserLogin, UserResponse, Token, UserUpdate
from app.schemas.almacen_articulo_schema import ArticuloSchema, TipoArticuloSchema
from app.schemas.almacen_devolucion import DevolucionSchema, ItemDevolucion, DevolucionResponse
from app.schemas.almacen_prestamo import PrestamoSchema, ItemPrestamo, PrestamoResponse, PrestamoDetalleSchema, PrestamoQRData
from app.schemas.vehiculo_schema import VehiculoBase, VehiculoCreate, VehiculoUpdate, VehiculoResponse
from app.schemas.ruta_asignacion_schema import RutaAsignacionBase, RutaAsignacionCreate, RutaAsignacionUpdate, RutaAsignacionResponse, RutaAsignacionFinalizar
from app.schemas.mantenimiento_schema import MantenimientoBase, MantenimientoCreate, MantenimientoUpdate, MantenimientoResponse
