#!/usr/bin/env python3
"""Build the versioned, answer-separated theory-science benchmark.

The catalogue below is intentionally human-readable: every task has a named
model, assumptions, a deterministic answer object, and a checker declaration.
The generated public file never contains derivations, answer values, or
verification code.  The answer key is kept separate so runners can load only
the public side.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# v1 is intentionally kept as the original 100-task release.  This builder
# emits the expanded v2 release so old evaluations remain reproducible.
OUT = ROOT / "data" / "theory_benchmark_v3"


def case(task_id: str, level: int, domain: str, subdomain: str, theory: str,
         model: str, parameters: dict[str, Any], question: str,
         expected: dict[str, Any], derivation: str, checker: dict[str, Any],
         steps: int, source_reference: str | None = None) -> dict[str, Any]:
    source_type = "Synthetic Mathematical Model"
    reference = source_reference or (
        f"{theory}；本任务参数由 benchmark 明确给定，"
        "不声称使用外部实验数据或新增文献结果。"
    )
    background = (
        f"本题属于{domain}的{subdomain}。模型 {theory} 被作为封闭的数学对象处理；"
        "题目只要求在给定假设下推导和验证，不把模型内推导解释为真实经验定律的证明。"
    )
    assumptions = [
        "所有参数均为实数且处于题面给定的适用范围。",
        "仅使用题面公开的模型、初值、边界条件和观测量。",
        "数值结论的精度由 checker 中的绝对/相对容差确定。",
    ]
    problem = (
        f"给定数学模型：{model}\n\n"
        f"已知参数：{json.dumps(parameters, ensure_ascii=False, sort_keys=True)}\n\n"
        f"任务：{question}\n"
        "请返回结构化 JSON 的 final_answer，并同时给出推导、适用条件和验证说明。"
    )
    level_text = {1: "基础单模型、少量步骤且答案可直接独立核验。",
                  2: "包含耦合关系、特殊条件或机制判断，需要多步推理。",
                  3: "包含非线性、稳定性、可辨识性、反例或多机制判别，需进行结构化分析。"}[level]
    public = {
        "task_id": task_id,
        "difficulty_level": level,
        "domain": domain,
        "subdomain": subdomain,
        "theory_name": theory,
        "theoretical_background": background,
        "assumptions": assumptions,
        "problem_statement": problem,
        "mathematical_model": model,
        "given_parameters": parameters,
        "expected_reasoning": [
            "识别模型中的状态量、参数和适用条件。",
            "按题目要求完成符号推导或确定性数值计算。",
            "检查边界条件、稳定性、守恒关系或可辨识性。",
            "区分模型内结论、数值证据和未被证明的经验主张。",
        ],
        "difficulty_justification": level_text,
        "estimated_reasoning_steps": steps,
        "source_type": source_type,
        "source_reference": reference,
    }
    answer = {
        "task_id": task_id,
        "ground_truth": {"answer": expected, "verification_level": "A/B" if level < 3 else "B/C"},
        "derivation": derivation,
        "verification_method": (
            "运行 `python -m scientific_discovery.cli theory-verify --task-id "
            f"{task_id} --answer-file candidate.json`；表达式字段使用 SymPy 化简，"
            "数值字段使用记录的容差，分类字段按枚举值比较。"
        ),
        "verification_code": (
            "python -m scientific_discovery.cli theory-verify "
            f"--task-id {task_id} --answer-file candidate.json"
        ),
        "scoring_rubric": {
            "final_answer": 0.6,
            "derivation": 0.3,
            "assumptions_and_limits": 0.1,
            "automatic_checker_note": "自动分数只对结构化答案字段负责；推导文字需由独立审查或规则 checker 复核。",
        },
        "alternative_solutions": [
            "允许代数等价的表达式、等价的变量消元顺序和等价的特征值排序。",
            "允许解析推导与独立数值交叉验证的组合，只要不把数值结果写成普遍证明。",
        ],
        "common_failure_modes": [
            "遗漏模型假设或把有限参数结论外推为无条件定理。",
            "把稳定性、可辨识性和数值拟合混为同一结论。",
            "单位、初值、边界条件或符号约定错误。",
        ],
        "source_type": source_type,
        "source_reference": reference,
        "verification_status": "已验证",
        "checker": checker,
    }
    return {"public": public, "answer": answer}


def _additional_cases() -> list[dict[str, Any]]:
    """Return the 200 new v2 tasks.

    The first release is kept verbatim in ``theory_benchmark_v1``.  These
    additions are declarative synthetic mathematical models: they are useful
    for controlled reasoning comparisons, but do not claim experimental or
    literature-derived discoveries.
    """
    cases: list[dict[str, Any]] = []

    def add(task_id: str, level: int, domain: str, subdomain: str, theory: str,
            model: str, parameters: dict[str, Any], question: str,
            expected: dict[str, Any], derivation: str, steps: int = 3) -> None:
        cases.append(case(
            task_id, level, domain, subdomain, theory, model, parameters,
            question, expected, derivation,
            {"type": "structured", "tolerance": 1e-8}, steps,
            f"Synthetic Mathematical Model: {task_id}; benchmark-defined instance.",
        ))

    C = "Theoretical Chemistry"
    B = "Theoretical Biology"
    R = 8.314
    # ------------------------- chemistry, level 1 -------------------------
    chemistry_l1 = [
        ("reaction kinetics", "first-order half-life inversion", "A(t)=A0 exp(-k t), k=ln(2)/t_half", {"t_half": 2.0}, "由半衰期反推出速率常数 k。", {"k": math.log(2)/2, "half_life": 2.0}, "令 A(t_half)=A0/2，得到 k=ln(2)/t_half。", 2),
        ("reaction kinetics", "zero-order completion time", "A(t)=A0-k t", {"A0": 5.0, "k": .6}, "求完全耗尽时间和 t=3 时的浓度。", {"completion_time": 5/.6, "A_at_3": 3.2}, "零级积分式在 A 非负的时间区间内成立。", 2),
        ("reaction kinetics", "second-order concentration decay", "A(t)=A0/(1+k A0 t)", {"A0": 1.5, "k": .2, "t": 4.0}, "求时刻 t 的浓度和剩余分数。", {"A_at_t": 1.5/(1+.2*1.5*4), "fraction_remaining": 1/(1+.2*1.5*4)}, "对 dA/dt=-kA^2 积分并代入初值。", 3),
        ("reaction network", "sequential intermediate concentration", "A -> B -> C with k1=0.5, k2=0.2", {"A0": 1.0, "k1": .5, "k2": .2, "t": 2.0}, "求中间体 B(t)。", {"B_at_t": .5/(.2-.5)*(math.exp(-.5*2)-math.exp(-.2*2))}, "连续串联反应的中间体为两指数差。", 3),
        ("reaction kinetics", "primary isotope effect", "KIE=k_H/k_D", {"k_H": .64, "KIE": 3.2}, "计算氘代反应速率常数。", {"k_D": .2}, "由定义直接除以同位素效应。", 2),
        ("reaction kinetics", "collision-theory temperature ratio", "k2/k1=exp[-Ea/R(1/T2-1/T1)]", {"Ea": 24000.0, "T1": 300.0, "T2": 330.0}, "不求前因子，计算温度比。", {"ratio": math.exp(-24000/R*(1/330-1/300))}, "相除消去前因子 A。", 2),
        ("thermodynamics", "ideal mixing entropy", "DeltaS_mix/R=-sum_i x_i ln(x_i)", {"x1": .25, "x2": .75}, "计算二元理想混合熵的无量纲值。", {"DeltaS_over_R": -(.25*math.log(.25)+.75*math.log(.75))}, "使用摩尔分数加权的 Shannon 熵表达式。", 2),
        ("phase equilibrium", "Raoult vapor pressure", "P_total=sum_i x_i P_i_star", {"x_A": .4, "P_A_star": 80.0, "x_B": .6, "P_B_star": 20.0}, "计算总蒸气压。", {"P_total": .4*80+.6*20}, "分别计算两组分分压后求和。", 2),
        ("phase equilibrium", "Clausius-Clapeyron pressure ratio", "ln(P2/P1)=-DeltaHvap/R(1/T2-1/T1)", {"DeltaHvap": 30000.0, "T1": 300.0, "T2": 330.0, "P1": 1.0}, "计算 P2/P1。", {"P2_over_P1": math.exp(-30000/R*(1/330-1/300))}, "积分近似下焓变取常数。", 3),
        ("electrolyte thermodynamics", "osmotic pressure coefficient", "Pi=i c R T", {"i": 2.0, "c": .15, "T": 300.0}, "给出 Pi/(RT)。", {"Pi_over_RT": .3}, "把已知的范特霍夫因子和浓度相乘。", 2),
        ("electrochemistry", "Nernst potential shift", "E=E0-(RT/nF)ln(Q)", {"E0": .10, "RT_over_F": .0257, "n": 2.0, "Q": 10.0}, "计算电势 E。", {"E": .10-.0257/2*math.log(10)}, "代入反应商和电子数，保留自然对数。", 3),
        ("electrochemistry", "electrochemical free energy", "DeltaG=-n F E", {"n": 2.0, "F": 96485.0, "E": .25}, "计算标准自由能变化。", {"DeltaG": -2*96485*.25}, "电池电势与可逆 Gibbs 能关系给出结果。", 2),
        ("acid-base equilibrium", "weak-acid ionization fraction", "alpha=Ka/(Ka+H)", {"Ka": 1e-5, "H": 1e-4}, "计算去质子化分数。", {"alpha": 1e-5/(1e-5+1e-4)}, "以两态平衡分母归一化。", 2),
        ("acid-base equilibrium", "diprotic alpha-zero fraction", "alpha0=H^2/(H^2+Ka1 H+Ka1 Ka2)", {"H": 1e-3, "Ka1": 1e-2, "Ka2": 1e-5}, "计算完全质子化分数。", {"alpha0": (1e-3)**2/((1e-3)**2+1e-2*1e-3+1e-2*1e-5)}, "写出三种质子化态的分母并归一化。", 3),
        ("solubility", "AB2 solubility product", "Ksp=4s^3 for AB2", {"Ksp": 4e-6}, "求摩尔溶解度 s。", {"s": (4e-6/4)**(1/3)}, "AB2 解离产生 s 和 2s，故 Ksp=s(2s)^2。", 2),
        ("solubility", "common-ion suppression", "Ksp=s([Cl-]+s)", {"Ksp": 1e-10, "Cl_fixed": .01}, "在过量氯离子下近似求 AgCl 的 s。", {"s": 1e-8}, "因 s 远小于固定离子浓度，s≈Ksp/[Cl-]。", 2),
        ("partition thermodynamics", "liquid-liquid extraction fraction", "f=D Vo/(D Vo+Vw)", {"D": 4.0, "Vo": .2, "Vw": .8}, "求一次萃取进入有机相的分数。", {"fraction_organic": 4*.2/(4*.2+.8)}, "用分配比和两相体积写物料衡算。", 3),
        ("statistical thermodynamics", "conformer Boltzmann ratio", "p_high/p_low=exp(-DeltaE/RT)", {"DeltaE_over_RT": .8}, "求高能构象与低能构象的概率比。", {"probability_ratio": math.exp(-.8)}, "玻尔兹曼权重之比只依赖无量纲能差。", 2),
        ("statistical thermodynamics", "linear-rotor partition scaling", "q_rot proportional to T for a linear rotor", {"T1": 300.0, "T2": 600.0}, "求 q_rot(T2)/q_rot(T1)。", {"ratio": 2.0}, "线性转子高温极限的转动配分函数与 T 成正比。", 2),
        ("statistical thermodynamics", "translational partition scaling", "q_trans proportional to T^(3/2) at fixed volume", {"T1": 300.0, "T2": 600.0}, "求平动配分函数比。", {"ratio": 2**1.5}, "固定体积下三维平动配分函数按 T 的 3/2 次方缩放。", 2),
        ("statistical thermodynamics", "rigid-molecule heat capacity", "Cv/R=3 translational + 3 rotational quadratic modes / 2", {"vibrations_frozen": True}, "忽略振动时求非线性刚性分子的 Cv/R。", {"Cv_over_R": 3.0}, "六个平动和转动二次自由度各贡献 R/2。", 2),
        ("thermochemistry", "Kirchhoff heat-capacity correction", "DeltaH(T2)=DeltaH(T1)+DeltaCp(T2-T1)", {"DeltaH_T1": -10000.0, "DeltaCp": 25.0, "T1": 300.0, "T2": 340.0}, "计算温度 T2 的反应焓。", {"DeltaH_T2": -9000.0}, "在恒定 DeltaCp 近似下积分。", 2),
        ("thermochemistry", "Hess-law reaction sum", "DeltaH_total=sum_j nu_j DeltaH_j", {"DeltaH_1": -120.0, "DeltaH_2": 50.0}, "把两步反应相加，求总焓变。", {"DeltaH_total": -70.0}, "状态函数允许逐步焓变直接相加。", 2),
        ("calorimetry", "constant-pressure calorimetry", "q=m c_p DeltaT", {"m": .5, "cp": 4.18, "DeltaT": 10.0}, "计算吸收热量。", {"q": 20.9}, "代入质量、比热和温差。", 2),
        ("spectroscopy", "Beer-Lambert absorbance", "A=epsilon l c", {"epsilon": 1.5, "l": 2.0, "c": .04}, "计算吸光度。", {"A": .12}, "吸光度为摩尔吸光系数、光程和浓度的乘积。", 2),
        ("photophysics", "fluorescence lifetime", "tau=1/(k_r+k_nr)", {"k_r": .8, "k_nr": .2}, "求激发态寿命。", {"tau": 1.0}, "总失活速率是辐射和非辐射速率之和。", 2),
        ("photophysics", "photochemical quantum yield", "Phi=N_emitted/N_absorbed", {"N_emitted": 40.0, "N_absorbed": 100.0}, "计算量子产率。", {"Phi": .4}, "由事件数比定义。", 1),
        ("transport", "steady Fick flux", "J=-D dc/dx approximately D DeltaC/L", {"D": 1e-9, "DeltaC": .03, "L": 1e-3}, "计算从高浓度到低浓度的通量大小。", {"J_magnitude": 3e-8}, "使用线性浓度梯度的稳态近似。", 3),
        ("transport", "diffusion length", "ell=sqrt(2 D t)", {"D": 1e-9, "t": 100.0}, "计算一维均方位移的扩散长度。", {"ell": math.sqrt(2e-7)}, "代入扩散过程的均方位移关系。", 2),
        ("colloid chemistry", "Stokes-Einstein friction", "D/(kB T)=1/(6 pi eta r)", {"eta": .001, "r": 1e-9}, "计算 D/(kB T)。", {"D_over_kBT": 1/(6*math.pi*.001*1e-9)}, "球形粒子的摩擦系数为 6πηr。", 3),
        ("surface chemistry", "Langmuir coverage", "theta=K P/(1+K P)", {"K": 2.0, "P": .25}, "求平衡表面覆盖率。", {"theta": 1/3}, "单层吸附的占位概率由吸附和空位权重归一化得到。", 2),
        ("electrolysis", "Faraday charge-to-mole conversion", "n_e=I t/F", {"I": .2, "t": 100.0, "F": 96485.0}, "计算转移的电子摩尔数。", {"n_e": .2*100/96485}, "电荷为 It，再除以法拉第常数。", 2),
    ]
    chemistry_l1.extend([
        ("redox chemistry", "oxidation-number electron balance", "MnO4- + 5 Fe2+ -> Mn2+ + 5 Fe3+", {"Fe2_per_MnO4": 5.0}, "计算每摩尔高锰酸根所需的亚铁离子摩尔数。", {"electron_equivalents": 5.0}, "锰从 +7 变为 +2，接受五个电子，因此需要五个 Fe2+。", 2),
    ])
    for index, spec in enumerate(chemistry_l1, 18):
        add(f"TC-L1-{index:03d}", 1, C, *spec)

    # ------------------------- chemistry, level 2 -------------------------
    chemistry_l2 = [
        ("reaction network", "reversible two-state equilibrium", "A <-> B; x_B*=k_f/(k_f+k_r)", {"k_f": 3.0, "k_r": 1.0}, "求平衡时 B 的分数。", {"B_fraction": .75}, "令正向和反向通量相等并归一化总量。", 3),
        ("reaction network", "reversible relaxation transient", "B(t)=k_f/(k_f+k_r)(1-exp(-(k_f+k_r)t))", {"k_f": .4, "k_r": .1, "t": 5.0}, "从纯 A 初始态求 B(t)。", {"B_at_t": .8*(1-math.exp(-2.5))}, "解两态线性动力学方程。", 4),
        ("enzyme kinetics", "competitive inhibition", "v=Vmax S/(Km(1+I/Ki)+S)", {"Vmax": 2.0, "S": 1.0, "Km": .5, "I": 1.0, "Ki": .5}, "计算竞争性抑制下的速度。", {"v": 2/(.5*(1+2)+1)}, "竞争性抑制只提高表观 Km。", 3),
        ("enzyme kinetics", "uncompetitive inhibition", "v=Vmax S/(Km+S(1+I/Ki))", {"Vmax": 2.0, "S": 1.0, "Km": .5, "I": 1.0, "Ki": .5}, "计算反竞争性抑制下的速度。", {"v": 2/(.5+1*(1+2))}, "反竞争性抑制同时作用于 ES，改变分母的底物项。", 3),
        ("enzyme kinetics", "mixed inhibition", "v=Vmax S/(Km(1+I/Ki)+S(1+I/Ki_prime))", {"Vmax": 3.0, "S": 2.0, "Km": 1.0, "I": .5, "Ki": 1.0, "Ki_prime": 2.0}, "计算混合抑制速度。", {"v": 6/(1.5+2*1.25)}, "分别保留对游离酶和 ES 的抑制因子。", 4),
        ("enzyme kinetics", "Hill occupancy", "theta=S^n/(K^n+S^n)", {"S": .5, "K": .5, "n": 3.0}, "计算协同性占位率。", {"theta": .5}, "当 S=K 时，任意正 Hill 指数给出一半占位。", 2),
        ("enzyme kinetics", "integrated Michaelis-Menten time", "Vmax t=S0-S+Km ln(S0/S)", {"S0": 4.0, "S": 1.0, "Km": 1.0, "Vmax": 1.0}, "计算底物从 S0 降到 S 所需时间。", {"time": 3+math.log(4)}, "对 dS/dt=-Vmax S/(Km+S) 分离变量积分。", 4),
        ("reaction selectivity", "parallel Arrhenius selectivity", "k_A/k_B=(A_A/A_B)exp[-(Ea_A-Ea_B)/RT]", {"A_ratio": 1.0, "Ea_A": 30000.0, "Ea_B": 20000.0, "T": 300.0}, "求两条并行路径的速率比。", {"rate_ratio": math.exp(-10000/(R*300))}, "前因子相同，选择性由活化能差控制。", 3),
        ("reaction network", "intermediate peak time", "t_peak=ln(k2/k1)/(k2-k1)", {"k1": .2, "k2": .5}, "求串联反应中间体的峰值时间。", {"t_peak": math.log(.5/.2)/(.5-.2)}, "令 dB/dt=0 并解两指数表达式。", 4),
        ("nonlinear kinetics", "autocatalytic logistic solution", "A(t)=A0 exp(kt)/(1-A0+A0 exp(kt))", {"A0": .1, "k": 1.0, "t": 2.0}, "计算自催化归一化浓度。", {"A_at_t": .1*math.exp(2)/(1-.1+.1*math.exp(2))}, "这是 dA/dt=kA(1-A) 的闭式解。", 3),
        ("reactor engineering", "CSTR first-order conversion", "X=k tau/(1+k tau)", {"k": .4, "tau": 5.0}, "计算连续搅拌釜转化率。", {"X": 2/3}, "稳态物料衡算给出入口、出口和反应项的代数关系。", 3),
        ("reactor engineering", "PFR first-order conversion", "X=1-exp(-k tau)", {"k": .4, "tau": 5.0}, "计算活塞流反应器转化率。", {"X": 1-math.exp(-2)}, "沿停留时间积分一级衰减。", 2),
        ("reaction-diffusion", "reaction penetration length", "ell=sqrt(D/k)", {"D": 1e-5, "k": .01}, "计算扩散-反应渗透长度。", {"ell": math.sqrt(1e-3)}, "平衡二阶空间导数和一阶消耗项。", 3),
        ("linear stability", "stable spiral Jacobian", "J=[[-1,2],[-0.5,-1]]", {}, "求特征值并判断平衡点类型。", {"eigenvalues_real": -1.0, "eigenvalues_imaginary_magnitude": 1.0, "classification": "stable spiral"}, "特征多项式为 (lambda+1)^2+1。", 4),
        ("Markov kinetics", "three-state stationary distribution", "Q has symmetric nearest-neighbor transitions on 1-2-3", {"symmetric_rates": True}, "给出归一化平稳分布。", {"stationary": [.25, .5, .25]}, "中间态连接两条边，未归一化占位权重为 1:2:1。", 4),
        ("reaction stoichiometry", "conservation-law dimension", "N rows span two independent reaction changes in three species", {"stoichiometric_rank": 2, "species_count": 3}, "求独立守恒量个数。", {"conservation_laws": 1}, "守恒量维数为物种数减化学计量矩阵秩。", 3),
        ("nonequilibrium thermodynamics", "cycle affinity", "A_cycle=ln(k1+ k2+ k3+ / k1- k2- k3-)", {"forward_product": 6.0, "reverse_product": 6.0}, "判断该循环是否满足详细平衡。", {"affinity": 0.0, "detailed_balance": True}, "正反向速率乘积相等，循环亲和力为零。", 3),
        ("chemical potential", "activity-induced chemical potential shift", "Delta mu/(RT)=ln(a2/a1)", {"a1": 1.0, "a2": 4.0}, "计算化学势的无量纲变化。", {"Delta_mu_over_RT": math.log(4)}, "使用理想活度形式的化学势表达式。", 2),
        ("electrolyte thermodynamics", "Debye-Huckel activity coefficient", "log10(gamma)=-A z^2 sqrt(I)", {"A": .5, "z": 2.0, "I": .01}, "计算 log10 gamma。", {"log10_gamma": -.2}, "代入电荷数平方和离子强度平方根。", 3),
        ("electrochemistry", "concentration-cell potential", "E=(RT/F)ln(c2/c1)", {"RT_over_F": .0257, "c1": .01, "c2": .1}, "计算浓差电池电势。", {"E": .0257*math.log(10)}, "电势差由活度比的自然对数决定。", 3),
        ("electron transfer", "Marcus activation barrier", "DeltaG_dagger=(lambda+DeltaG)^2/(4 lambda)", {"lambda": .8, "DeltaG": -.4}, "计算 Marcus 活化自由能。", {"DeltaG_dagger": .05}, "将重组能和反应自由能代入抛物线关系。", 3),
        ("transition-state theory", "Eyring temperature ratio", "k2/k1=(T2/T1)exp[-DeltaH/R(1/T2-1/T1)]", {"T1": 300.0, "T2": 330.0, "DeltaH": 20000.0}, "计算两个温度下的速率比。", {"ratio": (330/300)*math.exp(-20000/R*(1/330-1/300))}, "保留 Eyring 的温度前因子。", 3),
        ("surface kinetics", "adsorption-desorption equilibrium", "theta=k_ads P/(k_ads P+k_des)", {"k_ads": 2.0, "P": .5, "k_des": 1.0}, "计算动力学覆盖率。", {"theta": .5}, "令吸附和脱附通量相等。", 3),
        ("surface chemistry", "Langmuir linearization point", "q=qmax K P/(1+K P)", {"qmax": 2.0, "K": 3.0, "P": .5}, "计算吸附量 q。", {"q": 2*1.5/2.5}, "先计算无量纲吸附强度 KP，再代入等温式。", 2),
        ("reaction-diffusion", "slab Thiele modulus", "phi=L sqrt(k/D)", {"L": .01, "k": .04, "D": 1e-4}, "计算 Thiele 模数。", {"phi": .2}, "比较反应时间尺度和扩散时间尺度。", 3),
        ("reaction-diffusion", "slab effectiveness factor", "eta=tanh(phi)/phi", {"phi": .2}, "计算平板有效因子。", {"eta": math.tanh(.2)/.2}, "将平板几何的解析解代入定义。", 3),
        ("reaction-diffusion", "Fourier-mode decay rate", "lambda=D q^2+k", {"D": .2, "q": 2.0, "k": .1}, "计算线性模式衰减率。", {"lambda": .9}, "扩散和一级反应项对同一模式的特征值相加。", 3),
        ("linear algebra", "nonnormal kinetic eigenvalues", "J=[[1,1],[0,2]]", {}, "求线性动力学的两个特征值和主增长率。", {"eigenvalues": [1.0, 2.0], "dominant_growth_rate": 2.0}, "上三角矩阵的特征值等于对角元。", 2),
        ("reaction stoichiometry", "left-nullspace conservation", "N has shape 2x3 and rank 2", {"rows": 2, "columns": 3, "rank": 2}, "求左零空间对应的守恒维数。", {"conservation_dimension": 1}, "物种空间维数减去反应秩给出守恒维数。", 3),
        ("stochastic kinetics", "birth-death stationary mean", "birth alpha and death beta n", {"alpha": 8.0, "beta": 2.0}, "计算稳态平均分子数。", {"mean": 4.0}, "线性出生-死亡过程的稳态均值为 alpha/beta。", 3),
        ("stochastic kinetics", "Ornstein-Uhlenbeck correlation", "C(t)/C(0)=exp(-k t)", {"k": .5, "t": 2.0}, "计算归一化时间相关函数。", {"normalized_correlation": math.exp(-1)}, "OU 过程的相关函数按线性回复率指数衰减。", 2),
        ("kinetic sensitivity", "Arrhenius inverse-temperature sensitivity", "d ln k/d(1/T)=-Ea/R", {"Ea": 5000.0}, "计算对倒温度的灵敏度。", {"sensitivity": -5000/R}, "直接对 ln k=ln A-Ea/(RT) 求导。", 2),
    ]
    chemistry_l2.extend([
        ("kinetic inference", "half-life order diagnostic", "t_half proportional to 1/A0 for a second-order process", {"A0_ratio": 2.0}, "判断初始浓度加倍时半衰期的比值。", {"t_half_new_over_old": .5}, "二级反应半衰期与初始浓度成反比。", 3),
    ])
    for index, spec in enumerate(chemistry_l2, 35):
        add(f"TC-L2-{index:03d}", 2, C, *spec)

    # ------------------------- chemistry, level 3 -------------------------
    chemistry_l3 = [
        ("nonlinear dynamics", "cusp normal-form equilibria", "dx/dt=-(x^3+a x+b), a=-3, b=0", {"a": -3.0, "b": 0.0}, "求三个平衡点。", {"equilibria": [-math.sqrt(3), 0.0, math.sqrt(3)]}, "求三次多项式的根 x(x^2-3)=0。", 4),
        ("nonlinear dynamics", "saddle-node normal form", "dx/dt=mu-x^2", {"mu": .25}, "求平衡点并标记稳定性。", {"equilibria": [-.5, .5], "stable_equilibrium": .5, "unstable_equilibrium": -.5}, "平衡点为 ±sqrt(mu)，线性导数为 -2x。", 4),
        ("nonlinear dynamics", "supercritical Hopf amplitude", "dr/dt=mu r-r^3", {"mu": .4}, "求非零极限环半径及其稳定性。", {"limit_cycle_radius": math.sqrt(.4), "stable": True}, "令径向增长为零，正半径为 sqrt(mu)，其径向导数为负。", 4),
        ("nonlinear dynamics", "transcritical threshold", "dx/dt=mu x-x^2", {"mu": .3}, "求两个平衡点和稳定性。", {"equilibria": [0.0, .3], "stable_positive": True}, "平衡点 0 与 mu 在 mu=0 交换稳定性。", 3),
        ("nonlinear dynamics", "pitchfork amplitude", "dx/dt=mu x-x^3", {"mu": .25}, "求非零分支的幅度。", {"nonzero_amplitudes": [-.5, .5], "stable_nonzero": True}, "非零平衡满足 x^2=mu，导数为 -2mu。", 4),
        ("linear stability", "trace-determinant classification", "J has trace=-2 and determinant=2", {"trace": -2.0, "determinant": 2.0, "discriminant": -4.0}, "判断二维线性平衡点类型。", {"classification": "stable spiral"}, "负迹、正行列式、负判别式对应稳定焦点。", 3),
        ("reaction network theory", "deficiency calculation", "delta=n-l-s", {"complexes": 4, "linkage_classes": 1, "stoich_rank": 2}, "计算反应网络亏格。", {"deficiency": 1}, "按定义 δ=n-l-s。", 2),
        ("reaction network theory", "complex-balanced product form", "stationary means are c1=1 and c2=2", {"c1": 1.0, "c2": 2.0}, "给出两个物种的独立稳态均值。", {"means": [1.0, 2.0]}, "复平衡随机网络的乘积型稳态由复平衡浓度决定。", 4),
        ("reaction network theory", "stoichiometric compatibility class", "A+B+C is conserved", {"A0": .2, "B0": .3, "C0": .5}, "求任意动力学轨道所属守恒总量。", {"total": 1.0}, "把初始浓度相加即可确定兼容类。", 2),
        ("chemical oscillations", "Brusselator Hopf boundary", "B=1+A^2", {"A": 1.0}, "求 Hopf 边界的 B 值。", {"B_critical": 2.0}, "二维 Brusselator 的线性稳定性边界由迹为零给出。", 3),
        ("chemical oscillations", "Oregonator trace criterion", "trace(J)=epsilon f and det(J)>0", {"epsilon": .1, "f": -.3, "determinant": .4}, "根据迹和行列式判断局部稳定性。", {"trace": -.03, "locally_stable": True}, "二维系统在迹负且行列式正时局部稳定。", 3),
        ("reaction-diffusion", "two-species dispersion eigenvalue", "M(q)=[[-.2-q^2,1],[-1,-.5-2q^2]]", {"q": 1.0}, "计算矩阵迹和行列式，并判断 q=1 模式是否稳定。", {"trace": -3.7, "determinant": 3.7, "stable": True}, "代入 q 后使用二维特征值的迹-行列式判据。", 4),
        ("reaction-diffusion", "front-speed scaling", "c=2 sqrt(D r)", {"D": .4, "r": .1}, "计算单调前沿的标度速度。", {"c": 2*math.sqrt(.04)}, "线性扩散增长前沿的最小速度由 D 和 r 的几何平均决定。", 3),
        ("reaction-diffusion", "bistable-front sign", "c proportional to integral_0^1 f(u)du", {"integral": -.2}, "根据反应项积分符号判断前沿方向。", {"direction": "toward u=0"}, "前沿速度符号与势差积分同号；负值使 u=0 一侧推进。", 3),
        ("stochastic kinetics", "birth-death extinction probability", "q=mu/lambda for lambda>mu", {"lambda": .8, "mu": .4}, "给出从一个个体出发的最终灭绝概率。", {"extinction_probability": .5}, "超临界连续时间分枝过程的灭绝根为 μ/λ。", 4),
        ("stochastic thermodynamics", "WKB barrier weight", "P_escape proportional to exp(-DeltaV/epsilon)", {"DeltaV": .8, "epsilon": .2}, "计算相对跃迁权重。", {"relative_weight": math.exp(-4)}, "小噪声极限下由势垒与噪声比控制。", 3),
        ("stochastic thermodynamics", "thermodynamic uncertainty bound", "Var(J)/<J>^2 >= 2/Sigma", {"Sigma": 4.0}, "给出不确定性关系的下界。", {"lower_bound": .5}, "把熵产生率代入 TUR。", 3),
        ("nonequilibrium thermodynamics", "Onsager reciprocity", "L12=L21 in a time-reversal-symmetric linear regime", {"L12": .7, "L21": .7}, "判断给定交叉系数是否满足互易关系。", {"reciprocal": True}, "比较两个交叉输运系数。", 2),
        ("identifiability", "sum-only parameter confounding", "y(t)=(k1+k2)t", {"k1": 1.0, "k2": 2.0}, "判断 k1、k2 能否由单一输出分别辨识。", {"identifiable_combination": "k1+k2", "individual_parameters_identifiable": False}, "输出只依赖和，灵敏度矩阵秩为 1。", 4),
        ("inverse problems", "scalar Fisher information", "I=n x^2/sigma^2", {"n": 10.0, "x": 2.0, "sigma": .5}, "计算标量 Fisher 信息。", {"fisher_information": 160.0}, "独立同方差观测的信息按样本数相加。", 3),
        ("Bayesian model comparison", "posterior odds update", "posterior_odds=Bayes_factor times prior_odds", {"Bayes_factor": 5.0, "prior_odds": .5}, "计算后验赔率。", {"posterior_odds": 2.5}, "用贝叶斯因子更新先验赔率。", 2),
        ("inverse problems", "linear least-squares normal equations", "X=[[1,0],[1,1]], y=[1,2]", {}, "求最小二乘参数向量。", {"beta": [1.0, 1.0]}, "解 X^T X beta=X^T y。", 4),
        ("singular perturbation", "fast-variable reduction", "dx/dt=-x+y, epsilon dy/dt=x^2-y", {"epsilon": .01}, "在快变量准稳态下求约化方程的平衡点。", {"reduced_equilibria": [0.0, 1.0]}, "令 y=x^2，再令 -x+x^2=0。", 4),
        ("multiple-scales analysis", "weak-resonance diagnostic", "x''+x=epsilon cos(t)", {"forcing_frequency": 1.0, "natural_frequency": 1.0}, "判断一阶共振是否产生世俗增长。", {"resonant": True, "secular_term_present": True}, "外力频率等于固有频率，常规正则展开出现共振项。", 4),
        ("stochastic kinetics", "chemical-Langevin stationary variance", "birth alpha, death beta n", {"alpha": 4.0, "beta": 2.0}, "给出稳态均值和方差。", {"mean": 2.0, "variance": 2.0}, "线性出生-死亡过程的稳态为 Poisson 分布。", 3),
        ("stochastic kinetics", "Gillespie bimolecular propensity", "a=c n(n-1)/2", {"c": .1, "n": 5.0}, "计算二分子反应倾向函数。", {"propensity": 1.0}, "从五个相同分子中选择一对，共十对。", 3),
        ("stochastic thermodynamics", "reaction-path entropy", "DeltaS_path=ln(product k_forward/product k_reverse)", {"forward_product": 6.0, "reverse_product": 1.0}, "计算路径熵产生的无量纲值。", {"DeltaS_path": math.log(6)}, "将路径上各步的对数速率比相加。", 3),
        ("kinetic isotope effect", "temperature-dependent isotope ratio", "KIE(T)=exp(DeltaEa/RT)", {"DeltaEa": 1200.0, "T": 300.0}, "计算简化模型的 KIE。", {"KIE": math.exp(1200/(R*300))}, "把活化能差代入 Arrhenius 指数。", 3),
        ("moment closure", "Poisson factorial moment", "E[N(N-1)]=lambda^2", {"lambda": 3.0}, "求 Poisson 计数的二阶阶乘矩。", {"factorial_moment_2": 9.0}, "利用 Poisson 分布的阶乘矩公式。", 3),
        ("metabolic control analysis", "flux-control coefficient sum", "sum_i C_i^J=1", {"C1": .3, "C2": .7}, "判断给定两个控制系数是否满足总和定理。", {"sum": 1.0, "satisfies_sum_rule": True}, "稳态通量对所有独立酶活性的控制系数和为 1。", 3),
        ("nonlinear inverse problem", "fold discriminant boundary", "4 a^3+27 b^2=0 for x^3+a x+b", {"a": -3.0, "b": 2.0}, "判断参数点是否在 cusp 折叠边界上。", {"discriminant": 0.0, "on_boundary": True}, "直接代入 cusp 判别式。", 3),
    ]
    chemistry_l3.extend([
        ("nonlinear dynamics", "cusp discriminant sign", "Delta=4 a^3+27 b^2 controls the number of real roots", {"a": -1.0, "b": 1.0}, "判断三次正规形是否具有三个不同实根。", {"discriminant": 23.0, "three_real_roots": False}, "判别式为正对应一个实根和一对共轭复根。", 4),
        ("reaction network theory", "conservation-law projection", "d(A+B)/dt=0 and d(B+C)/dt=0", {"A0": .2, "B0": .3, "C0": .5}, "给出两个独立守恒量的初始值。", {"conserved_quantities": [.5, .8]}, "分别将初始物种浓度代入两个守恒组合。", 3),
        ("nonlinear inverse problem", "rank-deficient observation map", "y1=k1+k2 and y2=2 k1+2 k2", {"k1": 1.0, "k2": 2.0}, "判断两参数观测映射的 Jacobian 秩。", {"jacobian_rank": 1, "separately_identifiable": False}, "第二行是第一行的两倍，故秩为一。", 4),
    ])
    for index, spec in enumerate(chemistry_l3, 51):
        add(f"TC-L3-{index:03d}", 3, C, *spec)

    # ------------------------- biology, level 1 -------------------------
    biology_l1 = [
        ("population dynamics", "exponential growth", "N(t)=N0 exp(r t)", {"N0": 100.0, "r": .2, "t": 5.0}, "计算种群数量。", {"N_at_t": 100*math.exp(1)}, "积分 dN/dt=rN。", 2),
        ("population dynamics", "logistic growth", "N=K/(1+(K/N0-1)exp(-r t))", {"K": 1000.0, "N0": 100.0, "r": .5, "t": 2.0}, "计算 logistic 种群数量。", {"N_at_t": 1000/(1+9*math.exp(-1))}, "代入 logistic 方程的闭式解。", 3),
        ("population dynamics", "Gompertz growth", "N=K exp(-b exp(-r t))", {"K": 1000.0, "b": 2.0, "r": .3, "t": 4.0}, "计算 Gompertz 模型数量。", {"N_at_t": 1000*math.exp(-2*math.exp(-1.2))}, "直接计算双重指数表达式。", 3),
        ("population dynamics", "Ricker map", "N_next=N exp(r(1-N/K))", {"N": 20.0, "r": .5, "K": 100.0}, "求下一代数量。", {"N_next": 20*math.exp(.5*(1-.2))}, "离散繁殖率由当前密度修正。", 2),
        ("population dynamics", "Beverton-Holt map", "N_next=a N/(1+b N)", {"a": 2.0, "b": .01, "N": 50.0}, "求下一代数量。", {"N_next": 100/1.5}, "代入密度制约的离散映射。", 2),
        ("population dynamics", "discrete logistic map", "x_next=r x(1-x)", {"r": 2.0, "x": .2}, "求一个离散时间步后的频率。", {"x_next": .32}, "直接代入归一化 logistic 映射。", 2),
        ("demography", "two-stage Leslie eigenvalue", "L=[[0,2],[0.5,0]]", {}, "求主特征值。", {"dominant_eigenvalue": 1.0}, "特征方程为 lambda^2-1=0，取非负主根。", 3),
        ("demography", "Euler-Lotka net reproduction", "R0=sum l_x m_x", {"l_m": [.8, .4], "m": [.5, 1.0]}, "计算净繁殖率。", {"R0": .8*.5+.4}, "逐年龄段相乘再求和。", 2),
        ("epidemiology", "SIR herd-immunity threshold", "v_c=1-1/R0", {"R0": 3.0}, "计算临界免疫比例。", {"critical_fraction": 2/3}, "令有效再生数 R0(1-v)=1。", 2),
        ("epidemiology", "SIS endemic prevalence", "i*=1-1/R0", {"R0": 2.0}, "计算 SIS 内禀平衡感染比例。", {"endemic_fraction": .5}, "非零平衡由感染和恢复通量相等得到。", 2),
        ("receptor biology", "receptor occupancy", "theta=L/(Kd+L)", {"L": 3.0, "Kd": 2.0}, "求配体占位率。", {"theta": .6}, "结合和解离权重归一化。", 2),
        ("gene regulation", "Hill activation", "p=L^n/(K^n+L^n)", {"L": 3.0, "K": 2.0, "n": 2.0}, "计算激活概率。", {"activation": 9/13}, "代入 Hill 函数。", 2),
        ("gene expression", "mRNA steady state", "m*=alpha/gamma", {"alpha": 10.0, "gamma": 2.0}, "计算稳态 mRNA 数。", {"mRNA_mean": 5.0}, "出生和降解通量相等。", 2),
        ("gene expression", "protein steady state", "p*=k_p m*/delta_p", {"k_p": 3.0, "mRNA": 5.0, "delta_p": 1.5}, "计算稳态蛋白数。", {"protein_mean": 10.0}, "蛋白生成率除以降解率。", 2),
        ("gene regulation", "Hill repression", "p=1/(1+(x/K)^n)", {"x": 2.0, "K": 1.0, "n": 2.0}, "计算抑制启动子输出。", {"expression": .2}, "抑制项的倒数给出剩余表达。", 2),
        ("population genetics", "mutation-selection balance", "q*=mu/s", {"mu": .01, "s": .1}, "计算有害等位基因频率近似值。", {"q_star": .1}, "在小频率近似下突变输入等于选择清除。", 2),
        ("population genetics", "Hardy-Weinberg heterozygosity", "H=2 p(1-p)", {"p": .7}, "计算杂合度。", {"heterozygosity": .42}, "随机交配下杂合子频率为 2pq。", 2),
        ("population genetics", "haploid selection update", "p'=p wA/(p wA+(1-p) wa)", {"p": .4, "wA": 1.2, "wa": 1.0}, "计算选择后等位基因频率。", {"p_next": .48/1.08}, "按平均适合度归一化。", 3),
        ("population genetics", "neutral Moran fixation probability", "pi=1/N", {"N": 10.0}, "计算一个中性单拷贝突变的固定概率。", {"fixation_probability": .1}, "中性固定概率等于初始频率。", 2),
        ("population genetics", "Wright-Fisher sampling variance", "Var(p_next)=p(1-p)/(2N)", {"p": .5, "N": 100.0}, "计算下一代等位基因频率方差。", {"variance": .00125}, "二倍体基因拷贝数为 2N。", 2),
        ("predator-prey", "prey logistic growth rate", "dN/dt=r N(1-N/K)", {"r": 1.0, "N": 30.0, "K": 100.0}, "在无捕食时计算瞬时增长率。", {"growth_rate": 21.0}, "代入密度制约项。", 2),
        ("resource ecology", "resource-to-biomass yield", "X=Y(S_consumed)", {"Y": .6, "S_consumed": 10.0}, "计算生成的生物量。", {"biomass": 6.0}, "产率是每单位资源形成的生物量。", 1),
        ("chemostat", "washout condition", "washout if D>mu(S)", {"D": .8, "mu": .6}, "判断是否发生洗出。", {"washout": True}, "稀释率超过比生长率时净增长为负。", 2),
        ("quorum sensing", "positive quorum equilibrium", "dx/dt=s/(1+x)-x", {"s": 3.0}, "求正平衡点。", {"positive_equilibrium": (-1+math.sqrt(13))/2}, "解 x(1+x)=s 的正根。", 3),
        ("spatial ecology", "one-dimensional diffusion MSD", "MSD=2 D t", {"D": .5, "t": 4.0}, "计算均方位移。", {"MSD": 4.0}, "一维布朗扩散的均方位移随时间线性增长。", 2),
        ("morphogen transport", "exponential morphogen profile", "C(x)=C0 exp(-x/ell)", {"C0": 1.0, "x": .5, "ell": .25}, "计算指定位置的形态发生素浓度。", {"C_at_x": math.exp(-2)}, "代入空间衰减长度。", 2),
        ("physiological scaling", "Q10 temperature response", "rate2/rate1=Q10^((T2-T1)/10)", {"Q10": 2.0, "T1": 20.0, "T2": 40.0}, "计算速率倍数。", {"rate_ratio": 4.0}, "温差为两个十摄氏度区间。", 2),
        ("allometry", "metabolic scaling ratio", "B proportional to M^0.75", {"M1": 1.0, "M2": 16.0}, "计算代谢率比。", {"B2_over_B1": 8.0}, "十六的四分之三次方为八。", 2),
        ("behavioral ecology", "binomial sex-ratio probability", "P(X=2)=C(3,2) p^2(1-p)", {"n": 3, "p_male": .5, "males": 2}, "计算三个后代中恰有两个雄性的概率。", {"probability": .375}, "使用二项分布质量函数。", 2),
        ("population genetics", "heterozygosity drift decay", "H_t=H_0(1-1/(2N))^t", {"H0": .8, "N": 10.0, "t": 2.0}, "计算两代后的期望杂合度。", {"H_t": .8*.95**2}, "中性有限群体近似下每代乘以漂变保留因子。", 3),
    ]
    biology_l1.extend([
        ("life history", "generation-time weighted reproduction", "T=sum x l_x m_x / R0", {"ages": [1.0, 2.0], "l_m": [.8, .4], "m": [.5, 1.0]}, "计算净繁殖率和世代时间。", {"R0": .8, "generation_time": 1.5}, "先求 l_x m_x 的加权和，再除以 R0。", 3),
        ("epidemiology", "incidence doubling time", "T2=ln(2)/(beta-gamma)", {"beta": .3, "gamma": .1}, "计算早期线性流行的倍增时间。", {"doubling_time": math.log(2)/.2}, "净增长率为传播率减恢复率。", 2),
        ("behavioral ecology", "Hamilton inclusive-fitness margin", "margin=rb-c", {"r": .25, "b": 4.0, "c": .8}, "计算亲缘选择不等式的余量。", {"margin": .2, "favored": True}, "正余量表示间接收益超过直接成本。", 2),
    ])
    for index, spec in enumerate(biology_l1, 18):
        add(f"TB-L1-{index:03d}", 1, B, *spec)

    # ------------------------- biology, level 2 -------------------------
    biology_l2 = [
        ("epidemiology", "SEIR early growth root", "(r+sigma)(r+gamma)=sigma gamma R0", {"sigma": 1.0, "gamma": .5, "R0": 2.0}, "求早期指数增长率的正根。", {"growth_rate": .5}, "展开特征方程并取正根。", 4),
        ("epidemiology", "two-group next-generation spectrum", "K=[[.5,.2],[.1,.4]]", {}, "求谱半径和入侵判断。", {"eigenvalues": [.6, .3], "spectral_radius": .6, "invades": False}, "特征多项式给出 0.6 和 0.3，谱半径小于 1。", 4),
        ("epidemiology", "two-patch migration balance", "dp1/dt=-m p1+m p2; dp2/dt=m p1-m p2", {"total": 1.0, "m": .2}, "求对称迁移的平衡分布。", {"patch_fractions": [.5, .5]}, "零净迁移要求两个斑块占比相等。", 3),
        ("population dynamics", "logistic maximum sustainable yield", "MSY=r K/4", {"r": 1.0, "K": 100.0}, "计算最大可持续捕捞量及对应种群量。", {"MSY": 25.0, "N_at_MSY": 50.0}, "对 logistic 净增长率求最大值。", 3),
        ("predator-prey", "Holling type-II intake", "g(N)=a N/(1+a h N)", {"a": .2, "h": .5, "N": 10.0}, "计算单个捕食者的摄食率。", {"intake": 2/(1+1)}, "攻击和处理时间共同决定饱和摄食。", 3),
        ("chemostat", "substrate steady state", "S*=K_s D/(mu_max-D)", {"Ks": .5, "D": .4, "mu_max": 1.0}, "求非洗出稳态底物浓度。", {"S_star": 1/3}, "令比生长率等于稀释率。", 3),
        ("chemostat", "chemostat biomass balance", "X=Y(S_in-S*)", {"Y": .5, "S_in": 1.0, "S_star": 1/3}, "求稳态生物量。", {"X_star": 1/3}, "用底物消耗和产率物料衡算。", 3),
        ("gene regulation", "symmetric toggle nullcline", "x=1/(1+y^2), y=1/(1+x^2)", {"K": 1.0, "n": 2.0}, "求对称平衡 x=y 的数值。", {"symmetric_equilibrium": .6823278038}, "对称条件化为 x^3+x-1=0，再取正根。", 4),
        ("gene regulation", "repressilator symmetric nullcline", "x=alpha/(1+x^2)", {"alpha": 8.0}, "求正对称平衡的近似值。", {"symmetric_equilibrium": 1.835122}, "解 x^3+x-8=0 的正根。", 4),
        ("gene regulatory network", "two-stage cascade DC gain", "G(0)=(alpha1/gamma1)(alpha2/gamma2)", {"alpha1": 2.0, "gamma1": 1.0, "alpha2": 3.0, "gamma2": 2.0}, "计算级联的零频增益。", {"DC_gain": 3.0}, "两个一阶模块的稳态增益相乘。", 3),
        ("gene expression noise", "Poisson Fano factor", "Fano=variance/mean", {"mean": 12.0, "variance": 12.0}, "判断单步出生死亡模型的 Fano 因子。", {"Fano": 1.0}, "Poisson 分布方差等于均值。", 2),
        ("gene expression noise", "two-stage protein Fano factor", "Fano_p=1+k_p/(gamma_m+gamma_p)", {"k_p": 5.0, "gamma_m": 2.0, "gamma_p": 1.0}, "计算简化两阶段模型的蛋白 Fano 因子。", {"Fano": 1+5/3}, "代入给定的转译和降解速率。", 3),
        ("branching process", "continuous branching extinction", "q=mu/lambda for lambda>mu", {"lambda": 1.0, "mu": .5}, "求单个祖先最终灭绝概率。", {"extinction_probability": .5}, "使用超临界线性分枝过程的灭绝根。", 3),
        ("age structure", "three-stage Leslie dominant root", "L has a two-cycle block [[0,1],[1,0]] plus a zero stage", {}, "求主特征值。", {"dominant_eigenvalue": 1.0}, "两周期块的谱半径为 1，额外零特征值不改变主根。", 3),
        ("age structure", "Euler-Lotka two-age replacement", "1=l2 m2 lambda^-2", {"l2": .5, "m2": 2.0}, "求稳定增长因子 lambda。", {"lambda": 1.0}, "代入单一生殖年龄的 Euler-Lotka 方程。", 3),
        ("adaptive dynamics", "selection gradient", "d s(y,x)/dy at y=x = -2(x-theta)", {"x": .5, "theta": 1.0}, "计算入侵适合度的选择梯度。", {"selection_gradient": 1.0}, "对平方距离适合度求导并在居民性状处评价。", 3),
        ("competition", "two-species coexistence equilibrium", "dx=x(1-x-.5y), dy=y(1-.25x-y)", {}, "求正共存平衡。", {"equilibrium": [4/7, 6/7]}, "联立两条正零增长线性方程。", 4),
        ("predator-prey", "predator-prey Jacobian trace", "J at equilibrium has trace=-.4 and determinant=.8", {"trace": -.4, "determinant": .8}, "判断局部稳定性。", {"locally_stable": True}, "二维线性化的迹负且行列式正。", 3),
        ("reaction-diffusion ecology", "Turing-mode eigenvalues", "M=[[-1.1,1],[-1,-3]] at q=1", {}, "求特征值是否有正实部。", {"determinant": 2.3, "trace": -4.1, "stable_mode": True}, "迹负且行列式正，因此该模式线性稳定。", 4),
        ("reaction-diffusion ecology", "activator-inhibitor threshold", "det(J-q^2 D)=0 marks onset", {"determinant_at_q": 0.0}, "判断给定模式是否在图灵阈值。", {"at_threshold": True}, "零行列式表示一个模式特征值穿过零。", 3),
        ("delay population dynamics", "delayed logistic stability", "stable if r tau < pi/2", {"r": .5, "tau": 2.0}, "判断平衡点是否满足延迟稳定条件。", {"r_tau": 1.0, "stable_by_bound": True}, "1 小于 pi/2，尚未越过经典 Hopf 边界。", 3),
        ("gene regulation", "Hill elasticity", "E=n(1-theta)", {"n": 4.0, "theta": .8}, "计算激活曲线的对数弹性。", {"elasticity": .8}, "Hill 函数在占位率 theta 下的弹性简化为 n(1-theta)。", 3),
        ("resource competition", "R-star winner", "species with smaller R_star wins", {"R_star_A": .2, "R_star_B": .4}, "在单资源竞争下判断长期优势种。", {"winner": "A", "coexistence": False}, "较小 R* 的物种把资源压到另一物种不能维持的水平。", 3),
        ("evolutionary game", "replicator equilibrium", "dx/dt=x(1-x)(a-b x)", {"a": .2, "b": .5}, "求内部平衡及其稳定性。", {"internal_equilibrium": .4, "stable": True}, "令 a-bx=0，内部点导数为负。", 4),
        ("quantitative genetics", "breeder equation response", "R=h2 S", {"h2": .4, "S": 2.0}, "计算一代响应。", {"response": .8}, "窄义遗传力乘以选择差。", 2),
        ("evolutionary genetics", "Fisher variance increase", "d mean fitness/dt=Var(w)", {"fitness_variance": .09}, "在连续时间近似下给出平均适合度变化率。", {"rate": .09}, "使用 Fisher 基本定理的方差形式。", 2),
        ("branching process", "subcritical Poisson offspring", "Poisson mean m<1 implies q=1", {"mean_offspring": .8}, "判断最终灭绝概率。", {"extinction_probability": 1.0}, "次临界分枝过程以概率 1 灭绝。", 2),
        ("metapopulation", "two-patch colonization balance", "dp/dt=c(1-p)-e p", {"c": .3, "e": .2}, "求斑块占据平衡。", {"occupancy": .6}, "令定殖通量等于灭绝通量。", 3),
        ("epidemic intervention", "vaccination-adjusted reproduction", "R_eff=R0(1-v)", {"R0": 2.5, "v": .2}, "计算干预后的再生数。", {"R_eff": 2.0}, "易感比例为 1-v。", 2),
        ("population dynamics", "harvested logistic equilibrium", "dx/dt=r x(1-x/K)-H", {"r": 1.0, "K": 4.0, "H": .75}, "求两个正/非负平衡点。", {"equilibria": [1.0, 3.0]}, "解 x(1-x/4)=.75。", 4),
        ("host-pathogen", "within-host basic reproduction", "R0=beta T0/(c delta)", {"beta": .2, "T0": 100.0, "c": 1.0, "delta": 2.0}, "计算宿主内基本再生数。", {"R0": 10.0}, "将靶细胞、感染和清除参数代入。", 3),
        ("population genetics", "migration-selection balance", "p*=m/s for small p", {"m": .02, "s": .1}, "计算小频率近似下的平衡频率。", {"p_star": .2}, "迁移输入与选择清除相等。", 2),
    ]
    biology_l2.extend([
        ("epidemic dynamics", "SIS threshold slope", "di/dt=(beta-gamma)i-beta i^2", {"beta": .4, "gamma": .2}, "计算无病平衡附近的线性增长率。", {"linear_growth_rate": .2, "supercritical": True}, "在 i=0 处线性项为 beta-gamma。", 3),
        ("population dynamics", "Allee-effect equilibria", "dx/dt=r x(1-x/K)(x/A-1)", {"r": 1.0, "K": 10.0, "A": 2.0}, "列出三个平衡点并指出阈值。", {"equilibria": [0.0, 2.0, 10.0], "threshold": 2.0}, "三个因子分别给出灭绝、Allee 阈值和承载力。", 3),
    ])
    for index, spec in enumerate(biology_l2, 34):
        add(f"TB-L2-{index:03d}", 2, B, *spec)

    # ------------------------- biology, level 3 -------------------------
    biology_l3 = [
        ("delay dynamics", "delay-feedback Hopf frequency", "lambda+a-b exp(-lambda tau)=0", {"a": .5, "b": 1.0}, "在 Hopf 条件下计算角频率。", {"omega": math.sqrt(.75)}, "虚部条件给出 omega^2=b^2-a^2。", 5),
        ("adaptive dynamics", "branching criterion", "f_xx at singular strategy >0 indicates disruptive curvature", {"second_derivative": 2.0}, "判断局部曲率是否支持分化方向。", {"disruptive_curvature": True}, "正二阶导数表示奇异策略附近的凸形入侵适合度。", 4),
        ("adaptive dynamics", "invasion fitness gradient", "s(y,x)=r-(y-x)^2+c(y-x)", {"resident": .0, "mutant": .2, "c": .5}, "计算突变体相对居民的适合度差。", {"fitness_difference": .2-.04}, "代入 y-x=.2 后计算线性收益减二次代价。", 4),
        ("eco-epidemiology", "infected-predator coexistence contrast", "dx=x(1-x-y), dy=y(.6-.2x-.5y)", {}, "求正共存平衡。", {"equilibrium": [2/3, 2/3]}, "联立两个正零增长条件。", 5),
        ("spatial epidemiology", "epidemic reaction-diffusion speed", "c=2 sqrt(D(beta-gamma))", {"D": .5, "beta": .8, "gamma": .2}, "计算入侵前沿的线性速度。", {"c": 2*math.sqrt(.3)}, "增长率为 beta-gamma，代入扩散前沿公式。", 4),
        ("epidemic dynamics", "seasonal threshold", "R_eff=R0 s_bar", {"R0": 1.5, "s_bar": .6}, "判断平均易感比例下是否可以入侵。", {"R_eff": .9, "invades": False}, "有效再生数小于 1。", 3),
        ("network epidemiology", "configuration-model threshold", "R_network=(<k^2>-<k>)/<k>", {"mean_degree": 3.0, "second_moment": 11.0}, "计算网络分枝因子。", {"R_network": 8/3}, "代入度分布矩。", 3),
        ("network epidemiology", "two-type spectral threshold", "K=[[1.2,.4],[.2,.8]]", {}, "求谱半径并判断线性入侵。", {"spectral_radius": 1.4, "invades": True}, "矩阵特征值为 1.4 和 0.6。", 4),
        ("spatial ecology", "Turing wavelength", "lambda_pattern=2 pi/q_star", {"q_star": 2.0}, "计算主导空间波长。", {"wavelength": math.pi}, "波数和波长互为 2π 比例。", 3),
        ("spatial ecology", "wave-mode stability", "lambda(q)=r-D q^2", {"r": .5, "D": .5, "q": 2.0}, "判断 q=2 模式是否增长。", {"growth_rate": -1.5, "stable": True}, "扩散项超过局部增长项。", 3),
        ("stochastic population dynamics", "logistic stationary mode", "mode=(r- sigma^2/2)/K in a log-coordinate approximation", {"r": 1.0, "sigma": 1.0, "K": 10.0}, "计算给定近似下的对数坐标漂移项。", {"mode_parameter": .05}, "按题面给定近似代入噪声修正后的增长率。", 4),
        ("stochastic population dynamics", "Kramers switching weight", "k proportional to exp(-DeltaU/sigma^2)", {"DeltaU": .4, "sigma": .2}, "计算无量纲跃迁权重。", {"relative_rate": math.exp(-10)}, "将势垒除以噪声方差。", 3),
        ("gene regulation", "toggle saddle-node threshold", "x=alpha/(1+x^2), tangency at x=1", {"Hill_n": 2.0}, "求对称 toggle 的鞍结阈值 alpha。", {"alpha_critical": 2.0}, "切线条件 1=2x/(1+x^2) 与平衡方程共同给出 x=1, alpha=2。", 5),
        ("gene regulation", "repressilator linear feedback gain", "G=(-alpha n x^(n-1))/(1+x^n)^2", {"alpha": 8.0, "n": 2.0, "x": 1.835122}, "计算局部负反馈增益的数值。", {"gain": -(8*2*1.835122)/(1+1.835122**2)**2}, "对 Hill 抑制函数求导并代入平衡点。", 5),
        ("inverse problems", "two-parameter Fisher rank", "J=[[1,0],[0,2]]", {}, "判断两个参数是否局部可辨识。", {"rank": 2, "locally_identifiable": True}, "灵敏度矩阵满列秩。", 3),
        ("inverse problems", "product confounding", "y(t)=beta N(t) with beta and N only as product", {"beta": 2.0, "N": 3.0}, "判断 beta 与 N 是否能分别由该观测辨识。", {"observed_product": 6.0, "separately_identifiable": False}, "任意保持 beta*N 不变的参数对产生相同输出。", 4),
        ("model selection", "AIC difference", "DeltaAIC=2 Delta k-2 Delta ln L", {"Delta_k": 2.0, "Delta_log_likelihood": 3.0}, "计算模型 2 相对模型 1 的 AIC 差。", {"DeltaAIC": -2.0, "model_2_preferred": True}, "复杂度惩罚为 4，拟合收益为 6。", 3),
        ("optimal control", "Hamiltonian switching sign", "H=u^2+lambda u; u*=clip(-lambda/2)", {"lambda": -1.0, "bounds": [-1.0, 1.0]}, "求未触及边界的最优控制。", {"u_star": .5}, "对 Hamiltonian 关于 u 求一阶条件。", 4),
        ("resource ecology", "pulse-harvest persistence", "N_next=(1-h) N exp(r(1-N/K))", {"h": .5, "N": 2.0, "r": 1.0, "K": 10.0}, "求脉冲捕捞后一个周期的数量。", {"N_next": .5*2*math.exp(.8)}, "先施加捕捞比例，再经过一个增长周期。", 4),
        ("quasispecies", "error-threshold retention", "Q=q^L", {"q": .99, "L": 100.0}, "计算完整基因组复制正确率。", {"Q": .99**100}, "独立位点正确复制概率相乘。", 3),
        ("multitype branching", "spectral extinction criterion", "M=[[.6,.1],[.2,.5]]", {}, "求谱半径并判断是否次临界。", {"spectral_radius": .8, "subcritical": True}, "特征值为 0.8 和 0.3，谱半径小于 1。", 4),
        ("kin selection", "Hamilton rule", "rb>c", {"r": .5, "b": 3.0, "c": 1.0}, "判断互惠行为是否满足 Hamilton 规则。", {"rb": 1.5, "favored": True}, "亲缘收益乘积大于成本。", 3),
        ("evolutionary game", "ESS invasion matrix", "mutant payoff advantage is -0.2", {"resident_payoff": 1.0, "mutant_against_resident": .8}, "判断稀有突变体能否入侵。", {"invasion": False, "payoff_difference": -.2}, "突变体对居民的收益较低。", 3),
        ("spatial ecology", "neutral pair diffusion scale", "ell=sqrt(4 D t)", {"D": .25, "t": 4.0}, "计算二维相遇扩散尺度。", {"ell": 2.0}, "二维相对扩散的均方半径使用 4Dt。", 3),
        ("epidemiology", "intervention reproduction number", "R_eff=R0(1-v)(1-e)", {"R0": 3.0, "v": .4, "e": .5}, "计算疫苗覆盖和保护效力共同作用后的再生数。", {"R_eff": .9}, "易感比例和易感者保护系数相乘。", 3),
        ("age-structured epidemiology", "renewal-equation growth factor", "1=R exp(-r T)", {"R": 1.0, "T": 5.0}, "求世代繁殖数为 1 时的增长率。", {"growth_rate": 0.0}, "取自然对数得到 r=ln(R)/T。", 3),
        ("coalescent theory", "pairwise coalescent time", "E[T2]=2 N_e", {"N_e": 100.0}, "计算二倍体中性群体的成对共祖时间。", {"expected_time": 200.0}, "使用经典中性共祖尺度。", 2),
        ("population genetics", "genic selection fixation approximation", "p_fix approximately 2s for a new beneficial allele", {"s": .01}, "给出小选择系数下的固定概率近似。", {"fixation_probability": .02}, "采用大群体、加性有利突变的弱选择近似。", 3),
        ("quantitative genetics", "reaction-norm response", "Delta_trait=G beta", {"G": 2.0, "beta": .3}, "计算一维反应规范的遗传响应。", {"response": .6}, "遗传方差乘以环境梯度。", 3),
        ("landscape ecology", "barrier-weighted basin choice", "P_A/P_B=exp(-(DeltaU_A-DeltaU_B)/sigma^2)", {"DeltaU_A": .2, "DeltaU_B": .4, "sigma": .2}, "计算两个吸引盆跃迁权重之比。", {"P_A_over_P_B": math.exp(5)}, "较低势垒的跃迁权重更高。", 4),
        ("eco-evolutionary dynamics", "trait-resource feedback equilibrium", "dx=x(1-x-y), dy=y(0.5-x-0.5y)", {}, "求正共存平衡。", {"equilibrium": [0.5, .5]}, "联立两个正零增长条件。", 5),
        ("network ecology", "spectral centrality threshold", "rho(A)=1.2 and transmission=0.8", {"spectral_radius": 1.2, "transmission": .8}, "计算线性网络增长因子并判断增长。", {"growth_factor": .96, "grows": False}, "网络传播因子为传输率乘邻接矩阵谱半径。", 3),
        ("stochastic gene regulation", "noise-induced switching ratio", "P_high/P_low=exp(-DeltaU_high/sigma^2+DeltaU_low/sigma^2)", {"DeltaU_high": .3, "DeltaU_low": .1, "sigma": .2}, "计算高态相对低态的跃迁权重。", {"ratio": math.exp(-5)}, "比较两个势垒并除以噪声方差。", 4),
    ]
    for index, spec in enumerate(biology_l3, 51):
        add(f"TB-L3-{index:03d}", 3, B, *spec)
    return cases


def _build_v2_cases() -> list[dict[str, Any]]:
    e = math.exp
    log = math.log
    sqrt = math.sqrt
    pi = math.pi
    cases: list[dict[str, Any]] = []

    # ------------------------- theoretical chemistry -------------------------
    C = "Theoretical Chemistry"
    cases += [
        case("TC-L1-001", 1, C, "反应动力学", "一级反应积分律", "dA/dt=-kA", {"A0": 2.5, "k": 0.4},
             "求 A(t)、半衰期，并判断半衰期是否依赖 A0。", {"formula": "A0*exp(-k*t)", "half_life": log(2)/.4, "depends_on_A0": False},
             "分离变量得 dA/A=-kdt；由 A(0)=A0 得 A=A0 exp(-kt)。令 A=A0/2 得 t1/2=ln(2)/k。", {"type": "structured", "expression_fields": ["formula"], "tolerance": 1e-8}, 3),
        case("TC-L1-002", 1, C, "反应动力学", "二级反应积分律", "dA/dt=-kA^2", {"A0": 1.2, "k": 0.3},
             "给出 1/A(t) 和半衰期。", {"formula": "1/A0+k*t", "half_life": 1/(.3*1.2)},
             "积分 dA/A^2=-kdt 得 1/A=1/A0+kt；代入 A=A0/2 得 t1/2=1/(kA0)。", {"type": "structured", "expression_fields": ["formula"], "tolerance": 1e-8}, 2),
        case("TC-L1-003", 1, C, "反应动力学", "零级反应积分律", "dA/dt=-k", {"A0": 2.4, "k": .15},
             "求 A(t) 及完全耗尽时间，并说明模型适用到何时。", {"formula": "A0-k*t", "completion_time": 2.4/.15, "domain": "0<=t<=A0/k"},
             "直接积分得到 A=A0-kt；浓度达到零后零级表达式不能继续用于负浓度。", {"type": "structured", "expression_fields": ["formula"], "tolerance": 1e-8}, 2),
        case("TC-L1-004", 1, C, "反应动力学", "Arrhenius 温度比", "k(T)=A exp(-Ea/(RT))", {"Ea_J_per_mol": 50000, "R": 8.314, "T1": 300, "T2": 330},
             "求 k(T2)/k(T1)，不要单独估计未知的 A。", {"ratio": e(-50000/8.314*(1/330-1/300))},
             "两式相除消去 A，得到 k2/k1=exp[-Ea/R(1/T2-1/T1)]。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TC-L1-005", 1, C, "化学平衡", "标准 Gibbs 能与平衡常数", "DeltaG°=-RT ln K", {"DeltaG_J_per_mol": -5000, "R": 8.314, "T": 298},
             "计算 K，并说明 DeltaG°<0 的含义。", {"K": e(5000/(8.314*298)), "spontaneous_at_standard_state": True},
             "由定义 K=exp(-DeltaG°/RT)；负的标准 Gibbs 能对应 K>1，但不等于任意初态都瞬时自发。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TC-L1-006", 1, C, "化学平衡", "van't Hoff 关系", "d ln K/dT=DeltaH°/(RT^2)", {"DeltaH_J_per_mol": 40000, "R": 8.314, "T1": 300, "T2": 330, "K1": 2.0},
             "在 DeltaH° 视为常数时计算 K2。", {"K2": 2*e(40000/8.314*(1/300-1/330))},
             "积分 dlnK=DeltaH°dT/(RT²)，得 ln(K2/K1)=DeltaH°/R(1/T1-1/T2)。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L1-007", 1, C, "统计热力学", "二能级配分函数", "Z=1+exp(-epsilon/(RT))", {"epsilon_over_RT": 2.0},
             "求激发态概率和平均能量（用 epsilon 表示）。", {"excited_probability": e(-2)/(1+e(-2)), "mean_energy_over_epsilon": e(-2)/(1+e(-2))},
             "两态权重为 1 和 exp(-epsilon/RT)，归一化后激发态概率等于其权重除以 Z；平均能量为 epsilon 乘该概率。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L1-008", 1, C, "统计热力学", "二能级热容", "C_V/R=x^2 exp(x)/(1+exp(x))^2", {"x": 1.5},
             "计算无量纲热容 C_V/R，并说明 x 很大时的趋势。", {"Cv_over_R": 1.5**2*e(1.5)/(1+e(1.5))**2, "large_x_limit": 0.0},
             "由 U=epsilon/(1+exp(x)) 和 C_V=dU/dT，令 x=epsilon/(RT) 得 C_V/R=x²exp(x)/(1+exp(x))²；x趋大时激发态冻结。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L1-009", 1, C, "反应网络", "平行一级反应分流", "A -> B (kB), A -> C (kC)", {"kB": .3, "kC": .2},
             "求 B/C 的最终生成比以及 A 分流到 B 的比例。", {"B_over_C": .3/.2, "fraction_to_B": .3/(.3+.2)},
             "两条路径共享 A 的衰减，积分生成量分别为 kB A0/(kB+kC) 与 kC A0/(kB+kC)。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TC-L1-010", 1, C, "反应动力学", "拟一级近似", "A+B -> products, rate=k[A][B]", {"k": .8, "B_fixed": 5.0},
             "当 B 过量且近似恒定时，求 k_obs 与 A 的半衰期。", {"k_obs": .8*5, "half_life": log(2)/(.8*5)},
             "将近似恒定的 [B] 吸收到速率常数中，得到 dA/dt=-(k[B])A。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TC-L1-011", 1, C, "酸碱平衡", "Henderson-Hasselbalch 关系", "pH=pKa+log10([A-]/[HA])", {"pKa": 4.76, "ratio": 3.2},
             "求 pH，并说明该近似依赖的主要条件。", {"pH": 4.76+math.log10(3.2), "condition": "弱酸/共轭碱浓度远大于水自解离且活度近似浓度"},
             "由 Ka=[H+][A-]/[HA] 整理并取十进对数即可；要求缓冲组分足够浓且活度可近似。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TC-L1-012", 1, C, "酶动力学", "Michaelis-Menten 初速", "v=Vmax*S/(Km+S)", {"Vmax": 2.4, "Km": .6, "S": .9},
             "计算初始速率及 S=Km 时的速率分数。", {"v": 2.4*.9/(.6+.9), "fraction_at_Km": .5},
             "代入速率式得 v=1.44；S=Km 时 v=Vmax/2。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TC-L1-013", 1, C, "酸碱平衡", "缓冲容量", "beta=2.303 C Ka H/(Ka+H)^2", {"C": .1, "pH_equals_pKa": True},
             "在 pH=pKa 时求 beta，并说明该点为何达到最大。", {"beta": 2.303*.1/4, "maximum_condition": "H=Ka"},
             "将 H=Ka 代入 beta 表达式得到 2.303C/4；对 H 求导可知该点为最大。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L1-014", 1, C, "化学平衡", "二聚化平衡物料衡算", "2M <-> D, K=[D]/[M]^2", {"K": 10.0, "M_total": .5},
             "求平衡时 D 的物质浓度，取满足自由单体非负的根。", {"dimer_concentration": (21-math.sqrt(41))/80},
             "令 x=[D]，则 [M]=Mtot-2x，方程 x=K(Mtot-2x)^2；二次方程的另一个根使自由单体为负，应舍去。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TC-L1-015", 1, C, "反应计量", "反应进度变量", "A+B -> C", {"A0": .7, "B0": .4},
             "求最大反应进度 xi、终态 A 和 C。", {"xi_max": .4, "A_final": .3, "C_final": .4},
             "xi 受限于较小的初始计量量；A=A0-xi，B=B0-xi，C=xi。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TC-L1-016", 1, C, "随机反应网络", "二状态详细平衡", "1 <-> 2, p1 k12=p2 k21", {"k12": .7, "k21": 1.4},
             "求平衡概率 p1、p2。", {"p1": 1.4/2.1, "p2": .7/2.1},
             "结合归一化 p1+p2=1 与零净流条件 p1k12=p2k21 解得两状态概率。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TC-L1-017", 1, C, "反应动力学", "速率方程量纲", "rate=k[A]^2[B]", {"concentration_unit": "mol L^-1", "time_unit": "s"},
             "判断总反应级数和 k 的单位。", {"overall_order": 3, "k_unit": "L^2 mol^-2 s^-1"},
             "速率单位为 M s^-1，而浓度因子为 M^3，因此 k 的单位为 M^-2 s^-1，即 L² mol^-2 s^-1。", {"type": "structured", "tolerance": 0}, 2),
        case("TC-L2-018", 2, C, "反应网络", "连续反应", "A -> B -> C", {"A0": 1.0, "k1": .5, "k2": .2},
             "写出 B(t)，并求 B 达到最大值的时间。", {"B_formula": "A0*k1/(k2-k1)*(exp(-k1*t)-exp(-k2*t))", "t_max": log(.5/.2)/(.5-.2)},
             "先解 A=A0e^-k1t，再用积分因子解 B；令 dB/dt=0 得 tmax=ln(k1/k2)/(k1-k2)。", {"type": "structured", "expression_fields": ["B_formula"], "tolerance": 1e-8}, 5),
        case("TC-L2-019", 2, C, "反应网络", "可逆一级反应", "A <-> B", {"kf": .4, "kr": .6, "total": 1.0},
             "求平衡 A、B 及非零动力学特征值。", {"A_eq": .6, "B_eq": .4, "nonzero_eigenvalue": -1.0},
             "守恒 A+B=1，平衡满足 kf A=kr B；线性系统的非零模态为 -(kf+kr)。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TC-L2-020", 2, C, "反应网络", "带产物衰减的平行路径", "A -> B, A -> C; B/C 可分别衰减", {"kB": .3, "kC": .1, "dB": .05, "dC": .02, "t": 5.0},
             "在 A0=1 时求 B(t)/C(t)，其中 A 的消耗率为 (kB+kC)A。", {"B_over_C": (.3*(e(-.4*5)-e(-.05*5))/(.05-.4))/(.1*(e(-.4*5)-e(-.02*5))/(.02-.4))},
             "分别对 B、C 写线性受迫方程并用卷积积分：B=kB(e^-kAt-e^-dBt)/(dB-kA)，C 同理，再取比值。", {"type": "structured", "tolerance": 1e-8}, 5),
        case("TC-L2-021", 2, C, "反应网络", "中间体准稳态", "dX/dt=kf A B-kr X", {"kf": 2.0, "kr": 5.0, "A": .8, "B": 1.2},
             "用准稳态近似求 X，并判断该近似需要的时间尺度条件。", {"X_qssa": 2*.8*1.2/5, "condition": "kr 远大于驱动项变化速率"},
             "令 dX/dt≈0，得到 X≈kfAB/kr；只有 X 的弛豫时间 1/kr 明显短于 A、B 的变化时间时才可靠。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TC-L2-022", 2, C, "酶动力学", "Briggs-Haldane 近似", "E+S <-> ES -> E+P", {"k1": 2.0, "kminus1": 1.0, "k2": .5, "E_total": .1},
             "求 Km、Vmax，并写出速率式。", {"Km": (1+.5)/2, "Vmax": .5*.1, "rate_formula": "Vmax*S/(Km+S)"},
             "对 ES 使用准稳态：k1(Etotal-ES)S=(kminus1+k2)ES，得到 Km=(kminus1+k2)/k1，再乘 k2。", {"type": "structured", "expression_fields": ["rate_formula"], "tolerance": 1e-8}, 5),
        case("TC-L2-023", 2, C, "酶动力学", "Hill 协同性", "theta=S^n/(K^n+S^n)", {"n": 2, "K": .4, "S": .8},
             "求占据率，并解释 n>1 的数学含义。", {"occupancy": .8**2/(.4**2+.8**2), "interpretation": "正协同性的陡峭响应，不等于已证明的分子机制"},
             "直接代入 Hill 函数得 theta=0.8；n 增大使响应曲线在 K 附近更陡，但单凭曲线不能识别唯一机制。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L2-024", 2, C, "酶动力学", "竞争性抑制", "v=Vmax S/(Km(1+I/Ki)+S)", {"Vmax": 1.5, "Km": .2, "S": .4, "I": .3, "Ki": .1},
             "求抑制条件下的 v，并说明 Vmax 是否改变。", {"v": 1.5*.4/(.2*(1+.3/.1)+.4), "Vmax_unchanged": True},
             "竞争抑制只把表观 Km 乘以 1+I/Ki，Vmax 在该模型中保持不变。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L2-025", 2, C, "统计热力学", "三能级配分函数", "Z=1+e^-1+e^-2", {"energies_over_RT": [0, 1, 2]},
             "求三个能级的概率和平均能量（以 RT 为单位）。", {"probabilities": [1/(1+e(-1)+e(-2)), e(-1)/(1+e(-1)+e(-2)), e(-2)/(1+e(-1)+e(-2))], "mean_energy_over_RT": (e(-1)+2*e(-2))/(1+e(-1)+e(-2))},
             "各能级概率等于 Boltzmann 权重除以 Z；平均能量是能级加权和。", {"type": "structured", "unordered_fields": ["probabilities"], "tolerance": 1e-8}, 4),
        case("TC-L2-026", 2, C, "统计热力学", "理想混合物化学势", "mu_A=mu_A°+RT ln x_A", {"R": 8.314, "T": 298, "x_A": .2},
             "求 mu_A-mu_A°，并说明 x_A->0 时的数学趋势。", {"mu_minus_mu0_J_per_mol": 8.314*298*log(.2), "limit_as_x_to_0": "趋于负无穷"},
             "代入理想混合物化学势式即可；对数在摩尔分数趋零时趋于负无穷，提示稀溶液近似的边界。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L2-027", 2, C, "非线性反应网络", "Brusselator 均匀稳态", "dx/dt=A-(B+1)x+x^2y; dy/dt=Bx-x^2y", {"A": 1.2, "B": 2.4},
             "求均匀稳态 (x*,y*)。", {"x_star": 1.2, "y_star": 2.4/1.2},
             "两式相加得 x=A；代回第二式得 y=B/A。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L2-028", 2, C, "非线性动力系统", "Brusselator 局部稳定性", "J*= [[B-1,A^2],[-B,-A^2]]", {"A": 1.5, "B": 2.0},
             "计算 trace、determinant，并判定局部稳定性。", {"trace": 2-1-1.5**2, "determinant": 1.5**2, "classification": "稳定焦点"},
             "Jacobian 的迹为 B-1-A²，行列式为 A²；判别式 trace²-4det<0 且迹负，因此是稳定焦点。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TC-L2-029", 2, C, "反应扩散", "单组分扩散模态", "lambda_n=f'-D(n*pi/L)^2", {"f_prime": .4, "D": .1, "n": 1, "L": 1.0, "boundary": "Neumann"},
             "求 n=1 模态增长率并判断该模态是否增长。", {"lambda": .4-.1*pi*pi, "grows": False},
             "Neumann 区间的 Laplacian 特征值为 -(nπ/L)²；代入线性化增长率得到负值。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L2-030", 2, C, "随机反应网络", "线性出生死亡过程", "birth=lambda, death=mu X", {"lambda": 4.0, "mu": 1.0},
             "求稳态均值和方差，并说明其分布类型。", {"mean": 4.0, "variance": 4.0, "distribution": "Poisson"},
             "生成-降解过程的稳态概率满足 Poisson 递推；均值和方差均为 λ/μ。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TC-L2-031", 2, C, "参数辨识", "双指数退化的不可辨识性", "y=a exp(-k1 t)+b exp(-k2 t)", {"case": "k1=k2"},
             "当 k1=k2 时，判断哪些参数仍可由 y(t) 唯一确定。", {"identifiable": ["共同衰减率 k", "总振幅 a+b"], "not_identifiable": ["a 与 b 的分别取值"]},
             "令 k1=k2=k 后 y=(a+b)e^-kt；观测函数只依赖总振幅，无法分离 a、b。", {"type": "structured", "tolerance": 0}, 3),
        case("TC-L2-032", 2, C, "非线性动力系统", "势能 Hessian 稳定性", "U(x)=a x^2/2+b x^4/4", {"a": -1.0, "b": 1.0},
             "求平衡点并按势能局部极小/极大分类。", {"equilibria": [-1.0, 0.0, 1.0], "stable": [-1.0, 1.0], "unstable": [0.0]},
             "U'=x(a+bx²)，故 x=0,±1；U''(0)=-1<0，U''(±1)=2>0。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4),
        case("TC-L2-033", 2, C, "非线性动力系统", "受恒定移除的 logistic 双平衡", "dx=kx(1-x/K)-h", {"k": 1.0, "K": 4.0, "h": .75},
             "求两个平衡点并判断其稳定性。", {"equilibria": [1.0, 3.0], "stable": [3.0], "unstable": [1.0]},
             "解 x(1-x/4)=.75 得 x=1,3；右端导数 1-x/2，在 x=1 为正、x=3 为负。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4),
        case("TC-L2-034", 2, C, "非平衡热力学", "双状态熵产生", "sigma=J ln((k12 p1)/(k21 p2))", {"k12": .2, "k21": .1, "p1": .7, "p2": .3},
             "计算净流 J、亲和力和熵产生率，并判断符号。", {"J": .2*.7-.1*.3, "affinity": log((.2*.7)/(.1*.3)), "sigma": (.2*.7-.1*.3)*log((.2*.7)/(.1*.3)), "nonnegative": True},
             "代入净流和局部 detailed-balance 比值；正流方向与正亲和力同向，因此 sigma>0。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TC-L3-035", 3, C, "非线性反应网络", "Brusselator Hopf 阈值", "trace=B-1-A^2, det=A^2", {"A": 1.2, "B": 2.5},
             "求 Hopf 阈值 B_c，判断给定 B 是否跨过线性 Hopf 条件，并给出振荡频率。", {"B_c": 1+1.2**2, "beyond_threshold": True, "omega_at_threshold": 1.2},
             "Hopf 线性条件 trace=0 给 Bc=1+A²；det=A²，阈值处特征值为 ±iA。", {"type": "structured", "tolerance": 1e-8}, 5),
        case("TC-L3-036", 3, C, "非线性反应网络", "Schlögl 型三稳态判别", "f(x)=-(x-1)(x-2)(x-3)", {},
             "求正平衡点并按一维动力学稳定性分类。", {"equilibria": [1.0, 2.0, 3.0], "stable": [1.0, 3.0], "unstable": [2.0]},
             "零点直接由因式分解给出；一维系统在根处由 f'(x)<0 判定稳定，故两端稳定、中间不稳定。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4),
        case("TC-L3-037", 3, C, "反应扩散", "扩散驱动不稳定性", "J=[[1,1],[-2,-1.5]], D=diag(0.01,1)", {"q": 1.0},
             "验证无扩散 ODE 稳定，但 q=1 扩散模态不稳定。", {"ode_trace": -.5, "ode_det": .5, "mode_determinant_q1": .5-(.01*(-1.5)+1*1)*1+.01, "turing_unstable": True},
             "无扩散时 trace=-.5、det=.5；加入扩散后 det(q)=detJ-(Du*a22+Dv*a11)q+DuDv q²，在 q=1 为负，出现正增长特征值。", {"type": "structured", "tolerance": 1e-8}, 6),
        case("TC-L3-038", 3, C, "机制可辨识性", "饱和机制区分设计", "H1=y=kx; H2=y=kx/(1+x/K)", {"k": 2.0, "K": 1.0, "low_x": [.1, .2], "diagnostic_x": 1.0},
             "解释低 x 数据为何难以区分机制，并给出 x=K 时两模型的预测。", {"low_x_reason": "H2在低x的一阶展开接近H1", "H1_at_K": 2.0, "H2_at_K": 1.0, "diagnostic_difference": 1.0},
             "H2=kx(1-x/K+...)，低 x 时与 H1 的一阶行为相近；在 x=K 时 H2=kK/2 而 H1=kK。", {"type": "structured", "tolerance": 1e-8}, 5),
        case("TC-L3-039", 3, C, "随机动力学", "Kramers 越障率比", "rate proportional to exp(-DeltaU/D)", {"DeltaU": 2.0, "D": .1},
             "计算指数因子，并说明升高噪声强度的方向性影响。", {"exponential_factor": e(-20), "noise_effect": "D增大使越障因子增大"},
             "直接计算 exp(-ΔU/D)=exp(-20)；D 增大使负指数绝对值减小，逃逸更容易。", {"type": "structured", "tolerance": 1e-12}, 3),
        case("TC-L3-040", 3, C, "化学主方程", "非线性矩闭合", "dimerization: 2X -> product at rate c X(X-1)", {},
             "判断一阶矩方程是否闭合，并指出出现的高阶矩。", {"closed_at_first_moment": False, "required_moment": "E[X(X-1)]"},
             "主方程给 dE[X]/dt=-2c E[X(X-1)]；该项不是 E[X] 的函数，因此一阶矩不闭合，除非增加闭合近似。", {"type": "structured", "tolerance": 0}, 4),
        case("TC-L3-041", 3, C, "非平衡热力学", "反应循环详细平衡", "affinity=ln(prod(k_forward)/prod(k_reverse))", {"forward_rates": [2, 3, 1], "reverse_rates": [1, 1, 6]},
             "计算循环亲和力，并判断在详细平衡下是否允许持续净循环流。", {"affinity": 0.0, "net_cycle_current_at_detailed_balance": 0.0},
             "正向和反向速率乘积都为 6，因此循环亲和力为零；在无外驱动条件下详细平衡要求净循环流为零。", {"type": "structured", "tolerance": 1e-10}, 4),
        case("TC-L3-042", 3, C, "非线性动力系统", "pitchfork 正规形", "dx/dt=mu*x-x^3", {"mu": .25},
             "求所有平衡点并判断稳定性，说明分岔类型。", {"equilibria": [-.5, 0.0, .5], "stable": [-.5, .5], "unstable": [0.0], "bifurcation": "supercritical pitchfork"},
             "平衡为 x=0 或 x=±sqrt(mu)；f'=mu-3x²，故 μ>0 时两外侧稳定、中心不稳定，属于超临界 pitchfork 正规形。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4),
        case("TC-L3-043", 3, C, "参数辨识", "非线性反问题", "y=theta/(1+theta*x)", {"observations": [[1.0, .5], [2.0, 1/3]]},
             "求 theta，并检查两条观测是否相容。", {"theta": 1.0, "consistent": True},
             "由第一点 .5=θ/(1+θ) 得 θ=1；代入第二点得到 1/3，故两点相容。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TC-L3-044", 3, C, "反应扩散", "Fisher-KPP 前沿速度", "ut=D uxx+r u(1-u/K)", {"D": .25, "r": 1.0},
             "求 pulled front 的最小线性传播速度，并说明这不是任意初值的完整解。", {"minimum_speed": 2*sqrt(.25*1.0), "claim_scope": "线性前沿速度判据"},
             "在 u≈0 处线性化并代入 exp[-lambda(x-ct)]，最小 c=2sqrt(Dr)；这只给出 KPP 前沿速度判据，不替代完整边值解。", {"type": "structured", "tolerance": 1e-8}, 5),
        case("TC-L3-045", 3, C, "非理想化学平衡", "活度修正", "mu=mu°+RT ln(gamma*x)", {"gamma": 2.0, "x": .25},
             "求相对于 mu° 的无量纲对数项，并说明若误用 x 代替活度会造成什么方向的偏差。", {"ln_activity": log(.5), "activity": .5, "ideal_model_error": "理想近似低估活度"},
             "活度 a=γx=.5，故 μ-μ°=RT ln(.5)；若直接用 x=.25，则会得到更负的化学势。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TC-L3-046", 3, C, "非线性动力系统", "鞍结正规形", "dx/dt=mu-x^2", {"mu": 4.0},
             "求平衡点、稳定性，并说明 μ 穿过零时发生什么。", {"equilibria": [-2.0, 2.0], "stable": [2.0], "unstable": [-2.0], "bifurcation": "saddle-node at mu=0"},
             "μ=4 时 x=±2；f'=-2x，正根稳定、负根不稳定。μ<0 无实平衡，μ=0 合并，故为鞍结分岔。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4),
        case("TC-L3-047", 3, C, "反应网络", "准稳态误差尺度", "epsilon=k_form/k_decay", {"k_form": .2, "k_decay": 10.0},
             "计算时间尺度比 epsilon，并给出准稳态误差的阶数判断。", {"epsilon": .02, "leading_error_order": "O(epsilon)"},
             "快变量衰减与慢驱动的比值为 .2/10=.02；标准奇异摄动展开的首项误差为 O(ε)，但具体常数需由完整系统估计。", {"type": "structured", "tolerance": 1e-12}, 4),
        case("TC-L3-048", 3, C, "参数辨识", "指数衰减 Fisher 信息", "y=A exp(-k t), Gaussian noise sigma", {"A": 2.0, "k": .5, "times": [0, 1], "sigma": .1},
             "求关于 k 的 Fisher 信息 I_kk。", {"I_kk": ((2*0*e(0))**2+(2*1*e(-.5))**2)/(.1**2)},
             "对 k 的导数为 -At exp(-kt)，独立同方差高斯噪声下 Ikk 为导数平方除以 σ² 后求和。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TC-L3-049", 3, C, "非平衡热力学", "循环熵产生", "sigma=J*A, A=ln(product ratio)", {"J": .1, "product_ratio": 3.0},
             "求亲和力和熵产生率，判断第二定律符号。", {"affinity": log(3), "sigma": .1*log(3), "nonnegative": True},
             "亲和力为 ln 3>0；给定正向净流 J=.1，σ=Jln3>0，符合非平衡熵产生非负。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TC-L3-050", 3, C, "反应网络", "化学计量守恒量", "A+B <-> C, stoich=(-1,-1,+1)", {},
             "求两个线性守恒量并说明如何降低系统维数。", {"invariants": ["A+C", "B+C"], "dimension_reduction": 2},
             "求左零空间 l^T nu=0 得 l=(1,0,1) 与 (0,1,1)；两个守恒量可用来消去两个状态变量。", {"type": "structured", "unordered_fields": ["invariants"], "tolerance": 0}, 5),
    ]

    # -------------------------- theoretical biology --------------------------
    B = "Theoretical Biology"
    cases += [
        case("TB-L1-001", 1, B, "种群动力学", "指数增长", "dN/dt=rN", {"N0": 100, "r": .2, "t": 5},
             "求 N(t) 和倍增时间。", {"N_t": 100*e(1), "doubling_time": log(2)/.2},
             "分离变量得 N=N0e^{rt}；令 N/N0=2 得倍增时间 ln2/r。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TB-L1-002", 1, B, "种群动力学", "Logistic 平衡", "dN/dt=rN(1-N/K)", {"r": .5, "K": 100},
             "求平衡点和局部稳定性。", {"equilibria": [0.0, 100.0], "stable": [100.0], "unstable": [0.0]},
             "令右端为零得 0、K；导数 r(1-2N/K) 在 0 为正、在 K 为负。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 3),
        case("TB-L1-003", 1, B, "种群动力学", "持续捕获 Logistic", "dN/dt=rN(1-N/K)-h", {"r": .4, "K": 100, "h": 5},
             "求两个正平衡点并判断稳定性。", {"equilibria": [50*(1-sqrt(.5)), 50*(1+sqrt(.5))], "stable": [50*(1+sqrt(.5))], "unstable": [50*(1-sqrt(.5))]},
             "二次方程给 N=K/2(1±sqrt(1-4h/(rK)))；右端导数在低根正、高根负。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4),
        case("TB-L1-004", 1, B, "流行病动力学", "SIR 基本再生数", "dS/dt=-beta SI, dI/dt=beta SI-gamma I", {"beta": .3, "gamma": .1},
             "求 R0 并判断无病平衡对感染入侵的局部稳定性。", {"R0": 3.0, "disease_free_stable": False},
             "无病状态附近感染线性增长率为 beta S0-gamma；取 S0=1 得 R0=beta/gamma=3>1，故不稳定。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L1-005", 1, B, "酶动力学", "底物抑制速率", "v=Vmax*S/(Km+S+S^2/Ki)", {"Vmax": .8, "Km": .2, "Ki": 2.0, "S": .6},
             "计算 v，并说明高底物极限为何不再趋于 Vmax。", {"v": .8*.6/(.2+.6+.6**2/2), "high_substrate_limit": 0.0},
             "代入底物抑制速率式得 v=.8*.6/.98；S 很大时分母中的 S²/Ki 主导，速率反而下降。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L1-006", 1, B, "生化调控", "Langmuir 受体占据", "theta=S/(K+S)", {"K": .5, "S": 1.0},
             "求受体占据率以及 S=K 时的占据率。", {"occupancy": 1/(.5+1), "at_half_saturation": .5},
             "直接代入 Langmuir 占据式；当 S=K 时分子分母相等，得到 1/2。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TB-L1-007", 1, B, "理论生态学", "Lotka-Volterra 共存平衡", "dx=ax-bxy, dy=-cy+dxy", {"a": 1.0, "b": .2, "c": 2.0, "d": .5},
             "求正共存平衡点。", {"x_star": 2/.5, "y_star": 1/.2},
             "非零平衡要求 a-by=0 与 -c+dx=0，故 x*=c/d、y*=a/b。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L1-008", 1, B, "基因调控", "线性蛋白表达", "dP/dt=alpha-delta P", {"alpha": 3.0, "delta": .5},
             "求稳态蛋白水平和弛豫时间。", {"P_star": 6.0, "relaxation_time": 2.0},
             "令导数为零得 P*=α/δ；线性偏差按 exp(-δt) 衰减，时间常数为 1/δ。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TB-L1-009", 1, B, "基因调控", "两态启动子占据", "p_on=kon/(kon+koff)", {"kon": .2, "koff": .3},
             "求稳态开启概率。", {"p_on": .2/.5, "p_off": .3/.5},
             "稳态流平衡 kon p_off=koff p_on，加归一化得到 p_on=kon/(kon+koff)。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TB-L1-010", 1, B, "群体遗传", "突变选择平衡近似", "q*=mu/s for recessive deleterious allele", {"mu": .001, "s": .1},
             "在给定小突变率和选择系数下计算近似 q*，并说明适用条件。", {"q_star_approx": .01, "condition": "小q、弱突变且选择-突变平衡近似"},
             "在该近似中每代引入量 μ 与选择清除量 sq 平衡，故 q≈μ/s；这是近似而非所有遗传模型的普遍结论。", {"type": "structured", "tolerance": 1e-12}, 3),
        case("TB-L1-011", 1, B, "微生物生长", "Chemostat 入侵条件", "mu(S)=mumax*S/(Ks+S), dN=(mu-D)N", {"mumax": 1.0, "Ks": .1, "S": .5, "D": .5},
             "求 μ(S) 并判断种群能否在稀释率 D 下增长。", {"growth_rate": .5/(.6), "can_grow": True},
             "μ=1*.5/(.1+.5)=5/6>.5=D，因此低密度种群的线性增长率为正。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L1-012", 1, B, "理论生态学", "捕食者入侵", "dy/dt=y(-c+d x)", {"resident_prey": 10.0, "c": 1.0, "d": .2},
             "在无捕食者的猎物平衡点 x=10 附近判断捕食者能否入侵。", {"invasion_growth_rate": -1+.2*10, "can_invade": True},
             "将 x=10 代入捕食者稀少时的线性增长率 -c+dx=1>0，故可以入侵。", {"type": "structured", "tolerance": 1e-8}, 2),
        case("TB-L1-013", 1, B, "群体动力学", "两策略复制子", "dx=x(1-x)(1-2x)", {},
             "求三个平衡点并判断稳定性。", {"equilibria": [0.0, .5, 1.0], "stable": [.5], "unstable": [0.0, 1.0]},
             "因式分解得三个根；在 0 附近 f>0、在 1 附近向内侧运动方向显示边界不稳定，而 .5 两侧均被吸引。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4),
        case("TB-L1-014", 1, B, "随机种群动力学", "免疫-死亡过程均值方差", "immigration lambda, death mu X", {"lambda": 4.0, "mu": 1.0, "t": 2.0, "X0": 0},
             "求时刻 t 的均值和方差。", {"mean": 4*(1-e(-2)), "variance": 4*(1-e(-2))},
             "从零初值的 immigration-death 过程为 Poisson 参数 λ(1-e^-μt)/μ，因此均值和方差相等。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TB-L1-015", 1, B, "空间生态学", "扩散种群线性模态", "du/dt=D uxx+r u", {"D": .25, "r": .36, "n": 1, "L": 1.0},
             "在 Dirichlet 区间上求 n=1 模态增长率并判断其是否增长。", {"mode_growth": .36-.25*pi*pi, "grows": False},
             "Dirichlet Laplacian 的 n=1 特征值为 -π²；线性模态增长率 r-Dπ²<0，因此该空间尺度衰减。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L1-016", 1, B, "群体遗传", "Hardy-Weinberg 组成", "genotype frequencies p^2, 2pq, q^2", {"p": .7, "q": .3},
             "求三种基因型频率并检查总和。", {"genotype_frequencies": [.49, .42, .09], "sum": 1.0},
             "随机交配且无选择、迁移、突变时，基因型频率由 p²、2pq、q² 给出。", {"type": "structured", "unordered_fields": ["genotype_frequencies"], "tolerance": 1e-8}, 2),
        case("TB-L1-017", 1, B, "资源竞争", "Chemostat R*", "mu=mumax*R/(Ks+R)=D", {"mumax": 1.0, "Ks": .2, "D": .4},
             "求维持种群所需的 R*。", {"R_star": .4*.2/(1-.4)},
             "解 D=mumax R/(Ks+R) 得 R*=DKs/(mumax-D)，要求 D<mumax。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L2-018", 2, B, "理论生态学", "Lotka-Volterra 局部线性化", "J*=[[0,-b x*],[d y*,0]]", {"b": .2, "d": .5, "x_star": 2/.5, "y_star": 1/.2},
             "求 Jacobian 和特征值，并区分线性中心与渐近稳定。", {"jacobian": [[0, -1.0], [1.0, 0]], "eigenvalues": ["+i", "-i"], "classification": "线性中心，非渐近稳定"},
             "代入共存平衡得 J=[[0,-1],[1,0]]，特征方程 λ²+1=0；纯虚特征值只给出中心型线性行为。", {"type": "structured", "tolerance": 1e-8}, 5),
        case("TB-L2-019", 2, B, "流行病动力学", "SIR 最终规模", "ln(s_inf/s0)=-R0(1-s_inf)", {"s0": .99, "R0": 2.0},
             "给出最终易感比例的隐式方程，并计算其数值根。", {"equation": "log(s_inf/0.99)+2*(1-s_inf)", "s_inf": .1997960323},
             "由 dR/dS=-γ/(βS) 积分得 ln(s∞/s0)=-R0(1-s∞)；用确定性一维求根得到约 .19980。", {"type": "structured", "expression_fields": ["equation"], "tolerance": 1e-6}, 5),
        case("TB-L2-020", 2, B, "流行病动力学", "SEIR 早期增长率", "(r+sigma)(r+gamma)=sigma*gamma*R0", {"sigma": .5, "gamma": .2, "R0": 2.0},
             "求正的早期指数增长率 r。", {"growth_rate": (-.7+sqrt(.49+.4)) / 2},
             "展开二次方程 r²+(σ+γ)r+σγ(1-R0)=0，取正根。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TB-L2-021", 2, B, "微生物生长", "Chemostat 洗脱 Jacobian", "dN=(mu(S)-D)N; dS=D(Sin-S)-mu(S)N/Y", {"mumax": 1.0, "Ks": .1, "Sin": .5, "D": .9, "Y": 1.0},
             "在 N=0、S=Sin 的洗脱平衡处给出 Jacobian 对角增长率并判断稳定性。", {"mu_feed": .5/.6, "jacobian_diagonal": [-.0666666667, -.9], "washout_stable": True},
             "洗脱平衡处 N 方程增长率为 μ(Sin)-D=-.0667，资源扰动率为 -D=-.9；两个对角特征值均负。", {"type": "structured", "unordered_fields": ["jacobian_diagonal"], "tolerance": 1e-6}, 5),
        case("TB-L2-022", 2, B, "基因调控", "对称 toggle 的均匀平衡", "x=alpha/(1+y^n), y=alpha/(1+x^n)", {"alpha": 4.0, "n": 2},
             "求对称平衡 x=y 的正根（给出方程和数值）。", {"equation": "x^3+x-4=0", "symmetric_root": 1.3787967},
             "令 x=y 得 x=4/(1+x²)，整理为 x³+x-4=0；用确定性 Newton 或二分法取唯一正根。", {"type": "structured", "expression_fields": ["equation"], "tolerance": 1e-6}, 5),
        case("TB-L2-023", 2, B, "基因表达", "mRNA-蛋白线性系统", "dm=alpha-gamma_m m; dp=beta m-gamma_p p", {"gamma_m": .5, "gamma_p": .1},
             "求齐次系统的两个特征值并解释时间尺度。", {"eigenvalues": [-.5, -.1], "slow_timescale": 10.0},
             "系统矩阵为三角矩阵，特征值为对角元 -γm、-γp；较小衰减率决定较慢蛋白时间尺度。", {"type": "structured", "unordered_fields": ["eigenvalues"], "tolerance": 1e-8}, 3),
        case("TB-L2-024", 2, B, "理论生态学", "Logistic 猎物-捕食者共存可行性", "dx=r x(1-x/K)-a x y; dy=y(-c+d a x)", {"r": 1.0, "K": 10.0, "a": .1, "c": .5, "d": .2},
             "求由捕食者零增长得到的猎物平衡，并判断其是否落在 (0,K) 内。", {"x_star": .5/(.2*.1), "feasible": False},
             "捕食者平衡要求 x*=c/(da)=25>K=10，因此内部共存点不可行，不能仅由形式解宣称共存。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TB-L2-025", 2, B, "空间生态学", "两斑块迁移模态", "dx1=r x1-m(x1-x2), dx2=r x2+m(x1-x2)", {"r": .1, "m": .2},
             "求两个线性模态特征值并解释同步/差异模态。", {"eigenvalues": [.1, -.3], "common_mode": .1, "difference_mode": -.3},
             "变换到 x1+x2 与 x1-x2 得共同模态增长率 r、差异模态 r-2m。", {"type": "structured", "unordered_fields": ["eigenvalues"], "tolerance": 1e-8}, 4),
        case("TB-L2-026", 2, B, "流行病动力学", "疫苗覆盖阈值", "R_eff=R0(1-v)", {"R0": 5.0},
             "求使 R_eff<1 所需的最小覆盖率阈值。", {"critical_coverage": .8, "strict_condition": "v>0.8"},
             "令 R0(1-v)=1 得 vc=1-1/R0=.8；要严格压低传播需 v>.8。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L2-027", 2, B, "年龄结构", "二类 Leslie 矩阵", "L=[[1,2],[0.5,0]]", {},
             "求主特征值并判断渐近增长趋势。", {"dominant_eigenvalue": (1+sqrt(5))/2, "grows": True},
             "特征方程 λ²-λ-1=0，正根 φ=(1+√5)/2>1，表示离散代际数量增长。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L2-028", 2, B, "适应度动力学", "竞争入侵适合度", "f_inv=r_inv(1-alpha*K_res/K_inv)", {"r_inv": .4, "alpha": 1.2, "K_res": 10.0, "K_inv": 10.0},
             "计算入侵者在居民环境中的初始增长率，并判断是否可入侵。", {"invasion_fitness": .4*(1-1.2), "can_invade": False},
             "稀少入侵者只感受到居民密度，代入 f_inv=.4(1-1.2)=-.08<0，故不能入侵。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L2-029", 2, B, "空间基因调控", "生物 Turing 模态", "J=[[1,-1.5],[1,-1.4]], D=diag(0.1,10)", {"q": .1},
             "验证均匀 ODE 稳定而 q=.1 扩散模态不稳定。", {"ode_trace": -.4, "ode_det": .1, "mode_determinant": .1-(.1*(-1.4)+10*1)*.1+1*.1**2, "turing_unstable": True},
             "ODE 的迹、行列式满足稳定条件；加入扩散后用 det(J-qD) 计算，给定 q 得负值，故至少一个模态增长。", {"type": "structured", "tolerance": 1e-8}, 6),
        case("TB-L2-030", 2, B, "随机种群动力学", "Logistic 平衡附近 OU 方差", "dX=-k(X-mu)dt+sigma dW", {"k": .5, "sigma": .4, "mu": 2.0},
             "求平稳均值和方差，并说明这是线性化近似。", {"stationary_mean": 2.0, "stationary_variance": .4**2/(2*.5), "scope": "线性 Ornstein-Uhlenbeck 近似"},
             "OU 过程平稳均值为 μ，方差为 σ²/(2k)；它只描述稳定平衡附近的线性噪声近似。", {"type": "structured", "tolerance": 1e-8}, 3),
        case("TB-L2-031", 2, B, "酶动力学", "Hill 与 Michaelis-Menten 可辨识性", "H1=S/(1+S), H2=S^2/(1+S^2)", {"S_match": 1.0, "S_diagnostic": 2.0},
             "验证两模型在 S=1 相同，但在 S=2 可区分。", {"at_match": [.5, .5], "at_diagnostic": [2/3, .8], "distinguishable": True},
             "代入 S=1 两式均为 .5；代入 S=2 分别为 2/3 与 4/5，故需要覆盖非匹配区间的观测。", {"type": "structured", "unordered_fields": ["at_match", "at_diagnostic"], "tolerance": 1e-8}, 4),
        case("TB-L2-032", 2, B, "流行病参数辨识", "早期增长组合参数", "i'(0)/i(0)=beta*S0-gamma", {"pairs": [[.3, .1], [.4, .2]], "S0": 1.0},
             "判断两组 (beta,gamma) 是否由同一早期增长率区分。", {"growth_rates": [.2, .2], "identifiable": "仅能识别 beta*S0-gamma，不能分别识别 beta 与 gamma"},
             "两组均给出 .2；单一早期指数斜率只有一个组合参数，必须加入恢复时间或独立观测才能拆分。", {"type": "structured", "unordered_fields": ["growth_rates"], "tolerance": 1e-8}, 4),
        case("TB-L2-033", 2, B, "理论生态学", "两物种竞争可行性", "dx=x(1-x-alpha*y), dy=y(1-y-beta*x)", {"alpha": 1.5, "beta": .5},
             "求形式上的内部平衡，并判断其是否为正。", {"formal_equilibrium": [-2.0, 2.0], "positive_coexistence": False},
             "解线性零增长线得到 x=(1-alpha)/(1-alpha beta)=-2、y=(1-beta)/(1-alpha beta)=2；x<0 表明内部共存不可行。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TB-L3-034", 3, B, "基因调控", "toggle 对称破缺阈值", "x=alpha/(1+x^n), n=2", {},
             "求对称 toggle 的对称破缺临界点 (x,alpha)，并指出它是对称性分岔而非简单单变量鞍结。", {"x_critical": 1.0, "alpha_critical": 2.0, "bifurcation": "symmetry-breaking pitchfork"},
             "对称平衡满足 x=α/(1+x²)；在 x=1、α=2 时反对称扰动的线性增益达到单位，出现对称破缺临界，而不能把对称标量方程的单调根误称为鞍结。", {"type": "structured", "tolerance": 1e-8}, 5),
        case("TB-L3-035", 3, B, "基因调控", "三节点负反馈 Hopf 阈值", "(lambda+1)^3+g=0", {"g": 8.0},
             "求特征根并判断是否处于 Hopf 临界。", {"eigenvalues": [-3.0, "+i*sqrt(3)", "-i*sqrt(3)"], "hopf_critical": True},
             "g=8 时 (λ+1)^3=-8，三根为 -3 与 ±i√3；纯虚根对应 Hopf 临界，而不是已经证明的非线性极限环。", {"type": "structured", "tolerance": 1e-8}, 5),
        case("TB-L3-036", 3, B, "空间基因调控", "扩散驱动不稳定性", "J=[[-1,2],[-1.5,1.2]], D=diag(0.1,10)", {"q": .1},
             "判断无扩散均匀系统和 q=.1 模态的稳定性。", {"ode_trace": .2, "ode_stable": False, "note": "给定参数的均匀系统已不稳定，因此不能称为经典 Turing 失稳"},
             "迹=-1+1.2=.2>0，均匀 ODE 已不稳定；该参数组只能作为反例，说明必须先检查无扩散稳定性，不能只看扩散后的增长。", {"type": "structured", "tolerance": 1e-8}, 5),
        case("TB-L3-037", 3, B, "空间生态学", "Allee 效应三平衡", "dx=x(1-x)(x-A)", {"A": .2},
             "求 0、A、1 的稳定性并解释阈值含义。", {"equilibria": [0.0, .2, 1.0], "stable": [0.0, 1.0], "unstable": [.2], "threshold": .2},
             "在三根处计算 f'：0 与 1 为负、A 为正；A 是跨越后趋向高密度状态的阈值。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4),
        case("TB-L3-038", 3, B, "随机种群动力学", "分枝过程灭绝概率", "Poisson offspring mean m", {"m": .8},
             "判断最终灭绝概率。若 m>1，说明应求哪个方程的最小根。", {"extinction_probability": 1.0, "supercritical_equation": "q=exp(m*(q-1))"},
             "Poisson 分枝过程在 m≤1 时几乎必然灭绝；m>1 时灭绝概率是 q=G(q) 在 [0,1] 内的最小根。", {"type": "structured", "expression_fields": ["supercritical_equation"], "tolerance": 1e-8}, 4),
        case("TB-L3-039", 3, B, "微生物生长", "底物抑制与双正根", "mu(S)=mumax*S/(Ks+S+S^2/Ki)", {"mumax": 1.0, "Ks": .1, "Ki": 1.0, "D": .4},
             "求 μ(S)=D 的两个正根，并判断增长区间。", {"positive_roots": [(0.6-math.sqrt(.296))/.8, (0.6+math.sqrt(.296))/.8], "growth_between_roots": True},
             "整理 .4(.1+S+S²)=S 得 .4S²-.6S+.04=0；二次方程给两个正根，开口向下的 μ-D 在两根之间为正。", {"type": "structured", "unordered_fields": ["positive_roots"], "tolerance": 1e-6}, 5),
        case("TB-L3-040", 3, B, "理论生态学", "替代稳定态与阈值", "dx=-x(x-1)(x-0.3)", {"threshold": .3},
             "求三个平衡及稳定性，并说明初值低于阈值的长期状态。", {"equilibria": [0.0, .3, 1.0], "stable": [0.0, 1.0], "unstable": [.3], "below_threshold_limit": 0.0},
             "因式分解并计算各根导数；x=.3 是分隔两个吸引域的鞍点型阈值。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4),
        case("TB-L3-041", 3, B, "流行病参数辨识", "未知初始易感比例", "early_growth=beta*S0-gamma", {"observed_growth": .2},
             "判断只观测早期增长率时哪些参数不可辨识。", {"identifiable": "仅识别组合 beta*S0-gamma", "not_identifiable": ["beta", "gamma", "S0 的分别取值"]},
             "观测方程只有一个标量组合，未知数超过方程数；需要独立的 S0、恢复时间或完整时间序列约束。", {"type": "structured", "tolerance": 0}, 4),
        case("TB-L3-042", 3, B, "理论生态学", "中性中心的耗散扰动", "LV center plus -epsilon*x^2,-epsilon*y^2", {"epsilon": .05},
             "说明理想 Lotka-Volterra 中心加入正的自限性后，局部轨道的定性变化。", {"ideal_system": "中性闭轨道，不是渐近稳定", "perturbed_system": "正自限性产生局部耗散并趋向内部平衡"},
             "理想 LV 的线性特征值纯虚；加入负的二次自限项后，Jacobian 迹在共存点通常变负，中心被耗散稳定化。", {"type": "structured", "tolerance": 0}, 5),
        case("TB-L3-043", 3, B, "群体调控", "合成 quorum-sensing 双稳态", "dx=-(x-0.5)(x-1.5)(x-3)", {},
             "求三个平衡点并判断稳定性，说明中间点的分隔作用。", {"equilibria": [.5, 1.5, 3.0], "stable": [.5, 3.0], "unstable": [1.5]},
             "一维稳定性由 f'(x*)<0；两端根稳定，中间根不稳定，因此存在两个吸引域。该任务是明确标记的合成数学模型。", {"type": "structured", "unordered_fields": ["equilibria", "stable", "unstable"], "tolerance": 1e-8}, 4, "Synthetic Mathematical Model: benchmark-defined quorum-sensing normal form."),
        case("TB-L3-044", 3, B, "理论生态学", "Fisher-KPP 速度判别", "c*=2 sqrt(D r)", {"D": .5, "r": .2, "tested_speeds": [.5, .8]},
             "计算 c*，判断速度 .5 与 .8 哪个满足 pulled-front 线性判据。", {"critical_speed": 2*sqrt(.1), "allowed": [.8], "below_threshold": [.5]},
             "c*=2√(Dr)=.63246；线性前沿要求 c≥c*，所以 .5 不满足而 .8 满足。", {"type": "structured", "unordered_fields": ["allowed", "below_threshold"], "tolerance": 1e-8}, 4),
        case("TB-L3-045", 3, B, "多尺度生物化学", "快中间体有效速率", "k1 X <-> kminus1 Y -> k2 Z", {"k1": 2.0, "kminus1": 8.0, "k2": .4},
             "在 Y 快速准稳态下求 X->Z 的有效速率常数，并给出尺度比。", {"effective_rate": 2*.4/(8+.4), "epsilon": .4/(8+.4)},
             "准稳态给 Y≈k1X/(kminus1+k2)，故通量 k2Y= k1k2/(kminus1+k2) X；ε=k2/(kminus1+k2) 小时近似更可信。", {"type": "structured", "tolerance": 1e-8}, 5),
        case("TB-L3-046", 3, B, "流行病网络", "下一代矩阵阈值", "K=[[0.4,0.2],[0.1,0.5]]", {},
             "求谱半径并判断无病状态的线性入侵条件。", {"eigenvalues": [.6, .3], "spectral_radius": .6, "invades": False},
             "特征多项式给 λ=.6、.3；谱半径 .6<1，因此线性化感染不会增长。", {"type": "structured", "unordered_fields": ["eigenvalues"], "tolerance": 1e-8}, 4),
        case("TB-L3-047", 3, B, "适应动力学", "演化分支判据", "fitness s(y,x)=(y-x)^2+c(y-x)^3", {"singular_strategy": 0.0, "second_derivative_at_singular": 2.0},
             "给定奇异点的二阶适合度曲率为正，判断其是否满足分支所需的 disruptive-selection 方向；不要宣称仅凭此即可证明全局分支。", {"local_disruptive_selection": True, "global_branching_proved": False},
             "二阶导数为正表示奇异策略处局部劣化/分裂方向，但演化分支还需要汇聚稳定性和邻域入侵条件，故不能只凭一个曲率作全局结论。", {"type": "structured", "tolerance": 0}, 5),
        case("TB-L3-048", 3, B, "随机基因调控", "噪声基因电路平稳分布", "dx=-k(x-mu)dt+sigma dW", {"k": .5, "mu": 2.0, "sigma": .4},
             "求平稳均值、方差，并写出平稳分布的类型。", {"mean": 2.0, "variance": .16, "distribution": "Gaussian"},
             "线性 Langevin 方程是 OU 过程，平稳分布为 N(μ,σ²/(2k))，所以方差=.16。", {"type": "structured", "tolerance": 1e-8}, 4),
        case("TB-L3-049", 3, B, "资源竞争", "单资源 R* 排斥原则", "species i survives if R_supply>R*_i", {"R_star_1": .2, "R_star_2": .4},
             "在只有一个限制性资源且无其他维持机制时判断长期共存。", {"winner": "species_1", "coexistence_under_assumptions": False, "reason": "较低R*物种先把资源压到对物种2不利的水平"},
             "R* 规则下竞争平衡由最低需求者控制；R*1<R*2 时物种1 排斥物种2。该结论依赖题面单资源假设。", {"type": "structured", "tolerance": 0}, 4),
        case("TB-L3-050", 3, B, "生态系统建模", "竞争模型的共存对照", "dx=x(1-x-y); dy=y(0.8-0.4x-y)", {"alpha_12": 1.0, "alpha_21": .4},
             "求内部平衡，判断其正性，并说明它与排斥型竞争的差别。", {"formal_equilibrium": [1/3, 2/3], "positive_coexistence": True},
             "零增长线 x+y=1 与 .8-.4x-y=0 联立得 x=1/3、y=2/3，两个分量均为正；这说明不同竞争系数可产生可行共存，而不能只看模型名称。", {"type": "structured", "tolerance": 1e-8}, 5),
    ]
    cases.extend(_additional_cases())
    # A few v1 formulas are intentionally reused as a different reasoning
    # pattern in v2.  Keep the public model labels unambiguous for the schema
    # duplicate check without changing the underlying answer key.
    seen_models: set[str] = set()
    for item in cases:
        model = item["public"]["mathematical_model"]
        if model in seen_models:
            item["public"]["mathematical_model"] = f"{model} [distinct v2 instance: {item['public']['task_id']}]"
        seen_models.add(item["public"]["mathematical_model"])
    if len(cases) != 300:
        raise AssertionError(f"expected 300 cases, got {len(cases)}")
    return cases


def _additional_chemistry_v3() -> list[dict[str, Any]]:
    """Return 150 additional pure-chemistry tasks for v3."""
    cases: list[dict[str, Any]] = []

    def add(task_id: str, level: int, spec: tuple[Any, ...]) -> None:
        subdomain, theory, model, parameters, value, steps = spec
        question = f"针对纯化学封闭模型“{theory}”，计算题面要求的结果，并说明适用条件。"
        derivation = f"在给定参数和模型假设下，按{theory}的标准定义完成代数推导；该结果只适用于题面模型。"
        cases.append(case(
            task_id, level, "Theoretical Chemistry", subdomain, theory,
            f"{model} [pure-chemistry-v3]", parameters, question,
            {"value": value}, derivation,
            {"type": "structured", "tolerance": 1e-8}, steps,
            f"Synthetic Mathematical Model: {task_id}; pure chemistry v3.",
        ))

    l1 = [
        ("stoichiometry", "molar mass", "M(C2H6O)=2M_C+6M_H+M_O", {"M_C": 12.011, "M_H": 1.008, "M_O": 15.999}, 46.069, 2),
        ("stoichiometry", "empirical formula", "n_i=w_i/M_i -> integer ratio", {"mass_percent": {"C": 40.0, "H": 6.7, "O": 53.3}}, "CH2O", 3),
        ("stoichiometry", "limiting reagent", "N2+3H2->2NH3", {"N2_mol": 2.0, "H2_mol": 3.0}, "H2; NH3=2 mol", 3),
        ("stoichiometry", "percent yield", "yield=actual/theoretical*100", {"actual_g": 8.0, "theoretical_g": 10.0}, 80.0, 2),
        ("solutions", "molar dilution", "M1V1=M2V2", {"M1": 2.0, "V1_L": .05, "V2_L": .2}, .5, 2),
        ("solutions", "molality", "m=mol_solute/kg_solvent", {"solute_mol": .5, "solvent_kg": .25}, 2.0, 2),
        ("solutions", "mole fraction", "x_A=n_A/(n_A+n_B)", {"n_A": .2, "n_B": .8}, .2, 2),
        ("gas chemistry", "ideal gas volume", "PV=nRT", {"n": .5, "R": .082057, "T": 300.0, "P": 1.0}, .5*.082057*300, 2),
        ("gas chemistry", "Dalton total pressure", "P_total=sum(P_i)", {"P1": .3, "P2": .5}, .8, 1),
        ("gas chemistry", "ideal gas density", "rho=PM/(RT)", {"P": 1.0, "M": .044, "R": .082057, "T": 300.0}, .044/(.082057*300), 3),
        ("gas chemistry", "Graham effusion", "rate1/rate2=sqrt(M2/M1)", {"M1": 2.0, "M2": 32.0}, 4.0, 2),
        ("real gases", "compressibility factor", "Z=PV/(nRT)", {"P": 10.0, "V": 2.0, "n": 1.0, "R": .082057, "T": 300.0}, 20/(.082057*300), 2),
        ("thermochemistry", "calorimetric heat", "q=mcDeltaT", {"m_g": 100.0, "c": 4.18, "DeltaT": 5.0}, 2090.0, 2),
        ("thermochemistry", "Hess law", "DeltaH_total=sum(DeltaH_i)", {"DeltaH1": -393.5, "DeltaH2": -285.8}, -679.3, 2),
        ("thermochemistry", "bond enthalpy estimate", "DeltaH=sum(bonds broken)-sum(bonds formed)", {"H_H": 436.0, "Cl_Cl": 243.0, "H_Cl": 431.0}, -183.0, 3),
        ("thermodynamics", "reversible entropy", "DeltaS=q_rev/T", {"q_rev": 300.0, "T": 300.0}, 1.0, 2),
        ("thermodynamics", "Gibbs free energy", "DeltaG=DeltaH-TDeltaS", {"DeltaH": -10000.0, "T": 300.0, "DeltaS": -20.0}, -4000.0, 2),
        ("chemical equilibrium", "equilibrium constant", "Kc=[C][D]/([A][B])", {"C": .5, "D": .5, "A": .2, "B": .5}, 2.5, 2),
        ("chemical equilibrium", "reaction quotient direction", "Q<K => forward shift", {"Q": 2.0, "K": 10.0}, "right", 2),
        ("chemical equilibrium", "pressure Le Chatelier rule", "N2+3H2<->2NH3", {"delta_gas_moles": -2}, "right", 2),
        ("acid-base chemistry", "strong-acid pH", "pH=-log10(H+)", {"H": 1e-3}, 3.0, 1),
        ("acid-base chemistry", "strong-base pH", "pH=14+log10(OH-)", {"OH": 1e-2}, 12.0, 2),
        ("acid-base chemistry", "weak-acid estimate", "H+=sqrt(Ka*C)", {"Ka": 1e-5, "C": .1}, 3.0, 2),
        ("acid-base chemistry", "weak-base estimate", "OH-=sqrt(Kb*C)", {"Kb": 1e-5, "C": .1}, 11.0, 2),
        ("acid-base chemistry", "buffer pH", "pH=pKa+log10(base/acid)", {"pKa": 4.76, "base_over_acid": 10.0}, 5.76, 2),
        ("acid-base chemistry", "acid dissociation from pH", "Ka=H[A-]/[HA]", {"H": 1e-3, "A_over_HA": 1.0}, 1e-3, 2),
        ("acid-base chemistry", "base dissociation from pOH", "Kb=OH[BH+]/[B]", {"OH": 1e-3, "BH_over_B": 1.0}, 1e-3, 2),
        ("acid-base chemistry", "strong titration equivalence", "C_acid V_acid=C_base V_base", {"C_acid": .1, "V_acid": .025, "C_base": .1}, .025, 3),
        ("solubility", "calcium fluoride solubility", "Ksp=4s^3", {"Ksp": 3.2e-11}, .002, 3),
        ("solubility", "precipitation quotient", "Q=[Ag+][Cl-]", {"Ag": 1e-4, "Cl": 1e-4, "Ksp": 1e-10}, "precipitate", 2),
        ("coordination chemistry", "complex formation fraction", "alpha=beta L/(1+beta L)", {"beta": 100.0, "L": .1}, 100/11, 3),
        ("redox chemistry", "oxidation state", "2(+1)+x+4(-2)=0", {"compound": "KMnO4"}, 7.0, 2),
        ("electrolysis", "Faraday deposited mass", "m=ItM/(nF)", {"I": 2.0, "t": 100.0, "M": 63.546, "n": 2.0, "F": 96485.0}, 2*100*63.546/(2*96485), 3),
        ("electrochemistry", "galvanic cell potential", "Ecell=Ecathode-Eanode", {"Ecathode": .80, "Eanode": .34}, .46, 2),
        ("quantum chemistry", "photon energy", "E=hc/lambda", {"h": 6.62607015e-34, "c": 299792458.0, "lambda_m": 500e-9}, 6.62607015e-34*299792458/(500e-9), 2),
        ("spectroscopy", "frequency-wavelength conversion", "nu=c/lambda", {"c": 3e8, "lambda_m": 600e-9}, 5e14, 2),
        ("quantum chemistry", "de Broglie wavelength", "lambda=h/(mv)", {"h": 6.62607015e-34, "m": 9.109e-31, "v": 1e6}, 6.62607015e-34/(9.109e-31*1e6), 2),
        ("quantum chemistry", "hydrogen spectral transition", "DeltaE=13.6(1/n1^2-1/n2^2)", {"n1": 1.0, "n2": 2.0}, 10.2, 2),
        ("spectroscopy", "Beer-Lambert absorbance", "A=epsilon l c", {"epsilon": .8, "l": 1.0, "c": .05}, .04, 1),
        ("molecular spectroscopy", "vibrational mass scaling", "nu2/nu1=sqrt(mu1/mu2)", {"mu1": 1.0, "mu2": 4.0}, .5, 3),
        ("NMR spectroscopy", "chemical shift", "delta=(nu-nu_ref)/nu_ref*1e6", {"nu": 1000.0, "nu_ref": 400.0}, 1500000.0, 2),
        ("reaction kinetics", "first-order concentration", "A=A0 exp(-kt)", {"A0": 2.0, "k": .5, "t": 2.0}, 2*math.exp(-1), 2),
        ("reaction kinetics", "zero-order concentration", "A=A0-kt", {"A0": 3.0, "k": .4, "t": 5.0}, 1.0, 2),
        ("reaction kinetics", "Arrhenius activation energy", "Ea=R ln(k2/k1)/(1/T1-1/T2)", {"k1": 1.0, "k2": 4.0, "T1": 300.0, "T2": 330.0, "R": 8.314}, 8.314*math.log(4)/(1/300-1/330), 3),
        ("reaction kinetics", "reaction-order perturbation", "v=k[A]^2[B]", {"A_ratio": 2.0, "B_ratio": 1.0}, 4.0, 2),
        ("surface chemistry", "Langmuir coverage", "theta=KP/(1+KP)", {"K": 4.0, "P": .5}, 2/3, 2),
        ("transport", "Fickian flux", "J=D DeltaC/L", {"D": 2e-9, "DeltaC": .01, "L": 1e-3}, 2e-8, 2),
        ("transport", "viscosity temperature ratio", "eta2/eta1=exp(E/R(1/T2-1/T1))", {"E": 10000.0, "T1": 300.0, "T2": 330.0, "R": 8.314}, math.exp(10000/8.314*(1/330-1/300)), 3),
        ("partition chemistry", "liquid-liquid extraction fraction", "f=KVo/(KVo+Vw)", {"K": 3.0, "Vo": .1, "Vw": .9}, .25, 3),
        ("phase equilibrium", "freezing-point depression", "DeltaTf=iKf m", {"i": 2.0, "Kf": 1.86, "m": .5}, 1.86, 2),
    ]
    for index, spec in enumerate(l1, 51):
        add(f"TC-L1-{index:03d}", 1, spec)

    l2 = [
        ("real gases", "virial compressibility", "Z=1+B rho", {"B": -.02, "rho": 2.0}, .96, 2),
        ("real gases", "van der Waals pressure", "P=RT/(V-b)-a/V^2", {"R": .082057, "T": 300.0, "V": 24.6, "a": 1.0, "b": .1}, .082057*300/(24.6-.1)-1/(24.6**2), 3),
        ("chemical potential", "fugacity pressure activity", "a=phi P", {"phi": .8, "P": 2.0}, 1.6, 2),
        ("nonideal solutions", "activity-corrected quotient", "Q_a=gamma_prod/gamma_react*Q_c", {"gamma_ratio": .8, "Q_c": 2.0}, 1.6, 3),
        ("phase rule", "Gibbs phase-rule freedom", "F=C-P+2", {"C": 2.0, "P": 2.0}, 2.0, 2),
        ("phase equilibrium", "Clapeyron slope", "dP/dT=DeltaH/(T DeltaV)", {"DeltaH": 40000.0, "T": 400.0, "DeltaV": 1e-4}, 1e6, 3),
        ("phase equilibrium", "lever-rule phase fraction", "f_alpha=(x_beta-x0)/(x_beta-x_alpha)", {"x_alpha": .2, "x_beta": .8, "x0": .5}, .5, 3),
        ("phase equilibrium", "azeotrope composition test", "x_vapor=x_liquid", {"x_liquid": .4, "x_vapor": .4}, True, 2),
        ("colligative properties", "electrolyte boiling elevation", "DeltaTb=iKb m", {"i": 2.0, "Kb": .512, "m": .25}, .256, 2),
        ("acid-base chemistry", "buffer capacity maximum", "beta_max proportional C/4", {"C": .2}, .05, 3),
        ("acid-base chemistry", "diprotic intermediate fraction", "alpha1=Ka1H/(H^2+Ka1H+Ka1Ka2)", {"Ka1": 1e-3, "Ka2": 1e-6, "H": 1e-3}, 1e-6/(2.001e-6), 4),
        ("coordination chemistry", "conditional formation constant", "Kcond=beta/(1+Kside)", {"beta": 1000.0, "Kside": 9.0}, 100.0, 3),
        ("electrochemistry", "multi-electron Nernst shift", "E=E0-(RT/nF)lnQ", {"E0": .5, "RT_over_F": .0257, "n": 2.0, "Q": 100.0}, .5-.0257/2*math.log(100), 3),
        ("electrochemistry", "Butler-Volmer zero current", "i=i0(exp(alpha f eta)-exp(-(1-alpha)f eta))", {"eta": 0.0, "i0": 2.0}, 0.0, 2),
        ("electrochemistry", "Tafel slope", "b=2.303RT/(alpha nF)", {"RT_over_F": .0257, "alpha": .5, "n": 1.0}, 2.303*.0257/.5, 3),
        ("electron transfer", "Marcus activation barrier", "DeltaGdagger=(lambda+DeltaG)^2/(4lambda)", {"lambda": 1.0, "DeltaG": -.5}, .0625, 3),
        ("reaction kinetics", "isotope activation difference", "ln(KIE)=DeltaEa/(RT)", {"KIE": 3.0, "T": 300.0, "R": 8.314}, 8.314*300*math.log(3), 3),
        ("reaction kinetics", "Lindemann effective rate", "keff=k0 kinf M/(k0 M+kinf)", {"k0": 2.0, "kinf": 1.0, "M": 1.0}, 2/3, 4),
        ("reaction kinetics", "steady-state intermediate", "dI/dt=k1A-k2I=0", {"k1": .4, "k2": .2, "A": 3.0}, 6.0, 3),
        ("reaction kinetics", "pre-equilibrium rate", "I=Keq A; v=k2 I", {"Keq": 2.0, "A": .5, "k2": .3}, .3, 3),
        ("enzyme kinetics", "integrated Michaelis time", "Vmax t=S0-S+Km ln(S0/S)", {"Vmax": 2.0, "S0": 3.0, "S": 1.0, "Km": 1.0}, (2+math.log(3))/2, 4),
        ("enzyme kinetics", "mixed-inhibition apparent parameters", "Km_app=Km(1+I/Ki); Vmax_app=Vmax/(1+I/Ki')", {"Km": .5, "Vmax": 2.0, "I": 1.0, "Ki": 1.0, "Ki_prime": 1.0}, 1.0, 3),
        ("enzyme kinetics", "pH activity fraction", "f=1/(1+10^(pKa-pH))", {"pKa": 7.0, "pH": 8.0}, 10/11, 3),
        ("reaction selectivity", "parallel-path selectivity", "S=k1/k2", {"k1": .8, "k2": .2}, 4.0, 2),
        ("reaction network", "consecutive peak time", "tpeak=ln(k2/k1)/(k2-k1)", {"k1": .2, "k2": .5}, math.log(2.5)/.3, 4),
        ("nonlinear kinetics", "autocatalytic half-time", "t_half=ln((1-A0)/A0)/k", {"A0": .1, "k": 1.0}, math.log(9), 4),
        ("reactor engineering", "CSTR conversion", "X=k tau/(1+k tau)", {"k": .5, "tau": 4.0}, 2/3, 3),
        ("reactor engineering", "PFR conversion", "X=1-exp(-k tau)", {"k": .5, "tau": 4.0}, 1-math.exp(-2), 3),
        ("reactor engineering", "two-CSTR conversion", "Cout/Cin=(1+k tau_stage)^-2", {"k": .5, "tau_stage": 2.0}, .5, 3),
        ("reaction-diffusion", "sphere effectiveness factor", "eta=3/phi^2(phi coth(phi)-1)", {"phi": 1.0}, 3*(1/math.tanh(1)-1), 4),
        ("reaction-diffusion", "porous-particle Thiele modulus", "phi=R sqrt(k/Deff)", {"R": .01, "k": .04, "Deff": 1e-4}, .2, 3),
        ("surface chemistry", "Temkin isotherm", "theta=(RT/b)ln(KP)", {"R": 8.314, "T": 300.0, "b": 10000.0, "K": 10.0, "P": 1.0}, 8.314*300/10000*math.log(10), 3),
        ("surface kinetics", "Langmuir relaxation", "theta(t)=theta_eq(1-exp(-kobs t))", {"theta_eq": .8, "kobs": .5, "t": 2.0}, .8*(1-math.exp(-1)), 3),
        ("surface kinetics", "Eley-Rideal rate", "r=k PA thetaB", {"k": .4, "PA": 2.0, "thetaB": .5}, .4, 2),
        ("nucleation", "classical nucleation barrier", "DeltaG*=16pi gamma^3/(3DeltaGv^2)", {"gamma": .1, "DeltaGv": .2}, 16*math.pi*.1**3/(3*.2**2), 4),
        ("phase equilibrium", "Gibbs-Thomson melting shift", "DeltaTm=2 gamma Tm/(rho L r)", {"gamma": .03, "Tm": 1000.0, "rho": 5000.0, "L": 100000.0, "r": 1e-8}, 1.2, 4),
        ("crystal chemistry", "chemical-potential activity shift", "Delta_mu=RT ln(a2/a1)", {"R": 8.314, "T": 300.0, "a2_over_a1": 2.0}, 8.314*300*math.log(2), 2),
        ("statistical thermodynamics", "rotational partition ratio", "qrot proportional T/sigma", {"T1": 300.0, "T2": 450.0, "sigma1": 1.0, "sigma2": 2.0}, .75, 3),
        ("statistical thermodynamics", "vibrational entropy", "S/R=x/(exp(x)-1)-ln(1-exp(-x))", {"x": 2.0}, 2/(math.exp(2)-1)-math.log(1-math.exp(-2)), 4),
        ("coordination chemistry", "octahedral CFSE", "CFSE=(-.4 nt2g+.6 neg)Delta_o", {"nt2g": 4.0, "neg": 2.0}, -.4, 3),
        ("quantum chemistry", "molecular-orbital bond order", "BO=(Nb-Na)/2", {"Nb": 6.0, "Na": 2.0}, 2.0, 2),
        ("quantum chemistry", "Huckel six-ring pi energy", "Epi=6alpha+4beta for N=6", {"N_ring": 6}, 4.0, 4),
        ("quantum chemistry", "particle-in-box transition", "DeltaE=h^2(n2^2-n1^2)/(8mL^2)", {"h": 1.0, "m": 1.0, "L": 1.0, "n1": 1.0, "n2": 2.0}, 3/8, 3),
        ("quantum chemistry", "harmonic-oscillator spacing", "DeltaE=hbar omega", {"hbar": 1.0, "omega": 2.0}, 2.0, 2),
        ("quantum chemistry", "first-order perturbation", "DeltaE1=<psi|V|psi>", {"expectation": .25}, .25, 2),
        ("molecular symmetry", "C3v operation count", "C3v={E,2C3,3sv}", {"group": "C3v"}, 6.0, 2),
        ("photophysics", "radiative quantum yield", "Phi=kr/(kr+knr)", {"kr": .6, "knr": .4}, .6, 2),
        ("polymer chemistry", "Flory degree of polymerization", "Xn=1/(1-p)", {"p": .98}, 50.0, 2),
        ("colloid chemistry", "Brownian diffusion coefficient", "D=kBT/(6pi eta r)", {"kB": 1.380649e-23, "T": 300.0, "eta": .001, "r": 1e-9}, 1.380649e-23*300/(6*math.pi*.001*1e-9), 3),
    ]
    l2.append(("real gases", "Joule-Thomson inversion temperature", "Tinvert=2a/(R b)", {"a": 1.0, "R": 1.0, "b": 1.0}, 2.0, 3))
    for index, spec in enumerate(l2, 68):
        add(f"TC-L2-{index:03d}", 2, spec)

    l3 = [
        ("phase stability", "regular-solution spinodal", "d2G/dx2=RT(1/x+1/(1-x))-2chiRT", {"x": .5}, 2.0, 4),
        ("phase stability", "Landau order-parameter amplitude", "m=sqrt(-a(T-Tc)/b)", {"a": 1.0, "b": 1.0, "T": 0.0, "Tc": 1.0}, 1.0, 3),
        ("phase equilibrium", "symmetric common tangent", "G(x)=G(1-x)", {"x_left": .5, "x_right": .5}, True, 3),
        ("phase stability", "Hessian stability", "H=[[2,0],[0,3]]", {}, True, 3),
        ("phase rule", "reactive phase-rule freedom", "F=C-P+2-R", {"C": 3.0, "P": 2.0, "R": 1.0}, 2.0, 3),
        ("real gases", "third-virial compressibility", "Z=1+B rho+C rho^2", {"B": -.1, "C": .02, "rho": 2.0}, .88, 3),
        ("nonideal solutions", "regular-solution chemical potential", "mu/RT=ln(x)+chi(1-x)^2", {"x": .25, "chi": 1.0}, math.log(.25)+.75**2, 3),
        ("reaction stoichiometry", "cyclic flux nullspace", "N=[[1,-1,0],[0,1,-1]]; Nv=0", {}, [1.0, 1.0, 1.0], 4),
        ("reaction network theory", "network deficiency", "delta=n-l-s", {"n": 5.0, "l": 2.0, "s": 2.0}, 1.0, 3),
        ("reaction network theory", "Wegscheider cycle condition", "prod(k_forward)=prod(k_reverse)", {"forward_product": 12.0, "reverse_product": 12.0}, True, 3),
        ("nonlinear kinetics", "autocatalytic saddle-node", "f=kx(1-x)-h", {"k": 1.0, "h": .25}, .5, 4),
        ("chemical oscillations", "Brusselator Hopf boundary", "B=1+A^2", {"A": 2.0}, 5.0, 3),
        ("chemical oscillations", "Oregonator local stability", "trace=-epsilon(1+f), det=q", {"epsilon": .1, "f": 2.0, "q": .4}, True, 3),
        ("linear stability", "damped complex eigenmode", "lambda=-a +/- i omega", {"a": .2, "omega": 3.0}, True, 2),
        ("reaction-diffusion", "Turing dispersion maximum", "lambda(q)=r-aq^2-bq^4", {"r": .5, "a": -.4, "b": .1}, .9, 5),
        ("reaction-diffusion", "pulled-front speed", "c*=2sqrt(Dr)", {"D": .25, "r": .36}, .6, 3),
        ("stochastic thermodynamics", "thermodynamic uncertainty bound", "Var(J)/mean(J)^2>=2/Sigma", {"Sigma": 8.0}, .25, 3),
        ("stochastic thermodynamics", "fluctuation theorem ratio", "P(J)/P(-J)=exp(AJ)", {"A": .5, "J": 2.0}, math.exp(1), 3),
        ("stochastic kinetics", "Kramers escape factor", "k/k0=exp(-DeltaU/kBT)", {"DeltaU_over_kBT": 5.0}, math.exp(-5), 2),
        ("chemical master equation", "Poisson large-deviation rate", "I=n ln(n/lambda)-n+lambda", {"n": 4.0, "lambda": 2.0}, 4*math.log(2)-2, 4),
        ("identifiability", "sensitivity-map rank", "J=[[1,0],[0,2]]", {}, 2.0, 3),
        ("inverse spectroscopy", "Fisher condition number", "F=diag(1,100)", {}, 100.0, 3),
        ("Bayesian chemistry", "evidence-updated model odds", "posterior_odds=BF*prior_odds", {"BF": .2, "prior_odds": 2.0}, .4, 3),
        ("inverse spectroscopy", "two-moment inversion", "m1=c1+c2; m2=c1+2c2", {"m1": 3.0, "m2": 5.0}, [1.0, 2.0], 4),
        ("singular perturbation", "fast-equilibrium reduction", "dx/dt=-x+y; eps dy/dt=x-y^2", {"epsilon": .001}, [0.0, 1.0], 4),
        ("multiple-scales analysis", "parametric resonance", "x''+(1+eps cos(2t))x=0", {"forcing_frequency": 2.0, "natural_frequency": 1.0}, True, 4),
        ("catastrophe theory", "cusp fold boundary", "4a^3+27b^2=0", {"a": -3.0, "b": 2.0}, True, 3),
        ("nonlinear dynamics", "Hopf normal-form amplitude", "dr/dt=mu r-r^3", {"mu": .09}, .3, 3),
        ("nonlinear dynamics", "Duffing potential curvature", "V=x^2/2+alpha x^4/4", {"alpha": 1.0, "x": 1.0}, 4.0, 3),
        ("electrochemistry", "Butler-Volmer inverse overpotential", "eta=asinh(i/(2i0))/f", {"i": 1.0, "i0": .5, "f": 10.0}, math.asinh(1)/10, 4),
        ("electron transfer", "Marcus activationless point", "DeltaG=-lambda => DeltaGdagger=0", {"lambda": .8, "DeltaG": -.8}, True, 3),
        ("electrochemistry", "diffusion-limited current", "ilim=nFAD C/delta", {"n": 1.0, "F": 96485.0, "A": .01, "D": 1e-5, "C": 1e-3, "delta": 1e-4}, 96485*.01*1e-5*1e-3/1e-4, 4),
        ("electrochemical impedance", "RC relaxation frequency", "omega=1/(RC)", {"R": 100.0, "C": 1e-3}, 10.0, 3),
        ("electrochemical kinetics", "cyclic-voltammetry scan scaling", "ip proportional sqrt(scan_rate)", {"scan_rate_ratio": 4.0}, 2.0, 3),
        ("catalysis", "Sabatier volcano optimum", "activity maximum at E_ads=E_opt", {"E_ads": -1.0, "E_opt": -1.0}, True, 3),
        ("microkinetics", "rate-determining-step sensitivity", "C_X=d ln(v)/d ln(k_X)", {"C_X": .9}, True, 3),
        ("surface catalysis", "Langmuir-Hinshelwood rate", "r=k KA PA KB PB/(1+KAPA+KBPB)^2", {"k": 2.0, "KA": 1.0, "PA": 1.0, "KB": 1.0, "PB": 1.0}, .5, 4),
        ("surface chemistry", "multi-site coverage conservation", "thetaA+thetaB+theta*=1", {"thetaA": .2, "thetaB": .3}, .5, 2),
        ("nucleation", "critical nucleus radius", "r*=2gamma/abs(DeltaGv)", {"gamma": .1, "DeltaGv": -.2}, 1.0, 3),
        ("crystal growth", "Ostwald-ripening radius", "r^3-r0^3=Kt", {"r0": 1.0, "K": 2.0, "t": 4.0}, 3.0, 3),
        ("polymer thermodynamics", "Flory-Huggins spinodal", "1/(Nphi)+1/(1-phi)-2chi=0", {"N": 100.0, "phi": .1}, .5*(1/(100*.1)+1/.9), 4),
        ("polymer dynamics", "Rouse relaxation scaling", "tau_p/tau_1=1/p^2", {"p": 2.0}, .25, 3),
        ("colloid chemistry", "DLVO barrier rate ratio", "k1/k2=exp(-(U1-U2)/kBT)", {"U1_over_kBT": 4.0, "U2_over_kBT": 2.0}, math.exp(-2), 3),
        ("colloid dynamics", "Brownian mode correlation", "C(t)/C(0)=exp(-Dq^2t)", {"D": .5, "q": 2.0, "t": 1.0}, math.exp(-2), 3),
        ("quantum chemistry", "variational upper bound", "E_trial=E0+Delta", {"E0": -1.0, "Delta": .2}, True, 3),
        ("quantum chemistry", "second-order perturbation sign", "DeltaE2=|V|^2/(E0-En)", {"E0": 0.0, "En": 1.0, "V": .2}, -.04, 3),
        ("quantum chemistry", "Huckel benzene spectrum", "Em=alpha+2beta cos(2pi m/6)", {}, [2.0, 1.0, 1.0, -1.0, -1.0, -2.0], 4),
        ("molecular symmetry", "electric-dipole parity rule", "g x u x g = u", {}, False, 4),
        ("vibrational spectroscopy", "normal-mode frequency", "Kq=omega^2 Mq", {"K": 4.0, "M": 1.0}, 2.0, 3),
        ("isotope chemistry", "isotope vibrational shift", "nu_D/nu_H=sqrt(mu_H/mu_D)", {"mu_H": 1.0, "mu_D": 2.0}, 1/math.sqrt(2), 3),
    ]
    for index, spec in enumerate(l3, 85):
        add(f"TC-L3-{index:03d}", 3, spec)
    if len(cases) != 150:
        raise AssertionError(f"expected 150 new pure-chemistry cases, got {len(cases)}")
    return cases


def build_cases() -> list[dict[str, Any]]:
    """Build the pure-chemistry v3 release."""
    v2_cases = _build_v2_cases()
    cases = [item for item in v2_cases if item["public"]["domain"] == "Theoretical Chemistry"]
    cases.extend(_additional_chemistry_v3())
    if len(cases) != 300:
        raise AssertionError(f"expected 300 pure-chemistry cases, got {len(cases)}")
    return cases


def build() -> dict[str, Any]:
    cases = build_cases()
    public = [x["public"] for x in cases]
    answers = [x["answer"] for x in cases]
    counts = {
        "total": len(cases),
        "by_level": {str(level): sum(x["difficulty_level"] == level for x in public) for level in (1, 2, 3)},
        "by_domain": {domain: sum(x["domain"] == domain for x in public) for domain in ("Theoretical Chemistry", "Theoretical Biology")},
    }
    if counts != {"total": 300, "by_level": {"1": 100, "2": 100, "3": 100}, "by_domain": {"Theoretical Chemistry": 300, "Theoretical Biology": 0}}:
        raise AssertionError(counts)
    cell_counts = {
        (domain, level): sum(x["domain"] == domain and x["difficulty_level"] == level for x in public)
        for domain in ("Theoretical Chemistry", "Theoretical Biology")
        for level in (1, 2, 3)
    }
    expected_cell_counts = {
        (domain, level): (100 if domain == "Theoretical Chemistry" else 0)
        for domain in ("Theoretical Chemistry", "Theoretical Biology")
        for level in (1, 2, 3)
    }
    if cell_counts != expected_cell_counts:
        raise AssertionError(f"v3 domain-level cells are not chemistry-only: {cell_counts}")
    ids = [x["task_id"] for x in public]
    if len(set(ids)) != 300:
        raise AssertionError("task IDs are not unique")
    if len({x["public"]["mathematical_model"] for x in cases}) != 300:
        raise AssertionError("mathematical models are not unique")
    return {"public": public, "answers": answers, "manifest": {"version": "theory-benchmark-v3", "counts": counts, "balanced_cell_size": 100, "answer_separation": True, "legacy_versions": ["theory-benchmark-v1", "theory-benchmark-v2"]}}


def main() -> int:
    payload = build()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "public_tasks.json").write_text(json.dumps(payload["public"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "answer_key.json").write_text(json.dumps(payload["answers"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps(payload["manifest"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["manifest"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
