from io import BytesIO

from django.template.loader import render_to_string


def gerar_pdf_historico_cliente(context):
    from xhtml2pdf import pisa

    html = render_to_string('relacionamento/pdf/historico_cliente.html', context)
    buffer = BytesIO()
    pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    buffer.seek(0)
    return buffer
