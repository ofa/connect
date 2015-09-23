"""Views for media app."""
# pylint: disable=unused-argument
import json

from django.contrib.auth.decorators import permission_required
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import F
from django.http import HttpResponseRedirect, HttpResponse
from django.views.decorators.http import require_POST
from django.views.generic.list import ListView
from pure_pagination.mixins import PaginationMixin

from open_connect.media.models import Image, ShortenedURL
from open_connect.connect_core.utils.mixins import SortableListMixin
from open_connect.connect_core.utils.views import CommonViewMixin


def image_view(request, image_uuid, image_type='display_image'):
    """Counts image view and redirects to image."""

    # As signing URLs is relatively resource-intensive, and signed links last
    # an entire hour, we can cache the resulting redirect for a bit of time
    cache_key = 'imageurlcache_{type}_{uuid}'.format(
        type=image_type, uuid=image_uuid)
    response = cache.get(cache_key)
    image = Image.objects.defer("exif").filter(uuid=image_uuid)
    if response == None:
        if image_type == 'thumbnail':
            response = image.first().get_thumbnail.url
        else:
            if image_type == 'display_image':
                response = image.first().get_display_image.url
            else:
                response = image.first().image.url

        # Remove the URL from the cache after 45 minutes
        cache.set(cache_key, response, 45*60)

    if image_type != 'thumbnail':
        # Using F queries means we never need to actually select the image
        # once it's already in the cache and can pass the view-increment
        # responsibility to the database
        image.update(view_count=F('view_count') + 1)

    return HttpResponseRedirect(response)


@require_POST
def upload_photos_view(request):
    """Handles AJAX uploading of images."""
    images = []
    for uploaded_file in request.FILES.getlist('file'):
        image = Image.objects.create(image=uploaded_file, user=request.user)
        filelink = '{origin}{path}'.format(
            origin=settings.ORIGIN,
            path=reverse('image', kwargs={'image_uuid': image.uuid}))
        images.append(
            {'filelink': filelink,
             'id': image.pk}
        )
    return HttpResponse(json.dumps(images))


def my_images_view(request):
    """Returns JSON list of images uploaded by a user."""
    images = [
        {'thumb': image.get_thumbnail.url,
         'image': image.get_absolute_url(),
         'id': image.pk}
        for image in Image.objects.filter(user=request.user)[:20]
    ]
    return HttpResponse(json.dumps(images), content_type="application/json")


@require_POST
@permission_required('groups.can_promote_image')
def promote_image_view(request):
    """AJAX view for marking an image as promoted."""
    uuid = request.POST.get('uuid')
    Image.objects.filter(uuid=uuid).update(promoted=True)
    return HttpResponse(json.dumps({'status': 'success', 'uuid': uuid}))


@require_POST
@permission_required('groups.can_promote_image')
def demote_image_view(request):
    """AJAX view for unmarking a promoted image."""
    uuid = request.POST.get('uuid')
    Image.objects.filter(uuid=uuid).update(promoted=False)
    return HttpResponse(json.dumps({'status': 'success', 'uuid': uuid}))


class AdminGalleryView(CommonViewMixin, PaginationMixin, ListView):
    """Gallery for administrators to see all images posted to groups."""
    model = Image
    template_name = 'media/admin_gallery.html'
    nav_active_item = 'Admin'
    dd_active_item = 'Admin Gallery'
    context_object_name = 'images'

    def get_queryset(self):
        """Limit queryset to images posted to groups."""
        return Image.popular.with_user(self.request.user)


def shortened_url_redirect(request, code):
    """Increase ShortenedURL counter and redirect user."""
    url = ShortenedURL.objects.get(short_code=code)
    url.click()
    return HttpResponseRedirect(url.url)


class URLPopularityView(PaginationMixin, SortableListMixin, ListView):
    """Display list of popular urls."""
    model = ShortenedURL
    paginate_by = 10
    valid_order_by = [
        'message_count', 'url', 'short_code', 'created_at', 'click_count']
    default_order_by = 'click_count'
    default_sort = 'desc'
    context_object_name = 'urls'

    def get_context_data(self, **kwargs):
        """Update context for the view."""
        context = super(URLPopularityView, self).get_context_data(**kwargs)
        context['nav_active_item'] = 'Admin'
        context['dd_active_item'] = 'Popular URLs'
        return context
