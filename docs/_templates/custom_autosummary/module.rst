.. custom module to enable complete documentation of every function
   see https://stackoverflow.com/a/62613202

{{ fullname | escape | underline}}

.. automodule:: {{ fullname }}


   {% block classes %}
   {% if classes %}
   .. rubric:: {{ _('Classes') }}

   .. autosummary::
      :toctree:
      :template: custom_autosummary/class.rst
   {% for item in classes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}


   {% block functions %}
   {% if functions %}
   .. rubric:: {{ _('Functions') }}

   .. autosummary::
      :toctree:
   {% for item in functions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block exceptions %}
   {% if exceptions %}
   .. rubric:: {{ _('Exceptions') }}

   .. autosummary::
   {% for item in exceptions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block details %}
   .. rubric:: {{ _('Details') }}

   {% for item in classes %}
   .. autoclass:: {{ item }}
      :no-index:
   {%- endfor %}
   {% for item in functions %}
   .. autofunction:: {{ item }}
      :no-index:
   {%- endfor %}
   {% endblock %}


{% block modules %}
{% if modules %}
.. rubric:: Modules

.. autosummary::
   :toctree:
   :template: custom_autosummary/module.rst
   :recursive:
{% for item in modules %}
   {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
