from django.views.generic import TemplateView

from accounts.mixins import VendedorRequiredMixin

from .services.context import build_powerup_context


class PowerUPView(VendedorRequiredMixin, TemplateView):
    template_name = 'powerup/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_powerup_context(self.request))
        return context
