# some_other_module.py

import logging

from context import ctx


def create_widget_object(name: str):
    request_id = 'request_id={0}'.format(ctx.request_id)
    logging.debug('%s going to create widget: %s', request_id, name)

    try:
        # create the widget
        pass
    except Exception:
        logging.exception('%s something went wrong', request_id)

    logging.debug('%s created widget: %s', request_id, name)
