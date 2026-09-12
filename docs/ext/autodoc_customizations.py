"""Customizations to the autodoc functionalities"""

import sphinx.ext.autodoc as ad


def setup(app):
    # avoid adding "alias of xyz"
    ad.GenericAliasMixin.update_content = ad.DataDocumenterMixinBase.update_content

    return {'parallel_read_safe': True}
