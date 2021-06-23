# Server Specific Configurations
server = {'port': '8080', 'host': '0.0.0.0'}

# Pecan Application Configurations
app = {
    'root': 'nuts.controllers.root.RootController',
    'modules': ['nuts'],
    'static_root': '%(confdir)s/public',
    'template_path': '%(confdir)s/nuts/templates',
    'debug': False,
    'errors': {404: '/error/404', '__force_dict__': True},
}

logging = {
    'loggers': {
        'root': {'level': 'INFO', 'handlers': ['console']},
        'nuts': {'level': 'DEBUG', 'handlers': ['console']},
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    },
    'formatters': {
        'simple': {
            'format': (
                '%(asctime)s %(levelname)-5.5s [%(name)s]'
                '[%(threadName)s] %(message)s'
            )
        }
    },
}

# Custom Configurations must be in Python dictionary format::
#
# foo = {'bar':'baz'}
#
# All configurations are accessible at::
# pecan.conf
