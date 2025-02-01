from rich.markdown import Markdown

def render_response(response, live):
    """
    Renders the response in a formatted way using Rich.
    """
    live.update(Markdown(response), refresh=True)
