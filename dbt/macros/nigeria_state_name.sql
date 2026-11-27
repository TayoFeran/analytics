{#
    A state name as the FAAC reports print it ("AKWA IBOM", "NASSARAWA") turned into the
    spelling the gold tables and the nigeria_state seed use ("Akwa Ibom", "Nasarawa", "FCT").
#}
{% macro nigeria_state_name(column) -%}
    case
        upper(trim({{ column }}))
        when 'FCT'
        then 'FCT'
        -- The reports spell Nasarawa "NASSARAWA"
        when 'NASSARAWA'
        then 'Nasarawa'
        else
            array_to_string(
                list_transform(
                    string_split(lower(trim({{ column }})), ' '), lambda w:upper(w[1]) || w[2:]
                ),
                ' '
            )
    end
{%- endmacro %}
