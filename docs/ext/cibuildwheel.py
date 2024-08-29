"""
Binary wheels table extension for Sphinx.

This extension parses a GitHub Actions workflow for building binary wheels, and
summarizes it in a stylish table.
"""

from docutils import nodes
from sphinx.util.docutils import SphinxDirective


class WheelsDirective(SphinxDirective):
    """A directive to say hello!"""

    required_arguments = 1

    def run(self):
        paragraph_node = nodes.paragraph(text=f'hello {self.arguments[0]}!')
        return [paragraph_node]


def setup(app):
    app.add_directive('wheels', WheelsDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
