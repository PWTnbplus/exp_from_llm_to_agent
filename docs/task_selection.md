# Task selection

`benchmark/task_registry.py` discovers upstream `m*_*` modules and explicit law variants. It produces stable task IDs of the form `newtonbench:<module>:<difficulty>:<variant>:vanilla_equation` and does not use model outcomes. `stratified_select` shuffles with a registered seed and round-robins domains.

The current first-stage registry contains 108 direct-measurement tasks. The generated 12-task manifest is an engineering validation set, not a claim of 12 independent natural laws. Law variants share underlying law families and must be clustered in formal statistical analysis. Dynamic-system tasks are not included until their measurement budget and independent validation behavior are audited.
