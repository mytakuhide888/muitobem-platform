from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import ScheduledPost
from .services.post_importer import full_import, sync_latest


@staff_member_required
@require_POST
def import_posts(request):
    count = full_import()
    messages.success(request, f'{count}件取り込みました。')
    return redirect('admin:social_post_changelist')


@staff_member_required
@require_POST
def sync_posts(request):
    count = sync_latest()
    messages.success(request, f'{count}件同期しました。')
    return redirect('admin:social_post_changelist')


@staff_member_required
@require_POST
def approve_scheduled(request, pk):
    obj = get_object_or_404(ScheduledPost, pk=pk)
    if obj.status == ScheduledPost.Status.DRAFT:
        obj.status = ScheduledPost.Status.APPROVED
        obj.save()
        messages.success(request, '承認しました。')
    return redirect('admin:social_scheduledpost_change', pk)
