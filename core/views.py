from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import FileResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import AdminRequiredMixin, VendedorRequiredMixin
from clientes.models import Cliente
from comissoes.services.produtividade import (
    avaliar_conquistas,
    avaliar_conquistas_equipe,
    desempenho_usuario,
    equipe_comercial,
    obter_meta,
    ranking_mensal,
)
from relacionamento.services.dashboard import kpis_relacionamento

from .forms import RestaurarBackupForm
from .models import BackupLog, TipoBackup
from .services.backup import gerar_arquivo_backup, restaurar_arquivo_backup


class DashboardView(VendedorRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        hoje = timezone.localdate()

        clientes = Cliente.objects.para_usuario(user).ativos()
        ativos = clientes.filter(categoria='ativo').count()
        adormecidos = clientes.filter(categoria='adormecido').count()
        prospeccao = clientes.filter(categoria='prospeccao').count()
        total = clientes.count()

        context['total_clientes'] = total
        context['clientes_ativos'] = ativos
        context['clientes_adormecidos'] = adormecidos
        context['clientes_prospeccao'] = prospeccao
        context['papel'] = user.get_papel_display()
        context['mes_label'] = f'{hoje.month:02d}/{hoje.year}'

        meta = obter_meta(user, hoje.month, hoje.year)
        context['meta_mensal'] = meta

        estados_qs = (
            clientes.exclude(estado='')
            .values('estado')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
        context['chart_categorias'] = {
            'labels': ['Ativos', 'Adormecidos', 'Prospecção'],
            'values': [ativos, adormecidos, prospeccao],
        }
        context['chart_estados'] = {
            'labels': [e['estado'] for e in estados_qs],
            'values': [e['total'] for e in estados_qs],
        }
        context['sparkline_clientes'] = [prospeccao, adormecidos, ativos, total]

        rel_kpis = kpis_relacionamento(user)
        context.update(rel_kpis)

        desemp = desempenho_usuario(user, hoje.month, hoje.year)
        context['meu_desempenho'] = desemp['progresso']
        context['pontuacao_geral'] = desemp['pontuacao']

        avaliar_conquistas(user, hoje.month, hoje.year)
        if user.is_admin:
            avaliar_conquistas_equipe(hoje.month, hoje.year)
            context['equipe_comercial'] = equipe_comercial(hoje.month, hoje.year)
            context['ranking_comercial'] = ranking_mensal(hoje.month, hoje.year, limit=3)

        realizado_contatos = desemp['realizado']['contatos']
        meta_contatos = meta.meta_contatos if meta else 60
        context['sparkline_contatos'] = [
            0,
            max(realizado_contatos // 4, meta_contatos // 4),
            max(realizado_contatos // 2, meta_contatos // 2),
            max(realizado_contatos, meta_contatos),
        ]
        meta_vendas = float(meta.meta_vendas) if meta else 80000
        realizado_vendas = float(desemp['realizado']['vendas_valor'])
        context['sparkline_vendas'] = [
            0,
            int(max(realizado_vendas * 0.25, meta_vendas * 0.25)),
            int(max(realizado_vendas * 0.5, meta_vendas * 0.5)),
            int(max(realizado_vendas, meta_vendas)),
        ]
        context['top_clientes'] = clientes.filter(categoria='ativo').order_by('nome')[:8]

        pct_ativos = round(ativos / total * 100) if total else 0
        context['pct_ativos'] = pct_ativos

        return context


class BackupGerarView(AdminRequiredMixin, View):
    def get(self, request):
        try:
            buffer, filename = gerar_arquivo_backup()
            BackupLog.objects.create(
                usuario=request.user,
                tipo=TipoBackup.BACKUP,
                observacao=f'Backup gerado: {filename}',
            )
            response = FileResponse(buffer, as_attachment=True, filename=filename)
            response['Content-Type'] = 'application/zip'
            return response
        except Exception as exc:
            messages.error(request, f'Erro ao gerar backup: {exc}')
            return redirect('accounts:perfil')


class BackupRestaurarView(AdminRequiredMixin, View):
    def post(self, request):
        form = RestaurarBackupForm(request.POST, request.FILES)
        if not form.is_valid():
            for error in form.errors.values():
                messages.error(request, error[0])
            return redirect('accounts:perfil')

        try:
            restaurar_arquivo_backup(form.cleaned_data['arquivo'])
            BackupLog.objects.create(
                usuario=None,
                tipo=TipoBackup.RESTORE,
                observacao=f'Restauração via {form.cleaned_data["arquivo"].name}',
            )
            messages.success(
                request,
                'Backup restaurado com sucesso. Faça login novamente com as credenciais do backup.',
            )
            return redirect('accounts:login')
        except ValidationError as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))
        except Exception as exc:
            messages.error(request, f'Erro ao restaurar backup: {exc}')

        return redirect('accounts:perfil')
