{% macro clickhouse__day_of_week(date, isoweek) -%}
{% if isoweek %}
toDayOfWeek({{ date }})
{% else %}
toDayOfWeek({{ date }}, 3) + 1
{% endif %}
{%- endmacro %}
