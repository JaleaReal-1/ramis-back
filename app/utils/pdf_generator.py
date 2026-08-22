from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import base64
import os
from datetime import datetime

from app.config.company_config import COMPANY

def guardar_firma_base64(firma_base64: str, file_id: str, folder: str = "static/firmas") -> str:
    """Decodifica una firma base64 y la guarda como archivo PNG."""
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    
    # Remover prefijo si existe
    if "," in firma_base64:
        firma_base64 = firma_base64.split(",")[1]
        
    firma_bytes = base64.b64decode(firma_base64)
    firma_path = os.path.join(folder, f"firma_{file_id}.png")
    with open(firma_path, "wb") as f:
        f.write(firma_bytes)
    return firma_path

def generar_pdf_prestamo(prestamo) -> str:
    os.makedirs("static/prestamos", exist_ok=True)
    file_path = f"static/prestamos/prestamo_{prestamo.id}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=20)

    styles = getSampleStyleSheet()
    elements = []
    style_title = ParagraphStyle('TitleCentered', parent=styles['Title'], alignment=1)
    style_header = ParagraphStyle('HeaderCentered', parent=styles['Normal'], alignment=1, spaceAfter=2)
    style_worker = ParagraphStyle('WorkerData', parent=styles['Normal'], spaceAfter=4)
    style_footer = ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)
    
    logo_path = "static/logo.jpg"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=80, height=80)
    else:
        logo = Paragraph("", styles['Normal'])

    empresa_info = [
        Paragraph(f"<b>{COMPANY['nombre']}</b>", style_title),
        Paragraph(f"RUC: {COMPANY['ruc']}", style_header),
        Paragraph(COMPANY['direccion'], style_header),
        Paragraph(f"Cel: {COMPANY['telefono']}", style_header),
        Paragraph(f"Email: {COMPANY['email']}", style_header),
        Paragraph(f"Web: {COMPANY['web']}", style_header),
    ]
    header_table = Table([
        [logo, empresa_info, Paragraph(f"<b>Código:</b> {prestamo.codigo_unico}", styles['Normal'])]
    ], colWidths=[90, 330, 100])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>DOCUMENTO DE PRÉSTAMO DE EQUIPOS</b>", style_title))
    elements.append(Spacer(1, 15))
    worker_data = [
        f"<b>Trabajador:</b> {prestamo.nombres_completos}",
        f"<b>DNI:</b> {prestamo.dni}",
        f"<b>Cargo:</b> {prestamo.cargo}",
        f"<b>Fecha préstamo:</b> {prestamo.fecha_prestamo}",
        f"<b>Fecha devolución:</b> {prestamo.fecha_devolucion_prevista}",
    ]
    for d in worker_data:
        elements.append(Paragraph(d, style_worker))

    elements.append(Spacer(1, 15))
    table_data = [["Artículo", "Cantidad"]]
    for det in prestamo.detalles:
        table_data.append([det.articulo_nombre, str(det.cantidad_prestada)])

    table = Table(table_data, colWidths=[400, 120])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    if prestamo.firma_base64:
        firma_path = guardar_firma_base64(prestamo.firma_base64, f"prestamo_{prestamo.id}", "static/prestamos")
        elements.append(Paragraph("<b>Firma del trabajador:</b>", styles['Normal']))
        elements.append(Spacer(1, 10))
        elements.append(Image(firma_path, width=200, height=80))

    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", style_footer))
    doc.build(elements)

    return file_path

def generar_pdf_ruta(ruta) -> str:
    os.makedirs("static/rutas", exist_ok=True)
    file_path = f"static/rutas/ruta_{ruta.id}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=20)

    styles = getSampleStyleSheet()
    elements = []
    style_title = ParagraphStyle('TitleCentered', parent=styles['Title'], alignment=1)
    style_header = ParagraphStyle('HeaderCentered', parent=styles['Normal'], alignment=1, spaceAfter=2)
    style_worker = ParagraphStyle('WorkerData', parent=styles['Normal'], spaceAfter=4)
    style_footer = ParagraphStyle('Footer', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.grey)
    
    logo_path = "static/logo.jpg"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=80, height=80)
    else:
        logo = Paragraph("", styles['Normal'])

    empresa_info = [
        Paragraph(f"<b>{COMPANY['nombre']}</b>", style_title),
        Paragraph(f"RUC: {COMPANY['ruc']}", style_header),
        Paragraph(COMPANY['direccion'], style_header),
        Paragraph(f"Cel: {COMPANY['telefono']}", style_header),
        Paragraph(f"Email: {COMPANY['email']}", style_header),
        Paragraph(f"Web: {COMPANY['web']}", style_header),
    ]
    header_table = Table([
        [logo, empresa_info, Paragraph(f"<b>Código Ruta:</b> #{ruta.id}", styles['Normal'])]
    ], colWidths=[90, 330, 100])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>HOJA DE RUTA Y ASIGNACIÓN DE VEHÍCULO</b>", style_title))
    elements.append(Spacer(1, 15))
    
    trabajador_nombre = f"{ruta.trabajador.nombre} {ruta.trabajador.apellidos}" if getattr(ruta, "trabajador", None) else "N/A"
    placa_vehiculo = ruta.vehiculo.placa if getattr(ruta, "vehiculo", None) else "N/A"
    
    route_data = [
        f"<b>Trabajador / Conductor:</b> {trabajador_nombre}",
        f"<b>Vehículo (Placa):</b> {placa_vehiculo}",
        f"<b>Origen:</b> {ruta.origen}",
        f"<b>Destino:</b> {ruta.destino}",
        f"<b>Fecha de Salida:</b> {ruta.fecha_salida.strftime('%d/%m/%Y %H:%M') if isinstance(ruta.fecha_salida, datetime) else ruta.fecha_salida}",
        f"<b>Fecha de Llegada Estimada:</b> {ruta.fecha_llegada_estimada.strftime('%d/%m/%Y %H:%M') if isinstance(ruta.fecha_llegada_estimada, datetime) else ruta.fecha_llegada_estimada}",
        f"<b>Kilometraje de Salida:</b> {ruta.kilometraje_salida} km",
        f"<b>Combustible de Salida:</b> {ruta.combustible_salida}",
    ]
    for d in route_data:
        elements.append(Paragraph(d, style_worker))

    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("<b>Inspección Obligatoria de Seguridad:</b>", styles['Normal']))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"• Frenos: {'Aprobado (OK)' if getattr(ruta, 'check_frenos', False) else 'No verificado'}", styles['Normal']))
    elements.append(Paragraph(f"• Luces: {'Aprobado (OK)' if getattr(ruta, 'check_luces', False) else 'No verificado'}", styles['Normal']))
    elements.append(Paragraph(f"• Llantas: {'Aprobado (OK)' if getattr(ruta, 'check_llantas', False) else 'No verificado'}", styles['Normal']))
    
    elements.append(Spacer(1, 20))
    if getattr(ruta, "firma_trabajador", None):
        firma_path = guardar_firma_base64(ruta.firma_trabajador, f"ruta_{ruta.id}", "static/firmas")
        elements.append(Paragraph("<b>Firma de conformidad del trabajador:</b>", styles['Normal']))
        elements.append(Spacer(1, 10))
        elements.append(Image(firma_path, width=200, height=80))

    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", style_footer))
    doc.build(elements)

    return file_path
