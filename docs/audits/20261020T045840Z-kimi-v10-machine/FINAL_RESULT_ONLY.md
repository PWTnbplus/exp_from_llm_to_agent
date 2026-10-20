# V10 Machine Result

- Machine execution accepted: `TRUE`
- Base model: `kimi-k2.5` only
- Real provider calls: `96`
- Local usage cost (provider ledger): `$0.111820`
- Planned units: `96`; statuses: `{"COMPLETED": 96}`

## Scientific outcomes

- G6: `{"action_correct": 11, "planned": 32, "revision_valid": 3, "stats": {"all_planned_action": {"bootstrap": 2000, "ci95": [0.21875, 0.46875], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.34375, "n": 32, "score_key": "model_action_correct"}, "by_arm": {"G6_A_G3_GIVEN": {"bootstrap": 2000, "ci95": [0.125, 0.5], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.3125, "n": 16, "score_key": "model_action_correct"}, "G6_B_G4_GIVEN": {"bootstrap": 2000, "ci95": [0.25, 0.5], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.375, "n": 16, "score_key": "model_action_correct"}}, "by_cf": {"CF1": {"bootstrap": 2000, "ci95": [0.625, 1.0], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.875, "n": 8, "score_key": "model_action_correct"}, "CF2": {"bootstrap": 2000, "ci95": [0.0, 0.0], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.0, "n": 8, "score_key": "model_action_correct"}, "CF3": {"bootstrap": 2000, "ci95": [0.25, 0.875], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.5, "n": 8, "score_key": "model_action_correct"}, "CF4": {"bootstrap": 2000, "ci95": [0.0, 0.0], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.0, "n": 8, "score_key": "model_action_correct"}}}}`
- Q: `{"action_schema_valid": 8, "final_Y_correct": 1, "machine_truth_first": true, "planned": 8, "q_proof_valid": 8, "q_state_match": 2, "truth_key_sent_to_model": false}`
- G7: `{"d3_rows": 4, "d3_semantic_correct": 1, "d3_strict_token_correct": 0, "d3_strict_token_invalid": 4, "planned_stage_rows": 16, "private_Y_injected": false, "q_proof_valid": 4, "q_rows": 4}`
- LU/U: `{"correct_update": 0, "planned": 12, "stats": {"planned_fork_rows": 12, "shared_checkpoint": true, "u_correct_by_arm": {"CONTROL": {"bootstrap": 2000, "ci95": [0.0, 0.0], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.0, "n": 4, "score_key": "correct_update"}, "REAL": {"bootstrap": 2000, "ci95": [0.0, 0.0], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.0, "n": 4, "score_key": "correct_update"}, "SHAM": {"bootstrap": 2000, "ci95": [0.0, 0.0], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.0, "n": 4, "score_key": "correct_update"}}, "u_correct_real_minus_sham": 0.0, "y_correct_real_minus_sham": 0.0}}`
- Agent comparison: `{"action_valid": 15, "planned": 16, "stats": {"AGENT": {"bootstrap": 2000, "ci95": [0.625, 1.0], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 0.875, "n": 8, "score_key": "action_valid"}, "LLM_ONLY": {"bootstrap": 2000, "ci95": [1.0, 1.0], "cluster_key": "theory_family_id", "clusters": 4, "estimate": 1.0, "n": 8, "score_key": "action_valid"}}}`

No positive scientific claim is inferred from execution acceptance. Model errors and explicit failures remain in the raw append-only logs.

Independent audit: `E:\master_exp\nature_prj1_cal\from_llm_to_agent\docs\audits\20261020T045840Z-kimi-v10-machine\INDEPENDENT_READ_ONLY_AUDIT.json`
Machine acceptance: `E:\master_exp\nature_prj1_cal\from_llm_to_agent\docs\audits\20261020T045840Z-kimi-v10-machine\MACHINE_ACCEPTANCE.json`
Raw traces: `E:\master_exp\nature_prj1_cal\from_llm_to_agent\runs\ctflow_single_model\20261020T045840Z-kimi-v10-machine\logs\provider_traces.jsonl`
