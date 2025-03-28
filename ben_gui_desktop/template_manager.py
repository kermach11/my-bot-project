from jinja2 import Environment, FileSystemLoader
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def render_template(template_name, context):
    try:
        template = env.get_template(template_name)
        return template.render(context)
    except Exception as e:
        return f"❌ Template rendering error: {e}"