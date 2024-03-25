"""License information for the application."""

from dash import html


def app_license() -> html.P:
    """Returns a HTML paragraph element containing the software license information."""
    return html.P(
        """
This software is licensed under the GNU Lesser General Public License v3.0
Permissions of this copyleft license are conditioned on making available
complete source code of licensed works and modifications under the same license
or the GNU GPLv3. Copyright and license notices must be preserved. Contributors
provide an express grant of patent rights. However, a larger work using the
licensed work through interfaces provided by the licensed work may be
distributed under different terms and without source code for the larger work.
""",
        style={"color": "gray", "max-width": "95%", "margin": "auto"},
    )
