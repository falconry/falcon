from pecan import make_app

# from .controllers import root


def create():
    return make_app('controllers.root.RootController', logging={}, debug=False)


def setup_app(config):

    return make_app(
        config.app.root,
        static_root=config.app.static_root,
        template_path=config.app.template_path,
        logging=getattr(config, 'logging', {}),
        debug=getattr(config.app, 'debug', False),
        force_canonical=getattr(config.app, 'force_canonical', True),
    )
