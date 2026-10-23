{# Integer week index of a date: week 0 starts on var('start_date') (a Monday). #}
{% macro week_index(date_expr) -%}
    (cast({{ date_expr }} as date) - date '{{ var("start_date") }}') // 7
{%- endmacro %}
