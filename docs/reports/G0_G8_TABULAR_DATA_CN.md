| 阶段 | 核心对象 | 计划/样本规模 | 完成/有效数据 | 主要指标 | 当前状态 |
|---|---|---:|---:|---|---|
| G0 | 问题定义、任务注册、评估协议 | 108 个直接测量任务；正式目标 72×5×2 | 协议冻结 | 128 个数值验证点；64 个 OOD 点；RMSE ≤ 1e-5 | 协议完成；上游 provenance/远程交付仍受外部阻断 |
| G1 | 冻结计划 LLM-only | 12 任务×2 runner | 24/24 工程结果 | 2 次模型调用；无工具；无反馈；无重试 | 工程门禁通过；无真实科学结论 |
| G2 | 固定计算辅助 | 12 任务×2 runner | 24/24 工程结果 | 2 次模型调用；4 个 compute steps | 权限边界通过；无正式付费批次 |
| G3 | 固定两遍反思 | 12 任务×2 runner | 24/24 工程结果 | 2 次模型调用；固定 two-pass | G6 使用独立冻结 Tools+Iteration 修正版 |
| G4 | 自适应单 Agent | 12 任务×2 runner | 24/24 工程结果；G6 276 行；G7 作为 G4 组 | 最多 8 次模型调用；授权工具；观察反馈自适应 | 工程基线完成 |
| G5 | Agent+run-local memory | 12 任务×2 runner | 24/24 工程结果 | 10 次模型调用；10 次工具调用；32 memory slots | 23/24 family 独立源图验证；1 个排除 |
| G6 | 反事实验证 | 23 family×4 CF×3 replicate×2 arm=552 | 552/552 response、trace | 1,826 model requests；1,796 tool calls；3,454,449 tokens；$6.057783 | 结构审计通过；科学发布门禁未完全通过 |
| G7 | Failure Localization | 92 case×2 group×7 diagnostic arm=1,288 fork；184 checkpoint | 993/1,288 fork；153/184 checkpoint | Q valid 3/1,288；295 fork terminal failure；31 checkpoint provider error | 执行/merge/score 完成；provider/Q/edge 问题保留 |
| G8 | Causal Mechanism V | 18 case×6 arm×3 replicate=324 | 284 PASS；40 TECHNICAL_FAILURE；0 missing | 1,448,684 tokens；818 model calls；977 tool calls；$2.557378 | 统计完成；需外部科学复核；不自动宣称因果成立 |

| G0 指标 | 数值/规则 |
|---|---:|
| 第一阶段 registry | 108 个直接测量任务 |
| 工程验证集 | 12 个任务；2 个 runner；24 条结果 |
| Pilot 统计规划 | 12 domain×5 matched replicate |
| 正式目标规划 | 72 任务×5 replicate×2 arm |
| 统计独立单位 | NewtonBench law-family/module |
| 默认实验预算 | 6 experiments；120 measurements |
| deterministic numeric validation | 128 点 |
| deterministic legal OOD validation | 64 点 |
| numeric/OOD 阈值 | relative RMSE ≤ 1e-5 |
| OOD 有效点最低要求 | ≥16 个有限点 |
| 选择方法 | outcome-blind；seed=42；分层 round-robin |
| 失败分母 | provider、parse、budget、missing-arm 全部保留 |

| 能力组 | 模型调用 | 工具 | 反馈/规划 | memory | retrieval | transport retry |
|---|---:|---|---|---|---|---:|
| G1 | NewtonBench 2；theory 1 | 无 | frozen plan / one-shot | 无 | 无 | 0 |
| G2 | 2 | calculate_expression；4 compute steps | 固定计算辅助 | 无 | 无 | 0 |
| G3 | 2 | 无 | fixed two-pass reflection | 无 | 无 | 0 |
| G4 | 8 | calculate_expression；run_experiment | observation-conditioned adaptive | 无 | 无 | 0 |
| G5 | 10 | 同 G4 | adaptive | run-local 32 items | 无 | 0 |

| G1–G5 工程基线指标 | 数值 |
|---|---:|
| 任务数 | 12 |
| runner 数 | 2（LLM-only / Agent） |
| 结果记录 | 24/24 |
| 配对数 | 12 |
| Mock Agent−LLM 平均差 | 0.0 |
| Mock bootstrap 95% CI | [0.0, 0.0] |
| 负控制 | zero-function；验证成功数=0 |
| 真实 provider 请求 | 0 |
| G5 proof_graph.json | 1,309 |
| G5 graph sibling 完整 | 1,309/1,309 |
| source-only 独立核验 family | 24 |
| VERIFIED_INDEPENDENT_B | 23/24 |
| EXCLUDED_INVALID_SOURCE | 1/24（TB-L1-010） |
| private input 读取 | 否 |
| answer key 读取 | 否 |
| corrected G6 family | 23 |
| G6/G7 public cases | 92（23×4 CF） |

| G6 协议指标 | 数值 |
|---|---:|
| corrected family | 23 |
| counterfactual | CF1、CF2、CF3、CF4 |
| replicate | 3 |
| arms | G3 / G4 |
| 总计划行 | 552 |
| G3 行 | 276 |
| G4 行 | 276 |
| 每 arm×CF | 69 |
| workers | 2 |
| plan/response/trace | 552/552/552 |
| model requests/responses | 1,826/1,826 |
| tool calls/results | 1,796/1,796 |
| total tokens | 3,454,449 |
| trace-audit cost | $6.057783 |
| revision audit | 138；valid=0 |
| raw nonmonotonic trace | 0（derived trace view） |

| G6 CF | G3 正确/69 | G3 准确率 | G4 正确/69 | G4 准确率 | G4−G3 | family bootstrap 95% CI | McNemar p |
|---|---:|---:|---:|---:|---:|---|---:|
| CF1 | 37 | 53.623% | 43 | 62.319% | +8.696 pp | [−1.449, 20.290] pp | 0.263176 |
| CF2 | 69 | 100.000% | 69 | 100.000% | 0.000 pp | [0.000, 0.000] pp | 不适用 |
| CF3 | 44 | 63.768% | 25 | 36.232% | −27.536 pp | [−42.029, −11.594] pp | 0.000546 |
| CF4 | 41 | 59.420% | 49 | 71.014% | +11.594 pp | [−1.449, 24.638] pp | 0.133801 |
| ALL | 191/276 | 69.203% | 186/276 | 67.391% | −1.812 pp | [−7.609, 4.348] pp | 0.635308 |

| G7 计划指标 | 数值 |
|---|---:|
| public cases | 92 |
| theory families | 23 |
| CF/family | 4（CF1–CF4） |
| groups | G3、G4 |
| diagnostic arms | D0、D1、D2、D3、L_ONLY、U_ONLY、V_ONLY |
| replicate | 1 |
| fork 计划 | 1,288 |
| checkpoint 计划 | 184 |
| G3 fork 计划 | 644 |
| G4 fork 计划 | 644 |
| workers | 16 |
| model | glm-5 |
| evidence status | IMPORTED_REQUIRE_CHECKPOINT_PROVIDER_ORACLE_TRACE_AUDIT |

| G7 对象 | 计划 | selected | completed | terminal failure | 完成率 |
|---|---:|---:|---:|---:|---:|
| fork/state | 1,288 | 1,288 | 993 | 295 | 77.096% |
| checkpoint | 184 | 184 | 153 | 31 | 83.152% |

| G7 组别 | 条件 | 完成/计划 | 完成率 | 全计划最终决策准确率 | 有效回答准确率 | 缺失/无效 |
|---|---|---:|---:|---:|---:|---:|
| G3 | D0 | 56/92 | 60.870% | 41.304% | 67.857% | 36 |
| G3 | D1 | 61/92 | 66.304% | 50.000% | 75.410% | 31 |
| G3 | D2 | 59/92 | 64.130% | 47.826% | 74.576% | 33 |
| G3 | D3 | 59/92 | 64.130% | 51.087% | 79.661% | 33 |
| G3 | L_ONLY | 59/92 | 64.130% | 43.478% | 67.797% | 33 |
| G3 | U_ONLY | 59/92 | 64.130% | 41.304% | 64.407% | 33 |
| G3 | V_ONLY | 59/92 | 64.130% | 48.913% | 76.271% | 33 |
| G4 | D0 | 87/92 | 94.565% | 55.435% | 58.621% | 5 |
| G4 | D1 | 85/92 | 92.391% | 60.870% | 65.882% | 7 |
| G4 | D2 | 80/92 | 86.957% | 63.043% | 72.500% | 12 |
| G4 | D3 | 77/92 | 83.696% | 57.609% | 68.831% | 15 |
| G4 | L_ONLY | 85/92 | 92.391% | 57.609% | 62.353% | 7 |
| G4 | U_ONLY | 85/92 | 92.391% | 58.696% | 63.529% | 7 |
| G4 | V_ONLY | 82/92 | 89.130% | 61.957% | 69.512% | 10 |

| G7 配对比较 | 两臂均完成 | G3 均值差 | G4 均值差 | 可估计性 |
|---|---:|---:|---:|---|
| D1−D0 | 138 | +0.086957 | +0.054348 | 可估计 |
| D2−D1 | 136 | −0.021739 | +0.021739 | 可估计 |
| D3−D2 | 0 | — | — | 不可估计 |
| L_ONLY−D0 | 136 | +0.021739 | +0.021739 | 可估计 |
| U_ONLY−D0 | 0 | — | — | 不可估计 |
| V_ONLY−D0 | 133 | +0.076087 | +0.065217 | 可估计 |

| G7 独立审计指标 | 数值 |
|---|---:|
| V local label CF1/CF3 | CONTRADICTED |
| V local label CF2 | SUPPORTED |
| V local label CF4 | INDETERMINATE |
| L dependency edges | 0/92 cases |
| U eligible cases | 0/92 |
| U 注入 | 未伪造 |
| Q audit rows | 1,288 |
| Q independently valid | 3 |
| Q invalid | 1,285 |
| fork terminal breakdown | checkpoint_missing=217；provider_error=78 |
| checkpoint terminal breakdown | provider_error=31 |
| G7 worker 汇总 model calls | 约 5,540 |
| G7 worker 汇总 tool calls | 3,619 |
| G7 worker 汇总 tokens | 12,183,598 |
| G7 worker 汇总 cost | $19.263478 |
| G8 auto-selected mechanism | 0 |

| G8 输入/冻结指标 | 数值 |
|---|---:|
| G7 public cases 输入 | 92 |
| G7 families 输入 | 23 |
| G7 checkpoint 输入 | 184；完成153；provider error31 |
| G8 选用 families | 9 |
| G8 public cases | 18（9 CF1、9 CF2） |
| G8 checkpoint 基础行 | 54 个 case-replicate 基础 checkpoint |
| 输入 demo/mock | 0 |
| profile | theory_benchmark |
| mechanism | V |
| arms | A_G3_BASE、B_G3_REAL_M、C_G3_SHAM_M、D_G3_EXTRA_THINK、E_G4_PLUS_M、F_G4_MINUS_M |
| replicate | 3 |
| 总计划行 | 324 |
| workers | 16 |
| RPS | 4 |
| 每行 max model calls | 8 |
| 每行 max tool calls | 64 |
| 每行 max tokens | 32,000 |
| 每行 max cost | $0.25 |
| provider internal retries | 0 |
| 外层 retries | 2 |

| G8 执行状态 | 数量 | 占计划 |
|---|---:|---:|
| PASS | 284 | 87.654% |
| TECHNICAL_FAILURE | 40 | 12.346% |
| MISSING | 0 | 0% |
| 总计 | 324 | 100% |

| G8 资源指标 | 总量 |
|---|---:|
| result rows | 324 |
| total tokens | 1,448,684 |
| model calls | 818 |
| tool calls | 977 |
| provider cost | $2.557378 |
| 单行最大实际 cost | $0.022333 |
| 单行预算上限 | $0.25 |
| Q audit rows | 30 |
| process audit rows | 324 |
| independent output audit | 324/324 |

| G8 arm | planned | valid completed | all-planned 正确 | all-planned accuracy | valid-only accuracy | coverage | W→C rate | C→W rate | technical failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_G3_BASE | 54 | 42 | 33 | 0.6111 | 0.7857 | 0.7778 | 0.2500 | 0.1190 | 12 |
| B_G3_REAL_M | 54 | 49 | 40 | 0.7407 | 0.8163 | 0.9074 | 0.6667 | 0.1667 | 5 |
| C_G3_SHAM_M | 54 | 47 | 39 | 0.7222 | 0.8298 | 0.8704 | 0.3333 | 0.0476 | 7 |
| D_G3_EXTRA_THINK | 54 | 39 | 37 | 0.6852 | 0.9487 | 0.7222 | 0.5000 | 0.0238 | 15 |
| E_G4_PLUS_M | 54 | 54 | 43 | 0.7963 | 0.7963 | 1.0000 | 0.4615 | 0.0976 | 0 |
| F_G4_MINUS_M | 54 | 53 | 47 | 0.8704 | 0.8868 | 0.9815 | 0.7692 | 0.0732 | 1 |

| G8 配对效应 | pairs | 独立 families | all-planned 差值 | family bootstrap 95% CI |
|---|---:|---:|---:|---:|
| B−A：真实机制−G3 基线 | 54 | 9 | +0.1296 | [0.0370, 0.2407] |
| B−C：真实机制−sham | 54 | 9 | +0.0185 | [−0.0926, 0.1481] |
| B−D：真实机制−额外思考 | 54 | 9 | +0.0556 | [−0.1481, 0.2407] |
| E−F：G4 真实机制−G4 关闭机制 | 54 | 9 | −0.0741 | [−0.2037, 0.0556] |

| G8 目标失败过程指标 | pairs | 独立 families | 失败率差值 | family bootstrap 95% CI |
|---|---:|---:|---:|---:|
| B−A | 54 | 9 | −0.1296 | [−0.2407, −0.0370] |
| B−C | 54 | 9 | −0.0370 | [−0.1111, 0.0370] |
| B−D | 54 | 9 | −0.1852 | [−0.3148, −0.0556] |
| E−F | 54 | 9 | −0.0185 | [−0.0556, 0.0000] |

| 产物/检查 | 路径 | 状态/摘要 |
|---|---|---|
| G0–G7 原详细报告 | docs/reports/G0_G7_METRICS_CN_REPORT.md | 已有；本表为压缩重排版 |
| G8 详细报告 | docs/reports/G8_CAUSAL_MECHANISM_REPORT_CN.md | 已有；含实验解释与限制 |
| G0–G8 纯表格报告 | docs/reports/G0_G8_TABULAR_DATA_CN.md | 本文件 |
| G8 execution summary | results/g8_causal_mechanism/formal-20261015T030000Z-16workers/raw/execution_summary.json | 324 planned；284 PASS；40 technical failure |
| G8 independent audit | results/g8_causal_mechanism/formal-20261015T030000Z-16workers/audit/g8_independent_audit.json | 324/324 通过结构审计 |
| G8 arm scores | results/g8_causal_mechanism/formal-20261015T030000Z-16workers/score/g8_arm_scores.csv | 六臂指标 |
| G8 paired effects | results/g8_causal_mechanism/formal-20261015T030000Z-16workers/score/g8_paired_effects.csv | 四个预设比较 |
| G8 G9 handoff | results/g8_causal_mechanism/formal-20261015T030000Z-16workers/g9_handoff.json | REVIEW_REQUIRED |
| G6 package tests | — | 13 passed |
| G7 package tests | — | 8 passed |
| G8 package tests（临时审阅副本） | — | 8 passed |
| host pytest | — | 99 passed |
| py_compile | — | PASS |
| G7 offline doctor | — | PASS |

| 关键哈希产物 | SHA-256 |
|---|---|
| G6 run plan | c60b14205f061fa2178b9d0a42074d9957a460bea2cf4e06b841acbe4b0bbde0 |
| G6 canonical responses | 97022fa9ac84dad61c24c98fbc1fee2ba2b357ee853eccd9614cc348da8312fa |
| G6→G7 handoff | ec51c3114b84da9f818d0f6407794e42454cbe87565aa0baaf60081c61602c02 |
| G7 run plan | 549c39a9508fae3c7611564f0cca6022ade5dda67f52d8cc6c1fbd51b9633eb3 |
| G7 states | 714e53654e070a74bc026c11c7396fc243b8e4b72a45e3ed4e9025d8fe66efef |
| G7 checkpoints | 28cbfead349cc35682141df3ac99841d3ebbecdde08280d2849738645b201932 |
| G7 Q audit | 7090520110215c742259dc5598d0c37dc14a155dfd93dc165d011a3e460d27ff |
| G7 score report | 060e5a59fc52caaed6bdc773c0fe4252cc732f5d66e8b837f5740c14095da43e |
| G8 plan | e784dfdb108e0d7534557a3c20e83959f3054ee0daa3cccef5ae9f44986296dd |
| G8 execution summary | 081e84970d1a10da38f9385284723c3a35bbdcb0797bfab24f11f4fc60e196f5 |
| G8 independent audit | 06c2c88bbeb3507837a6f01c21470729b6b4794b940fec3a50b38d7e7ecfc70b |
| G8 score manifest | 439744adba375e3e5a06d3cc46acb0d912300cc5254a96f623f3d9939a1b45c2 |
| G8 G9 handoff | 8f047d9855cfed77217a92518217d22d857dfd06e89c7b37dad4871b717b51f9 |
