from z3c.form import validator, error
import zope.interface
import zope.component

from zope.interface import Interface, Attribute
from collective.plonetruegallery.interfaces import \
    IGalleryAdapter, IBaseSettings
from collective.plonetruegallery.validators import \
    Data
from collective.plonetruegallery.utils import getGalleryAdapter

#dont know if next line is needed
from zope.interface import implements
from collective.plonetruegallery.galleryadapters.base import BaseAdapter
from zope import schema

from zope.i18nmessageid import MessageFactory

_ = MessageFactory('collective.ptg.picasa')

try:
    import gdata.photos.service
    from gdata.photos.service import GooglePhotosException
except:
    pass


def add_condition():
    try:
        import gdata.photos.service
        from gdata.photos.service import GooglePhotosException
    except:
        return False
    return True

GDATA = {}
DATA_FEED_URL = '/data/feed/api/user/%s/album' + \
                '/%s?kind=photo&imgmax=%s&thumbsize=%sc'

def empty(v):
    return v is None or len(v.strip()) == 0

class IPicasaGallerySettings(IBaseSettings):
    picasa_username = schema.TextLine(
        title=_(u"label_picasa_username", default=u"GMail address"),
        description=_(u"description_picasa_username",
            default=u"GMail address of who this album belongs to. "
                    u"(*Picasa* gallery type)"
        ),
        required=False)
    picasa_album = schema.TextLine(
        title=_(u"label_picasa_album", default=u"Picasa Album"),
        description=_(u"description_picasa_album",
            default=u"Name of your picasa web album. "
                    u"This will be the qualified name you'll see in "
                    u"the address bar or the full length name of the "
                    u"album. (*Picasa* gallery type)"
        ),
        required=False)


class IPicasaAdapter(IGalleryAdapter):
    """
    """

    gd_client = Attribute("property for gd_client instance")

    def get_album_name(name, user):
        """
        Returns the selected album name and user.
        Uses name and user in settings if not specified.
        """

    def feed():
        """
        Returns the picasa feed for the given album.
        """

class PicasaAdapter(BaseAdapter):
    implements(IPicasaAdapter, IGalleryAdapter)

    schema = IPicasaGallerySettings
    name = u"picasa"
    description = _(u"label_picasa_gallery_type",
        default=u"Picasa Web Albums")

    sizes = {
        'small': {
            'width': 320,
            'height': 320
        },
        'medium': {
            'width': 576,
            'height': 576
        },
        'large': {
            'width': 800,
            'height': 800
        },
        'thumb': {
            'width': 72,
            'height': 72
        }
    }

    def get_gd_client(self):
        uid = self.gallery.UID()
        if uid in GDATA:
            return GDATA[uid]
        else:
            self.gd_client = gdata.photos.service.PhotosService()
            return GDATA[uid]

    def set_gd_client(self, value):
        GDATA[self.gallery.UID()] = value

    gd_client = property(get_gd_client, set_gd_client)

    def assemble_image_information(self, image):
        return {
            'image_url': image.content.src,
            'thumb_url': image.media.thumbnail[0].url,
            'link': image.content.src,
            'title': image.title.text,
            'description': image.summary.text or ''
        }

    def get_album_name(self, name=None, user=None):
        if name is None:
            name = self.settings.picasa_album
        name = name.strip()

        if user is None:
            user = self.settings.picasa_username
        user = user.strip()

        feed = self.gd_client.GetUserFeed(user=user)
        for entry in feed.entry:
            if entry.name.text.decode("utf-8") == name or \
                entry.title.text.decode("utf-8") == name:
                return entry.name.text

        return None

    def feed(self):
        gd_client = self.gd_client

        try:
            url = DATA_FEED_URL % (
                self.settings.picasa_username,
                self.get_album_name(),
                self.sizes[self.settings.size]['width'],
                self.sizes['thumb']['width']
            )
            feed = gd_client.GetFeed(url)
            return feed
        except GooglePhotosException, inst:
            #Do not show anything if connection failed
            self.log_error(GooglePhotosException, inst,
                "Error getting photo feed")
            return None

    def retrieve_images(self):
        try:
            picasaGallery = self.feed()
            images = [self.assemble_image_information(i)
                for i in picasaGallery.entry]
            return images
        except Exception, inst:
            self.log_error(Exception, inst, "Error getting all images")
            return []

class PicasaUsernameValidator(validator.SimpleFieldValidator):

    def validate(self, username):
        settings = Data(self.view)
        if settings.gallery_type != 'picasa':
            return

        if empty(username):
            raise zope.schema.ValidationError(
                _(u"label_validate_picasa_specify_username",
                default=u"You must specify a picasa username."),
                True
            )
validator.WidgetValidatorDiscriminators(PicasaUsernameValidator,
    field=IPicasaGallerySettings['picasa_username'])
zope.component.provideAdapter(PicasaUsernameValidator)


class PicasaAlbumValidator(validator.SimpleFieldValidator):

    def validate(self, album):
        settings = Data(self.view)

        if settings.gallery_type != 'picasa':
            return

        username = settings.picasa_username

        if empty(album):
            raise zope.schema.ValidationError(
                _(u"label_validate_picasa_ablum_empty",
                default=u"You must specify a picasa album."),
                True
            )
        if empty(username):
            # do not continue validation until they have a valid username
            return
        adapter = getGalleryAdapter(self.context, self.request,
                                    gallery_type=settings.gallery_type)
        found = adapter.get_album_name(name=album, user=username)

        if found is None:
            raise zope.schema.ValidationError(
                _(u"label_validate_picasa_find_album",
                default=u"Could not find album."),
                True
            )
validator.WidgetValidatorDiscriminators(PicasaAlbumValidator,
    field=IPicasaGallerySettings['picasa_album'])
zope.component.provideAdapter(PicasaAlbumValidator)

            
            
